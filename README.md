# iPhone PC Transfer

Local application for transferring files between a Windows PC and an iPhone over a private Wi-Fi network.

## Features

- PC → iPhone file transfer.
- iPhone → PC file transfer.
- Multiple file upload from iPhone.
- Direct camera capture from iPhone.
- PDF preview in Safari.
- Image gallery.
- QR-based access.
- Optional password and temporary code.
- Six-language selector with automatic PC language detection.
- Browser interface language detection and six-language selector for Safari/iPhone.
- Drag and drop support.
- Transfer history, connected devices, live activity and statistics.
- Automatic date-based organization for received files.

## Installation

```bash
python -m pip install -r requirements.txt
python run.py
```

## Build Windows EXE

```bash
pyinstaller --onefile --windowed --name "iPhone_PC_Transfer" --collect-all customtkinter --collect-all tkinterdnd2 --collect-all win10toast src\iphone_pc_transfer\app.py
```

## Repository notes

This repository is intended to contain the source code and documentation only.

Do not commit:

- Transferred runtime files.
- Local configuration files containing passwords.
- Generated build folders.
- Compiled executables, except as GitHub Release assets.

## License

MIT License.

Copyright (c) 2026 Rubén Navarrete Millán.
