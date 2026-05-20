"""
GhostWire – secure Morse-code messaging desktop app
"""

import os
import hashlib
import sqlite3
import base64
import time
import tkinter as tk
from tkinter import messagebox
from cryptography.fernet import Fernet

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
    words = morse.strip().split(' / ')
    decoded = []
    for word in words:
        letters = [REVERSE_MORSE.get(code, '?') for code in word.strip().split()]
        decoded.append(''.join(letters))
    return ' '.join(decoded)


# ──────────────────────────────────────────────────────────────────────────────
#  Database & authentication
# ──────────────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.expanduser('~'), 'ghostwire_accounts.sqlite')


def derive_key(password: str) -> Fernet:
    key = hashlib.sha256(password.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def setup_database() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user     TEXT UNIQUE,
                password TEXT,
                salt     BLOB
            )
        """)
        conn.commit()


def db_register(username: str, password: str) -> tuple[bool, str]:
    salt = os.urandom(16)
    hashed = hashlib.sha3_512(salt + password.encode()).hexdigest()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO users (user, password, salt) VALUES (?, ?, ?)",
                (username, hashed, salt),
            )
            conn.commit()
        return True, ''
    except sqlite3.IntegrityError:
        return False, 'Username already exists.'


def db_login(username: str, password: str) -> tuple[bool, str]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT password, salt FROM users WHERE user = ?", (username,)
        ).fetchone()
    if not row:
        return False, 'User not found.'
    stored_pw, salt = row
    if hashlib.sha3_512(salt + password.encode()).hexdigest() == stored_pw:
        return True, ''
    return False, 'Incorrect password.'


# ──────────────────────────────────────────────────────────────────────────────
#  Colour palette  (deep navy, no white)
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
ACCENT_DIM   = '#3d3578'

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


# ──────────────────────────────────────────────────────────────────────────────
#  Widget helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_entry(parent, textvariable, show=None):
    return tk.Entry(
        parent,
        textvariable=textvariable,
        show=show,
        font=('Helvetica', 12),
        bg=BG_INPUT,
        fg=TEXT_PRI,
        insertbackground=ACCENT,
        relief='flat',
        highlightthickness=1,
        highlightbackground=BORDER_LIGHT,
        highlightcolor=ACCENT,
    )


def make_btn(parent, text, command, fg='#d6d3e8', bg=ACCENT, hover=ACCENT_HOVER,
             font_size=10, bold=True, padx=16, pady=8):
    weight = 'bold' if bold else 'normal'
    btn = tk.Button(
        parent, text=text, command=command,
        font=('Helvetica', font_size, weight),
        bg=bg, fg=fg,
        activebackground=hover, activeforeground=fg,
        relief='flat', cursor='hand2',
        padx=padx, pady=pady, bd=0,
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

        # Logo
        logo = tk.Frame(card, bg=BG_PANEL, pady=30)
        logo.pack(fill='x')
        tk.Label(logo, text='◉', font=('Courier', 30, 'bold'),
                 bg=BG_PANEL, fg=ACCENT).pack()
        tk.Label(logo, text='GhostWire', font=('Helvetica', 20, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(pady=(4, 0))
        tk.Label(logo, text='secure · morse · messaging',
                 font=('Helvetica', 9), bg=BG_PANEL, fg=TEXT_MORSE).pack(pady=(3, 0))

        divider(card).pack(fill='x')

        # Tabs
        tabs = tk.Frame(card, bg=BG_CARD)
        tabs.pack(fill='x')
        tabs.grid_columnconfigure(0, weight=1)
        tabs.grid_columnconfigure(1, weight=1)

        self._tab_login = tk.Button(
            tabs, text='Login', font=('Helvetica', 10, 'bold'),
            bg=ACCENT, fg='#d6d3e8',
            activebackground=ACCENT_HOVER, activeforeground='#d6d3e8',
            relief='flat', cursor='hand2', pady=10,
            command=lambda: self._switch('login'))
        self._tab_login.grid(row=0, column=0, sticky='ew')

        self._tab_reg = tk.Button(
            tabs, text='Register', font=('Helvetica', 10, 'bold'),
            bg=BG_CARD, fg=TEXT_SEC,
            activebackground=BG_HOVER, activeforeground=TEXT_PRI,
            relief='flat', cursor='hand2', pady=10,
            command=lambda: self._switch('register'))
        self._tab_reg.grid(row=0, column=1, sticky='ew')

        divider(card).pack(fill='x')

        # Form
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

        # Confirm password (register only)
        self._confirm_frame = tk.Frame(form, bg=BG_PANEL)
        self._confirm_frame.pack(fill='x')
        tk.Label(self._confirm_frame, text='Confirm Password', font=('Helvetica', 9),
                 bg=BG_PANEL, fg=TEXT_SEC).pack(anchor='w', pady=(16, 0))
        self._confirm_var = tk.StringVar()
        make_entry(self._confirm_frame, self._confirm_var,
                   show='●').pack(fill='x', ipady=8, pady=(3, 0))
        self._confirm_frame.pack_forget()

        # Status
        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(
            form, textvariable=self._status_var,
            font=('Helvetica', 9), bg=BG_PANEL, fg=RED_ERR,
            wraplength=310, justify='left')
        self._status_lbl.pack(anchor='w', pady=(12, 0))

        # Submit
        self._submit_btn = make_btn(form, 'Login  →', self._submit,
                                     font_size=11, pady=10)
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
        if self._mode == 'register':
            confirm = self._confirm_var.get()
            if password != confirm:
                self._set_status('Passwords do not match.', error=True)
                return
            if len(password) < 6:
                self._set_status('Password must be at least 6 characters.', error=True)
                return
            ok, msg = db_register(username, password)
            if ok:
                self._set_status('Account created! Logging you in…', error=False)
                self.after(800, lambda: self._launch(username, password))
            else:
                self._set_status(msg, error=True)
        else:
            ok, msg = db_login(username, password)
            if ok:
                self._set_status(f'Welcome back, {username}!', error=False)
                self.after(500, lambda: self._launch(username, password))
            else:
                self._set_status(msg, error=True)

    def _set_status(self, msg: str, error: bool = True) -> None:
        self._status_var.set(msg)
        self._status_lbl.config(fg=RED_ERR if error else GREEN_OK)

    def _launch(self, username: str, password: str) -> None:
        self.master.unbind('<Return>')
        self.destroy()
        self.on_success(username, password)


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

        setup_database()
        AuthScreen(self, self._on_login)

    def _on_login(self, username: str, password: str) -> None:
        self._username = username
        self._fernet   = derive_key(password)

        self.contacts = [
            {'name': 'Alex K.',   'initials': 'AK', 'online': True,  'color': ACCENT},
            {'name': 'Sam R.',    'initials': 'SR', 'online': True,  'color': TEAL},
            {'name': 'Jordan T.', 'initials': 'JT', 'online': False, 'color': '#c45c8a'},
            {'name': 'Morgan B.', 'initials': 'MB', 'online': True,  'color': '#d4893a'},
        ]
        self.histories = {c['name']: [] for c in self.contacts}
        self.histories['Alex K.'] = [
            {'side': 'recv', 'morse': '.-- .... .- - ... / ..- .--.', 'original': "What's up?"},
            {'side': 'sent', 'morse': '- .... .. ... / .- .--. .--. / .. ... / -.-. --- --- .-..', 'original': 'This app is cool'},
            {'side': 'recv', 'morse': '-.-. .-.. .- ... ... / .--. .-. --- .--- . -.-. -', 'original': 'Class project?'},
        ]
        self.active = 'Alex K.'
        self._build_ui()
        self._load_chat(self.active)

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

        # App header
        hdr = tk.Frame(side, bg=BG_PANEL, pady=16, padx=16)
        hdr.grid(row=0, column=0, sticky='ew')

        top_row = tk.Frame(hdr, bg=BG_PANEL)
        top_row.pack(fill='x')
        tk.Label(top_row, text='◉', font=('Courier', 14, 'bold'),
                 bg=BG_PANEL, fg=ACCENT).pack(side='left', padx=(0, 6))
        tk.Label(top_row, text='GhostWire', font=('Helvetica', 13, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side='left')

        user_row = tk.Frame(hdr, bg=BG_PANEL)
        user_row.pack(fill='x', pady=(8, 0))

        dot_c = tk.Canvas(user_row, width=8, height=8, bg=BG_PANEL, highlightthickness=0)
        dot_c.pack(side='left', padx=(0, 6))
        dot_c.create_oval(1, 1, 7, 7, fill=TEAL, outline='')

        tk.Label(user_row, text=self._username, font=('Helvetica', 10),
                 bg=BG_PANEL, fg=TEXT_SEC).pack(side='left')

        logout_btn = tk.Button(
            user_row, text='logout',
            font=('Helvetica', 8), bg=BG_PANEL, fg=TEXT_MORSE,
            activebackground=BG_HOVER, activeforeground=TEXT_SEC,
            relief='flat', cursor='hand2', padx=6, pady=2,
            command=self._logout)
        logout_btn.pack(side='right')
        logout_btn.bind('<Enter>', lambda e: logout_btn.config(fg=TEXT_SEC))
        logout_btn.bind('<Leave>', lambda e: logout_btn.config(fg=TEXT_MORSE))

        divider(side).grid(row=1, column=0, sticky='ew')

        # Contacts
        contacts_wrap = tk.Frame(side, bg=BG_PANEL)
        contacts_wrap.grid(row=2, column=0, sticky='nsew', pady=6)

        tk.Label(contacts_wrap, text='CONVERSATIONS',
                 font=('Helvetica', 8, 'bold'), bg=BG_PANEL,
                 fg=TEXT_MORSE).pack(anchor='w', padx=16, pady=(8, 4))

        self.contact_btns = {}
        for c in self.contacts:
            self._make_contact_row(contacts_wrap, c)

    def _make_contact_row(self, parent, c: dict) -> None:
        name     = c['name']
        is_active = (name == self.active)
        row_bg   = BG_ACTIVE if is_active else BG_PANEL

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

        last = (self.histories[name][-1]['morse'][:24] + '…') if self.histories[name] else '—'
        preview_lbl = tk.Label(txt, text=last, font=('Courier', 8),
                                bg=row_bg, fg=TEXT_MORSE)
        preview_lbl.pack(anchor='w')

        if c['online']:
            dot = tk.Canvas(inner, width=8, height=8, bg=row_bg, highlightthickness=0)
            dot.pack(side='right', padx=(4, 2))
            dot.create_oval(1, 1, 7, 7, fill=TEAL, outline='')

        all_w = [row, inner, av, txt, name_lbl, preview_lbl]
        for w in all_w:
            w.bind('<Button-1>', lambda e, n=name: self._switch_contact(n))

        def on_enter(e, widgets=all_w, n=name):
            if n != self.active:
                for w in widgets:
                    try: w.configure(bg=BG_HOVER)
                    except Exception: pass

        def on_leave(e, widgets=all_w, n=name):
            if n != self.active:
                for w in widgets:
                    try: w.configure(bg=BG_PANEL)
                    except Exception: pass

        for w in all_w:
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)

        self.contact_btns[name] = all_w

    def _build_chat_pane(self) -> None:
        pane = tk.Frame(self, bg=BG_DARK)
        pane.grid(row=0, column=1, sticky='nsew')
        pane.grid_rowconfigure(1, weight=1)
        pane.grid_columnconfigure(0, weight=1)

        # Chat header
        self.chat_header = tk.Frame(pane, bg=BG_PANEL, pady=12, padx=18)
        self.chat_header.grid(row=0, column=0, columnspan=2, sticky='ew')

        self.hdr_canvas = tk.Canvas(self.chat_header, width=40, height=40,
                                    bg=BG_PANEL, highlightthickness=0)
        self.hdr_canvas.pack(side='left', padx=(0, 12))

        hdr_txt = tk.Frame(self.chat_header, bg=BG_PANEL)
        hdr_txt.pack(side='left')
        self.hdr_name = tk.Label(hdr_txt, text='', font=('Helvetica', 13, 'bold'),
                                  bg=BG_PANEL, fg=TEXT_PRI)
        self.hdr_name.pack(anchor='w')
        self.hdr_status = tk.Label(hdr_txt, text='● online',
                                    font=('Helvetica', 9), bg=BG_PANEL, fg=TEAL)
        self.hdr_status.pack(anchor='w')

        divider(pane).grid(row=0, column=0, columnspan=2, sticky='sew')

        # Scrollable messages
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

        # Input bar
        inp = tk.Frame(pane, bg=BG_PANEL, pady=12, padx=16)
        inp.grid(row=2, column=0, columnspan=2, sticky='ew')
        inp.grid_columnconfigure(0, weight=1)

        # Morse preview
        prev_strip = tk.Frame(inp, bg=BG_CARD, padx=10, pady=6,
                               highlightthickness=1, highlightbackground=BORDER)
        prev_strip.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 10))
        tk.Label(prev_strip, text='MORSE PREVIEW', font=('Helvetica', 7, 'bold'),
                 bg=BG_CARD, fg=TEXT_MORSE).pack(anchor='w')
        self.preview_var = tk.StringVar(value='start typing…')
        tk.Label(prev_strip, textvariable=self.preview_var,
                 font=('Courier', 10), bg=BG_CARD, fg=ACCENT,
                 anchor='w', wraplength=600, justify='left').pack(anchor='w')

        # Text entry
        self.entry_var = tk.StringVar()
        self.entry_var.trace_add('write', self._on_type)
        entry = tk.Entry(inp, textvariable=self.entry_var,
                         font=('Helvetica', 12), bg=BG_INPUT, fg=TEXT_PRI,
                         insertbackground=ACCENT, relief='flat',
                         highlightthickness=1, highlightbackground=BORDER_LIGHT,
                         highlightcolor=ACCENT)
        entry.grid(row=1, column=0, sticky='ew', ipady=9, padx=(0, 10))
        entry.bind('<Return>', lambda e: self._send())

        send_btn = make_btn(inp, 'Send  ▶', self._send, font_size=10, pady=9, padx=18)
        send_btn.grid(row=1, column=1)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _logout(self) -> None:
        if messagebox.askyesno('Logout', 'Log out of GhostWire?'):
            for w in self.winfo_children():
                w.destroy()
            self.grid_columnconfigure(0, weight=0)
            self.grid_columnconfigure(1, weight=1)
            AuthScreen(self, self._on_login)

    def _switch_contact(self, name: str) -> None:
        old, self.active = self.active, name
        self._refresh_sidebar_highlight(old, name)
        self._load_chat(name)

    def _refresh_sidebar_highlight(self, old: str, new: str) -> None:
        if old in self.contact_btns:
            for w in self.contact_btns[old]:
                try: w.configure(bg=BG_PANEL)
                except Exception: pass
        if new in self.contact_btns:
            for w in self.contact_btns[new]:
                try: w.configure(bg=BG_ACTIVE)
                except Exception: pass

    def _load_chat(self, name: str) -> None:
        c = next(x for x in self.contacts if x['name'] == name)
        self.hdr_name.config(text=name)
        self.hdr_status.config(
            text='● online' if c['online'] else '○ offline',
            fg=TEAL if c['online'] else TEXT_MORSE,
        )
        self.hdr_canvas.delete('all')
        self.hdr_canvas.create_oval(2, 2, 38, 38, fill=c['color'], outline='')
        self.hdr_canvas.create_text(20, 20, text=c['initials'],
                                     fill='#d6d3e8', font=('Helvetica', 10, 'bold'))
        for w in self.msg_frame.winfo_children():
            w.destroy()
        for msg in self.histories[name]:
            self._render_message(msg['side'], msg['morse'], msg['original'])
        self._scroll_bottom()

    def _on_type(self, *_) -> None:
        text = self.entry_var.get()
        self.preview_var.set(to_morse(text) if text else 'start typing…')

    def _send(self) -> None:
        text = self.entry_var.get().strip()
        if not text:
            return
        morse = to_morse(text)
        self.histories[self.active].append({'side': 'sent', 'morse': morse, 'original': text})
        self._render_message('sent', morse, text)
        self.entry_var.set('')
        self.preview_var.set('start typing…')
        self._scroll_bottom()

    def _render_message(self, side: str, morse: str, original: str) -> None:
        outer = tk.Frame(self.msg_frame, bg=BG_DARK)
        outer.pack(fill='x', padx=16, pady=6)

        if side == 'sent':
            bubble_bg, bubble_fg, anchor = BG_SENT, TEXT_SENT, 'e'
            inner = tk.Frame(outer, bg=BG_DARK)
            inner.pack(side='right')
        else:
            bubble_bg, bubble_fg, anchor = BG_RECV, TEXT_PRI, 'w'
            inner = tk.Frame(outer, bg=BG_DARK)
            inner.pack(side='left')

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