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

Copyright 2026/5/20, Paralya Ramrakhyani

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
