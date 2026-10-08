"""
Application-level protocol for the UAP CSE 433 P2P Network Assignment.

Framing:
    [4-byte big-endian JSON length][JSON payload]
For file transfer:
    [framed JSON file metadata][raw file bytes]
"""

import json
import struct


HEADER_SIZE = 4
MAX_JSON_SIZE = 10 * 1024 * 1024


def encode_message(message: dict) -> bytes:
    payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if len(payload) > MAX_JSON_SIZE:
        raise ValueError("JSON message is too large.")
    return struct.pack("!I", len(payload)) + payload


def recv_exact(sock, size: int) -> bytes:
    """Receive exactly size bytes or raise ConnectionError."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(64 * 1024, size - len(data)))
        if not chunk:
            raise ConnectionError("Peer disconnected.")
        data.extend(chunk)
    return bytes(data)


def recv_message(sock) -> dict:
    """Receive one framed JSON message."""
    header = recv_exact(sock, HEADER_SIZE)
    length = struct.unpack("!I", header)[0]
    if length > MAX_JSON_SIZE:
        raise ValueError("Invalid JSON message length.")
    payload = recv_exact(sock, length)
    message = json.loads(payload.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Protocol message must be a JSON object.")
    return message


def send_message(sock, message: dict) -> None:
    sock.sendall(encode_message(message))
