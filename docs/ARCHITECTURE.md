# Architecture

## Project layers

```text
src/iphone_pc_transfer/
├── app.py
├── main.py
├── core/
├── gui/
├── web/
└── assets/
```

## Responsibilities

- `app.py`: stable integrated application entry point.
- `main.py`: package entry point.
- `core/`: reusable support modules.
- `gui/`: reserved for future CustomTkinter components.
- `web/`: reserved for future Flask templates and static assets.
- `data/`: runtime transfer folders, history and configuration.

## Design note

The current implementation keeps a stable single-file runtime in `app.py`.
The folder structure is prepared for future modularization without changing
user-facing behavior.
