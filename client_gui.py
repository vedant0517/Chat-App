"""
client_gui.py — Real-Time Chat Application Client
==================================================
College Mini Project | Python Tkinter GUI

Theme: Cyber / Terminal Dark
  - Deep dark backgrounds (#0D1117, #161B22)
  - Neon cyan (#00D4FF) and green (#39FF85) accents
  - Monospace Consolas font for terminal feel
  - Matrix-inspired colour palette throughout
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox, font
import socket
import threading
import json
import hashlib
import datetime
import os
import base64
from tkinter import filedialog
import ctypes
import tempfile
import subprocess
try:
    import pystray
    from pystray import MenuItem as item
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

try:
    # Make Tkinter sharp on high-DPI Windows displays
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ─── Configuration ────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 12345
ENCRYPTION_KEY = "ChatAppSecretKey2024"   # must match server.py

# ─── Colour Palettes ──────────────────────────────────────────────────────────

# CYBER DARK (default)
DARK_THEME = {
    "bg":           "#0D1117",   # GitHub-dark near-black
    "panel_bg":     "#161B22",   # slightly lighter panels
    "card_bg":      "#21262D",   # cards / input areas
    "border":       "#30363D",
    "header_bg":    "#010409",   # near-black header
    "header_fg":    "#00D4FF",   # neon cyan
    "accent":       "#00D4FF",   # primary accent (cyan)
    "accent2":      "#39FF85",   # secondary accent (neon green)
    "accent3":      "#BD93F9",   # purple (private msgs)
    "warn":         "#FF6E6E",   # red for errors / leave

    "text":         "#FFFFFF",   # main text
    "muted":        "#A0A0A0",   # muted / timestamps
    "muted2":       "#A0A0A0",   # slightly lighter muted

    "sent_bg":      "#003040",   # distinct dark-blue sent bubble
    "sent_fg":      "#FFFFFF",   # highly readable white text
    "sent_border":  "#00D4FF",

    "recv_bg":      "#1E252D",   # slightly lighter than panel bg
    "recv_fg":      "#FFFFFF",
    "recv_border":  "#30363D",

    "priv_bg":      "#2A1A4A",
    "priv_fg":      "#E2D6FF",
    "priv_border":  "#BD93F9",

    "sys_fg":       "#A0A0A0",
    "online_dot":   "#39FF85",
    "offline_dot":  "#FF6E6E",

    "btn_bg":       "#00D4FF",
    "btn_fg":       "#010409",
    "btn2_bg":      "#39FF85",
    "btn2_fg":      "#010409",
    "btn_hover":    "#00BFEA",

    "input_bg":     "#161B22",
    "input_fg":     "#E6EDF3",
    "scrollbar":    "#30363D",

    "sidebar_bg":   "#0D1117",
    "sidebar_title":"#00D4FF",
    "user_fg":      "#8B949E",
    "user_you_fg":  "#00D4FF",
}

# LIGHT TECH (for toggle)
LIGHT_THEME = {
    "bg":           "#F0F4F8",
    "panel_bg":     "#FFFFFF",
    "card_bg":      "#E8EDF2",
    "border":       "#C8D0D8",
    "header_bg":    "#1A1F2E",
    "header_fg":    "#00D4FF",
    "accent":       "#0066CC",
    "accent2":      "#00AA55",
    "accent3":      "#7B2FBE",
    "warn":         "#CC3333",

    "text":         "#1C2733",
    "muted":        "#A0ADB8",
    "muted2":       "#6B7A8A",

    "sent_bg":      "#D6EEFF",
    "sent_fg":      "#0055AA",
    "sent_border":  "#0088DD",

    "recv_bg":      "#FFFFFF",
    "recv_fg":      "#1C2733",
    "recv_border":  "#C8D0D8",

    "priv_bg":      "#F3EEFF",
    "priv_fg":      "#6A1FAB",
    "priv_border":  "#9B5DE5",

    "sys_fg":       "#7A8A9A",
    "online_dot":   "#00AA55",
    "offline_dot":  "#CC3333",

    "btn_bg":       "#0066CC",
    "btn_fg":       "#FFFFFF",
    "btn2_bg":      "#00AA55",
    "btn2_fg":      "#FFFFFF",
    "btn_hover":    "#0055AA",

    "input_bg":     "#FFFFFF",
    "input_fg":     "#1C2733",
    "scrollbar":    "#C8D0D8",

    "sidebar_bg":   "#F0F4F8",
    "sidebar_title":"#0066CC",
    "user_fg":      "#5A6A7A",
    "user_you_fg":  "#0066CC",
}

EMOJI_LIST = [
    "😀","😂","😍","🥹","😎","🤔","😅","🙄","😭","🥺",
    "❤️","🔥","✨","💯","👍","👏","🎉","🚀","💬","🤝",
    "😊","😢","😡","🤣","😇","🥳","😴","🤯","👋","🙏",
]


# ══════════════════════════════════════════════════════════════════════════════
#  ENCRYPTION (identical to server)
# ══════════════════════════════════════════════════════════════════════════════

def xor_encrypt(text: str, key: str) -> str:
    key_bytes = key.encode("utf-8")
    encrypted = [char ^ key_bytes[i % len(key_bytes)]
                 for i, char in enumerate(text.encode("utf-8"))]
    return bytes(encrypted).hex()


def xor_decrypt(hex_text: str, key: str) -> str:
    try:
        raw = bytes.fromhex(hex_text)
        key_bytes = key.encode("utf-8")
        decrypted = [byte ^ key_bytes[i % len(key_bytes)]
                     for i, byte in enumerate(raw)]
        return bytes(decrypted).decode("utf-8")
    except Exception:
        return hex_text


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_ts_local() -> str:
    """Current time as HH:MM:SS (for client-side use)."""
    return datetime.datetime.now().strftime("%H:%M:%S")


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED WIDGET HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def make_entry(parent, var, show="", **kw):
    """Styled Entry widget with overridable defaults."""
    # Set defaults if not provided in kw
    params = {
        "textvariable": var,
        "show": show,
        "font": ("Consolas", 12),
        "bg": "#21262D",
        "fg": "#FFFFFF",
        "insertbackground": "#00D4FF",
        "relief": "flat",
        "bd": 0,
        "highlightthickness": 1,
        "highlightcolor": "#00D4FF",
        "highlightbackground": "#30363D"
    }
    params.update(kw)
    return tk.Entry(parent, **params)


def make_btn(parent, text, cmd, bg, fg, hover=None):
    """Styled flat button with hover effect."""
    hover = hover or bg
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg,
                  font=("Consolas", 10, "bold"),
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=hover, activeforeground=fg,
                  padx=12, pady=6)
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════

class LoginWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NexusChat // Login")
        self.root.geometry("440x560")
        self.root.resizable(False, False)
        self.root.configure(bg="#0D1117")

        # Centre
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 440) // 2
        y = (self.root.winfo_screenheight() - 560) // 2
        self.root.geometry(f"440x560+{x}+{y}")

        self.processing_auth = False
        self._build()

    def _build(self):
        t = DARK_THEME

        # ── Banner ────────────────────────────────────────────────────────────
        banner = tk.Frame(self.root, bg="#010409", height=160)
        banner.pack(fill="x")
        banner.pack_propagate(False)

        # Glowing title using stacked labels
        tk.Label(banner, text="[ NEXUSCHAT ]",
                 font=("Consolas", 26, "bold"),
                 bg="#010409", fg="#00D4FF").pack(pady=(32, 0))
        tk.Label(banner, text="real-time secure messaging",
                 font=("Consolas", 9),
                 bg="#010409", fg="#484F58").pack()
        tk.Label(banner, text="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                 font=("Consolas", 9),
                 bg="#010409", fg="#30363D").pack(pady=(8, 0))

        # ── Card ──────────────────────────────────────────────────────────────
        card = tk.Frame(self.root, bg="#161B22",
                        highlightthickness=1,
                        highlightbackground="#30363D")
        card.pack(padx=36, pady=20, fill="both", expand=True)

        def label(txt, color="#8B949E", size=9):
            return tk.Label(card, text=txt, font=("Consolas", size),
                            bg="#161B22", fg=color, anchor="w")

        # Username
        label("> username", "#00D4FF", 9).pack(padx=20, pady=(22, 2), fill="x")
        self.uname_var = tk.StringVar()
        u_entry = make_entry(card, self.uname_var)
        u_entry.pack(padx=20, fill="x", ipady=8)
        u_entry.focus()

        # Password
        label("> password", "#00D4FF", 9).pack(padx=20, pady=(14, 2), fill="x")
        self.pwd_var = tk.StringVar()
        self.pwd_entry = make_entry(card, self.pwd_var, show="●")
        self.pwd_entry.pack(padx=20, fill="x", ipady=8)

        # Show pwd toggle
        self.show_pwd = tk.BooleanVar()
        tk.Checkbutton(card, text="show password",
                       variable=self.show_pwd,
                       command=lambda: self.pwd_entry.config(
                           show="" if self.show_pwd.get() else "●"),
                       bg="#161B22", fg="#484F58",
                       selectcolor="#21262D",
                       activebackground="#161B22",
                       activeforeground="#8B949E",
                       font=("Consolas", 8)).pack(padx=20, anchor="w", pady=(4, 0))

        # Error / status
        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(card, textvariable=self.status_var,
                                   font=("Consolas", 8),
                                   bg="#161B22", fg="#FF6E6E",
                                   wraplength=360, justify="left")
        self.status_lbl.pack(padx=20, pady=(6, 0), fill="x")

        # Buttons
        btn_frame = tk.Frame(card, bg="#161B22")
        btn_frame.pack(padx=20, pady=(16, 24), fill="x")

        self.login_btn = make_btn(btn_frame, "[ LOGIN ]",
                                  self._do_login,
                                  "#00D4FF", "#010409", "#00BFEA")
        self.login_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.reg_btn = make_btn(btn_frame, "[ REGISTER ]",
                                self._do_register,
                                "#39FF85", "#010409", "#00CC66")
        self.reg_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Footer
        tk.Label(self.root, text="// localhost:12345  |  XOR-256 encrypted",
                 font=("Consolas", 7), bg="#0D1117", fg="#30363D").pack(pady=(0, 10))

        self.root.bind("<Return>", lambda e: self._do_login())

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def _get_fields(self):
        u = self.uname_var.get().strip()
        p = self.pwd_var.get().strip()
        if not u:
            self.status_var.set("! username required")
            return None, None
        if len(u) < 2 or len(u) > 20:
            self.status_var.set("! username: 2–20 chars")
            return None, None
        if len(p) < 3:
            self.status_var.set("! password: min 3 chars")
            return None, None
        return u, hash_password(p)

    def _set_busy(self, busy: bool):
        self.processing_auth = busy
        state = "disabled" if busy else "normal"
        if hasattr(self, 'login_btn') and self.login_btn.winfo_exists():
            self.login_btn.config(state=state)
        if hasattr(self, 'reg_btn') and self.reg_btn.winfo_exists():
            self.reg_btn.config(state=state)

    def _do_login(self):
        threading.Thread(target=self._auth, args=("login",), daemon=True).start()

    def _do_register(self):
        threading.Thread(target=self._auth, args=("register",), daemon=True).start()

    def _auth(self, action: str):
        if self.processing_auth:
            return
        username, pwd_hash = self._get_fields()
        if not username:
            return

        self.root.after(0, lambda: self.status_var.set("// connecting..."))
        self.root.after(0, lambda: self._set_busy(True))

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((HOST, PORT))
            sock.settimeout(None)
        except Exception as e:
            self.root.after(0, lambda: self._err(
                "! server unreachable — start server.py first"))
            return

        pkt = json.dumps({"type": action,
                          "username": username,
                          "password_hash": pwd_hash},
                         ensure_ascii=False) + "\n"
        try:
            sock.sendall(pkt.encode("utf-8"))
        except Exception as e:
            self.root.after(0, lambda: self._err(f"! send error: {e}"))
            sock.close()
            return

        # Read response
        buf = []
        remainder = ""
        try:
            while True:
                raw = "".join(buf)
                if "\n" in raw:
                    line, remainder = raw.split("\n", 1)
                    resp = json.loads(line.strip())
                    break
                chunk = sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Server closed connection.")
                buf.append(chunk.decode("utf-8"))
        except Exception as e:
            self.root.after(0, lambda: self._err(f"! error: {e}"))
            sock.close()
            return

        if resp.get("type") == "auth_ok":
            uname = resp.get("username", username)
            self.root.after(0, lambda: self._open_chat(sock, uname, remainder))
        else:
            reason = resp.get("reason", "Auth failed.")
            self.root.after(0, lambda: self._err(f"! {reason}"))
            sock.close()

    def _err(self, msg: str):
        if hasattr(self, 'status_var'):
            self.status_var.set(msg)
        self._set_busy(False)

    def _open_chat(self, sock, username, initial_buffer: str = ""):
        # Clear login screen widgets to reuse the root window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Instantiate ChatWindow on the existing root
        ChatWindow(self.root, sock, username, initial_buffer=initial_buffer)
# ══════════════════════════════════════════════════════════════════════════════
#  CHAT WINDOW
# ══════════════════════════════════════════════════════════════════════════════

class ChatWindow:
    def __init__(self, root: tk.Tk, sock: socket.socket, username: str, initial_buffer: str = ""):
        self.root = root
        self.sock = sock
        self.username = username
        self.dark_mode = True
        self.theme = DARK_THEME
        self.connected = True
        self._recv_buf = [initial_buffer] if initial_buffer else []
        
        self._is_typing_sent = False
        self._typing_users = set()
        self._typing_after_id = None
        self._img_refs = []

        # Read receipts: {msg_ts → tag_name} so we can update ✓ → ✓✓
        self._pending_acks = {}

        # Unread badge
        self._unread = 0
        self._focused = True

        # Current room
        self._room = "#general"

        # System tray icon reference (set in _on_close if minimised)
        self._tray = None
        self._cursor_state = True
        self._cursor_after_id = None

        self.root.title(f"NexusChat // {username}")
        self.root.geometry("1000x680")
        self.root.minsize(750, 500)
        self.root.resizable(True, True)  # Unlock resizing
        self.root.configure(bg=self.theme["bg"])

        # Centre
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 1000) // 2
        y = (self.root.winfo_screenheight() - 680) // 2
        self.root.geometry(f"1000x680+{x}+{y}")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self._apply_theme()

        threading.Thread(target=self._recv_loop, daemon=True).start()
        self.root.after(0, lambda: self._sys("Welcome to NexusChat. Type /help for commands."))
        self.root.after(0, lambda: self._update_users([self.username]))
        self.root.after(0, self.msg_entry.focus_set)
        self.root.bind("<FocusIn>",  self._on_focus)
        self.root.bind("<FocusOut>", self._on_blur)
        self.root.bind("<Control-f>", lambda e: self._toggle_search())

    # ──────────────────────────────────────────────────────────────────────────
    #  BUILD UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        t = self.theme

        # ── Header bar ────────────────────────────────────────────────────────
        self.header = tk.Frame(self.root, height=50, bg=t["header_bg"])
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.dot_lbl = tk.Label(self.header, text="◆",
                                font=("Consolas", 12),
                                bg=t["header_bg"], fg=t["online_dot"])
        self.dot_lbl.pack(side="left", padx=(14, 4))

        self.title_lbl = tk.Label(
            self.header,
            text=f"NEXUSCHAT  //  {self.username.upper()}",
            font=("Consolas", 13, "bold"),
            bg=t["header_bg"], fg=t["header_fg"])
        self.title_lbl.pack(side="left")

        # Typing indicator label
        self.typing_lbl = tk.Label(self.header, text="", 
                                   font=("Consolas", 8, "italic"), 
                                   bg=t["header_bg"], fg=t["accent"])
        self.typing_lbl.pack(side="left", padx=10)

        # Encrypted tag
        tk.Label(self.header, text="[ XOR-ENC ]",
                 font=("Consolas", 8),
                 bg=t["header_bg"], fg=t["muted"]).pack(side="left", padx=10)

        # Theme toggle
        self.theme_btn = tk.Button(
            self.header, text="[ ☀ LIGHT ]",
            font=("Consolas", 8, "bold"),
            bg=t["header_bg"], fg=t["muted2"],
            activebackground=t["header_bg"], activeforeground=t["muted2"],
            relief="flat", cursor="hand2", bd=0,
            command=self._toggle_theme)
        self.theme_btn.pack(side="right", padx=12)

        # Connection status
        self.conn_lbl = tk.Label(self.header, text="● CONNECTED",
                                 font=("Consolas", 8),
                                 bg=t["header_bg"], fg=t["online_dot"])
        self.conn_lbl.pack(side="right", padx=8)

        # Room label
        self.room_lbl = tk.Label(self.header,
                                 text=f"[ {self._room.upper()} ]",
                                 font=("Consolas", 9, "bold"),
                                 bg=t["header_bg"], fg=t["muted"])
        self.room_lbl.pack(side="right", padx=6)
        # Search toggle button
        self.search_btn = tk.Button(
            self.header, text="[ 🔍 ]",
            font=("Consolas", 8, "bold"),
            bg=t["header_bg"], fg=t["muted"],
            activebackground=t["header_bg"],
            relief="flat", cursor="hand2", bd=0,
            command=self._toggle_search)
        self.search_btn.pack(side="right", padx=4)

        # Clear chat button
        self.clear_btn = tk.Button(
            self.header, text="[ 🗑️ CLEAR ]",
            font=("Consolas", 8, "bold"),
            bg=t["header_bg"], fg=t["warn"],
            activebackground=t["header_bg"],
            relief="flat", cursor="hand2", bd=0,
            command=self._clear_chat_display)
        self.clear_btn.pack(side="right", padx=4)

        # Separator line
        self.sep = tk.Frame(self.root, height=1, bg=t["border"])
        self.sep.pack(fill="x")

        # ── Input bar ─────────────────────────────────────────────────────────
        self.input_bar = tk.Frame(self.root, bg=t["input_bg"], padx=12, pady=8)
        self.input_bar.pack(side="bottom", fill="x")

        # ── Input separator ───────────────────────────────────────────────────
        self.input_sep = tk.Frame(self.root, height=1, bg=t["border"])
        self.input_sep.pack(side="bottom", fill="x")

        # ── Body (Rest of the window) ─────────────────────────────────────────
        self.body = tk.Frame(self.root, bg=t["bg"])
        self.body.pack(fill="both", expand=True)

        # Sidebar (right)
        self.sidebar = tk.Frame(self.body, width=180, bg=t["sidebar_bg"])
        self.sidebar.pack(side="right", fill="y")
        self.sidebar.pack_propagate(False)

        self.sidebar_sep = tk.Frame(self.body, width=1, bg=t["border"])
        self.sidebar_sep.pack(side="right", fill="y")

        self.sidebar_title = tk.Label(
            self.sidebar, text="// ONLINE",
            font=("Consolas", 9, "bold"), anchor="w",
            bg=t["sidebar_bg"], fg=t["sidebar_title"])
        self.sidebar_title.pack(fill="x", padx=12, pady=(14, 6))

        self.users_frame = tk.Frame(self.sidebar, bg=t["sidebar_bg"])
        self.users_frame.pack(fill="both", expand=True, padx=6)

        # Chat area (left)
        self.chat_area = tk.Frame(self.body, bg=t["bg"])
        self.chat_area.pack(side="left", fill="both", expand=True)

        self.chat = scrolledtext.ScrolledText(
            self.chat_area,
            wrap="word",
            font=("Consolas", 11),
            relief="flat", bd=0,
            bg=t["panel_bg"], fg=t["text"],
            padx=14, pady=10,
            cursor="arrow",
            state="disabled",
            spacing1=3,
            spacing3=3,
        )
        self.chat.pack(fill="both", expand=True)
        self._configure_tags()

        # ── Search Bar (Hidden by default) ────────────────────────────────────
        self.search_frame = tk.Frame(self.root, bg=t["card_bg"], padx=8, pady=4)
        self.search_var = tk.StringVar()
        self.search_entry = make_entry(
            self.search_frame, self.search_var,
            font=("Consolas", 10), bg=t["input_bg"])
        self.search_entry.pack(side="left", fill="both", expand=True, padx=(6, 6), pady=2, ipady=6)
        self.search_entry.bind("<Return>", lambda e: self._do_search())
        
        tk.Button(self.search_frame, text="🔍 FIND", font=("Consolas", 9, "bold"),
                  bg=t["btn_bg"], fg=t["btn_fg"], relief="flat", bd=0, cursor="hand2",
                  command=self._do_search).pack(side="right", padx=4, pady=6)
        tk.Button(self.search_frame, text="❌ CLOSE", font=("Consolas", 9, "bold"),
                  bg=t["warn"], fg="#111", relief="flat", bd=0, cursor="hand2",
                  command=self._toggle_search).pack(side="right", padx=(0,14), pady=6)

        # Prompt label (terminal style)
        self.prompt_lbl = tk.Label(
            self.input_bar, text=f"{self.username} ❯",
            font=("Consolas", 10, "bold"), bg=t["input_bg"], fg=t["accent"])
        self.prompt_lbl.pack(side="left", padx=(2, 8))
        
        # Start blinking cursor
        self._blink_cursor()

        self.msg_var = tk.StringVar()
        self.msg_entry = tk.Entry(
            self.input_bar, textvariable=self.msg_var,
            font=("Consolas", 11), relief="flat", bd=0,
            bg=t["input_bg"], fg=t["input_fg"], insertbackground=t["accent"],
            highlightthickness=1, highlightbackground=t["border"], highlightcolor=t["accent"])
        self.msg_entry.pack(side="left", fill="both", expand=True, padx=(0, 8), ipady=8)
        self.msg_entry.bind("<Return>", lambda e: self._send())
        self.msg_entry.bind("<KeyRelease>", self._on_keyrelease)
        self.msg_entry.focus()

        # Emoji btn
        self.emoji_btn = tk.Button(
            self.input_bar, text="😊",
            font=("Segoe UI Emoji", 13),
            bg=t["input_bg"], activebackground=t["input_bg"],
            relief="flat", bd=0, cursor="hand2",
            command=self._emoji_picker)
        self.emoji_btn.pack(side="left", padx=(0, 8))

        # Send File button
        self.file_btn = tk.Button(
            self.input_bar, text="FILE 📎",
            font=("Consolas", 9, "bold"),
            bg=t["card_bg"], fg=t["text"],
            activebackground=t["border"], activeforeground=t["text"],
            relief="flat", bd=0, cursor="hand2",
            command=self._send_file)
        self.file_btn.pack(side="right", padx=(0, 8), ipadx=8, ipady=6)

        # Send button
        self.send_btn = tk.Button(
            self.input_bar, text="SEND ▶",
            font=("Consolas", 9, "bold"),
            bg=t["btn_bg"], fg=t["btn_fg"],
            activebackground=t["btn_hover"], activeforeground=t["btn_fg"],
            relief="flat", bd=0, cursor="hand2",
            command=self._send)
        self.send_btn.pack(side="right", ipadx=12, ipady=6)

    # ──────────────────────────────────────────────────────────────────────────
    #  TEXT TAGS
    # ──────────────────────────────────────────────────────────────────────────

    def _configure_tags(self):
        t = self.theme
        c = self.chat

        # Reduced lmargin/rmargin to prevent squashing text on narrow windows
        
        # ── Sent messages (right-aligned)
        c.tag_configure("sent_hdr",
                         foreground=t["sent_border"], font=("Consolas", 9, "bold"),
                         justify="right", rmargin=14, spacing1=10)
        c.tag_configure("sent_body",
                         background=t["sent_bg"], foreground=t["sent_fg"],
                         font=("Consolas", 11), justify="right",
                         rmargin=14, lmargin1=100, lmargin2=100,
                         spacing3=4)
        c.tag_configure("sent_ts",
                         foreground=t["muted"], font=("Consolas", 8),
                         justify="right", rmargin=14, spacing3=10)

        # ── Received messages (left-aligned)
        c.tag_configure("recv_hdr",
                         foreground=t["accent"], font=("Consolas", 9, "bold"),
                         justify="left", lmargin1=14, spacing1=10)
        c.tag_configure("recv_body",
                         background=t["recv_bg"], foreground=t["recv_fg"],
                         font=("Consolas", 11), justify="left",
                         lmargin1=14, lmargin2=14, rmargin=100,
                         spacing3=4)
        c.tag_configure("recv_ts",
                         foreground=t["muted"], font=("Consolas", 8),
                         justify="left", lmargin1=14, spacing3=10)

        # ── Private messages (purple)
        c.tag_configure("priv_hdr",
                         foreground=t["accent3"], font=("Consolas", 9, "bold"),
                         justify="left", lmargin1=14, spacing1=10)
        c.tag_configure("priv_body",
                         background=t["priv_bg"], foreground=t["priv_fg"],
                         font=("Consolas", 11, "italic"), justify="left",
                         lmargin1=14, lmargin2=14, rmargin=100,
                         spacing3=4)
        c.tag_configure("priv_ts",
                         foreground=t["muted"], font=("Consolas", 8),
                         justify="left", lmargin1=14, spacing3=10)

        # ── System messages (centred, muted)
        c.tag_configure("sys",
                         foreground=t["sys_fg"], font=("Consolas", 9, "italic"),
                         justify="center", spacing1=8, spacing3=8)

        # ── Search Highlight
        c.tag_configure("search", background="#FFFF00", foreground="#000000")

    # ──────────────────────────────────────────────────────────────────────────
    #  THEMING
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        t = self.theme
        self.root.configure(bg=t["bg"])

        # Header
        self.header.configure(bg=t["header_bg"])
        self.dot_lbl.configure(bg=t["header_bg"], fg=t["online_dot"])
        self.title_lbl.configure(bg=t["header_bg"], fg=t["header_fg"])
        self.conn_lbl.configure(bg=t["header_bg"],
                                fg=t["online_dot"] if self.connected else t["offline_dot"])
        self.theme_btn.configure(bg=t["header_bg"], fg=t["muted2"],
                                 activebackground=t["header_bg"],
                                 text="[ ☀ LIGHT ]" if self.dark_mode else "[ 🌑 DARK ]")
        self.typing_lbl.configure(bg=t["header_bg"], fg=t["accent"])
        for w in self.header.winfo_children():
            if isinstance(w, tk.Label):
                try:
                    if w not in (self.dot_lbl, self.title_lbl, self.conn_lbl, self.typing_lbl):
                        w.configure(bg=t["header_bg"], fg=t["muted"])
                except Exception:
                    pass

        self.sep.configure(bg=t["border"])
        self.body.configure(bg=t["bg"])

        # Sidebar
        self.sidebar.configure(bg=t["sidebar_bg"])
        self.sidebar_sep.configure(bg=t["border"])
        self.users_frame.configure(bg=t["sidebar_bg"])
        self.sidebar_title.configure(bg=t["sidebar_bg"], fg=t["sidebar_title"])

        # Chat
        self.chat_area.configure(bg=t["chat_bg"] if "chat_bg" in t else t["bg"])
        self.chat.configure(bg=t["panel_bg"], fg=t["text"])

        # Input
        self.input_sep.configure(bg=t["border"])
        self.input_bar.configure(bg=t["input_bg"])
        self.prompt_lbl.configure(bg=t["input_bg"], fg=t["accent"])
        self.msg_entry.configure(bg=t["input_bg"], fg=t["input_fg"],
                                 insertbackground=t["accent"],
                                 highlightbackground=t["border"],
                                 highlightcolor=t["accent"])
        self.emoji_btn.configure(bg=t["input_bg"],
                                 fg=t["text"],
                                 activebackground=t["input_bg"],
                                 activeforeground=t["text"])
        self.file_btn.configure(bg=t["card_bg"], fg=t["text"],
                                activebackground=t["border"],
                                activeforeground=t["text"])
        self.send_btn.configure(bg=t["btn_bg"], fg=t["btn_fg"],
                                activebackground=t["btn_hover"],
                                activeforeground=t["btn_fg"])
        self.search_frame.configure(bg=t["card_bg"])
        self.search_entry.configure(bg=t["input_bg"], fg=t["input_fg"],
                                    insertbackground=t["accent"],
                                    highlightbackground=t["border"],
                                    highlightcolor=t["accent"])

        # Re-apply tags with new colours
        self._configure_tags()

    def _toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self._apply_theme()

    def _blink_cursor(self):
        """Toggle the terminal prompt literal between ❯ and ▌."""
        if self._cursor_state:
            self.prompt_lbl.config(text=f"{self.username} ▌")
        else:
            self.prompt_lbl.config(text=f"{self.username} ❯")
        self._cursor_state = not self._cursor_state
        self._cursor_after_id = self.root.after(600, self._blink_cursor)

    def _on_focus(self, event):
        if event.widget == self.root:
            self._focused = True
            self._unread = 0
            self._update_title()

    def _on_blur(self, event):
        if event.widget == self.root:
            self._focused = False

    def _update_title(self):
        badge = f" [{self._unread} new]" if self._unread > 0 else ""
        self.root.title(f"NexusChat // {self.username}{badge}")

    # ──────────────────────────────────────────────────────────────────────────
    #  SEARCH
    # ──────────────────────────────────────────────────────────────────────────

    def _toggle_search(self):
        """Show or hide the search bar."""
        if self.search_frame.winfo_ismapped():
            self.search_frame.pack_forget()
            self.chat.tag_remove("search", "1.0", "end")
            self.msg_entry.focus()
        else:
            self.search_frame.pack(fill="x", before=self.input_sep)
            self.search_entry.focus()

    def _do_search(self):
        """Find and highlight text in the chat widget."""
        self.chat.tag_remove("search", "1.0", "end")
        query = self.search_var.get()
        if not query:
            return
        
        idx = "1.0"
        while True:
            idx = self.chat.search(query, idx, nocase=1, stopindex="end")
            if not idx:
                break
            lastidx = f"{idx}+{len(query)}c"
            self.chat.tag_add("search", idx, lastidx)
            idx = lastidx
        
        # Scroll to the last match if any
        if self.chat.tag_ranges("search"):
            self.chat.see(self.chat.tag_ranges("search")[-1])

    # ──────────────────────────────────────────────────────────────────────────
    #  CHAT DISPLAY HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _sys(self, text: str):
        """Insert a centred system/status line."""
        self.chat.config(state="normal")
        self.chat.insert("end", f"  ──  {text}  ──\n", "sys")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _clear_chat_display(self):
        """Clear the local chat display."""
        self.chat.config(state="normal")
        self.chat.delete("1.0", tk.END)
        self.chat.config(state="disabled")

    def _msg(self, sender: str, text: str, ts: str):
        """Insert a regular chat message bubble."""
        is_self = sender == self.username
        
        # Update unread title if window not in focus and not from self
        if not self._focused and not is_self:
            self._unread += 1
            self._update_title()

        if is_self:
            hdr, body, ts_tag = "sent_hdr", "sent_body", "sent_ts"
            name = "YOU"
        else:
            hdr, body, ts_tag = "recv_hdr", "recv_body", "recv_ts"
            name = sender.upper()

            # Send read receipt back
            if ts:
                self._tx({"type": "read_ack", "msg_ts": ts})

        self.chat.config(state="normal")
        self.chat.insert("end", f"{name}\n", hdr)
        self.chat.insert("end", f"{text}\n", body)
        
        # For our own messages, add a single tick ✓ that becomes ✓✓ when ack'd
        if is_self and ts:
            ack_tag = f"ack_{ts}"
            self.chat.insert("end", f"✓ {ts}\n", (ts_tag, ack_tag))
            self._pending_acks[ts] = ack_tag
        else:
            self.chat.insert("end", f"{ts}\n", ts_tag)
            
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _mark_read(self, msg_ts: str):
        """Upgrade ✓ to ✓✓ when read receipt arrives."""
        tag = self._pending_acks.get(msg_ts)
        if tag:
            try:
                self.chat.config(state="normal")
                # find the tag range
                ranges = self.chat.tag_ranges(tag)
                if ranges:
                    start, end = ranges[0], ranges[1]
                    old_text = self.chat.get(start, end)
                    if old_text.startswith("✓ "):
                        new_text = "✓✓ " + old_text[2:]
                        self.chat.delete(start, end)
                        self.chat.insert(start, new_text, ("sent_ts", tag))
                self.chat.config(state="disabled")
            except Exception:
                pass

    def _priv(self, sender: str, text: str, ts: str):
        """Insert a private message bubble."""
        self.chat.config(state="normal")
        self.chat.insert("end", f"🔒 {sender.upper()} (private)\n", "priv_hdr")
        self.chat.insert("end", f"{text}\n", "priv_body")
        self.chat.insert("end", f"{ts}\n", "priv_ts")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _show_file_in_chat(self, sender: str, filename: str, file_bytes: bytes, ts: str):
        """
        Embed a file in the chat:
        - Images: show a thumbnail preview and a [ SAVE ] button.
        - Other files: show a file card with a [ SAVE ] button.
        """
        is_self = (sender == self.username)
        t = self.theme
        ext = os.path.splitext(filename)[1].lower()
        is_image = ext in IMAGE_EXTENSIONS and PIL_AVAILABLE

        hdr_tag = "sent_hdr" if is_self else "recv_hdr"
        name    = "YOU" if is_self else sender.upper()

        self.chat.config(state="normal")
        self.chat.insert("end", f"{name}  \u2014  📎 {filename}\n", hdr_tag)

        if is_image and file_bytes:
            try:
                import io
                pil_img = Image.open(io.BytesIO(file_bytes))
                # Scale to max 300x200 thumbnail
                pil_img.thumbnail((300, 200), Image.LANCZOS)
                photo = ImageTk.PhotoImage(pil_img)
                self._img_refs.append(photo)          # prevent GC

                # Embed image in text widget
                self.chat.image_create("end", image=photo, padx=14)
                self.chat.insert("end", "\n")
            except Exception as img_err:
                self.chat.insert("end", f"  [image could not be previewed: {img_err}]\n", "sys")
        else:
            # Non-image: show a text card
            size_kb = len(file_bytes) / 1024 if file_bytes else 0
            self.chat.insert("end", f"  📄 {filename}  ({size_kb:.1f} KB)\n",
                             "sent_body" if is_self else "recv_body")

        # Button row: OPEN + SAVE
        btn_frame = tk.Frame(self.chat, bg=t["card_bg"], bd=0, relief="flat")

        open_btn = tk.Button(
            btn_frame,
            text="[ OPEN \u25b6 ]",
            font=("Consolas", 9, "bold"),
            bg=t["accent"], fg="#000000",
            relief="flat", bd=0, cursor="hand2",
            padx=10, pady=4,
            command=lambda fn=filename, fb=file_bytes: self._open_file_temp(fn, fb)
        )
        open_btn.pack(side="left", padx=4, pady=4)

        save_btn = tk.Button(
            btn_frame,
            text="[ SAVE ]",
            font=("Consolas", 9, "bold"),
            bg=t["accent2"],
            fg="#000000",
            relief="flat", bd=0, cursor="hand2",
            padx=10, pady=4,
            command=lambda fn=filename, fb=file_bytes: self._save_file_local(fn, fb)
        )
        save_btn.pack(side="left", padx=4, pady=4)
        self.chat.window_create("end", window=btn_frame, padx=14)
        self.chat.insert("end", "\n")
        self.chat.insert("end", f"{ts}\n", "sent_ts" if is_self else "recv_ts")
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _open_file_temp(self, filename: str, file_bytes: bytes):
        """Write to a temporary file and open it with the OS default viewer."""
        try:
            ext = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=ext,
                prefix="chatapp_"
            ) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            import sys as _sys
            import subprocess as _sub
            if _sys.platform == "win32":
                os.startfile(tmp_path)
            elif _sys.platform == "darwin":
                _sub.Popen(["open", tmp_path])
            else:
                _sub.Popen(["xdg-open", tmp_path])
        except Exception as err:
            messagebox.showerror("Open Error", f"Cannot open file:\n{err}", parent=self.root)

    def _save_file_local(self, filename: str, file_bytes: bytes):
        """Pop a Save As dialog and write the file bytes."""
        save_path = filedialog.asksaveasfilename(
            parent=self.root,
            initialfile=filename,
            title="Save file"
        )
        if save_path:
            try:
                with open(save_path, "wb") as f:
                    f.write(file_bytes)
                self._sys(f"💾 Saved to {save_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save:\n{e}", parent=self.root)

    # ──────────────────────────────────────────────────────────────────────────
    #  SIDEBAR
    # ──────────────────────────────────────────────────────────────────────────

    def _update_users(self, users: list):
        t = self.theme
        for w in self.users_frame.winfo_children():
            w.destroy()
        for name in sorted(users):
            row = tk.Frame(self.users_frame, bg=t["sidebar_bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text="●", font=("Consolas", 9),
                     bg=t["sidebar_bg"], fg=t["online_dot"]).pack(side="left")
            is_you = name == self.username
            disp = f" {name.upper()}" + (" (you)" if is_you else "")
            tk.Label(row, text=disp,
                     font=("Consolas", 9, "bold" if is_you else "normal"),
                     bg=t["sidebar_bg"],
                     fg=t["user_you_fg"] if is_you else t["user_fg"]).pack(side="left")

    # ──────────────────────────────────────────────────────────────────────────
    #  EMOJI PICKER
    # ──────────────────────────────────────────────────────────────────────────

    def _emoji_picker(self):
        t = self.theme
        pop = tk.Toplevel(self.root)
        pop.title("")
        pop.geometry("320x140")
        pop.resizable(False, False)
        pop.configure(bg=t["panel_bg"])
        pop.transient(self.root)
        pop.grab_set()

        x = self.root.winfo_x() + 10
        y = self.root.winfo_y() + self.root.winfo_height() - 210
        pop.geometry(f"+{x}+{y}")

        tk.Label(pop, text="// EMOJI", font=("Consolas", 8),
                 bg=t["panel_bg"], fg=t["muted2"]).pack(anchor="w", padx=8, pady=(6, 2))

        grid = tk.Frame(pop, bg=t["panel_bg"])
        grid.pack(padx=6, pady=4)

        row, col = 0, 0
        for emoji in EMOJI_LIST:
            btn = tk.Button(grid, text=emoji, font=("Segoe UI Emoji", 13),
                            bg=t["card_bg"], relief="flat", cursor="hand2",
                            command=lambda e=emoji: self._insert_emoji(e, pop))
            btn.grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col >= 10:
                col = 0
                row += 1

    def _insert_emoji(self, emoji: str, pop: tk.Toplevel):
        self.msg_entry.insert("end", emoji)
        pop.destroy()
        self.msg_entry.focus()

    # ──────────────────────────────────────────────────────────────────────────
    #  NOTIFICATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def _notify(self, title: str, body: str):
        try:
            if not self.root.focus_displayof():
                messagebox.showinfo(title, body)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    #  SENDING
    # ──────────────────────────────────────────────────────────────────────────

    def _send(self):
        text = self.msg_var.get().strip()
        if not text:
            return
        self.msg_var.set("")

        if text == "/help":
            self._sys("commands: /msg <user> <text> | /users | /exit | /help")
            self._sys("advanced: /join #room | /passwd <new> | /log")
            self._sys("admin:    /kick <user> | /ban <user> | /unban <user> | /clearall")
            return

        if text.startswith("/msg "):
            parts = text[5:].split(" ", 1)
            if len(parts) < 2:
                self._sys("usage: /msg <username> <message>")
                return
            target, msg = parts
            self._tx({"type": "private", "to": target,
                      "text": xor_encrypt(msg, ENCRYPTION_KEY)})
            return

        if text.startswith("/join "):
            room = text[6:].strip()
            if room:
                self._tx({"type": "command", "cmd": "join", "room": room})
            return

        if text.startswith("/passwd "):
            new_pass = text[8:].strip()
            if new_pass:
                import hashlib
                new_hash = hashlib.sha256(new_pass.encode("utf-8")).hexdigest()
                self._tx({"type": "command", "cmd": "passwd", "new_hash": new_hash})
            return

        if text.startswith("/kick "):
            target = text[6:].strip()
            if target:
                self._tx({"type": "command", "cmd": "kick", "target": target})
            return

        if text.startswith("/ban "):
            target = text[5:].strip()
            if target:
                self._tx({"type": "command", "cmd": "ban", "target": target})
            return

        if text.startswith("/unban "):
            target = text[7:].strip()
            if target:
                self._tx({"type": "command", "cmd": "unban", "target": target})
            return

        if text == "/log":
            self._tx({"type": "command", "cmd": "log"})
            return

        if text == "/users":
            self._tx({"type": "command", "cmd": "users"})
            return

        if text == "/clearall":
            self._tx({"type": "command", "cmd": "clearall"})
            return

        if text == "/exit":
            self._on_close()
            return

        self._tx({"type": "message",
                  "text": xor_encrypt(text, ENCRYPTION_KEY)})

    # ──────────────────────────────────────────────────────────────────────────
    #  TYPING AND FILES
    # ──────────────────────────────────────────────────────────────────────────

    def _on_keyrelease(self, event):
        """Send typing indicator over network if state changes."""
        text_len = len(self.msg_var.get())
        if text_len > 0 and not self._is_typing_sent:
            self._is_typing_sent = True
            self._tx({"type": "typing", "is_typing": True})
        elif text_len == 0 and self._is_typing_sent:
            self._is_typing_sent = False
            self._tx({"type": "typing", "is_typing": False})

    def _send_file(self):
        """Prompt user for a file, encode it, and send over a background thread."""
        file_path = filedialog.askopenfilename(
            parent=self.root,
            title="Select File to Send",
            filetypes=[
                ("All files", "*.*"),
                ("Images", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"),
                ("Documents", "*.pdf;*.txt;*.docx"),
            ]
        )
        if not file_path:
            return
        
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            messagebox.showerror("File Error", f"Cannot open file:\n{e}", parent=self.root)
            return

        size_kb = len(file_bytes) / 1024
        if size_kb > 5 * 1024:  # 5MB
            messagebox.showwarning("File Too Large",
                f"File is {size_kb:.0f} KB. Max allowed is 5120 KB.",
                parent=self.root)
            return

        filename = os.path.basename(file_path)
        self._sys(f"Sending {filename} ({size_kb:.1f} KB)...")
        
        # Run the encode+send on a background thread so GUI doesn't freeze
        threading.Thread(
            target=self._do_send_file,
            args=(filename, file_bytes),
            daemon=True
        ).start()

    def _do_send_file(self, filename: str, file_bytes: bytes):
        """Background thread: encode and send the file over the socket."""
        try:
            b64_str = base64.b64encode(file_bytes).decode("ascii")
            packet = json.dumps({
                "type": "file",
                "filename": filename,
                "data": b64_str
            }, ensure_ascii=False) + "\n"

            # Send directly (bypasses _tx so we can catch errors cleanly)
            if self.connected:
                self.sock.sendall(packet.encode("utf-8"))
                # Server broadcasts back to us too, so _handle -> _show_file_in_chat displays it.

        except Exception as e:
            err_msg = str(e)
            self._queue(lambda msg=err_msg: self._sys(f"File send error: {msg}"))


    def _process_typing_users(self, username: str, is_typing: bool):
        """Update the typing indicator label."""
        if is_typing:
            self._typing_users.add(username)
        else:
            self._typing_users.discard(username)
            
        self._update_typing_label()
        
        # Reset timeout to clear if they disconnected suddenly
        if self._typing_after_id:
            self.root.after_cancel(self._typing_after_id)
        if self._typing_users:
            self._typing_after_id = self.root.after(5000, self._auto_clear_typing)
            
    def _auto_clear_typing(self):
        """Failsafe to clear stale typing indicators."""
        self._typing_users.clear()
        self._update_typing_label()
        
    def _update_typing_label(self):
        if not self._typing_users:
            self.typing_lbl.config(text="")
        else:
            names = list(self._typing_users)
            if len(names) == 1:
                txt = f"{names[0]} is typing..."
            elif len(names) == 2:
                txt = f"{names[0]} and {names[1]} are typing..."
            else:
                txt = "Multiple people are typing..."
            self.typing_lbl.config(text=txt)

    def _tx(self, data: dict):
        if not self.connected:
            return
        try:
            self.sock.sendall((json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8"))
        except Exception as e:
            err = str(e)
            self._queue(lambda msg=err: self._sys(f"send error: {msg}"))
            self.connected = False

    # ──────────────────────────────────────────────────────────────────────────
    #  RECEIVING (background thread)
    # ──────────────────────────────────────────────────────────────────────────

    def _recv_loop(self):
        while self.connected:
            try:
                # 1. Process all complete lines already in buffer
                while self.connected:
                    raw = "".join(self._recv_buf)
                    if "\n" not in raw:
                        break
                    
                    line, rest = raw.split("\n", 1)
                    self._recv_buf.clear()
                    if rest:
                        self._recv_buf.append(rest)
                    
                    try:
                        data = json.loads(line.strip())
                        self._queue(lambda d=data: self._handle(d))
                    except json.JSONDecodeError:
                        pass

                # 2. Wait for new data
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionError("Server closed connection.")
                self._recv_buf.append(chunk.decode("utf-8"))

            except Exception as e:
                if self.connected:
                    self.connected = False
                    self._queue(lambda: self._disconnected(str(e)))
                break

    def _queue(self, fn):
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    def _handle(self, data: dict):
        mt = data.get("type")

        if mt == "message":
            sender = data.get("from", "?")
            text   = xor_decrypt(data.get("text", ""), ENCRYPTION_KEY)
            ts     = data.get("ts", "")
            self._msg(sender, text, ts)

        elif mt == "private":
            sender = data.get("from", "?")
            text   = xor_decrypt(data.get("text", ""), ENCRYPTION_KEY)
            ts     = data.get("ts", "")
            self._priv(sender, text, ts)

        elif mt == "typing":
            sender = data.get("from", "?")
            is_typing = data.get("is_typing", False)
            if sender != self.username:
                self._process_typing_users(sender, is_typing)

        elif mt == "read_receipt":
            ack_by = data.get("by", "?")
            msg_ts = data.get("msg_ts", "")
            if ack_by != self.username:
                self._mark_read(msg_ts)

        elif mt == "room_change":
            new_room = data.get("room", "#general")
            self._room = new_room
            self.room_lbl.config(text=f"[ {new_room.upper()} ]")
            self._sys(f"You migrated to {new_room}")
                
        elif mt == "file":
            sender   = data.get("from", "?")
            filename = data.get("filename", "file")
            b64_str  = data.get("data", "")
            ts       = data.get("ts", now_ts_local())
            
            try:
                file_bytes = base64.b64decode(b64_str)
            except Exception:
                file_bytes = b""

            # Show for BOTH sender (echo) and receiver
            self._show_file_in_chat(sender, filename, file_bytes, ts)

        elif mt == "clear_chat":
            self._clear_chat_display()

        elif mt == "system":
            self._sys(data.get("text", ""))

        elif mt == "users":
            self._update_users(data.get("list", []))

        elif mt == "history":
            msgs = data.get("messages", [])
            if msgs:
                self._sys(f"chat history — last {len(msgs)} messages")
                for m in msgs:
                    if m.get("type") == "message":
                        self._msg(
                            m.get("from", "?"),
                            xor_decrypt(m.get("text", ""), ENCRYPTION_KEY),
                            m.get("ts", ""),
                        )
                    elif m.get("type") == "system":
                        self._sys(m.get("text", ""))
                self._sys("live chat")
                
        elif mt == "kicked":
            # Admin kicked or banned us
            self._disconnected(data.get("reason", "kicked by admin"))
            try:
                self.sock.close()
            except Exception:
                pass

        elif mt == "conn_log":
            entries = data.get("entries", [])
            self._show_conn_log(entries)

    def _show_conn_log(self, entries: list):
        """Show connection log in a popup window."""
        top = tk.Toplevel(self.root)
        top.title("Connection Log")
        top.geometry("600x400")
        top.configure(bg=self.theme["bg"])
        
        txt = scrolledtext.ScrolledText(top, font=("Consolas", 10), bg=self.theme["panel_bg"], fg=self.theme["text"])
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        
        txt.insert("end", f"{'TIME':<22} | {'USER':<15} | {'IP':<15} | {'EVENT'}\n")
        txt.insert("end", "-" * 70 + "\n")
        
        for e in entries:
            ts   = e.get("ts", "")[:19] # trim microseconds
            user = e.get("username", "")[:14]
            ip   = e.get("ip", "")[:14]
            evt  = e.get("event", "")
            txt.insert("end", f"{ts:<22} | {user:<15} | {ip:<15} | {evt}\n")
            
        txt.config(state="disabled")

    # ──────────────────────────────────────────────────────────────────────────
    #  DISCONNECT
    # ──────────────────────────────────────────────────────────────────────────

    def _disconnected(self, reason: str = ""):
        self.connected = False
        self.conn_lbl.config(text="● DISCONNECTED", fg=self.theme["warn"])
        self.send_btn.config(state="disabled")
        self.msg_entry.config(state="disabled")
        self.dot_lbl.config(fg=self.theme["warn"])
        self._sys(f"disconnected — {reason}" if reason else "disconnected")

    def _on_close(self):
        """Minimize to system tray instead of quitting directly."""
        if not (PIL_AVAILABLE and HAS_TRAY):
            self._quit_app()
            return
            
        self.root.withdraw()  # Hide main window
        
        # Create a simple icon for the tray
        image = Image.new('RGB', (64, 64), color=(0, 212, 255))
        dc = ImageDraw.Draw(image)
        dc.rectangle([16, 16, 48, 48], fill=(13, 17, 23))

        menu = pystray.Menu(
            pystray.MenuItem('Open', self._show_window, default=True),
            pystray.MenuItem('Quit', self._quit_app)
        )
        self._tray = pystray.Icon("ChatApp", image, "ChatApp", menu)
        
        # Run tray in a thread so Tkinter mainloop can wait
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _show_window(self, icon, item):
        self._tray.stop()
        self.root.after(0, self.root.deiconify)

    def _quit_app(self, icon=None, item=None):
        if getattr(self, '_tray', None):
            self._tray.stop()
        if self.connected:
            try:
                self._tx({"type": "command", "cmd": "exit"})
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception:
                pass
        self.root.destroy()
        os._exit(0)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()