# ◉ GhostWire

> secure · morse · messaging

A desktop chat app that displays messages as Morse code, with local account authentication and Fernet-based encryption.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- 🔐 Local account system (SHA3-512 + random salt)
- 📡 All messages displayed as Morse code
- ⟺ One-click translate button on received messages
- 👁 Live Morse preview as you type
- 🎨 Dark themed UI built with Tkinter

---

## Requirements

- Python 3.10 or newer
- `tkinter` (included with most Python installs)

---

## Installation

### 1 — Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/ghostwire.git
cd ghostwire
```

### 2 — Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate it:

| Platform | Command |
|----------|---------|
| macOS / Linux | `source venv/bin/activate` |
| Windows | `venv\Scripts\activate` |

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Run the app

```bash
python ghostwire.py
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'tkinter'`**

- Ubuntu/Debian: `sudo apt install python3-tk`
- Fedora: `sudo dnf install python3-tkinter`
- macOS (Homebrew): `brew install python-tk`

**App won't start on macOS**

Try running with the system Python or a Homebrew Python that includes Tk support:
```bash
brew install python-tk
```

---

## Project structure

```
ghostwire/
├── ghostwire.py       # entire application
├── requirements.txt   # third-party dependencies
└── README.md
```

> Account data is stored in a SQLite database at `~/ghostwire_accounts.sqlite`.

---

## License

MIT
