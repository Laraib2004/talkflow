# WhisprLocal — Install Instructions

Hold **Ctrl + Alt**, speak, release — your words are transcribed on your own
machine and typed into whatever app is focused. Nothing is sent to the cloud.

Pick your operating system below.

---

## Windows

- Install **Python 3.11+** from [python.org](https://python.org) (tick **"Add Python to PATH"** during setup).
- Download or clone this project, then open **PowerShell** in the project folder.
- Run the one-command setup:
  - `powershell -ExecutionPolicy Bypass -File .\setup.ps1`
  - This creates the environment, installs everything, and downloads the models.
- Start the app:
  - `.venv\Scripts\python.exe -m whisprlocal`
- Hold **Ctrl + Alt**, speak, release. The text appears where your cursor is.
- *(Optional)* Start it automatically on login, with no window:
  - Press **Win + R**, type `shell:startup`, press Enter.
  - Put a shortcut to `whisprlocal-autostart.vbs` in that folder.

---

## Mac

- Install **Python 3.11+** and **PortAudio** (needed for the microphone):
  - `brew install python portaudio`
- Open **Terminal** in the project folder.
- Run the one-command setup:
  - `./setup.sh`
- Start the app:
  - `./.venv/bin/whisprlocal`
- Grant permissions when asked (or in **System Settings → Privacy & Security**):
  - **Microphone**, **Accessibility**, and **Input Monitoring** for your Terminal.
- Hold **Ctrl + Alt**, speak, release. The text appears where your cursor is.

---

## Linux

- Install **Python 3.11+** and **PortAudio**:
  - Debian/Ubuntu: `sudo apt install python3 python3-venv portaudio19-dev libportaudio2`
- Open a **terminal** in the project folder.
- Run the one-command setup:
  - `./setup.sh`
- Start the app:
  - `./.venv/bin/whisprlocal`
- Use an **X11** session (Wayland blocks global hotkeys and typing into other apps).
- Hold **Ctrl + Alt**, speak, release. The text appears where your cursor is.

---

## Notes

- **Hotkey:** the hold-to-talk key is **Ctrl + Alt** by default.
- To change it, edit `hotkey` in `config.toml` (e.g. `hotkey = "f9"`).
- First launch downloads the speech model once; after that it works offline.
- Lighter install without the AI cleanup: add `-NoLlm` (Windows) or `--no-llm` (Mac/Linux) to the setup command.
