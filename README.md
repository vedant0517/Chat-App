# Real-Time Chat Application

Python socket-based chat application with a Tkinter desktop client, SQLite-backed authentication, multi-room messaging, admin controls, and a polished cyber-style UI.

## Overview

This project includes:

- `server.py` for the threaded TCP chat server
- `client_gui.py` for the desktop chat client
- `database.py` for SQLite persistence

The app supports registration and login, public room chat, direct messages, typing indicators, read receipts, file sharing, chat history, and admin moderation commands.

## Features

- Multi-client chat over TCP sockets
- SQLite-backed user accounts and persistent chat history
- Room-based messaging with `#general` as the default room
- Private messaging with `/msg`
- Password changes with `/passwd`
- Typing indicators and read receipts
- File sharing up to 5 MB
- Inline image preview when `Pillow` is installed
- Search inside chat with `Ctrl+F`
- Dark/light theme toggle
- Admin commands for kick, ban, unban, log viewing, and clearing history
- Client-side SHA-256 password hashing
- Simple XOR message obfuscation for chat payloads

## Project Structure

```text
Chat Application/
|-- server.py
|-- client_gui.py
|-- database.py
|-- chat_database.db   # auto-created at runtime
|-- .gitignore
`-- README.md
```

## Requirements

- Python 3.10 or newer
- Standard library modules only for the core app

Optional packages:

- `Pillow` for inline image previews and tray icon image support
- `pystray` for minimize-to-tray support

Install the optional packages with:

```bash
pip install pillow pystray
```

## Quick Start

### 1. Start the server

```bash
cd "d:\Project\Chat Application"
python server.py
```

Default server settings:

- Host: `0.0.0.0`
- Port: `12345`
- Admin username: `admin`

### 2. Launch one or more clients

Open a separate terminal for each client:

```bash
python client_gui.py
```

Use the client to:

- register a new user account
- log in with an existing account
- chat with other connected users in the same room

## Commands

Type these in the client message box:

| Command | Description |
|---|---|
| `/msg <username> <message>` | Send a private message |
| `/join #room` | Switch to another room |
| `/users` | Refresh the online user list |
| `/passwd <new_password>` | Change your password |
| `/help` | Show available commands |
| `/exit` | Disconnect from the server |
| `/kick <user>` | Admin: disconnect a user |
| `/ban <user>` | Admin: ban a user |
| `/unban <user>` | Admin: remove a ban |
| `/log` | Admin: view recent connection log entries |
| `/clearall` | Admin: clear stored chat history for everyone |

## Persistence

The application uses SQLite and creates `chat_database.db` automatically.

Stored data includes:

- registered users
- chat history
- banned users

You can override the database file location with the `CHATAPP_DB_FILE` environment variable.

## Notes

- The client connects to `127.0.0.1:12345` by default.
- If you change the port, update both [server.py](D:/Project/Chat%20Application/server.py) and [client_gui.py](D:/Project/Chat%20Application/client_gui.py).
- The encryption used here is a simple XOR-based scheme intended for a college/demo project, not production security.
- Passwords are hashed with SHA-256 before being sent.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Connection refused` | Start `server.py` before opening the client |
| Port already in use | Change `PORT` in both the server and client files |
| Image previews do not appear | Install `Pillow` |
| Minimize-to-tray does not work | Install both `Pillow` and `pystray` |
| Login keeps failing after repeated attempts | Wait for the rate-limit window to reset |

## Tech Stack

- Python
- `socket`
- `threading`
- `tkinter`
- `sqlite3`
- `hashlib`
- `json`
- `pystray` and `Pillow` for optional GUI enhancements
