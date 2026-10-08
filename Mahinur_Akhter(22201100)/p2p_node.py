"""
P2P networking layer.

Every peer is both:
1. A TCP server that accepts incoming peer connections.
2. A TCP client that initiates outgoing peer connections.

Features required by the assignment:
- HELLO / HELLO_ACK handshake
- Text messaging
- Binary file transfer
- Multiple peers using threads
- Basic network/file error handling
"""

from __future__ import annotations

import os
import socket
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from protocol import recv_exact, recv_message, send_message


BUFFER_SIZE = 64 * 1024


@dataclass
class PeerConnection:
    peer_id: str
    name: str
    ip: str
    port: int
    sock: socket.socket
    send_lock: threading.Lock


class P2PNode:
    def __init__(
        self,
        peer_name: str,
        port: int,
        downloads_dir: str = "downloads",
        event_callback: Optional[Callable[[str], None]] = None,
        message_callback: Optional[Callable[[str, str, str], None]] = None,
        peer_callback: Optional[Callable[[], None]] = None,
    ):
        self.peer_id = uuid.uuid4().hex[:8]
        self.peer_name = peer_name.strip()
        self.port = int(port)
        self.downloads_dir = Path(downloads_dir)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        self.event_callback = event_callback
        self.message_callback = message_callback
        self.peer_callback = peer_callback

        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.peers: dict[str, PeerConnection] = {}
        self.peers_lock = threading.RLock()

    def _event(self, text: str):
        if self.event_callback:
            self.event_callback(text)

    def _notify_peers_changed(self):
        if self.peer_callback:
            self.peer_callback()

    def start(self):
        if self.running:
            raise RuntimeError("Peer is already running.")

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen()
            self.server_socket.settimeout(1.0)
            self.running = True
        except OSError as exc:
            if self.server_socket:
                self.server_socket.close()
            self.server_socket = None
            raise RuntimeError(f"Could not start peer: {exc}") from exc

        threading.Thread(target=self._accept_loop, daemon=True).start()
        self._event(
            f"[STARTED] {self.peer_name} [{self.peer_id}] listening on port {self.port}"
        )

    def stop(self):
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        with self.peers_lock:
            peers = list(self.peers.values())
            self.peers.clear()

        for peer in peers:
            try:
                peer.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                peer.sock.close()
            except OSError:
                pass

        self._notify_peers_changed()
        self._event("[STOPPED] Peer stopped.")

    def _accept_loop(self):
        while self.running and self.server_socket:
            try:
                conn, address = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            threading.Thread(
                target=self._handle_connection,
                args=(conn, address, False),
                daemon=True,
            ).start()

    def connect_to_peer(self, ip: str, port: int):
        if not self.running:
            raise RuntimeError("Start your peer before connecting.")

        ip = ip.strip()
        port = int(port)

        def worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            try:
                sock.connect((ip, port))
                sock.settimeout(None)
                self._event(f"[CONNECT] Connected to {ip}:{port}")
                self._handle_connection(sock, (ip, port), True)
            except (OSError, ValueError, ConnectionError) as exc:
                try:
                    sock.close()
                except OSError:
                    pass
                self._event(f"[ERROR] Connection failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _handle_connection(self, sock: socket.socket, address, outgoing: bool):
        remote_ip, remote_port = address[0], int(address[1])

        try:
            # Outgoing peer sends HELLO first. Incoming peer waits for HELLO.
            if outgoing:
                self._send_hello(sock)
                hello = recv_message(sock)
                if hello.get("type") != "hello_ack":
                    raise ValueError("Expected hello_ack.")
                peer = self._peer_from_hello(hello, sock, remote_ip, remote_port)
            else:
                hello = recv_message(sock)
                if hello.get("type") != "hello":
                    raise ValueError("Expected hello.")
                peer = self._peer_from_hello(hello, sock, remote_ip, remote_port)
                self._send_hello_ack(sock)

            self._register_peer(peer)

            while self.running:
                message = recv_message(sock)
                self._process_message(peer, message)

        except (ConnectionError, OSError, ValueError, UnicodeError) as exc:
            if self.running:
                self._event(
                    f"[DISCONNECTED] {remote_ip}:{remote_port} ({exc})"
                )
        finally:
            self._remove_socket(sock)

    def _send_hello(self, sock):
        send_message(
            sock,
            {
                "type": "hello",
                "peer_id": self.peer_id,
                "peer_name": self.peer_name,
                "port": self.port,
            },
        )

    def _send_hello_ack(self, sock):
        send_message(
            sock,
            {
                "type": "hello_ack",
                "peer_id": self.peer_id,
                "peer_name": self.peer_name,
                "port": self.port,
            },
        )

    def _peer_from_hello(self, message, sock, ip, remote_port):
        peer_id = str(message.get("peer_id", "")).strip()
        peer_name = str(message.get("peer_name", "")).strip()
        port = int(message.get("port", remote_port))

        if not peer_id or not peer_name:
            raise ValueError("Invalid HELLO information.")
        if peer_id == self.peer_id:
            raise ValueError("Cannot connect to the same peer.")

        return PeerConnection(
            peer_id=peer_id,
            name=peer_name,
            ip=ip,
            port=port,
            sock=sock,
            send_lock=threading.Lock(),
        )

    def _register_peer(self, peer: PeerConnection):
        with self.peers_lock:
            old = self.peers.get(peer.peer_id)
            if old and old.sock is not peer.sock:
                try:
                    old.sock.close()
                except OSError:
                    pass
            self.peers[peer.peer_id] = peer

        self._event(
            f"[CONNECTED] {peer.name} [{peer.peer_id}] at {peer.ip}:{peer.port}"
        )
        self._notify_peers_changed()

    def _remove_socket(self, sock):
        removed = None
        with self.peers_lock:
            for peer_id, peer in list(self.peers.items()):
                if peer.sock is sock:
                    removed = self.peers.pop(peer_id)
                    break

        try:
            sock.close()
        except OSError:
            pass

        if removed:
            self._event(f"[OFFLINE] {removed.name} [{removed.peer_id}]")
            self._notify_peers_changed()

    def _process_message(self, peer: PeerConnection, message: dict):
        msg_type = message.get("type")

        if msg_type == "text":
            text = str(message.get("message", ""))
            sender_name = str(message.get("sender_name", peer.name))
            self._event(f"{sender_name} -> You: {text}")
            if self.message_callback:
                self.message_callback(sender_name, peer.peer_id, text)

        elif msg_type == "file":
            self._receive_file(peer, message)

        elif msg_type == "hello":
            # Normally only used during the initial handshake.
            self._event(f"[INFO] HELLO received from {peer.name}")

        else:
            self._event(f"[ERROR] Unknown message type: {msg_type}")

    def _receive_file(self, peer: PeerConnection, metadata: dict):
        filename = os.path.basename(str(metadata.get("filename", "")).strip())
        try:
            filesize = int(metadata.get("filesize", -1))
        except (TypeError, ValueError):
            filesize = -1

        if not filename:
            raise ValueError("Invalid file name.")
        if filesize < 0:
            raise ValueError("Invalid file size.")

        destination = self._unique_download_path(filename)

        remaining = filesize
        with destination.open("wb") as output:
            while remaining > 0:
                chunk = recv_exact(peer.sock, min(BUFFER_SIZE, remaining))
                output.write(chunk)
                remaining -= len(chunk)

        self._event(
            f"[FILE RECEIVED] {filename} ({filesize} bytes) from {peer.name}"
        )

    def _unique_download_path(self, filename: str) -> Path:
        path = self.downloads_dir / filename
        if not path.exists():
            return path

        stem = path.stem
        suffix = path.suffix
        counter = 1
        while True:
            candidate = self.downloads_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def get_peers(self) -> list[PeerConnection]:
        with self.peers_lock:
            return list(self.peers.values())

    def get_peer(self, peer_id: str) -> Optional[PeerConnection]:
        with self.peers_lock:
            return self.peers.get(peer_id)

    def send_text(self, peer_id: str, text: str):
        text = text.strip()
        if not text:
            raise ValueError("Message cannot be empty.")

        peer = self.get_peer(peer_id)
        if not peer:
            raise ValueError("Select a connected peer.")

        message = {
            "type": "text",
            "sender_id": self.peer_id,
            "sender_name": self.peer_name,
            "message": text,
        }

        try:
            with peer.send_lock:
                send_message(peer.sock, message)
        except OSError as exc:
            self._remove_socket(peer.sock)
            raise ConnectionError(f"Could not send message: {exc}") from exc

        self._event(f"You -> {peer.name}: {text}")

    def send_file(self, peer_id: str, file_path: str):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        if not path.is_file():
            raise ValueError("Selected path is not a file.")

        filesize = path.stat().st_size
        peer = self.get_peer(peer_id)
        if not peer:
            raise ValueError("Select a connected peer.")

        metadata = {
            "type": "file",
            "sender_id": self.peer_id,
            "sender_name": self.peer_name,
            "filename": path.name,
            "filesize": filesize,
        }

        try:
            with peer.send_lock:
                send_message(peer.sock, metadata)
                with path.open("rb") as file:
                    while True:
                        chunk = file.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        peer.sock.sendall(chunk)
        except OSError as exc:
            self._remove_socket(peer.sock)
            raise ConnectionError(f"File transfer failed: {exc}") from exc

        self._event(
            f"[FILE SENT] {path.name} ({filesize} bytes) -> {peer.name}"
        )
