# GitHub release guide

## Before publishing

- Verify that `LICENSE` contains the correct copyright holder.
- Confirm that no runtime files from `data/TRANSFERENCIA_IPHONE_PC` are included.
- Do not commit passwords or configuration JSON files.
- Build executables locally and upload them under GitHub Releases.

## Recommended release asset

Use PyInstaller:

```bash
pyinstaller --onefile --windowed --name "iPhone_PC_Transfer" --collect-all customtkinter --collect-all tkinterdnd2 --collect-all win10toast src\iphone_pc_transfer\app.py
```

Upload the generated executable as a release asset, not as a normal committed
file.
