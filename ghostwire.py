"""
GhostWire – multi-user secure Morse-code messaging app
Powered by Supabase for real-time messaging and invite-code contacts.
Video/audio calls powered by Jitsi Meet via pywebview — FREE, no account, no API key.

Setup:
    pip install pillow pywebview

macOS: When asked for camera/microphone permission, click Allow.
       pywebview uses the real WebKit engine so permissions work natively.
"""

import base64
import hashlib
import os
import random
import string
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox

# ── Supabase (REST only, no extra SDK needed) ─────────────────────────────────
import urllib.request
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import urllib.parse
import json

SUPABASE_URL = "https://ovntepipcokcpccamybx.supabase.co"
SUPABASE_KEY = "sb_publishable_GhhQaMSEYQUTLxfr4Y_enA_Nd1ce-7A"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def sb_request(method: str, path: str, data: dict = None, params: dict = None) -> list | dict | None:
    url = SUPABASE_URL + "/rest/v1/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        print(f"[Supabase] {method} {path} → {e.code}: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"[Supabase] {method} {path} → {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
#  Jitsi helpers
# ──────────────────────────────────────────────────────────────────────────────

JITSI_SERVER = "https://meet.jit.si"  # free, no account needed


def make_jitsi_room_name() -> str:
    """Generate a hard-to-guess room name."""
    chars = string.ascii_lowercase + string.digits
    return "ghostwire-" + "".join(random.choices(chars, k=16))


def jitsi_room_url(room_name: str, start_audio_only: bool = False) -> str:
    """
    Build a Jitsi Meet URL with config fragment parameters.
    startWithVideoMuted=true  → audio-only call
    """
    base = f"{JITSI_SERVER}/{room_name}"
    if start_audio_only:
        base += "#config.startWithVideoMuted=true&config.startWithAudioMuted=false"
    return base


def open_jitsi_window(url: str, title: str = "GhostWire Call") -> None:
    """
    Open Jitsi in an embedded pywebview window.
    Camera and microphone work natively through WebKit on macOS.
    Falls back to the system browser if pywebview isn't installed.
    """
    try:
        import webview  # pywebview

        def _run():
            window = webview.create_window(
                title, url,
                width=1024, height=720,
                min_size=(640, 480),
                resizable=True,
            )
            # On macOS, pywebview uses WKWebView which handles media permissions.
            webview.start(gui='cocoa')  # 'cocoa' on Mac; auto-detects on other OS

        threading.Thread(target=_run, daemon=True).start()

    except ImportError:
        # Graceful fallback — open in browser with a note
        webbrowser.open(url)
        messagebox.showinfo(
            "pywebview not installed",
            "The call opened in your browser instead.\n\n"
            "For an embedded call window with native camera/mic support, run:\n"
            "  pip install pywebview")


# ──────────────────────────────────────────────────────────────────────────────
#  Morse utilities
# ──────────────────────────────────────────────────────────────────────────────

MORSE_CODE = {
    'A': '.-',    'B': '-...',  'C': '-.-.',  'D': '-..',
    'E': '.',     'F': '..-.',  'G': '--.',   'H': '....',
    'I': '..',    'J': '.---',  'K': '-.-',   'L': '.-..',
    'M': '--',    'N': '-.',    'O': '---',   'P': '.--.',
    'Q': '--.-',  'R': '.-.',   'S': '...',   'T': '-',
    'U': '..-',   'V': '...-',  'W': '.--',   'X': '-..-',
    'Y': '-.--',  'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', '!': '-.-.--',
    ' ': '/',
}
REVERSE_MORSE = {v: k for k, v in MORSE_CODE.items()}


def to_morse(text: str) -> str:
    return ' '.join(MORSE_CODE.get(c.upper(), '') for c in text).strip()


def from_morse(morse: str) -> str:
    if not morse or not morse.strip():
        return ''
    words = morse.strip().split(' / ')
    return ' '.join(''.join(REVERSE_MORSE.get(c, '?') for c in w.split()) for w in words)


# ──────────────────────────────────────────────────────────────────────────────
#  Auth helpers
# ──────────────────────────────────────────────────────────────────────────────

def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.sha3_512(salt + password.encode()).hexdigest()


def db_register(username: str, password: str) -> tuple[bool, str]:
    salt = os.urandom(16)
    hashed = _hash_password(password, salt)
    result = sb_request("POST", "users", {
        "username": username,
        "password_hash": hashed,
        "salt": base64.b64encode(salt).decode(),
    })
    if result is None:
        return False, "Username already exists or server error."
    return True, result[0]["id"] if isinstance(result, list) else result.get("id", "")


def db_login(username: str, password: str) -> tuple[bool, str]:
    rows = sb_request("GET", "users", params={"username": f"eq.{username}", "select": "id,password_hash,salt"})
    if not rows:
        return False, "User not found."
    row = rows[0]
    salt = base64.b64decode(row["salt"])
    if _hash_password(password, salt) == row["password_hash"]:
        return True, row["id"]
    return False, "Incorrect password."


# ──────────────────────────────────────────────────────────────────────────────
#  Invite code helpers
# ──────────────────────────────────────────────────────────────────────────────

def generate_invite_code(user_id: str) -> str:
    code = "GW-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    sb_request("POST", "invite_codes", {
        "code": code,
        "created_by": user_id,
        "used": False,
    })
    return code


def redeem_invite_code(code: str, my_user_id: str) -> tuple[bool, str]:
    rows = sb_request("GET", "invite_codes", params={
        "code": f"eq.{code}",
        "used": "eq.false",
        "select": "code,created_by",
    })
    if not rows:
        return False, "Invalid or already-used code."
    row = rows[0]
    their_id = row["created_by"]
    if their_id == my_user_id:
        return False, "You can't add yourself."
    sb_request("PATCH", f"invite_codes?code=eq.{code}", {"used": True})
    user_rows = sb_request("GET", "users", params={"id": f"eq.{their_id}", "select": "username"})
    their_name = user_rows[0]["username"] if user_rows else "Unknown"
    sb_request("POST", "contacts", {"user_id": my_user_id, "contact_id": their_id})
    sb_request("POST", "contacts", {"user_id": their_id,   "contact_id": my_user_id})
    return True, their_name


# ──────────────────────────────────────────────────────────────────────────────
#  Messaging helpers
# ──────────────────────────────────────────────────────────────────────────────

def fetch_contacts(user_id: str) -> list[dict]:
    rows = sb_request("GET", "contacts", params={
        "user_id": f"eq.{user_id}",
        "select": "contact_id",
    })
    if not rows:
        return []
    contacts = []
    for r in rows:
        cid = r["contact_id"]
        user_rows = sb_request("GET", "users", params={"id": f"eq.{cid}", "select": "id,username"})
        if user_rows:
            u = user_rows[0]
            initials = "".join(w[0].upper() for w in u["username"].split()[:2]) or u["username"][:2].upper()
            contacts.append({"id": cid, "name": u["username"], "initials": initials})
    return contacts


def fetch_messages(my_id: str, their_id: str) -> list[dict]:
    sent = sb_request("GET", "messages", params={
        "sender_id": f"eq.{my_id}",
        "receiver_id": f"eq.{their_id}",
        "order": "created_at.asc",
        "select": "sender_id,morse,original,created_at",
    }) or []
    recv = sb_request("GET", "messages", params={
        "sender_id": f"eq.{their_id}",
        "receiver_id": f"eq.{my_id}",
        "order": "created_at.asc",
        "select": "sender_id,morse,original,created_at",
    }) or []
    all_msgs = sent + recv
    all_msgs.sort(key=lambda r: r.get("created_at", ""))
    result = []
    for r in all_msgs:
        side = "sent" if r["sender_id"] == my_id else "recv"
        result.append({"side": side, "morse": r["morse"], "original": r["original"]})
    return result


def send_message(sender_id: str, receiver_id: str, morse: str, original: str) -> bool:
    result = sb_request("POST", "messages", {
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "morse": morse,
        "original": original,
    })
    return result is not None


# ──────────────────────────────────────────────────────────────────────────────
#  Call helpers (Jitsi-backed, stored in Supabase for signalling)
# ──────────────────────────────────────────────────────────────────────────────

def db_create_call(caller_id: str, receiver_id: str,
                   room_url: str, room_name: str) -> str | None:
    result = sb_request("POST", "calls", {
        "caller_id":       caller_id,
        "receiver_id":     receiver_id,
        "status":          "ringing",
        "daily_room_url":  room_url,    # column reused for Jitsi URL
        "daily_room_name": room_name,   # column reused for Jitsi room name
    })
    if result:
        row = result[0] if isinstance(result, list) else result
        return row.get("id")
    return None


def db_get_incoming_call(user_id: str) -> dict | None:
    rows = sb_request("GET", "calls", params={
        "receiver_id": f"eq.{user_id}",
        "status":      "eq.ringing",
        "select":      "id,caller_id,daily_room_url,daily_room_name,created_at",
        "order":       "created_at.desc",
        "limit":       "1",
    })
    return rows[0] if rows else None


def db_update_call_status(call_id: str, status: str) -> None:
    sb_request("PATCH", f"calls?id=eq.{call_id}", {"status": status})


def db_get_call(call_id: str) -> dict | None:
    rows = sb_request("GET", "calls", params={
        "id":     f"eq.{call_id}",
        "select": "status,daily_room_url,daily_room_name",
    })
    return rows[0] if rows else None


def db_is_call_active(call_id: str) -> bool:
    rows = sb_request("GET", "calls", params={
        "id":     f"eq.{call_id}",
        "select": "status",
    })
    if not rows:
        return False
    return rows[0].get("status") in ("ringing", "active")


def db_get_caller_name(caller_id: str) -> str:
    rows = sb_request("GET", "users", params={
        "id":     f"eq.{caller_id}",
        "select": "username",
    })
    return rows[0]["username"] if rows else "Unknown"


# ──────────────────────────────────────────────────────────────────────────────
#  Colour palette
# ──────────────────────────────────────────────────────────────────────────────

BG_DARK      = '#0b0d14'
BG_PANEL     = '#13151f'
BG_CARD      = '#1a1d2e'
BG_INPUT     = '#21253a'
BG_SENT      = '#2d2a52'
BG_RECV      = '#1a1d2e'
BG_HOVER     = '#252840'
BG_ACTIVE    = '#1e2038'

ACCENT       = '#7c6af7'
ACCENT_HOVER = '#9182ff'

TEAL         = '#2dd4a0'
TEAL_DARK    = '#163d2e'
TEAL_FG      = '#7ef5c8'

TEXT_PRI     = '#d6d3e8'
TEXT_SEC     = '#7a7897'
TEXT_MORSE   = '#4a4868'
TEXT_SENT    = '#c4beff'

BORDER       = '#252840'
BORDER_LIGHT = '#2e3152'

RED_ERR      = '#e05c6a'
GREEN_OK     = '#2dd4a0'

CONTACT_COLORS = ['#7c6af7', '#2dd4a0', '#c45c8a', '#d4893a', '#4a90d9', '#c0a030']


# ──────────────────────────────────────────────────────────────────────────────
#  Widget helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_entry(parent, textvariable, show=None):
    return tk.Entry(
        parent, textvariable=textvariable, show=show,
        font=('Helvetica', 12), bg=BG_INPUT, fg=TEXT_PRI,
        insertbackground=ACCENT, relief='flat',
        highlightthickness=1, highlightbackground=BORDER_LIGHT,
        highlightcolor=ACCENT,
    )


def make_btn(parent, text, command, fg='#d6d3e8', bg=ACCENT, hover=ACCENT_HOVER,
             font_size=10, bold=True, padx=16, pady=8):
    weight = 'bold' if bold else 'normal'
    btn = tk.Button(
        parent, text=text, command=command,
        font=('Helvetica', font_size, weight),
        bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
        relief='flat', cursor='hand2', padx=padx, pady=pady, bd=0,
    )
    btn.bind('<Enter>', lambda e: btn.config(bg=hover))
    btn.bind('<Leave>', lambda e: btn.config(bg=bg))
    return btn


def divider(parent):
    return tk.Frame(parent, bg=BORDER, height=1)


# ──────────────────────────────────────────────────────────────────────────────
#  Auth screen
# ──────────────────────────────────────────────────────────────────────────────

class AuthScreen(tk.Frame):

    def __init__(self, master, on_success):
        super().__init__(master, bg=BG_DARK)
        self.master = master
        self.on_success = on_success
        self._mode = 'login'
        self._build()

    def _build(self):
        self.place(relx=0, rely=0, relwidth=1, relheight=1)

        card = tk.Frame(self, bg=BG_PANEL,
                        highlightthickness=1, highlightbackground=BORDER_LIGHT)
        card.place(relx=0.5, rely=0.5, anchor='center', width=400)

        logo = tk.Frame(card, bg=BG_PANEL, pady=30)
        logo.pack(fill='x')
        tk.Label(logo, text='◉', font=('Courier', 30, 'bold'),
                 bg=BG_PANEL, fg=ACCENT).pack()
        tk.Label(logo, text='GhostWire', font=('Helvetica', 20, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(pady=(4, 0))
        tk.Label(logo, text='secure · morse · messaging',
                 font=('Helvetica', 9), bg=BG_PANEL, fg=TEXT_MORSE).pack(pady=(3, 0))

        divider(card).pack(fill='x')

        tabs = tk.Frame(card, bg=BG_CARD)
        tabs.pack(fill='x')
        tabs.grid_columnconfigure(0, weight=1)
        tabs.grid_columnconfigure(1, weight=1)

        self._tab_login = tk.Button(
            tabs, text='Login', font=('Helvetica', 10, 'bold'),
            bg=ACCENT, fg='#d6d3e8', activebackground=ACCENT_HOVER,
            relief='flat', cursor='hand2', pady=10,
            command=lambda: self._switch('login'))
        self._tab_login.grid(row=0, column=0, sticky='ew')

        self._tab_reg = tk.Button(
            tabs, text='Register', font=('Helvetica', 10, 'bold'),
            bg=BG_CARD, fg=TEXT_SEC, activebackground=BG_HOVER,
            relief='flat', cursor='hand2', pady=10,
            command=lambda: self._switch('register'))
        self._tab_reg.grid(row=0, column=1, sticky='ew')

        divider(card).pack(fill='x')

        form = tk.Frame(card, bg=BG_PANEL, padx=36, pady=28)
        form.pack(fill='x')

        tk.Label(form, text='Username', font=('Helvetica', 9),
                 bg=BG_PANEL, fg=TEXT_SEC).pack(anchor='w')
        self._user_var = tk.StringVar()
        self._user_entry = make_entry(form, self._user_var)
        self._user_entry.pack(fill='x', ipady=8, pady=(3, 16))

        tk.Label(form, text='Password', font=('Helvetica', 9),
                 bg=BG_PANEL, fg=TEXT_SEC).pack(anchor='w')
        self._pw_var = tk.StringVar()
        self._pw_entry = make_entry(form, self._pw_var, show='●')
        self._pw_entry.pack(fill='x', ipady=8, pady=(3, 0))

        self._confirm_frame = tk.Frame(form, bg=BG_PANEL)
        self._confirm_frame.pack(fill='x')
        tk.Label(self._confirm_frame, text='Confirm Password', font=('Helvetica', 9),
                 bg=BG_PANEL, fg=TEXT_SEC).pack(anchor='w', pady=(16, 0))
        self._confirm_var = tk.StringVar()
        make_entry(self._confirm_frame, self._confirm_var,
                   show='●').pack(fill='x', ipady=8, pady=(3, 0))
        self._confirm_frame.pack_forget()

        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(
            form, textvariable=self._status_var,
            font=('Helvetica', 9), bg=BG_PANEL, fg=RED_ERR,
            wraplength=310, justify='left')
        self._status_lbl.pack(anchor='w', pady=(12, 0))

        self._submit_btn = make_btn(form, 'Login  →', self._submit, font_size=11, pady=10)
        self._submit_btn.pack(fill='x', pady=(14, 4))

        self.master.bind('<Return>', lambda e: self._submit())
        self._user_entry.focus_set()

    def _switch(self, mode: str) -> None:
        self._mode = mode
        self._status_var.set('')
        if mode == 'login':
            self._tab_login.config(bg=ACCENT, fg='#d6d3e8')
            self._tab_reg.config(bg=BG_CARD, fg=TEXT_SEC)
            self._confirm_frame.pack_forget()
            self._submit_btn.config(text='Login  →')
        else:
            self._tab_reg.config(bg=ACCENT, fg='#d6d3e8')
            self._tab_login.config(bg=BG_CARD, fg=TEXT_SEC)
            self._confirm_frame.pack(fill='x')
            self._submit_btn.config(text='Create Account  →')

    def _submit(self) -> None:
        username = self._user_var.get().strip()
        password = self._pw_var.get()
        if not username or not password:
            self._set_status('Please fill in all fields.', error=True)
            return
        self._submit_btn.config(state='disabled', text='Please wait…')
        self.update()
        if self._mode == 'register':
            if password != self._confirm_var.get():
                self._set_status('Passwords do not match.', error=True)
                self._submit_btn.config(state='normal', text='Create Account  →')
                return
            if len(password) < 6:
                self._set_status('Password must be at least 6 characters.', error=True)
                self._submit_btn.config(state='normal', text='Create Account  →')
                return
            ok, result = db_register(username, password)
            if ok:
                self._set_status('Account created! Logging you in…', error=False)
                self.after(800, lambda: self._launch(username, result))
            else:
                self._set_status(result, error=True)
                self._submit_btn.config(state='normal', text='Create Account  →')
        else:
            ok, result = db_login(username, password)
            if ok:
                self._set_status(f'Welcome back, {username}!', error=False)
                self.after(500, lambda: self._launch(username, result))
            else:
                self._set_status(result, error=True)
                self._submit_btn.config(state='normal', text='Login  →')

    def _set_status(self, msg: str, error: bool = True) -> None:
        self._status_var.set(msg)
        self._status_lbl.config(fg=RED_ERR if error else GREEN_OK)

    def _launch(self, username: str, user_id: str) -> None:
        self.master.unbind('<Return>')
        self.destroy()
        self.on_success(username, user_id)


# ──────────────────────────────────────────────────────────────────────────────
#  Invite code dialog
# ──────────────────────────────────────────────────────────────────────────────

class InviteDialog(tk.Toplevel):

    def __init__(self, master, user_id: str, on_contact_added):
        super().__init__(master)
        self.title('Add Contact')
        self.configure(bg=BG_PANEL)
        self.resizable(False, False)
        self.grab_set()
        self._user_id = user_id
        self._on_contact_added = on_contact_added
        self._build()
        self.geometry('440x380')

    def _build(self):
        pad = tk.Frame(self, bg=BG_PANEL, padx=30, pady=24)
        pad.pack(fill='both', expand=True)

        tk.Label(pad, text='Add Contact', font=('Helvetica', 14, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(anchor='w')
        tk.Label(pad, text="Share your code or enter a friend's code",
                 font=('Helvetica', 9), bg=BG_PANEL, fg=TEXT_SEC).pack(anchor='w', pady=(2, 16))

        divider(pad).pack(fill='x', pady=(0, 16))

        tk.Label(pad, text='YOUR INVITE CODE', font=('Helvetica', 8, 'bold'),
                 bg=BG_PANEL, fg=TEXT_MORSE).pack(anchor='w')

        code_row = tk.Frame(pad, bg=BG_PANEL)
        code_row.pack(fill='x', pady=(4, 0))

        self._my_code_var = tk.StringVar(value='Click Generate to get a code')
        code_lbl = tk.Label(code_row, textvariable=self._my_code_var,
                             font=('Courier', 13, 'bold'), bg=BG_CARD, fg=ACCENT,
                             padx=12, pady=10, anchor='w')
        code_lbl.pack(side='left', fill='x', expand=True)

        gen_btn = make_btn(code_row, 'Generate', self._generate,
                           font_size=9, padx=10, pady=10)
        gen_btn.pack(side='right', padx=(8, 0))

        tk.Label(pad, text='Share this code once — it deletes after use.',
                 font=('Helvetica', 8), bg=BG_PANEL, fg=TEXT_MORSE).pack(anchor='w', pady=(4, 20))

        divider(pad).pack(fill='x', pady=(0, 16))

        tk.Label(pad, text="ENTER A FRIEND'S CODE", font=('Helvetica', 8, 'bold'),
                 bg=BG_PANEL, fg=TEXT_MORSE).pack(anchor='w')

        enter_row = tk.Frame(pad, bg=BG_PANEL)
        enter_row.pack(fill='x', pady=(4, 0))
        enter_row.grid_columnconfigure(0, weight=1)

        self._code_var = tk.StringVar()
        code_entry = make_entry(enter_row, self._code_var)
        code_entry.grid(row=0, column=0, sticky='ew', ipady=8, padx=(0, 8))
        code_entry.bind('<Return>', lambda e: self._redeem())

        make_btn(enter_row, 'Add', self._redeem,
                 font_size=9, padx=14, pady=8).grid(row=0, column=1)

        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(pad, textvariable=self._status_var,
                                     font=('Helvetica', 9), bg=BG_PANEL, fg=RED_ERR,
                                     wraplength=360)
        self._status_lbl.pack(anchor='w', pady=(10, 0))

    def _generate(self):
        code = generate_invite_code(self._user_id)
        self._my_code_var.set(code)

    def _redeem(self):
        code = self._code_var.get().strip().upper()
        if not code:
            return
        self._status_var.set('Connecting…')
        self._status_lbl.config(fg=TEXT_SEC)
        self.update()
        ok, result = redeem_invite_code(code, self._user_id)
        if ok:
            self._status_var.set(f'Added {result}!')
            self._status_lbl.config(fg=GREEN_OK)
            self.after(1000, lambda: (self._on_contact_added(), self.destroy()))
        else:
            self._status_var.set(result)
            self._status_lbl.config(fg=RED_ERR)


# ──────────────────────────────────────────────────────────────────────────────
#  Incoming call dialog
# ──────────────────────────────────────────────────────────────────────────────

class IncomingCallDialog(tk.Toplevel):

    def __init__(self, master, call_id: str, caller_name: str,
                 room_url: str, on_accept, on_decline):
        super().__init__(master)
        self.title('Incoming Call')
        self.configure(bg=BG_PANEL)
        self.resizable(False, False)
        self.grab_set()
        self.attributes('-topmost', True)
        self._call_id   = call_id
        self._room_url  = room_url
        self._on_accept = on_accept
        self._on_decline = on_decline
        self._build(caller_name)
        self.geometry('340x240')
        self._centre()

    def _centre(self):
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width()  - 340) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - 240) // 2
        self.geometry(f'340x240+{x}+{y}')

    def _build(self, caller_name: str):
        pad = tk.Frame(self, bg=BG_PANEL, padx=30, pady=24)
        pad.pack(fill='both', expand=True)

        ring = tk.Canvas(pad, width=60, height=60, bg=BG_PANEL, highlightthickness=0)
        ring.pack()
        ring.create_oval(5, 5, 55, 55, fill=TEAL, outline='')
        ring.create_text(30, 30, text='📞', font=('Helvetica', 20))
        self._animate_ring(ring)

        tk.Label(pad, text=caller_name, font=('Helvetica', 15, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(pady=(10, 2))
        tk.Label(pad, text='Incoming GhostWire call…',
                 font=('Helvetica', 9), bg=BG_PANEL, fg=TEXT_SEC).pack()

        # Show whether it's a video or audio-only call
        is_audio_only = 'startWithVideoMuted=true' in self._room_url
        call_type_txt = '🎙  Audio-only call' if is_audio_only else '📹  Video + audio call'
        tk.Label(pad, text=call_type_txt,
                 font=('Helvetica', 9, 'bold'), bg=BG_PANEL, fg=TEAL).pack(pady=(4, 0))

        btns = tk.Frame(pad, bg=BG_PANEL)
        btns.pack(pady=(18, 0))

        dec = tk.Button(btns, text='✕  Decline', font=('Helvetica', 10, 'bold'),
                        bg=RED_ERR, fg='white', activebackground='#c0455a',
                        relief='flat', cursor='hand2', padx=16, pady=8,
                        command=self._decline)
        dec.pack(side='left', padx=(0, 12))

        acc = tk.Button(btns, text='✓  Accept', font=('Helvetica', 10, 'bold'),
                        bg=TEAL, fg='#0b0d14', activebackground='#25b88a',
                        relief='flat', cursor='hand2', padx=16, pady=8,
                        command=self._accept)
        acc.pack(side='left')

    def _animate_ring(self, canvas, step=0):
        colours = [TEAL, '#25b88a', TEAL, '#1fa077']
        canvas.configure(bg=colours[step % len(colours)])
        self._anim_job = self.after(400, lambda: self._animate_ring(canvas, step + 1))

    def _accept(self):
        if hasattr(self, '_anim_job'):
            self.after_cancel(self._anim_job)
        db_update_call_status(self._call_id, 'active')
        self.destroy()
        self._on_accept(self._call_id, self._room_url)

    def _decline(self):
        if hasattr(self, '_anim_job'):
            self.after_cancel(self._anim_job)
        db_update_call_status(self._call_id, 'declined')
        self.destroy()
        self._on_decline()


# ──────────────────────────────────────────────────────────────────────────────
#  Active call status window
# ──────────────────────────────────────────────────────────────────────────────

class CallStatusWindow(tk.Toplevel):
    """
    Small always-on-top overlay shown while a Jitsi call is running.
    The actual video/audio plays inside a pywebview window (real WebKit).
    This overlay shows elapsed time, call type, and an End Call button.
    """

    POLL_MS = 4000

    def __init__(self, master, call_id: str, remote_name: str,
                 room_name: str, call_type: str, on_end):
        super().__init__(master)
        self.title(f'Call with {remote_name}')
        self.configure(bg=BG_DARK)
        self.geometry('320x200')
        self.resizable(False, False)
        self.attributes('-topmost', True)

        self._call_id    = call_id
        self._remote     = remote_name
        self._room_name  = room_name
        self._call_type  = call_type   # 'video' or 'audio'
        self._on_end     = on_end
        self._running    = True
        self._elapsed    = 0

        self._build_ui()
        self._schedule_poll()
        self._tick()
        self.protocol('WM_DELETE_WINDOW', self._hang_up)

    def _build_ui(self):
        pad = tk.Frame(self, bg=BG_DARK, padx=20, pady=16)
        pad.pack(fill='both', expand=True)

        # Status row
        dot_row = tk.Frame(pad, bg=BG_DARK)
        dot_row.pack()
        self._dot_canvas = tk.Canvas(dot_row, width=12, height=12,
                                     bg=BG_DARK, highlightthickness=0)
        self._dot_canvas.pack(side='left', padx=(0, 6))
        self._dot = self._dot_canvas.create_oval(1, 1, 11, 11, fill=TEAL, outline='')

        call_label = ('📹  Jitsi video call' if self._call_type == 'video'
                      else '🎙  Jitsi audio-only call')
        tk.Label(dot_row, text=call_label,
                 font=('Helvetica', 9), bg=BG_DARK, fg=TEAL).pack(side='left')

        tk.Label(pad, text=self._remote,
                 font=('Helvetica', 16, 'bold'), bg=BG_DARK, fg=TEXT_PRI).pack(pady=(10, 2))

        self._timer_var = tk.StringVar(value='00:00')
        tk.Label(pad, textvariable=self._timer_var,
                 font=('Courier', 12), bg=BG_DARK, fg=TEXT_SEC).pack()

        tk.Label(pad, text='Camera & mic running in embedded WebKit window',
                 font=('Helvetica', 8), bg=BG_DARK, fg=TEXT_MORSE).pack(pady=(4, 0))

        btn_row = tk.Frame(pad, bg=BG_DARK)
        btn_row.pack(pady=(14, 0))

        tk.Button(btn_row, text='⬛  End Call',
                  font=('Helvetica', 10, 'bold'),
                  bg=RED_ERR, fg='white', activebackground='#c0455a',
                  relief='flat', cursor='hand2', padx=18, pady=7,
                  command=self._hang_up).pack()

    def _tick(self):
        if not self._running:
            return
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self._timer_var.set(f'{m:02d}:{s:02d}')
        colour = TEAL if self._elapsed % 2 == 0 else TEAL_DARK
        self._dot_canvas.itemconfig(self._dot, fill=colour)
        self._tick_job = self.after(1000, self._tick)

    def _schedule_poll(self):
        if not self._running:
            return
        threading.Thread(target=self._check_status, daemon=True).start()
        self._poll_job = self.after(self.POLL_MS, self._schedule_poll)

    def _check_status(self):
        if not db_is_call_active(self._call_id):
            self.after(0, self._remote_hung_up)

    def _remote_hung_up(self):
        if not self._running:
            return
        self._running = False
        self._cancel_jobs()
        tk.Label(self, text='Call ended by remote', font=('Helvetica', 10),
                 bg=BG_DARK, fg=RED_ERR).place(relx=0.5, rely=0.5, anchor='center')
        self.after(2500, self._close)

    def _hang_up(self):
        self._running = False
        self._cancel_jobs()
        db_update_call_status(self._call_id, 'ended')
        self._close()

    def _cancel_jobs(self):
        for attr in ('_tick_job', '_poll_job'):
            job = getattr(self, attr, None)
            if job:
                try: self.after_cancel(job)
                except Exception: pass

    def _close(self):
        self._on_end()
        try: self.destroy()
        except Exception: pass


# ──────────────────────────────────────────────────────────────────────────────
#  Main chat application
# ──────────────────────────────────────────────────────────────────────────────

class MorseChatApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('GhostWire')
        self.geometry('920x640')
        self.minsize(720, 520)
        self.configure(bg=BG_DARK)
        self.resizable(True, True)
        self._poll_job = None
        AuthScreen(self, self._on_login)

    def _on_login(self, username: str, user_id: str) -> None:
        self._username = username
        self._user_id  = user_id
        self.contacts  = []
        self.histories = {}
        self.active_contact = None
        self._active_call = None                  # FIX: was missing
        self._seen_incoming_call_id = None        # FIX: was missing
        self._build_ui()
        self._reload_contacts()
        self._start_polling()

    # ── Polling ───────────────────────────────────────────────────────────────

    def _start_polling(self):
        self._poll()

    def _poll(self):
        if self.active_contact:
            self._refresh_messages()
        self._check_incoming_calls()              # FIX: was missing from poll loop
        self._poll_job = self.after(3000, self._poll)

    def _refresh_messages(self):
        if not self.active_contact:
            return
        their_id = self.active_contact['id']
        msgs = fetch_messages(self._user_id, their_id)
        current = self.histories.get(self.active_contact['name'], [])
        if len(msgs) != len(current):
            self.histories[self.active_contact['name']] = msgs
            self._redraw_messages()

    def _redraw_messages(self):
        for w in self.msg_frame.winfo_children():
            w.destroy()
        name = self.active_contact['name']
        for msg in self.histories.get(name, []):
            self._render_message(msg['side'], msg['morse'], msg['original'])
        self._scroll_bottom()

    # ── Contacts ──────────────────────────────────────────────────────────────

    def _reload_contacts(self):
        def _fetch():
            contacts = fetch_contacts(self._user_id)
            self.after(0, lambda: self._update_contacts(contacts))
        threading.Thread(target=_fetch, daemon=True).start()

    def _update_contacts(self, contacts: list):
        self.contacts = contacts
        for c in self.contacts:
            if c['name'] not in self.histories:
                self.histories[c['name']] = []
            c['color'] = CONTACT_COLORS[hash(c['name']) % len(CONTACT_COLORS)]

        for w in self._contacts_frame.winfo_children():
            w.destroy()
        self.contact_btns = {}

        if not self.contacts:
            tk.Label(self._contacts_frame,
                     text='No contacts yet.\nClick + to add someone.',
                     font=('Helvetica', 9), bg=BG_PANEL, fg=TEXT_MORSE,
                     justify='center').pack(pady=20)
        else:
            for c in self.contacts:
                self._make_contact_row(self._contacts_frame, c)

        if self.contacts and not self.active_contact:
            self._switch_contact(self.contacts[0])

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_chat_pane()

    def _build_sidebar(self) -> None:
        side = tk.Frame(self, bg=BG_PANEL, width=240)
        side.grid(row=0, column=0, sticky='nsew')
        side.grid_propagate(False)
        side.grid_rowconfigure(2, weight=1)
        side.grid_columnconfigure(0, weight=1)

        hdr = tk.Frame(side, bg=BG_PANEL, pady=14, padx=14)
        hdr.grid(row=0, column=0, sticky='ew')

        top_row = tk.Frame(hdr, bg=BG_PANEL)
        top_row.pack(fill='x')
        tk.Label(top_row, text='◉', font=('Courier', 13, 'bold'),
                 bg=BG_PANEL, fg=ACCENT).pack(side='left', padx=(0, 6))
        tk.Label(top_row, text='GhostWire', font=('Helvetica', 12, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side='left')

        user_row = tk.Frame(hdr, bg=BG_PANEL)
        user_row.pack(fill='x', pady=(8, 0))

        dot_c = tk.Canvas(user_row, width=8, height=8, bg=BG_PANEL, highlightthickness=0)
        dot_c.pack(side='left', padx=(0, 6))
        dot_c.create_oval(1, 1, 7, 7, fill=TEAL, outline='')
        tk.Label(user_row, text=self._username, font=('Helvetica', 10),
                 bg=BG_PANEL, fg=TEXT_SEC).pack(side='left')

        logout_btn = tk.Button(
            user_row, text='logout', font=('Helvetica', 8),
            bg=BG_PANEL, fg=TEXT_MORSE, activebackground=BG_HOVER,
            relief='flat', cursor='hand2', padx=6, pady=2,
            command=self._logout)
        logout_btn.pack(side='right')
        logout_btn.bind('<Enter>', lambda e: logout_btn.config(fg=TEXT_SEC))
        logout_btn.bind('<Leave>', lambda e: logout_btn.config(fg=TEXT_MORSE))

        divider(side).grid(row=1, column=0, sticky='ew')

        contacts_wrap = tk.Frame(side, bg=BG_PANEL)
        contacts_wrap.grid(row=2, column=0, sticky='nsew', pady=6)

        conv_hdr = tk.Frame(contacts_wrap, bg=BG_PANEL)
        conv_hdr.pack(fill='x', padx=10, pady=(8, 4))
        tk.Label(conv_hdr, text='CONVERSATIONS',
                 font=('Helvetica', 8, 'bold'), bg=BG_PANEL,
                 fg=TEXT_MORSE).pack(side='left', padx=6)
        add_btn = make_btn(conv_hdr, '+ Add Contact', self._open_invite,
                           font_size=8, bold=True, padx=8, pady=4,
                           bg=ACCENT, hover=ACCENT_HOVER)
        add_btn.pack(side='right')

        self._contacts_frame = tk.Frame(contacts_wrap, bg=BG_PANEL)
        self._contacts_frame.pack(fill='both', expand=True)
        self.contact_btns = {}

    def _make_contact_row(self, parent, c: dict) -> None:
        name      = c['name']
        is_active = self.active_contact and self.active_contact['name'] == name
        row_bg    = BG_ACTIVE if is_active else BG_PANEL

        row = tk.Frame(parent, bg=row_bg, cursor='hand2')
        row.pack(fill='x', padx=6, pady=1)
        inner = tk.Frame(row, bg=row_bg, padx=10, pady=9)
        inner.pack(fill='x')

        av = tk.Canvas(inner, width=38, height=38, bg=row_bg, highlightthickness=0)
        av.pack(side='left', padx=(0, 10))
        av.create_oval(2, 2, 36, 36, fill=c['color'], outline='')
        av.create_text(19, 19, text=c['initials'], fill='#d6d3e8',
                       font=('Helvetica', 10, 'bold'))

        txt = tk.Frame(inner, bg=row_bg)
        txt.pack(side='left', fill='x', expand=True)
        name_lbl = tk.Label(txt, text=name, font=('Helvetica', 11, 'bold'),
                             bg=row_bg, fg=TEXT_PRI)
        name_lbl.pack(anchor='w')

        last_msgs = self.histories.get(name, [])
        last = (last_msgs[-1]['morse'][:22] + '…') if last_msgs else '—'
        preview_lbl = tk.Label(txt, text=last, font=('Courier', 8),
                                bg=row_bg, fg=TEXT_MORSE)
        preview_lbl.pack(anchor='w')

        all_w = [row, inner, av, txt, name_lbl, preview_lbl]

        def on_click(e, contact=c):
            self._switch_contact(contact)

        def on_enter(e, widgets=all_w, n=name):
            if not self.active_contact or self.active_contact['name'] != n:
                for w in widgets:
                    try: w.configure(bg=BG_HOVER)
                    except Exception: pass

        def on_leave(e, widgets=all_w, n=name):
            if not self.active_contact or self.active_contact['name'] != n:
                for w in widgets:
                    try: w.configure(bg=BG_PANEL)
                    except Exception: pass

        for w in all_w:
            w.bind('<Button-1>', on_click)
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)

        self.contact_btns[name] = all_w

    def _build_chat_pane(self) -> None:
        pane = tk.Frame(self, bg=BG_DARK)
        pane.grid(row=0, column=1, sticky='nsew')
        pane.grid_rowconfigure(1, weight=1)
        pane.grid_columnconfigure(0, weight=1)

        # ── Chat header ───────────────────────────────────────────────────────
        self.chat_header = tk.Frame(pane, bg=BG_PANEL, pady=12, padx=18)
        self.chat_header.grid(row=0, column=0, columnspan=2, sticky='ew')

        # Contact avatar + name (left side)
        self.hdr_canvas = tk.Canvas(self.chat_header, width=40, height=40,
                                    bg=BG_PANEL, highlightthickness=0)
        self.hdr_canvas.pack(side='left', padx=(0, 12))

        hdr_txt = tk.Frame(self.chat_header, bg=BG_PANEL)
        hdr_txt.pack(side='left')
        self.hdr_name = tk.Label(hdr_txt, text='Select a contact',
                                  font=('Helvetica', 13, 'bold'), bg=BG_PANEL, fg=TEXT_PRI)
        self.hdr_name.pack(anchor='w')
        self.hdr_sub = tk.Label(hdr_txt, text='Add a contact with the + button',
                                 font=('Helvetica', 9), bg=BG_PANEL, fg=TEXT_MORSE)
        self.hdr_sub.pack(anchor='w')

        # ── Call buttons (right side) ─────────────────────────────────────────
        # Jitsi badge
        tk.Label(self.chat_header, text='Jitsi · free · no account',
                 font=('Helvetica', 7), bg=BG_PANEL, fg=TEXT_MORSE).pack(side='right', padx=(0, 6))

        # 📞 Audio-only button
        self._audio_btn = tk.Button(
            self.chat_header,
            text='📞',
            font=('Helvetica', 15),
            bg=BG_PANEL, fg=TEAL,
            activebackground=BG_HOVER,
            relief='flat', cursor='hand2',
            padx=6, pady=2,
            command=lambda: self._start_call(audio_only=True),
        )
        self._audio_btn.pack(side='right', padx=(0, 2))
        self._audio_btn.bind('<Enter>', lambda e: self._audio_btn.config(bg=BG_HOVER))
        self._audio_btn.bind('<Leave>', lambda e: self._audio_btn.config(bg=BG_PANEL))
        self._make_tooltip(self._audio_btn, 'Audio-only call  (camera muted)')

        # 📹 Video call button
        self._video_btn = tk.Button(
            self.chat_header,
            text='📹',
            font=('Helvetica', 15),
            bg=BG_PANEL, fg=ACCENT,
            activebackground=BG_HOVER,
            relief='flat', cursor='hand2',
            padx=6, pady=2,
            command=lambda: self._start_call(audio_only=False),
        )
        self._video_btn.pack(side='right', padx=(0, 4))
        self._video_btn.bind('<Enter>', lambda e: self._video_btn.config(bg=BG_HOVER))
        self._video_btn.bind('<Leave>', lambda e: self._video_btn.config(bg=BG_PANEL))
        self._make_tooltip(self._video_btn, 'Video call  (camera + mic)')

        divider(pane).grid(row=0, column=0, columnspan=2, sticky='sew')

        # ── Message canvas ────────────────────────────────────────────────────
        self.msg_canvas = tk.Canvas(pane, bg=BG_DARK, highlightthickness=0, bd=0)
        self.msg_canvas.grid(row=1, column=0, sticky='nsew')

        sb = tk.Scrollbar(pane, orient='vertical', command=self.msg_canvas.yview,
                          bg=BG_PANEL, troughcolor=BG_DARK, width=6)
        sb.grid(row=1, column=1, sticky='ns')
        self.msg_canvas.configure(yscrollcommand=sb.set)

        self.msg_frame  = tk.Frame(self.msg_canvas, bg=BG_DARK)
        self.msg_window = self.msg_canvas.create_window((0, 0), window=self.msg_frame, anchor='nw')

        self.msg_frame.bind('<Configure>', self._on_frame_configure)
        self.msg_canvas.bind('<Configure>', self._on_canvas_configure)

        self.msg_canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        self.msg_canvas.bind_all('<Button-4>',   lambda e: self.msg_canvas.yview_scroll(-1, 'units'))
        self.msg_canvas.bind_all('<Button-5>',   lambda e: self.msg_canvas.yview_scroll(1, 'units'))

        # ── Input bar ─────────────────────────────────────────────────────────
        inp = tk.Frame(pane, bg=BG_PANEL, pady=12, padx=16)
        inp.grid(row=2, column=0, columnspan=2, sticky='ew')
        inp.grid_columnconfigure(0, weight=1)

        prev_strip = tk.Frame(inp, bg=BG_CARD, padx=10, pady=6,
                               highlightthickness=1, highlightbackground=BORDER)
        prev_strip.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        tk.Label(prev_strip, text='MORSE PREVIEW', font=('Helvetica', 7, 'bold'),
                 bg=BG_CARD, fg=TEXT_MORSE).pack(anchor='w')
        self.preview_var = tk.StringVar(value='start typing…')
        tk.Label(prev_strip, textvariable=self.preview_var,
                 font=('Courier', 10), bg=BG_CARD, fg=ACCENT,
                 anchor='w', wraplength=600, justify='left').pack(anchor='w')

        self.entry_var = tk.StringVar()
        self.entry_var.trace_add('write', self._on_type)
        entry = tk.Entry(inp, textvariable=self.entry_var,
                         font=('Helvetica', 12), bg=BG_INPUT, fg=TEXT_PRI,
                         insertbackground=ACCENT, relief='flat',
                         highlightthickness=1, highlightbackground=BORDER_LIGHT,
                         highlightcolor=ACCENT)
        entry.grid(row=1, column=0, sticky='ew', ipady=9, padx=(0, 10))
        entry.bind('<Return>', lambda e: self._send())

        make_btn(inp, 'Send  ▶', self._send, font_size=10, pady=9, padx=18).grid(row=1, column=1)

    # ── Tooltip helper ────────────────────────────────────────────────────────

    def _make_tooltip(self, widget, text: str) -> None:
        tip = None

        def show(e):
            nonlocal tip
            tip = tk.Toplevel(widget)
            tip.wm_overrideredirect(True)
            tip.attributes('-topmost', True)
            x = widget.winfo_rootx() + widget.winfo_width() // 2
            y = widget.winfo_rooty() - 28
            tip.wm_geometry(f'+{x}+{y}')
            tk.Label(tip, text=text, font=('Helvetica', 9),
                     bg='#2e3152', fg=TEXT_PRI, padx=8, pady=4).pack()

        def hide(e):
            nonlocal tip
            if tip:
                tip.destroy()
                tip = None

        widget.bind('<Enter>', show, add='+')
        widget.bind('<Leave>', hide, add='+')

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_invite(self):
        InviteDialog(self, self._user_id, self._reload_contacts)

    def _logout(self) -> None:
        if messagebox.askyesno('Logout', 'Log out of GhostWire?'):
            if self._poll_job:
                self.after_cancel(self._poll_job)
                self._poll_job = None
            for w in self.winfo_children():
                w.destroy()
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=0)
            AuthScreen(self, self._on_login)

    def _switch_contact(self, contact: dict) -> None:
        self.active_contact = contact
        self._refresh_sidebar_highlight()
        self._load_chat(contact)

    def _refresh_sidebar_highlight(self):
        for name, widgets in self.contact_btns.items():
            color = BG_ACTIVE if (self.active_contact and self.active_contact['name'] == name) else BG_PANEL
            for w in widgets:
                try: w.configure(bg=color)
                except Exception: pass

    def _load_chat(self, contact: dict) -> None:
        self.hdr_name.config(text=contact['name'])
        self.hdr_sub.config(text='GhostWire user', fg=TEAL)
        self.hdr_canvas.delete('all')
        self.hdr_canvas.create_oval(2, 2, 38, 38, fill=contact['color'], outline='')
        self.hdr_canvas.create_text(20, 20, text=contact['initials'],
                                     fill='#d6d3e8', font=('Helvetica', 10, 'bold'))

        def _fetch():
            msgs = fetch_messages(self._user_id, contact['id'])
            self.histories[contact['name']] = msgs
            self.after(0, self._redraw_messages)

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_type(self, *_) -> None:
        text = self.entry_var.get()
        self.preview_var.set(to_morse(text) if text else 'start typing…')

    def _send(self) -> None:
        if not self.active_contact:
            return
        text = self.entry_var.get().strip()
        if not text:
            return
        morse = to_morse(text)
        self.entry_var.set('')
        self.preview_var.set('start typing…')

        def _do_send():
            send_message(self._user_id, self.active_contact['id'], morse, text)
            msgs = fetch_messages(self._user_id, self.active_contact['id'])
            self.histories[self.active_contact['name']] = msgs
            self.after(0, self._redraw_messages)

        threading.Thread(target=_do_send, daemon=True).start()

    def _render_message(self, side: str, morse: str, original: str) -> None:
        outer = tk.Frame(self.msg_frame, bg=BG_DARK)
        outer.pack(fill='x', padx=16, pady=6)

        if side == 'sent':
            bubble_bg, bubble_fg, pack_side, anchor = BG_SENT, TEXT_SENT, 'right', 'e'
        else:
            bubble_bg, bubble_fg, pack_side, anchor = BG_RECV, TEXT_PRI, 'left', 'w'

        inner = tk.Frame(outer, bg=BG_DARK)
        inner.pack(side=pack_side)

        bubble = tk.Frame(inner, bg=bubble_bg, padx=14, pady=10,
                           highlightthickness=1, highlightbackground=BORDER_LIGHT)
        bubble.pack(anchor=anchor)
        tk.Label(bubble, text=morse, font=('Courier', 11),
                 bg=bubble_bg, fg=bubble_fg,
                 wraplength=400, justify='left').pack(anchor='w')

        meta_row = tk.Frame(inner, bg=BG_DARK)
        meta_row.pack(fill='x', pady=(4, 0))

        ts = time.strftime('%I:%M %p').lstrip('0')

        if side == 'sent':
            tk.Label(meta_row, text=original, font=('Helvetica', 9),
                     bg=BG_DARK, fg=TEXT_MORSE).pack(side='right', padx=(8, 0))
            tk.Label(meta_row, text=ts, font=('Helvetica', 8),
                     bg=BG_DARK, fg=TEXT_MORSE).pack(side='right')
        else:
            translated_lbl = tk.Label(inner, text='', font=('Helvetica', 10),
                                       bg=BG_DARK, fg=TEAL, wraplength=400, justify='left')

            def toggle(o=original, lbl=translated_lbl):
                if lbl.cget('text'):
                    lbl.config(text='')
                    lbl.pack_forget()
                    btn.config(text='⟺  translate')
                else:
                    lbl.config(text=f'"{o}"')
                    lbl.pack(anchor='w', pady=(2, 0))
                    btn.config(text='⟺  hide')
                self._on_frame_configure()

            btn = make_btn(meta_row, '⟺  translate', toggle,
                           bg=TEAL_DARK, fg=TEAL_FG, hover='#1f5240',
                           font_size=8, bold=False, padx=8, pady=3)
            btn.pack(side='left')
            tk.Label(meta_row, text=ts, font=('Helvetica', 8),
                     bg=BG_DARK, fg=TEXT_MORSE).pack(side='left', padx=(8, 0))

    # ── Call integration (Jitsi via pywebview) ────────────────────────────────

    def _set_call_buttons_state(self, state: str) -> None:
        """Enable or disable both call buttons."""
        for btn in (self._video_btn, self._audio_btn):
            btn.config(state=state)

    def _start_call(self, audio_only: bool = False) -> None:
        """Initiate a Jitsi call — video or audio-only."""
        if not self.active_contact:
            return
        if self._active_call:
            messagebox.showinfo('Call in progress', 'You already have an active call.')
            return

        their_id   = self.active_contact['id']
        their_name = self.active_contact['name']

        # Show busy state on both buttons
        self._set_call_buttons_state('disabled')
        self._video_btn.config(text='⏳')
        self._audio_btn.config(text='⏳')

        call_type = 'audio' if audio_only else 'video'

        def _restore_buttons():
            self._video_btn.config(text='📹', state='normal')
            self._audio_btn.config(text='📞', state='normal')

        def _do():
            # 1. Generate a Jitsi room
            room_name = make_jitsi_room_name()
            room_url  = jitsi_room_url(room_name, start_audio_only=audio_only)

            # 2. Store call in Supabase for signalling
            call_id = db_create_call(self._user_id, their_id, room_url, room_name)
            if not call_id:
                self.after(0, lambda: (
                    _restore_buttons(),
                    messagebox.showerror('Error', 'Could not register call in database.')))
                return

            # 3. Open Jitsi for the caller immediately in embedded window
            call_title = f'GhostWire — {"Audio" if audio_only else "Video"} call with {their_name}'
            self.after(0, lambda: open_jitsi_window(room_url, call_title))

            # 4. Poll for receiver acceptance (up to 60 s)
            for _ in range(60):
                time.sleep(1)
                rows = sb_request("GET", "calls", params={
                    "id": f"eq.{call_id}", "select": "status"})
                if rows:
                    status = rows[0].get('status')
                    if status == 'active':
                        self.after(0, lambda cid=call_id, rn=room_name: (
                            _restore_buttons(),
                            self._open_call_status(cid, their_name, rn, call_type)))
                        return
                    if status in ('declined', 'ended'):
                        self.after(0, lambda: (
                            _restore_buttons(),
                            messagebox.showinfo('Call', f'{their_name} declined the call.')))
                        return

            # Timed out
            db_update_call_status(call_id, 'ended')
            self.after(0, lambda: (
                _restore_buttons(),
                messagebox.showinfo('Call', f'{their_name} did not answer.')))

        # FIX: removed stray `supabase.table("calls")` line that caused NameError
        threading.Thread(target=_do, daemon=True).start()

    def _check_incoming_calls(self):
        if self._active_call:
            return

        def _do():
            call = db_get_incoming_call(self._user_id)
            if not call:
                return
            call_id  = call['id']
            if call_id == self._seen_incoming_call_id:
                return
            self._seen_incoming_call_id = call_id
            caller_name = db_get_caller_name(call['caller_id'])
            room_url    = call.get('daily_room_url', '')   # column reused for Jitsi URL

            def _show():
                IncomingCallDialog(
                    self, call_id, caller_name, room_url,
                    on_accept=self._on_call_accepted,
                    on_decline=lambda: None,
                )
            self.after(0, _show)

        threading.Thread(target=_do, daemon=True).start()

    def _on_call_accepted(self, call_id: str, room_url: str):
        """Called when the receiver taps Accept — open Jitsi for them too."""
        call = db_get_call(call_id)
        room_name  = call.get('daily_room_name', '') if call else ''
        audio_only = 'startWithVideoMuted=true' in room_url
        call_type  = 'audio' if audio_only else 'video'

        rows = sb_request("GET", "calls", params={"id": f"eq.{call_id}", "select": "caller_id"})
        remote_name = db_get_caller_name(rows[0]['caller_id']) if rows else 'Caller'
        call_title  = f'GhostWire — {"Audio" if audio_only else "Video"} call with {remote_name}'

        # Open Jitsi embedded window for the receiver
        open_jitsi_window(room_url, call_title)
        self._open_call_status(call_id, remote_name, room_name, call_type)

    def _open_call_status(self, call_id: str, remote_name: str,
                          room_name: str, call_type: str):
        self._active_call = call_id

        def _on_end():
            self._active_call = None
            self._video_btn.config(text='📹', state='normal')
            self._audio_btn.config(text='📞', state='normal')

        CallStatusWindow(self, call_id, remote_name, room_name, call_type, _on_end)

    # ── Canvas helpers ────────────────────────────────────────────────────────

    def _on_frame_configure(self, *_) -> None:
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox('all'))

    def _on_canvas_configure(self, event) -> None:
        self.msg_canvas.itemconfig(self.msg_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self.msg_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _scroll_bottom(self) -> None:
        self.update_idletasks()
        self.msg_canvas.yview_moveto(1.0)


# ──────────────────────────────────────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    app = MorseChatApp()
    app.mainloop()


if __name__ == '__main__':
    main()