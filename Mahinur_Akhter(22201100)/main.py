"""
GUI entry point for the UAP CSE 433 P2P Network Assignment.

Run:
    python main.py
"""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from p2p_node import P2PNode


class P2PApp:
    def __init__(self, root):
        self.root = root
        self.root.title("UAP CSE 433 - Peer-to-Peer Network")
        self.root.geometry("1000x720")
        self.root.minsize(900, 650)

        self.node = None
        self.ui_queue = queue.Queue()
        self.peer_ids = {}

        self._build_ui()
        self.root.after(100, self._process_ui_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        title = ttk.Label(
            self.root,
            text="Peer-to-Peer Network - Communication and File Sharing",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(pady=(12, 6))

        subtitle = ttk.Label(
            self.root,
            text="CSE 433 | TCP Sockets | Python",
            font=("Segoe UI", 10),
        )
        subtitle.pack(pady=(0, 10))

        config = ttk.LabelFrame(self.root, text="My Peer")
        config.pack(fill="x", padx=14, pady=7)

        ttk.Label(config, text="Name:").grid(row=0, column=0, padx=7, pady=10)
        self.name_var = tk.StringVar(value="Alice")
        ttk.Entry(config, textvariable=self.name_var, width=20).grid(
            row=0, column=1, padx=7
        )

        ttk.Label(config, text="Port:").grid(row=0, column=2, padx=7)
        self.port_var = tk.StringVar(value="5000")
        ttk.Entry(config, textvariable=self.port_var, width=12).grid(
            row=0, column=3, padx=7
        )

        self.start_button = ttk.Button(
            config, text="Start Peer", command=self.start_peer
        )
        self.start_button.grid(row=0, column=4, padx=8)

        self.stop_button = ttk.Button(
            config, text="Stop", command=self.stop_peer, state="disabled"
        )
        self.stop_button.grid(row=0, column=5, padx=8)

        self.status_var = tk.StringVar(value="Status: Not running")
        ttk.Label(config, textvariable=self.status_var).grid(
            row=0, column=6, padx=10
        )

        connect = ttk.LabelFrame(self.root, text="Connect to Another Peer")
        connect.pack(fill="x", padx=14, pady=7)

        ttk.Label(connect, text="Remote IP:").grid(row=0, column=0, padx=7, pady=10)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(connect, textvariable=self.ip_var, width=22).grid(
            row=0, column=1, padx=7
        )

        ttk.Label(connect, text="Remote Port:").grid(row=0, column=2, padx=7)
        self.remote_port_var = tk.StringVar(value="5001")
        ttk.Entry(connect, textvariable=self.remote_port_var, width=12).grid(
            row=0, column=3, padx=7
        )

        ttk.Button(connect, text="Connect", command=self.connect_peer).grid(
            row=0, column=4, padx=8
        )

        middle = ttk.Frame(self.root)
        middle.pack(fill="both", expand=True, padx=14, pady=7)

        peer_frame = ttk.LabelFrame(middle, text="Connected Peers")
        peer_frame.pack(side="left", fill="y", padx=(0, 7))

        self.peer_list = tk.Listbox(peer_frame, width=31, height=20)
        self.peer_list.pack(fill="both", expand=True, padx=8, pady=8)

        event_frame = ttk.LabelFrame(middle, text="Messages / Events")
        event_frame.pack(side="left", fill="both", expand=True)

        self.log = tk.Text(event_frame, wrap="word", state="disabled")
        self.log.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        log_scroll = ttk.Scrollbar(
            event_frame, orient="vertical", command=self.log.yview
        )
        log_scroll.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=log_scroll.set)

        message_frame = ttk.LabelFrame(self.root, text="Send Text")
        message_frame.pack(fill="x", padx=14, pady=7)

        self.message_var = tk.StringVar()
        message_entry = ttk.Entry(message_frame, textvariable=self.message_var)
        message_entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        message_entry.bind("<Return>", lambda event: self.send_text())

        ttk.Button(
            message_frame, text="Send", command=self.send_text
        ).pack(side="right", padx=8)

        file_frame = ttk.Frame(self.root)
        file_frame.pack(fill="x", padx=14, pady=(0, 12))

        ttk.Button(
            file_frame, text="Choose File & Send", command=self.send_file
        ).pack(side="left")

        ttk.Label(
            file_frame,
            text="Received files are saved in the downloads/ folder.",
        ).pack(side="left", padx=12)

    def _put_ui(self, action, value=None):
        self.ui_queue.put((action, value))

    def _process_ui_queue(self):
        try:
            while True:
                action, value = self.ui_queue.get_nowait()
                if action == "event":
                    self._append_log(value)
                elif action == "peers":
                    self.refresh_peers()
                elif action == "message":
                    sender, peer_id, message = value
                    self._append_log(f"{sender} -> You: {message}")
        except queue.Empty:
            pass
        self.root.after(100, self._process_ui_queue)

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_peer(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Invalid Input", "Enter a peer name.")
            return

        try:
            port = int(self.port_var.get())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Port must be 1-65535.")
            return

        try:
            self.node = P2PNode(
                peer_name=name,
                port=port,
                event_callback=lambda msg: self._put_ui("event", msg),
                message_callback=lambda sender, pid, msg: self._put_ui(
                    "message", (sender, pid, msg)
                ),
                peer_callback=lambda: self._put_ui("peers"),
            )
            self.node.start()
            self.status_var.set(f"Status: Running on port {port}")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
        except Exception as exc:
            self.node = None
            messagebox.showerror("Start Error", str(exc))

    def stop_peer(self):
        if self.node:
            self.node.stop()
            self.node = None
        self.peer_ids.clear()
        self.peer_list.delete(0, "end")
        self.status_var.set("Status: Not running")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def connect_peer(self):
        if not self.node:
            messagebox.showerror("Not Running", "Start your peer first.")
            return

        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showerror("Invalid Input", "Enter an IP address.")
            return

        try:
            port = int(self.remote_port_var.get())
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Remote port must be 1-65535.")
            return

        self.node.connect_to_peer(ip, port)

    def _selected_peer_id(self):
        selection = self.peer_list.curselection()
        if not selection:
            return None
        return self.peer_ids.get(selection[0])

    def refresh_peers(self):
        if not self.node:
            self.peer_list.delete(0, "end")
            self.peer_ids.clear()
            return

        peers = self.node.get_peers()
        self.peer_list.delete(0, "end")
        self.peer_ids.clear()

        for index, peer in enumerate(peers):
            label = f"{peer.name} [{peer.peer_id}]  {peer.ip}:{peer.port}"
            self.peer_list.insert("end", label)
            self.peer_ids[index] = peer.peer_id

    def send_text(self):
        if not self.node:
            messagebox.showerror("Not Running", "Start your peer first.")
            return

        peer_id = self._selected_peer_id()
        if not peer_id:
            messagebox.showwarning("Select Peer", "Select a connected peer.")
            return

        message = self.message_var.get().strip()
        if not message:
            return

        def worker():
            try:
                self.node.send_text(peer_id, message)
                self._put_ui("clear_message")
            except Exception as exc:
                self._put_ui("event", f"[ERROR] {exc}")

        threading.Thread(target=worker, daemon=True).start()
        self.message_var.set("")

    def send_file(self):
        if not self.node:
            messagebox.showerror("Not Running", "Start your peer first.")
            return

        peer_id = self._selected_peer_id()
        if not peer_id:
            messagebox.showwarning("Select Peer", "Select a connected peer.")
            return

        path = filedialog.askopenfilename(title="Select a file to send")
        if not path:
            return

        def worker():
            try:
                self._put_ui("event", f"[SENDING] {path}")
                self.node.send_file(peer_id, path)
            except Exception as exc:
                self._put_ui("event", f"[ERROR] {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def on_close(self):
        if self.node:
            self.node.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = P2PApp(root)
    root.mainloop()
