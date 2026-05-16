# Windows executable packaging

## Recommended single-file build

```bash
pyinstaller --onefile --windowed --name "iPhone_PC_Transfer" --collect-all customtkinter --collect-all tkinterdnd2 --collect-all win10toast src\iphone_pc_transfer\app.py
```

The generated executable will be located at:

```text
dist\iPhone_PC_Transfer.exe
```

## Folder-based build

If the single-file build has startup issues, use the folder-based option:

```bash
pyinstaller --windowed --name "iPhone_PC_Transfer" --collect-all customtkinter --collect-all tkinterdnd2 --collect-all win10toast src\iphone_pc_transfer\app.py
```

The output will be located at:

```text
dist\iPhone_PC_Transfer\
```

Copy the full folder to another Windows PC.

## Firewall

On first execution, allow the application on private networks. Without this
permission, the iPhone will not be able to access the local server.
