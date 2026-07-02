# WhisprLocal

A local, private, hold-to-talk voice dictation tool — a self-hosted take on Wispr Flow.
Hold a hotkey, speak, release, and your words are transcribed on-device and typed into
whatever app has focus. **No audio, and no text, ever leaves your machine.**

---

## How it works

WhisprLocal is a small background daemon. It listens for a global hotkey; while you hold
it, it records your mic; when you release, it runs the audio through a local pipeline and
types the result into whatever window has focus.

```
 hold hotkey ─► record mic ─► release ─► faster-whisper (local STT)
                                              │
                                              ▼
                                     regex cleanup (fast)
                                              │
                                              ▼
                            [optional] local LLM cleanup (semantic)
                                              │
                                              ▼
                                 type / paste into focused app
```

Each stage maps to one module:

| Stage | Module | What it does |
|-------|--------|--------------|
| Hotkey + recording | `app.py` | Global hotkey listener + mic capture, orchestrates the run |
| Speech-to-text | `transcriber.py` | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2), fully offline |
| Fast cleanup | `clean.py` | Regex pass: strips `um`/`uh`, hedges, fixes spacing/casing, handles "new line" etc. |
| Semantic cleanup | `llm_clean.py` | *Optional* tiny local LLM: removes false starts, collapses repeated sentences |
| Typing | `injector.py` | Types short text key-by-key; pastes long text via clipboard (then restores it) |
| Config | `config.py` | Loads `config.toml` + environment overrides |

**Why Python:** it has the most mature local-STT bindings plus native cross-platform
hotkey/injection libraries. Nothing here touches the cloud.

---

## Quick start

```bash
cd whisprlocal
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -e .

whisprlocal                       # first launch downloads the STT model once
```

Then hold **Ctrl+Alt**, speak, and release. Text appears in your focused field.

> The optional semantic-cleanup LLM is a separate opt-in step — see
> [Semantic cleanup](#semantic-cleanup-optional-local-llm) below.

---

## Install

```bash
cd whisprlocal
python -m venv .venv && .venv\Scripts\activate   # macOS/Linux: source .venv/bin/activate
pip install -e .
```

You also need the PortAudio system library for mic capture:

- **Windows:** bundled with the `sounddevice` wheel — nothing to do.
- **macOS:** `brew install portaudio`
- **Debian/Ubuntu:** `sudo apt install portaudio19-dev libportaudio2`

The Whisper model downloads automatically on first run (a few hundred MB for `base.en`)
and is cached under `~/.cache/huggingface`.

---

## Run

The app runs in the foreground as a daemon and prints status to the terminal:

```bash
whisprlocal
# or, equivalently:
python -m whisprlocal
```

Hold **Ctrl+Alt**, speak, release. You'll see log lines like:

```
[init] ready. Hold the hotkey and speak.
[rec] listening...
[rec] 2.3s captured, transcribing...
[stt] (0.6s) -> 'Send the report to Sarah and also to Mike.'
```

### One-off overrides via environment variables

```bash
# Windows PowerShell
$env:WHISPRLOCAL_MODEL="small.en"; $env:WHISPRLOCAL_LLM=1; whisprlocal

# macOS/Linux
WHISPRLOCAL_MODEL=small.en WHISPRLOCAL_LLM=1 whisprlocal
```

| Variable | Effect |
|----------|--------|
| `WHISPRLOCAL_MODEL` | Whisper model size (`tiny.en`, `base.en`, `small.en`, …) |
| `WHISPRLOCAL_DEVICE` | `cpu` or `cuda` |
| `WHISPRLOCAL_HOTKEY` | Hold-to-talk combo, e.g. `f9` or `ctrl+alt` |
| `WHISPRLOCAL_LLM` | `1`/`true` to enable semantic LLM cleanup |
| `WHISPRLOCAL_LLM_MODEL_PATH` | Path to a `.gguf` model file |

### Run on startup (Windows, no terminal window)

The repo ships `whisprlocal-autostart.vbs`, which launches the daemon silently. Drop a
shortcut to it in your Startup folder (`Win+R` → `shell:startup`). Set your preferred
options in `config.toml` (below) so no env vars are needed.

To stop the daemon, close its terminal (or end the `python.exe` running `whisprlocal`).

---

## Configure

Copy the example config and edit it:

```bash
mkdir -p ~/.config/whisprlocal
cp config.example.toml ~/.config/whisprlocal/config.toml
```

Config lives at `~/.config/whisprlocal/config.toml` (override the location with
`WHISPRLOCAL_CONFIG`). Environment variables take precedence over the file.

| Key | Default | Meaning |
|-----|---------|---------|
| `model` | `base.en` | Whisper size: `tiny.en` → `large-v3` (bigger = better, slower) |
| `device` | `cpu` | `cpu`, or `cuda` for an NVIDIA GPU |
| `compute_type` | `int8` | `int8` on CPU, `float16` on CUDA |
| `language` | `en` | Language code, or drop `.en` + set this for multilingual models |
| `hotkey` | `ctrl+alt` | Hold-to-talk combo. Tokens: `ctrl`, `alt`, `shift`, `cmd`/`win`, `f9`, `f10`, a letter |
| `trailing_space` | `true` | Add a space after each dictation so phrases don't run together |
| `filler_level` | `1` | `0` off, `1` strip `um`/`uh`, `2` also strip hedges (`like`, `you know`) parenthetically |
| `llm_cleanup` | `false` | Enable the semantic LLM cleanup pass |
| `llm_model_path` | `~/.cache/whisprlocal/qwen2.5-1.5b-instruct-q4_k_m.gguf` | GGUF model file |
| `llm_idle_unload_seconds` | `60` | Free the LLM's RAM after this many idle seconds (`0` = never) |
| `llm_threads` | *(unset)* | CPU threads for the LLM; default = physical cores |

---

## Semantic cleanup (optional local LLM)

The default cleanup is fast regex: it strips `um`/`uh` and hedges. It can't reason about
*meaning* — it won't notice you restarted a sentence, said the same thing twice, or
trailed off. Turn on `llm_cleanup` to add a tiny local model (Qwen2.5-1.5B-Instruct, Q4,
~1 GB) that also collapses repeats and false starts. Fully offline, like everything else.

Example — this transcript:

> *"So I was thinking, um, I was thinking we should, like, we should meet tomorrow. We
> should meet tomorrow to go over the, uh, the budget."*

becomes:

> *"I was thinking we should meet tomorrow to go over the budget."*

Dictated **questions and commands stay as text** — they are typed, never answered.

### Resource policy (the whole point of the design)

- **Nothing loaded while idle.** The model is *not* resident when you're not dictating:
  ~0 % CPU, ~0 extra RAM. Only the featherweight hotkey listener runs.
- **No lag on first use.** The model starts loading the instant you press the hotkey, so
  the ~1–2 s load hides behind your speech + transcription. By the time cleanup runs it's
  already warm. Steady-state cleanup is ~1 s per utterance.
- **Self-releasing.** After `llm_idle_unload_seconds` (default 60) with no dictation, the
  model unloads and frees its RAM.

If the model file is missing or anything fails, it silently falls back to the regex-only
text — dictation never breaks.

### Setup

```bash
# 1. Install the LLM runtime (prebuilt CPU wheels, no compiler needed).
#    NOTE: PyPI's llama-cpp-python wheels are built with AVX-512 and will crash with an
#    illegal-instruction error (WinError 0xc000001d) on CPUs that lack it — e.g. Intel
#    Comet Lake (10th-gen H). The wheels on the CPU index below are AVX2-only and run
#    everywhere. Pin the version so pip takes that wheel:
pip install "llama-cpp-python==0.2.90" --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
#    (If your CPU has AVX-512, plain `pip install -e ".[llm]"` gets a newer build.)

# 2. Download the model once (~1 GB) to the default path
python -c "from huggingface_hub import hf_hub_download; import os; \
d=os.path.expanduser('~/.cache/whisprlocal'); os.makedirs(d,exist_ok=True); \
hf_hub_download('Qwen/Qwen2.5-1.5B-Instruct-GGUF','qwen2.5-1.5b-instruct-q4_k_m.gguf',local_dir=d)"

# 3. Enable it — set `llm_cleanup = true` in config.toml, or for a one-off:
#    PowerShell:  $env:WHISPRLOCAL_LLM=1; whisprlocal
#    bash:        WHISPRLOCAL_LLM=1 whisprlocal
```

Want a lighter footprint? Swap in `qwen2.5-0.5b-instruct-q4_k_m.gguf` (~0.4 GB, ~2.5 %
RAM) and point `llm_model_path` at it — plenty for filler + dedup.

---

## Efficiency notes

- **`base.en` + `int8`** is the sweet spot: near real-time on a modern CPU, low RAM.
- Bump to `small.en` for accuracy; use `device="cuda"` + `compute_type="float16"` if you
  have an NVIDIA GPU (multi-x faster).
- `vad_filter` trims silence so short utterances transcribe almost instantly.
- Strings longer than ~60 chars are pasted via clipboard (and your clipboard is restored)
  instead of typed key-by-key, avoiding per-character lag.
- The LLM pass runs on CPU by default (`n_gpu_layers=0`) so it doesn't compete with the
  GPU for VRAM. On a small GPU (e.g. 4 GB) that keeps STT and cleanup out of each other's
  way.

---

## Platform permissions

- **Windows:** run the terminal normally; no extra permissions needed.
- **macOS:** grant your terminal (or the built app) **Accessibility** and **Input
  Monitoring** in System Settings → Privacy & Security, plus **Microphone**. Global
  hotkeys and synthetic typing won't work otherwise.
- **Linux:** works on **X11**. On Wayland, global key capture and synthetic input are
  restricted; run an X11 session or use an `xdotool`/`ydotool`-based injector.

---

## Layout

```
whisprlocal/
├── app.py          # daemon: hotkey loop, recording orchestration
├── transcriber.py  # faster-whisper wrapper + resampling
├── injector.py     # type/paste into focused app
├── config.py       # TOML + env config
├── clean.py        # transcript post-processing (fast regex)
├── llm_clean.py    # optional semantic cleanup (lazy-loaded local LLM)
├── __main__.py
└── __init__.py
```

## License

MIT — do whatever, brochacho.
