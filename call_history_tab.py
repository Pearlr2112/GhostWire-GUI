"""
call_history_tab.py  –  GhostWire Call History sidebar tab

Drop this file next to ghostwire.py.

Usage in ghostwire.py:
    from call_history_tab import CallHistoryFrame, history_add

See bottom of this file for integration notes.
"""

from datetime import datetime
import tkinter as tk

# ── Paste these colour constants or import them from ghostwire.py ─────────────
BG_DARK      = '#0b0d14'
BG_PANEL     = '#13151f'
BG_CARD      = '#1a1d2e'
BG_HOVER     = '#252840'
BG_ACTIVE    = '#1e2038'
ACCENT       = '#7c6af7'
ACCENT_HOVER = '#9182ff'
TEAL         = '#2dd4a0'
TEAL_DARK    = '#163d2e'
TEXT_PRI     = '#d6d3e8'
TEXT_SEC     = '#7a7897'
TEXT_MORSE   = '#4a4868'
BORDER       = '#252840'
RED_ERR      = '#e05c6a'


# ──────────────────────────────────────────────────────────────────────────────
#  In-memory call log
# ──────────────────────────────────────────────────────────────────────────────

# Each record is a dict:
# {
#   "remote_name": str,
#   "direction":   "outgoing" | "incoming",
#   "call_type":   "video"    | "audio",
#   "status":      "answered" | "declined" | "missed" | "no answer",
#   "started_at":  datetime,
#   "duration_s":  int | None,   # seconds connected; None if never answered
# }
_call_history: list[dict] = []


def history_add(
    remote_name: str,
    direction: str,        # "outgoing" | "incoming"
    call_type: str,        # "video"    | "audio"
    status: str,           # "answered" | "declined" | "missed" | "no answer"
    started_at: datetime,
    duration_s: int | None,
) -> None:
    """Prepend a call record.  Call this whenever a call ends."""
    _call_history.insert(0, {
        "remote_name": remote_name,
        "direction":   direction,
        "call_type":   call_type,
        "status":      status,
        "started_at":  started_at,
        "duration_s":  duration_s,
    })


def history_get() -> list[dict]:
    return list(_call_history)


# ──────────────────────────────────────────────────────────────────────────────
#  Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return ""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _fmt_timestamp(dt: datetime) -> str:
    now   = datetime.now()
    delta = now - dt
    if delta.days == 0:
        return dt.strftime("Today %I:%M %p").lstrip("0")
    if delta.days == 1:
        return dt.strftime("Yesterday %I:%M %p").lstrip("0")
    if delta.days < 7:
        return dt.strftime("%A %I:%M %p").lstrip("0")
    return dt.strftime("%b %d, %Y %I:%M %p")


# ──────────────────────────────────────────────────────────────────────────────
#  CallHistoryFrame  –  drop-in sidebar widget
# ──────────────────────────────────────────────────────────────────────────────

class CallHistoryFrame(tk.Frame):
    """
    Scrollable call-history panel.
    Pack or grid it wherever you want inside the sidebar.
    Call .refresh() to redraw after adding new records.
    """

    def __init__(self, parent):
        super().__init__(parent, bg=BG_PANEL)
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # Header row
        hdr = tk.Frame(self, bg=BG_PANEL)
        hdr.pack(fill='x', padx=14, pady=(10, 6))
        tk.Label(hdr, text='CALL HISTORY', font=('Helvetica', 8, 'bold'),
                 bg=BG_PANEL, fg=TEXT_MORSE).pack(side='left', padx=2)
        self._close_cb = None
        self._close_btn = tk.Button(
            hdr, text='✕ Close', font=('Helvetica', 9),
            bg=BG_PANEL, fg=TEXT_SEC, activebackground=BG_HOVER,
            relief='flat', cursor='hand2', padx=4, pady=0,
            command=self._do_close,
        )
        self._close_btn.pack(side='right')
        tk.Button(
            hdr, text='↻', font=('Helvetica', 11),
            bg=BG_PANEL, fg=TEXT_SEC, activebackground=BG_HOVER,
            relief='flat', cursor='hand2', padx=4, pady=0,
            command=self.refresh,
        ).pack(side='right')

        # Scrollable body
        wrap = tk.Frame(self, bg=BG_PANEL)
        wrap.pack(fill='both', expand=True)

        self._canvas = tk.Canvas(wrap, bg=BG_PANEL, highlightthickness=0, bd=0)
        self._canvas.pack(side='left', fill='both', expand=True)

        sb = tk.Scrollbar(wrap, orient='vertical', command=self._canvas.yview,
                          bg=BG_PANEL, troughcolor=BG_DARK, width=5)
        sb.pack(side='right', fill='y')
        self._canvas.configure(yscrollcommand=sb.set)

        self._inner = tk.Frame(self._canvas, bg=BG_PANEL)
        self._win   = self._canvas.create_window((0, 0), window=self._inner, anchor='nw')

        self._inner.bind('<Configure>', lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox('all')))
        self._canvas.bind('<Configure>', lambda e: self._canvas.itemconfig(
            self._win, width=e.width))
        self._canvas.bind('<MouseWheel>', self._on_scroll)
        self._canvas.bind('<Button-4>',   lambda e: self._canvas.yview_scroll(-1, 'units'))
        self._canvas.bind('<Button-5>',   lambda e: self._canvas.yview_scroll(1, 'units'))

        self.refresh()

    def set_close_callback(self, cb):
        self._close_cb = cb

    def _do_close(self):
        if self._close_cb:
            self._close_cb()

    def _on_scroll(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        for w in self._inner.winfo_children():
            w.destroy()

        entries = history_get()
        if not entries:
            tk.Label(self._inner,
                     text='No calls yet.\nMake a call to see history here.',
                     font=('Helvetica', 9), bg=BG_PANEL, fg=TEXT_MORSE,
                     justify='center').pack(pady=30)
            return

        for entry in entries:
            self._make_row(entry)

    # ── Single row ────────────────────────────────────────────────────────────

    def _make_row(self, entry: dict):
        direction  = entry['direction']    # 'outgoing' | 'incoming'
        call_type  = entry['call_type']    # 'video' | 'audio'
        status     = entry['status']       # 'answered' | 'declined' | 'missed' | 'no answer'
        started_at = entry['started_at']   # datetime
        duration_s = entry['duration_s']   # int | None
        remote     = entry['remote_name']

        # Icons
        type_icon = '📹' if call_type == 'video' else '🎙'
        dir_icon  = '↗' if direction == 'outgoing' else '↙'

        # Colour
        if status == 'answered':
            accent = TEAL if direction == 'incoming' else ACCENT
        else:
            accent = RED_ERR

        status_label = {
            'answered':  'Answered',
            'declined':  'Declined',
            'missed':    'Missed',
            'no answer': 'No answer',
        }.get(status, status.title())

        type_label = 'Video' if call_type == 'video' else 'Audio'

        # Row frame
        row = tk.Frame(self._inner, bg=BG_PANEL, cursor='hand2')
        row.pack(fill='x', padx=6, pady=1)
        inner = tk.Frame(row, bg=BG_PANEL, padx=10, pady=8)
        inner.pack(fill='x')

        # Left icon tile
        icon_tile = tk.Frame(inner, bg=BG_CARD, width=42, height=42)
        icon_tile.pack(side='left', padx=(0, 10))
        icon_tile.pack_propagate(False)
        tk.Label(icon_tile, text=type_icon, font=('Helvetica', 18),
                 bg=BG_CARD).place(relx=0.5, rely=0.5, anchor='center')

        # Text column
        txt = tk.Frame(inner, bg=BG_PANEL)
        txt.pack(side='left', fill='x', expand=True)

        # Row 1 – direction arrow + name
        r1 = tk.Frame(txt, bg=BG_PANEL)
        r1.pack(fill='x')
        tk.Label(r1, text=dir_icon, font=('Helvetica', 10, 'bold'),
                 bg=BG_PANEL, fg=accent).pack(side='left', padx=(0, 4))
        tk.Label(r1, text=remote, font=('Helvetica', 11, 'bold'),
                 bg=BG_PANEL, fg=TEXT_PRI).pack(side='left')

        # Row 2 – call type · status
        r2 = tk.Frame(txt, bg=BG_PANEL)
        r2.pack(fill='x')
        tk.Label(r2, text=f'{type_label} · {status_label}',
                 font=('Helvetica', 8), bg=BG_PANEL,
                 fg=accent if status != 'answered' else TEXT_SEC).pack(side='left')

        # Row 3 – timestamp  duration
        r3 = tk.Frame(txt, bg=BG_PANEL)
        r3.pack(fill='x')
        ts  = _fmt_timestamp(started_at)
        dur = _fmt_duration(duration_s)
        tk.Label(r3, text=f'{ts}   {dur}'.rstrip(),
                 font=('Helvetica', 8), bg=BG_PANEL, fg=TEXT_MORSE).pack(side='left')

        # Thin divider below each row
        tk.Frame(self._inner, bg=BORDER, height=1).pack(fill='x', padx=10)

        # Hover highlight
        all_widgets = [row, inner, txt, r1, r2, r3]

        def on_enter(e, ws=all_widgets, tile=icon_tile):
            for w in ws:
                try: w.configure(bg=BG_HOVER)
                except Exception: pass
            tile.configure(bg=BG_ACTIVE)

        def on_leave(e, ws=all_widgets, tile=icon_tile):
            for w in ws:
                try: w.configure(bg=BG_PANEL)
                except Exception: pass
            tile.configure(bg=BG_CARD)

        for w in all_widgets + [icon_tile]:
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)