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
#  Colour palette
# ──────────────────────────────────────────────────────────────────────────────

BG_DARK      = '#0e0e12'
BG_PANEL     = '#16161e'
BG_INPUT     = '#1c1c26'
BG_SENT      = '#2a2250'
BG_RECV      = '#1c1c26'
ACCENT       = '#7c6af7'
ACCENT_LIGHT = '#a594ff'
TEAL         = '#3ecf8e'
TEAL_DARK    = '#1a6646'
TEXT_PRI     = '#e8e6f0'
TEXT_SEC     = '#8884a8'
TEXT_MORSE   = '#5c5a7a'
BORDER       = '#2a2838'
RED_ERR      = '#e05c6a'
GREEN_OK     = '#3ecf8e'


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
                        highlightthickness=1, highlightbackground=BORDER)
        card.place(relx=0.5, rely=0.5, anchor='center', width=380)

        # Logo
        logo = tk.Frame(card, bg=BG_PANEL, pady=28)
        logo.pack(fill='x')
        tk.Label(logo, text='◉', font=('Courier', 28),
                 bg=BG_PANEL, fg=ACCENT).pack()
        tk.Label(logo, text='GhostWire', font=('Courier', 18, 'bold'),
                 bg=BG_PANEL, fg=ACCENT_LIGHT).pack()
        tk.Label(logo, text='secure · morse · messaging',
                 font=('Courier', 9), bg=BG_PANEL, fg=TEXT_MORSE).pack(pady=(2, 0))

        tk.Frame(card, bg=BORDER, height=1).pack(fill='x')

        # Tab bar
        tabs = tk.Frame(card, bg=BG_PANEL)
        tabs.pack(fill='x')
        self._tab_login = tk.Button(
            tabs, text='Login', font=('Courier', 10, 'bold'),
            bg=ACCENT, fg='#fff', relief='flat', cursor='hand2',
            padx=20, pady=8, command=lambda: self._switch('login'))
        self._tab_login.pack(side='left', fill='x', expand=True)
        self._tab_reg = tk.Button(
            tabs, text='Register', font=('Courier', 10, 'bold'),
            bg=BG_INPUT, fg=TEXT_SEC, relief='flat', cursor='hand2',
            padx=20, pady=8, command=lambda: self._switch('register'))
        self._tab_reg.pack(side='left', fill='x', expand=True)

        tk.Frame(card, bg=BORDER, height=1).pack(fill='x')

        # Form
        form = tk.Frame(card, bg=BG_PANEL, padx=32, pady=24)
        form.pack(fill='x')

        tk.Label(form, text='username', font=('Courier', 9),
                 bg=BG_PANEL, fg=TEXT_MORSE).pack(anchor='w')
        self._user_var = tk.StringVar()
        self._user_entry = tk.Entry(
            form, textvariable=self._user_var,
            font=('Courier', 12), bg=BG_INPUT, fg=TEXT_PRI,
            insertbackground=ACCENT_LIGHT, relief='flat',
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT)
        self._user_entry.pack(fill='x', ipady=7, pady=(2, 14))

        tk.Label(form, text='password', font=('Courier', 9),
                 bg=BG_PANEL, fg=TEXT_MORSE).pack(anchor='w')
        self._pw_var = tk.StringVar()
        self._pw_entry = tk.Entry(
            form, textvariable=self._pw_var, show='●',
            font=('Courier', 12), bg=BG_INPUT, fg=TEXT_PRI,
            insertbackground=ACCENT_LIGHT, relief='flat',
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT)
        self._pw_entry.pack(fill='x', ipady=7, pady=(2, 0))

        # Confirm password (register only)
        self._confirm_frame = tk.Frame(form, bg=BG_PANEL)
        self._confirm_frame.pack(fill='x')
        tk.Label(self._confirm_frame, text='confirm password', font=('Courier', 9),
                 bg=BG_PANEL, fg=TEXT_MORSE).pack(anchor='w')
        self._confirm_var = tk.StringVar()
        tk.Entry(
            self._confirm_frame, textvariable=self._confirm_var, show='●',
            font=('Courier', 12), bg=BG_INPUT, fg=TEXT_PRI,
            insertbackground=ACCENT_LIGHT, relief='flat',
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT).pack(fill='x', ipady=7, pady=(2, 0))
        self._confirm_frame.pack_forget()

        # Status label
        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(
            form, textvariable=self._status_var,
            font=('Courier', 9), bg=BG_PANEL, fg=RED_ERR,
            wraplength=300, justify='left')
        self._status_lbl.pack(anchor='w', pady=(10, 0))

        # Submit button
        self._submit_btn = tk.Button(
            form, text='Login  ▶', font=('Courier', 11, 'bold'),
            bg=ACCENT, fg='#fff', activebackground=ACCENT_LIGHT,
            relief='flat', cursor='hand2', pady=9,
            command=self._submit)
        self._submit_btn.pack(fill='x', pady=(14, 0))

        self.master.bind('<Return>', lambda e: self._submit())
        self._user_entry.focus_set()

    def _switch(self, mode: str) -> None:
        self._mode = mode
        self._status_var.set('')
        if mode == 'login':
            self._tab_login.config(bg=ACCENT, fg='#fff')
            self._tab_reg.config(bg=BG_INPUT, fg=TEXT_SEC)
            self._confirm_frame.pack_forget()
            self._submit_btn.config(text='Login  ▶')
        else:
            self._tab_reg.config(bg=ACCENT, fg='#fff')
            self._tab_login.config(bg=BG_INPUT, fg=TEXT_SEC)
            self._confirm_frame.pack(fill='x')
            self._submit_btn.config(text='Create Account  ▶')

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
        self.geometry('860x620')
        self.minsize(700, 500)
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
            {'name': 'Jordan T.', 'initials': 'JT', 'online': False, 'color': '#d4537e'},
            {'name': 'Morgan B.', 'initials': 'MB', 'online': True,  'color': '#ef9f27'},
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
        side = tk.Frame(self, bg=BG_PANEL, width=220)
        side.grid(row=0, column=0, sticky='nsew')
        side.grid_propagate(False)
        side.grid_rowconfigure(1, weight=1)

        hdr = tk.Frame(side, bg=BG_PANEL, pady=12, padx=14)
        hdr.grid(row=0, column=0, sticky='ew')

        tk.Label(hdr, text='◉ GhostWire', font=('Courier', 13, 'bold'),
                 bg=BG_PANEL, fg=ACCENT_LIGHT).pack(anchor='w')

        user_row = tk.Frame(hdr, bg=BG_PANEL)
        user_row.pack(fill='x', pady=(4, 0))
        tk.Label(user_row, text=f'● {self._username}', font=('Courier', 9),
                 bg=BG_PANEL, fg=TEAL).pack(side='left')
        tk.Button(user_row, text='logout', font=('Courier', 8),
                  bg=BG_PANEL, fg=TEXT_MORSE, relief='flat', cursor='hand2',
                  command=self._logout).pack(side='right')

        tk.Frame(side, bg=BORDER, height=1).grid(row=0, column=0, sticky='sew')

        contacts_frame = tk.Frame(side, bg=BG_PANEL)
        contacts_frame.grid(row=1, column=0, sticky='nsew', padx=6, pady=6)

        self.contact_btns = {}
        for c in self.contacts:
            self._make_contact_row(contacts_frame, c)

    def _make_contact_row(self, parent, c: dict) -> None:
        name = c['name']
        row  = tk.Frame(parent, bg=BG_PANEL, cursor='hand2')
        row.pack(fill='x', pady=2)
        inner = tk.Frame(row, bg=BG_PANEL, padx=10, pady=8)
        inner.pack(fill='x')

        av = tk.Canvas(inner, width=34, height=34, bg=BG_PANEL, highlightthickness=0)
        av.pack(side='left', padx=(0, 8))
        av.create_oval(2, 2, 32, 32, fill=c['color'], outline='')
        av.create_text(17, 17, text=c['initials'], fill='#fff', font=('Courier', 9, 'bold'))

        txt = tk.Frame(inner, bg=BG_PANEL)
        txt.pack(side='left', fill='x', expand=True)
        tk.Label(txt, text=name, font=('Courier', 11, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(anchor='w')
        last = (self.histories[name][-1]['morse'][:22] + '…') if self.histories[name] else '—'
        tk.Label(txt, text=last, font=('Courier', 9),
                 bg=BG_PANEL, fg=TEXT_MORSE).pack(anchor='w')

        if c['online']:
            dot = tk.Canvas(inner, width=10, height=10, bg=BG_PANEL, highlightthickness=0)
            dot.pack(side='right', padx=(0, 2))
            dot.create_oval(1, 1, 9, 9, fill=TEAL, outline='')

        for w in (row, inner, av, txt):
            w.bind('<Button-1>', lambda e, n=name: self._switch_contact(n))
        for child in txt.winfo_children():
            child.bind('<Button-1>', lambda e, n=name: self._switch_contact(n))

        self.contact_btns[name] = row
        if name == self.active:
            row.configure(bg=BG_INPUT)
            inner.configure(bg=BG_INPUT)

    def _build_chat_pane(self) -> None:
        pane = tk.Frame(self, bg=BG_DARK)
        pane.grid(row=0, column=1, sticky='nsew')
        pane.grid_rowconfigure(1, weight=1)
        pane.grid_columnconfigure(0, weight=1)

        # Header
        self.chat_header = tk.Frame(pane, bg=BG_PANEL, pady=10, padx=16)
        self.chat_header.grid(row=0, column=0, sticky='ew')

        self.hdr_canvas = tk.Canvas(self.chat_header, width=36, height=36,
                                    bg=BG_PANEL, highlightthickness=0)
        self.hdr_canvas.pack(side='left', padx=(0, 10))

        hdr_txt = tk.Frame(self.chat_header, bg=BG_PANEL)
        hdr_txt.pack(side='left')
        self.hdr_name   = tk.Label(hdr_txt, text='', font=('Courier', 13, 'bold'),
                                    bg=BG_PANEL, fg=TEXT_PRI)
        self.hdr_name.pack(anchor='w')
        self.hdr_status = tk.Label(hdr_txt, text='● online', font=('Courier', 9),
                                    bg=BG_PANEL, fg=TEAL)
        self.hdr_status.pack(anchor='w')

        tk.Frame(pane, bg=BORDER, height=1).grid(row=0, column=0, sticky='sew')

        # Scrollable message area
        self.msg_canvas = tk.Canvas(pane, bg=BG_DARK, highlightthickness=0, bd=0)
        self.msg_canvas.grid(row=1, column=0, sticky='nsew')

        sb = tk.Scrollbar(pane, orient='vertical', command=self.msg_canvas.yview)
        sb.grid(row=1, column=1, sticky='ns')
        self.msg_canvas.configure(yscrollcommand=sb.set)

        self.msg_frame  = tk.Frame(self.msg_canvas, bg=BG_DARK)
        self.msg_window = self.msg_canvas.create_window((0, 0), window=self.msg_frame, anchor='nw')

        self.msg_frame.bind('<Configure>', self._on_frame_configure)
        self.msg_canvas.bind('<Configure>', self._on_canvas_configure)
        self.msg_canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        # Input bar
        inp = tk.Frame(pane, bg=BG_PANEL, pady=10, padx=14)
        inp.grid(row=2, column=0, sticky='ew')
        inp.grid_columnconfigure(0, weight=1)

        prev = tk.Frame(inp, bg=BG_INPUT, padx=8, pady=4,
                        highlightthickness=1, highlightbackground=BORDER)
        prev.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 8))
        tk.Label(prev, text='morse preview', font=('Courier', 8),
                 bg=BG_INPUT, fg=TEXT_MORSE).pack(anchor='w')
        self.preview_var = tk.StringVar(value='start typing…')
        tk.Label(prev, textvariable=self.preview_var,
                 font=('Courier', 10), bg=BG_INPUT, fg=ACCENT_LIGHT,
                 anchor='w', wraplength=560, justify='left').pack(anchor='w')

        self.entry_var = tk.StringVar()
        self.entry_var.trace_add('write', self._on_type)
        entry = tk.Entry(inp, textvariable=self.entry_var,
                         font=('Courier', 12), bg=BG_INPUT, fg=TEXT_PRI,
                         insertbackground=ACCENT_LIGHT, relief='flat',
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT)
        entry.grid(row=1, column=0, sticky='ew', ipady=7, padx=(0, 8))
        entry.bind('<Return>', lambda e: self._send())

        tk.Button(inp, text='▶', font=('Courier', 13, 'bold'),
                  bg=ACCENT, fg='#fff', activebackground=ACCENT_LIGHT,
                  relief='flat', cursor='hand2', padx=10,
                  command=self._send).grid(row=1, column=1)

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
        def _recolor(frame, color):
            frame.configure(bg=color)
            for child in frame.winfo_children():
                try:
                    child.configure(bg=color)
                    for sub in child.winfo_children():
                        try:
                            sub.configure(bg=color)
                        except Exception:
                            pass
                except Exception:
                    pass

        if old in self.contact_btns:
            _recolor(self.contact_btns[old], BG_PANEL)
        if new in self.contact_btns:
            _recolor(self.contact_btns[new], BG_INPUT)

    def _load_chat(self, name: str) -> None:
        c = next(x for x in self.contacts if x['name'] == name)
        self.hdr_name.config(text=name)
        self.hdr_status.config(
            text='● online' if c['online'] else '○ offline',
            fg=TEAL if c['online'] else TEXT_MORSE,
        )
        self.hdr_canvas.delete('all')
        self.hdr_canvas.create_oval(2, 2, 34, 34, fill=c['color'], outline='')
        self.hdr_canvas.create_text(18, 18, text=c['initials'],
                                     fill='#fff', font=('Courier', 9, 'bold'))
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
        outer.pack(fill='x', padx=14, pady=5)

        if side == 'sent':
            bubble_bg, bubble_fg, anchor = BG_SENT, '#c8c2f0', 'e'
            inner = tk.Frame(outer, bg=BG_DARK)
            inner.pack(side='right')
        else:
            bubble_bg, bubble_fg, anchor = BG_RECV, TEXT_PRI, 'w'
            inner = tk.Frame(outer, bg=BG_DARK)
            inner.pack(side='left')

        bubble = tk.Frame(inner, bg=bubble_bg, padx=12, pady=8,
                           highlightthickness=1, highlightbackground=BORDER)
        bubble.pack(anchor=anchor)
        tk.Label(bubble, text=morse, font=('Courier', 11),
                 bg=bubble_bg, fg=bubble_fg,
                 wraplength=380, justify='left').pack(anchor='w')

        if side == 'sent':
            tk.Label(inner, text=f'original: {original}',
                     font=('Courier', 9), bg=BG_DARK, fg=TEXT_MORSE).pack(anchor='e', pady=(2, 0))
        else:
            btn_frame = tk.Frame(inner, bg=BG_DARK)
            btn_frame.pack(anchor='w', pady=(3, 0))
            translated_lbl = tk.Label(inner, text='', font=('Courier', 10),
                                       bg=BG_DARK, fg=TEAL, wraplength=380, justify='left')

            def toggle(o=original, lbl=translated_lbl):
                if lbl.cget('text'):
                    lbl.config(text='')
                    lbl.pack_forget()
                    btn.config(text='⟺ translate')
                else:
                    lbl.config(text=f'"{o}"')
                    lbl.pack(anchor='w')
                    btn.config(text='⟺ hide')
                self._on_frame_configure()

            btn = tk.Button(btn_frame, text='⟺ translate', font=('Courier', 9),
                            bg=TEAL_DARK, fg='#a0f0cc', activebackground=TEAL,
                            relief='flat', cursor='hand2', padx=8, pady=2,
                            command=toggle)
            btn.pack(side='left')

        ts = time.strftime('%I:%M %p').lstrip('0')
        tk.Label(inner, text=ts, font=('Courier', 8),
                 bg=BG_DARK, fg=TEXT_MORSE).pack(anchor=anchor, pady=(2, 0))

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
