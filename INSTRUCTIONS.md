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
- *(Optional)* Start it automatically on login (no window):
  - Easiest: re-run setup with `-Autostart`, e.g. `powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Autostart`
  - Or manually: press **Win + R**, type `shell:startup`, and put a shortcut to `whisprlocal-autostart.vbs` in that folder.

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
- *(Optional)* Start it automatically on login:
  - Re-run setup with `./setup.sh --autostart` (installs a `launchd` agent).

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
- *(Optional)* Start it automatically on login:
  - Re-run setup with `./setup.sh --autostart` (installs a `~/.config/autostart` entry).

---

## Turn off the AI cleanup (use plain regex cleanup instead)

The app has two cleanup modes:

- **Regex cleanup** (always on): fast, lightweight — removes filler words like "um" and "uh".
- **AI (LLM) cleanup** (optional): also fixes false starts and repeated sentences, but uses more memory and adds a short delay.

To disable the AI cleanup and use only the simple regex cleanup:

- Open your config file:
  - Windows: `%USERPROFILE%\.config\whisprlocal\config.toml`
  - Mac/Linux: `~/.config/whisprlocal/config.toml`
- Find the line `llm_cleanup = true` and change it to:
  - `llm_cleanup = false`
- Save the file and restart the app.

That's it — dictation now uses only the regex cleanup. Nothing else needs to be uninstalled.

- *(Optional)* To skip the AI cleanup from the very start, install with `-NoLlm` (Windows) or `--no-llm` (Mac/Linux) added to the setup command.
- *(Optional)* To free up disk space, you can delete the downloaded AI model:
  - Windows: `%USERPROFILE%\.cache\whisprlocal\`
  - Mac/Linux: `~/.cache/whisprlocal/`

---

## Logs

The app writes a log of everything it does — what it heard, what the cleanup
produced, and how the text was inserted — to a file on your machine:

- Windows: `%LOCALAPPDATA%\whisprlocal\logs\whisprlocal.log`
- macOS: `~/Library/Logs/whisprlocal/whisprlocal.log`
- Linux: `~/.local/state/whisprlocal/whisprlocal.log`

Open it if dictation ever behaves oddly — each entry shows the raw transcript,
the cleaned text, the final output, and how it was typed/pasted.

---

## Notes

- **Hotkey:** the hold-to-talk key is **Ctrl + Alt** by default.
- To change it, edit `hotkey` in `config.toml` (e.g. `hotkey = "f9"`).
- First launch downloads the speech model once; after that it works offline.
