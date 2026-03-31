"""
server.py — Real-Time Chat Application Server
================================================
College Mini Project | Python Socket Programming

Features:
  - SQLite-backed user auth (database.py)
  - Multi-room support  (#general default, /join #room)
  - Admin commands: /kick, /ban, /unban
  - Login rate limiting (3 fails / 60s → lockout)
  - Read receipts (✓✓)
  - /passwd password change
  - Connection log (/log command)
  - Typing indicators
  - File sharing (Base64)
  - XOR-encrypted chat
"""

import socket
import threading
import json
import datetime
import time
import sys

import database as db

# ─── Configuration ────────────────────────────────────────────────────────────
HOST        = "0.0.0.0"
PORT        = 12345
ADMIN_USER  = "admin"          # The only user with admin privileges
MAX_HISTORY = 50

# ─── Shared State ─────────────────────────────────────────────────────────────

# clients: {sock → {"username": str, "room": str, "addr": tuple}}
clients      = {}
clients_lock = threading.Lock()

# Pending read-receipt tracking: {msg_ts → sender_sock}
ack_map      = {}
ack_lock     = threading.Lock()

# Rate-limiting: {ip → [fail_timestamps]}
login_fails  = {}
fail_lock    = threading.Lock()

# Connection log
conn_log     = []
conn_log_lock = threading.Lock()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def now_ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")

def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")

def send_json(sock: socket.socket, data: dict):
    """Send a JSON object terminated by newline."""
    try:
        msg = json.dumps(data, ensure_ascii=False) + "\n"
        sock.sendall(msg.encode("utf-8"))
    except Exception as e:
        print(f"[WARN] send_json failed: {e}")


def recv_json(sock: socket.socket, buffer: list) -> dict | None:
    """
    Read one newline-terminated JSON object from the socket.
    Uses a mutable list as a per-client receive buffer.
    Returns None on connection error.
    """
    try:
        while True:
            raw = "".join(buffer)
            if "\n" in raw:
                line, remainder = raw.split("\n", 1)
                buffer.clear()
                if remainder:
                    buffer.append(remainder)
                return json.loads(line.strip())

            chunk = sock.recv(65536)
            if not chunk:
                return None
            buffer.append(chunk.decode("utf-8"))
    except Exception:
        return None


def log_event(username: str, ip: str, event: str):
    """Add an entry to the connection log."""
    with conn_log_lock:
        conn_log.append({
            "username": username,
            "ip":       ip,
            "event":    event,
            "ts":       now_iso(),
        })
        # Keep last 200 entries
        if len(conn_log) > 200:
            conn_log.pop(0)


def force_disconnect(sock: socket.socket, reason: str):
    """Tell a client it has been removed, then close the socket."""
    try:
        send_json(sock, {"type": "kicked", "reason": reason})
        time.sleep(0.05)
    except Exception:
        pass

    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass

    try:
        sock.close()
    except Exception:
        pass


# ─── Broadcast / Room Helpers ─────────────────────────────────────────────────

def broadcast(data: dict, room: str | None = None, exclude: socket.socket | None = None):
    """
    Send to all clients in the given room (or all rooms if room is None).
    """
    with clients_lock:
        targets = [
            (s, info) for s, info in clients.items()
            if s is not exclude and (room is None or info["room"] == room)
        ]
    for sock, _ in targets:
        send_json(sock, data)


def send_active_users(room: str | None = None):
    """Send the user list to all clients. If room given, send room-specific list."""
    with clients_lock:
        if room:
            user_list = sorted({
                info["username"] for s, info in clients.items()
                if info["room"] == room
            })
        else:
            user_list = sorted({info["username"] for info in clients.values()})

    if room:
        # Notify only clients in that room
        with clients_lock:
            targets = [(s, info) for s, info in clients.items() if info["room"] == room]
        for sock, _ in targets:
            send_json(sock, {"type": "users", "list": user_list, "room": room})
    else:
        broadcast({"type": "users", "list": user_list})


def get_client_info(sock: socket.socket) -> dict:
    with clients_lock:
        return clients.get(sock, {})


def get_sock_by_name(username: str) -> socket.socket | None:
    with clients_lock:
        for s, info in clients.items():
            if info["username"].lower() == username.lower():
                return s
    return None


def is_user_online(username: str) -> bool:
    with clients_lock:
        return any(
            info["username"].lower() == username.lower()
            for info in clients.values()
        )

# ─── Rate Limiter ──────────────────────────────────────────────────────────────

RATE_WINDOW = 60   # seconds
RATE_MAX    = 3    # attempts

def record_fail(ip: str) -> bool:
    """Record a failed login. Returns True if the IP should now be blocked."""
    with fail_lock:
        now = time.time()
        timestamps = login_fails.get(ip, [])
        # Purge old entries
        timestamps = [t for t in timestamps if now - t < RATE_WINDOW]
        timestamps.append(now)
        login_fails[ip] = timestamps
        return len(timestamps) > RATE_MAX

def is_rate_limited(ip: str) -> bool:
    with fail_lock:
        now = time.time()
        timestamps = login_fails.get(ip, [])
        recent = [t for t in timestamps if now - t < RATE_WINDOW]
        return len(recent) > RATE_MAX

def clear_fails(ip: str):
    with fail_lock:
        login_fails.pop(ip, None)

# ─── Client Handler ───────────────────────────────────────────────────────────

def handle_client(sock: socket.socket, addr: tuple):
    ip = addr[0]
    username = None
    buffer   = []
    room     = "#general"

    print(f"[CONNECT] {addr}")

    try:
        # ── Authentication ─────────────────────────────────────────────────────
        while True:
            data = recv_json(sock, buffer)
            if not data:
                return

            msg_type = data.get("type")

            if msg_type == "register":
                uname = data.get("username", "").strip().lower()
                phash = data.get("password_hash", "")

                if db.is_banned(uname):
                    send_json(sock, {"type": "auth_fail",
                                     "reason": "Account is banned."})
                    return

                if db.add_user(uname, phash):
                    send_json(sock, {"type": "auth_ok", "username": uname})
                    username = uname
                    log_event(username, ip, "registered")
                    break
                else:
                    send_json(sock, {"type": "auth_fail",
                                     "reason": "Username already taken."})

            elif msg_type == "login":
                uname = data.get("username", "").strip().lower()
                phash = data.get("password_hash", "")

                if db.is_banned(uname):
                    send_json(sock, {"type": "auth_fail",
                                     "reason": "⛔ Your account has been banned."})
                    log_event(uname, ip, "banned_login_attempt")
                    return

                if is_user_online(uname):
                    send_json(sock, {"type": "auth_fail",
                                     "reason": "User already logged in."})
                    return

                if is_rate_limited(ip):
                    send_json(sock, {"type": "auth_fail",
                                     "reason": "Too many failed attempts. Try again in 60s."})
                    return

                if db.verify_user(uname, phash):
                    clear_fails(ip)
                    send_json(sock, {"type": "auth_ok", "username": uname})
                    username = uname
                    log_event(username, ip, "login")
                    break
                else:
                    blocked = record_fail(ip)
                    with fail_lock:
                        recent = [t for t in login_fails.get(ip, []) if time.time() - t < RATE_WINDOW]
                    attempts_left = max(0, RATE_MAX - len(recent))
                    if blocked:
                        send_json(sock, {"type": "auth_fail",
                                         "reason": "Too many failed attempts. Try again in 60s."})
                        return
                    send_json(sock, {"type": "auth_fail",
                                     "reason": f"Wrong username or password. ({attempts_left} tries left)"})

        # ── Register client ────────────────────────────────────────────────────
        with clients_lock:
            clients[sock] = {"username": username, "room": room, "addr": addr}

        # Send chat history
        history = db.get_recent_history(MAX_HISTORY)
        if history:
            send_json(sock, {"type": "history", "messages": history})

        # Announce join
        join_msg = {
            "type": "system",
            "text": f"🟢 {username} joined {room}",
            "ts":   now_ts()
        }
        broadcast(join_msg, room=room)
        send_active_users(room=room)
        print(f"[JOIN] {username} from {addr} → {room}")

        # ── Message loop ───────────────────────────────────────────────────────
        while True:
            data = recv_json(sock, buffer)
            if not data:
                break

            msg_type = data.get("type")
            ts = now_ts()

            # ── Public message ─────────────────────────────────────────────────
            if msg_type == "message":
                text = data.get("text", "")
                current_room = get_client_info(sock).get("room", "#general")
                msg = {
                    "type": "message",
                    "from": username,
                    "text": text,
                    "ts":   ts
                }
                broadcast(msg, room=current_room)
                db.save_message(username, text, ts, datetime.date.today().isoformat())

                # Track for read receipt
                with ack_lock:
                    ack_map[ts] = sock

            # ── Read receipt ───────────────────────────────────────────────────
            elif msg_type == "read_ack":
                ack_ts = data.get("msg_ts")
                with ack_lock:
                    original_sender = ack_map.get(ack_ts)
                if original_sender:
                    send_json(original_sender, {
                        "type":   "read_receipt",
                        "msg_ts": ack_ts,
                        "by":     username
                    })

            # ── Private message ────────────────────────────────────────────────
            elif msg_type == "private":
                target = data.get("to", "")
                text   = data.get("text", "")
                target_sock = get_sock_by_name(target)
                if target_sock:
                    priv = {
                        "type": "private",
                        "from": username,
                        "to":   target,
                        "text": text,
                        "ts":   ts
                    }
                    send_json(target_sock, priv)
                    send_json(sock, priv)   # echo to sender
                else:
                    send_json(sock, {
                        "type": "system",
                        "text": f"❌ User '{target}' is not online.",
                        "ts":   ts
                    })

            # ── Typing indicator ───────────────────────────────────────────────
            elif msg_type == "typing":
                current_room = get_client_info(sock).get("room", "#general")
                broadcast({
                    "type":      "typing",
                    "from":      username,
                    "is_typing": data.get("is_typing", False)
                }, room=current_room, exclude=sock)

            # ── File sharing ───────────────────────────────────────────────────
            elif msg_type == "file":
                current_room = get_client_info(sock).get("room", "#general")
                broadcast({
                    "type":     "file",
                    "from":     username,
                    "filename": data.get("filename", "file"),
                    "data":     data.get("data", ""),
                    "ts":       ts
                }, room=current_room)

            # ── Commands ───────────────────────────────────────────────────────
            elif msg_type == "command":
                cmd = data.get("cmd", "")

                # /join #room
                if cmd == "join":
                    new_room = data.get("room", "#general").strip()
                    if not new_room.startswith("#"):
                        new_room = "#" + new_room
                    old_room = get_client_info(sock).get("room", "#general")

                    with clients_lock:
                        clients[sock]["room"] = new_room

                    broadcast({
                        "type": "system",
                        "text": f"🚪 {username} left {old_room}",
                        "ts":   ts
                    }, room=old_room)
                    send_active_users(room=old_room)

                    broadcast({
                        "type": "system",
                        "text": f"🟢 {username} joined {new_room}",
                        "ts":   ts
                    }, room=new_room)
                    send_active_users(room=new_room)

                    send_json(sock, {
                        "type": "room_change",
                        "room": new_room,
                        "ts":   ts
                    })
                    print(f"[ROOM] {username} moved to {new_room}")

                # /users
                elif cmd == "users":
                    current_room = get_client_info(sock).get("room", "#general")
                    with clients_lock:
                        user_list = sorted({
                            info["username"] for s, info in clients.items()
                            if info["room"] == current_room
                        })
                    send_json(sock, {"type": "users", "list": user_list})

                # /exit
                elif cmd == "exit":
                    print(f"[EXIT] {username} requested disconnect.")
                    break

                # /passwd — change password
                elif cmd == "passwd":
                    new_hash = data.get("new_hash", "")
                    if new_hash and db.update_password(username, new_hash):
                        send_json(sock, {"type": "system",
                                         "text": "✅ Password changed successfully.",
                                         "ts": ts})
                        log_event(username, ip, "passwd_change")
                    else:
                        send_json(sock, {"type": "system",
                                         "text": "❌ Password change failed.",
                                         "ts": ts})

                # /log — connection log (admin only)
                elif cmd == "log":
                    if username == ADMIN_USER:
                        with conn_log_lock:
                            log_snapshot = list(conn_log)
                        send_json(sock, {"type": "conn_log", "entries": log_snapshot})
                    else:
                        send_json(sock, {"type": "system",
                                         "text": "⛔ Admin only command.",
                                         "ts": ts})

                # /kick (admin only)
                elif cmd == "kick":
                    if username != ADMIN_USER:
                        send_json(sock, {"type": "system",
                                         "text": "⛔ Admin only.", "ts": ts})
                    else:
                        target = data.get("target", "")
                        t_sock = get_sock_by_name(target)
                        if t_sock:
                            force_disconnect(t_sock, "kicked by admin")
                            send_json(sock, {
                                "type": "system",
                                "text": f"✅ Kicked {target}.",
                                "ts":   ts
                            })
                            log_event(target, "", f"kicked_by_{username}")
                        else:
                            send_json(sock, {"type": "system",
                                             "text": f"❌ User '{target}' not found.",
                                             "ts": ts})

                # /ban (admin only)
                elif cmd == "ban":
                    if username != ADMIN_USER:
                        send_json(sock, {"type": "system",
                                         "text": "⛔ Admin only.", "ts": ts})
                    else:
                        target = data.get("target", "")
                        db.ban_user(target, username)
                        t_sock = get_sock_by_name(target)
                        if t_sock:
                            force_disconnect(t_sock, "banned by admin")

                        send_json(sock, {
                            "type": "system",
                            "text": f"✅ Banned {target}.",
                            "ts":   ts
                        })
                        log_event(target, "", f"banned_by_{username}")

                # /unban (admin only)
                elif cmd == "unban":
                    if username != ADMIN_USER:
                        send_json(sock, {"type": "system",
                                         "text": "⛔ Admin only.", "ts": ts})
                    else:
                        target = data.get("target", "")
                        db.unban_user(target)
                        send_json(sock, {
                            "type": "system",
                            "text": f"✅ Unbanned {target}.",
                            "ts": ts
                        })
                        log_event(target, "", f"unbanned_by_{username}")

                # /clearall (admin only, clears DB history and client screens)
                elif cmd == "clearall":
                    if username != ADMIN_USER:
                        send_json(sock, {"type": "system",
                                         "text": "⛔ Admin only.", "ts": ts})
                    else:
                        db.clear_history()
                        broadcast({"type": "clear_chat"})
                        broadcast({
                            "type": "system",
                            "text": "🧹 Chat history was cleared by admin.",
                            "ts": ts
                        })
                        log_event("", ip, f"cleared_history_by_{username}")

                else:
                    print(f"[WARN] Unknown command '{cmd}' from {username}")

            else:
                print(f"[WARN] Unknown packet type '{msg_type}' from {username}")

    except Exception as e:
        print(f"[ERROR] Exception for {addr}: {e}")

    finally:
        if username:
            with clients_lock:
                current_room = clients.get(sock, {}).get("room", room)
                clients.pop(sock, None)

            leave_msg = {
                "type": "system",
                "text": f"🔴 {username} left the chat",
                "ts":   now_ts()
            }
            broadcast(leave_msg, room=current_room)
            send_active_users(room=current_room)
            log_event(username, ip, "disconnect")
            print(f"[LEAVE] {username} disconnected from {addr}")

        try:
            sock.close()
        except Exception:
            pass


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    db.init_db()    # Ensure tables exist, including banned_users
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(50)

    # Windows terminals often default to cp1252; keep startup logging ASCII-safe.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except Exception:
            pass

    print(
        "\n".join(
            [
                "==================================================",
                "  CYBER CHAT SERVER v3.0",
                f"  Listening on {HOST}:{PORT}",
                f"  Connect from clients using: 127.0.0.1:{PORT}",
                f"  Admin user: '{ADMIN_USER}'",
                "==================================================",
            ]
        )
    )

    try:
        while True:
            client_sock, addr = server.accept()
            t = threading.Thread(target=handle_client,
                                 args=(client_sock, addr),
                                 daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server.close()
        print("[SERVER] Closed.")


if __name__ == "__main__":
    main()