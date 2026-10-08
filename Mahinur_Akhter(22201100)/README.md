# UAP CSE 433 - Peer-to-Peer Network

## Communication and File Sharing

A lightweight peer-to-peer communication application implemented in Python using TCP sockets and threads.

This project follows the requirements of the UAP CSE 433 Peer-to-Peer Network Programming Assignment.

## Features

- Each peer acts as both a TCP server and TCP client.
- Peer startup with a peer name and listening port.
- Direct peer-to-peer TCP connections.
- HELLO / HELLO_ACK peer identification handshake.
- Connected peer list.
- Text messaging.
- Binary file transfer.
- Supports ordinary files such as TXT, images, audio, video, PDF, ZIP, and other binary files.
- Large files are transferred in 64 KB chunks.
- Multiple peers can be connected concurrently using threads.
- Received files are stored in `downloads/`.
- Basic error handling for invalid input, connection failures, missing files, and peer disconnections.
- Simple Tkinter graphical user interface.
- No central server is used.

## Requirements

- Python 3.9 or later
- Tkinter
- Built-in Python libraries: `socket`, `threading`, `json`, `struct`, `uuid`, etc.
- No third-party packages are required.

## Project Structure

```text
P2P_Network/
|
|-- main.py
|-- p2p_node.py
|-- protocol.py
|-- requirements.txt
|-- README.md
|
`-- downloads/
```

## Installation / Setup

1. Install Python 3.9 or later.
2. Extract the project ZIP.
3. Open a terminal in the project directory.
4. Run:

```bash
python main.py
```

## How to Run Two Peers on One Computer

### Peer A

Start:

- Name: Alice
- Port: 5000

### Peer B

Run a second copy of the program:

- Name: Bob
- Port: 5001

In Bob's window enter:

- Remote IP: `127.0.0.1`
- Remote Port: `5000`

Click **Connect**.

The connected peer should appear in the Connected Peers list.

## How to Run on Two Computers

Connect both computers to the same Wi-Fi/LAN.

Example:

Computer A:
- IP: `192.168.1.10`
- Port: `5000`

Computer B:
- IP: `192.168.1.11`
- Port: `5001`

Start both peers. From Computer B, connect to:

```text
192.168.1.10:5000
```

If Windows Firewall asks for permission, allow Python on the appropriate private network.

## How to Send a Text Message

1. Start the peer.
2. Connect to another peer.
3. Select the peer from **Connected Peers**.
4. Type a message in **Send Text**.
5. Click **Send**.

## How to Transfer a File

1. Connect to another peer.
2. Select the destination peer.
3. Click **Choose File & Send**.
4. Select any ordinary file.
5. The receiver stores the file inside:

```text
downloads/
```

The protocol treats files as binary data, so separate transfer implementations are not needed for images, audio, video, PDFs, ZIP files, etc.

## Communication Protocol

Messages use application-level framing:

```text
[4-byte length][JSON payload]
```

For a file:

```text
[4-byte length][JSON file metadata][raw file bytes]
```

Example text message:

```json
{
  "type": "text",
  "sender_id": "a83f21c4",
  "sender_name": "Alice",
  "message": "Hello Bob!"
}
```

Example file metadata:

```json
{
  "type": "file",
  "sender_id": "a83f21c4",
  "sender_name": "Alice",
  "filename": "photo.jpg",
  "filesize": 2456789
}
```

The receiver uses the declared file size to read exactly the expected number of bytes.

## HELLO Handshake

When a peer connects, the peers exchange identity information.

HELLO:

```json
{
  "type": "hello",
  "peer_id": "a83f21c4",
  "peer_name": "Alice",
  "port": 5000
}
```

HELLO_ACK:

```json
{
  "type": "hello_ack",
  "peer_id": "92bd71e3",
  "peer_name": "Bob",
  "port": 5001
}
```

## Testing Checklist

### Test 1 - Same Computer

Run two application instances.

Test:
- Connection
- Text message
- Image transfer
- Audio transfer
- Video transfer

### Test 2 - Two Computers

Use two computers connected to the same LAN/Wi-Fi.

Test:
- Direct TCP connection
- Text messaging
- File transfer

### Test 3 - Multiple Peers

Use at least three peers:

- Alice: 5000
- Bob: 5001
- Charlie: 5002

Test:
- Alice ↔ Bob
- Bob ↔ Charlie
- Charlie ↔ Alice
- File transfer between different pairs

## Error Handling

The application handles common cases including:

- Invalid port
- Connection refused
- Peer not running
- Unexpected peer disconnection
- Missing file
- Invalid file size
- Sending without selecting a peer
- Empty messages

## Assignment Scope

This project intentionally does not implement:

- Blockchain
- Cryptocurrency
- Smart contracts
- Proof of Work / Proof of Stake
- Distributed consensus
- DHT
- BitTorrent
- NAT traversal
- WebRTC
- End-to-end encryption
- Authentication
- Database systems
- Cloud deployment
- Complex routing
- File deduplication
- File chunk recovery

## Viva Preparation

Important questions include:

1. What is the difference between a client and a server?
2. Why can one peer act as both client and server?
3. What is the purpose of an IP address?
4. What is the purpose of a port number?
5. Why do different peers need different ports on one computer?
6. What happens when `connect()` is called?
7. What happens when `accept()` is called?
8. Why is TCP used instead of UDP?
9. Why are threads used?
10. What is the purpose of the HELLO message?
11. What is message framing?
12. Why can one `recv()` call not be assumed to contain one complete message?
13. Why is file metadata sent before file data?
14. Why are files transferred in chunks?
15. How does the receiver know that a file transfer has finished?
16. What happens if the other peer disconnects?
17. Where are received files stored?
18. Is there a central server?
19. What would happen if a traditional central server went offline?
20. What additional challenges exist in a large-scale Internet P2P system?

## Running Command

```bash
python main.py
```

## Submission

Rename the project folder according to the assignment's required format, for example:

```text
22101001_3A_P2P_Assignment/
```

Then submit it as a ZIP file.
