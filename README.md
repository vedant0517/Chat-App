# 💬 Real-Time Chat Application
**College Mini Project — Python Socket Programming + Tkinter GUI**

---

## 📁 File Structure

```
Chat Application/
├── server.py          ← Server (run this first)
├── client_gui.py      ← GUI Client (run multiple instances)
├── database.py        ← SQLite database layer (auto-creates chat_database.db)
├── chat_database.db   ← Auto-created: stores users, messages, banned list
└── README.md
```

> **Note:** `users.json` and `chat_history.json` are legacy files from an older version.
> The app now uses SQLite (`chat_database.db`) for all persistence.

---

## 🚀 How to Run

### Step 1 — Start the Server

Open a terminal and run:

```bash
cd "d:\Project\Chat Application"
python server.py
```

Expected output:
```
==================================================
  CYBER CHAT SERVER v3.0
  Listening on 0.0.0.0:12345
  Connect from clients using: 127.0.0.1:12345
  Admin user: 'admin'
==================================================
```

### Step 2 — Launch Client(s)

Open one or more **separate terminals** and run:

```bash
python client_gui.py
```

- First time: click **Register** to create an account
- Next time: click **Login**

> Launch multiple clients to test messaging between users.

---

## 💡 Commands (type in the message box)

| Command | Action |
|---|---|
| `/msg username text` | Send a private message to a user |
| `/join #room` | Switch to a different chat room |
| `/users` | Refresh the active users list |
| `/passwd <new_password>` | Change your password |
| `/help` | Show available commands |
| `/exit` | Disconnect and close the app |
| `/kick <user>` | (admin) Kick a user |
| `/ban <user>` | (admin) Ban a user |
| `/unban <user>` | (admin) Unban a user |
| `/log` | (admin) View connection log |

---

## ✨ Features

| Feature | Details |
|---|---|
| **Multi-client** | Server handles unlimited simultaneous clients using threads |
| **Authentication** | Register/Login with SHA-256 hashed passwords stored in SQLite |
| **Broadcast** | Messages sent to all connected users in the same room |
| **Rooms** | `/join #room` to switch rooms; messages are isolated per room |
| **Private messaging** | `/msg username text` syntax |
| **Chat history** | Last 50 messages loaded when you join |
| **Active users sidebar** | Live-updated list of online users in current room |
| **Encryption** | XOR cipher applied to all message payloads |
| **Dark / Light mode** | Toggle with the `[ ☀ LIGHT ]` button in the header |
| **Emoji picker** | Click 😊 in the input bar |
| **Typing indicators** | Shows when other users are typing |
| **Read receipts** | ✓ upgrades to ✓✓ when the recipient reads your message |
| **File sharing** | Attach files up to 5MB; images preview inline |
| **Search** | Ctrl+F to search in chat history |
| **Admin controls** | Kick, ban, unban users; view connection log |
| **Rate limiting** | 3 failed login attempts per IP per 60s → lockout |
| **Disconnect handling** | Graceful join/leave notifications; GUI stays stable |

---

## 🛡️ Security Notes

- Passwords are **SHA-256 hashed** on the client before being sent
- Messages are **XOR-encrypted** in transit (symmetric key shared between client files)
- Banned users are stored in SQLite and cannot log in even after reconnecting
- For production: use TLS/SSL and bcrypt — this is a college demo project

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| `Connection refused` | Make sure `server.py` is running first |
| `User already logged in` | Close duplicate client window |
| `Username taken` | Choose a different username |
| GUI freezes | Should not happen; uses threading + `root.after()` |
| Port in use | Change `PORT = 12345` in both `server.py` and `client_gui.py` |
| File open fails on Linux/Mac | Fixed — uses `xdg-open` / `open` on non-Windows |

---

## 🔧 Tech Stack

- **Python 3.10+** (no extra packages required for core features)
- `socket` — TCP networking
- `threading` — concurrent client handling
- `sqlite3` — persistent user auth and message history
- `tkinter` — cross-platform GUI
- `json` / `hashlib` — serialization and password hashing
- `pystray` + `Pillow` — optional system tray support (install with pip if desired)
