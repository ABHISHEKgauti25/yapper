<div align="center">

<img src="assets/yapper-header.png" alt="Yapper" width="620" />

**Open-source voice dictation for English, Hindi & Hinglish - offline, on your own computer.**
Hold a key, talk, and your words are typed into any app.

[![license](https://img.shields.io/badge/license-MIT-2f2927.svg)](LICENSE)
![python](https://img.shields.io/badge/python-3.9--3.13-e87553.svg)
![offline](https://img.shields.io/badge/100%25-offline-3b9a73.svg)
![version](https://img.shields.io/badge/version-2.0-6b5b95.svg)

</div>

---

A free, local alternative to paid dictation apps for people who **mix English and Hindi** and want
their voice as **Roman text** (`kal meeting hai na?`) to paste into ChatGPT, Claude, an editor, a chat box,
anywhere. No account, no subscription, no cloud: audio never leaves your machine.

## What's new in v2

- **Two new speech models.** A new **base** model (most accurate, now the default) and a retrained **tiny**
  model, both fine-tuned on ~304 hours of Indian speech (v1: tiny only).
- **About half the errors of v1.** Average word error rate across 14 test sets: v1 38.9% -> v2 base 20.0%.
  Big gains on Hindi, numbers, commands and whispered speech.
- **Uses your NVIDIA GPU automatically** when you have one (CPU otherwise).
- **Small by default, full precision on request.** int8 models (41 / 76 MB); `--fp32` for full-precision weights.

## Install and run

1. Install **Python 3.9 - 3.13** from [python.org](https://www.python.org/downloads/)
   (Windows: tick *"Add python.exe to PATH"*).
2. In a terminal:

```bash
git clone https://github.com/ABHISHEKgauti25/yapper.git
cd yapper
python run.py
```

That's it. The **first run** sets everything up by itself (a few minutes):
creates a private `.venv`, installs the dependencies and downloads the base model (76 MB) from Hugging Face.
If you have an NVIDIA GPU, it first checks for CUDA libraries already on your computer (CUDA Toolkit 12 +
cuDNN 9) and uses them; only if they are missing does it download the CUDA runtime (~1 GB, one time).
Later runs start in seconds.

**Use it:** put the cursor in any text field, **hold Right Ctrl, speak, release**. A small mascot in the
corner shows when it's listening and thinking; Yapper lives in the system tray (right-click -> Quit).

> Use the python.org Python, not Anaconda. If you start `run.py` from Anaconda, it finds a python.org
> Python on its own and uses that instead.

## Options

```bash
python run.py                  # base model, GPU if available (recommended)
python run.py --model tiny     # fastest model; bundled, works fully offline
python run.py --fp32           # full-precision weights (bigger one-time download)
python run.py --cpu            # never use the GPU
python run.py --transcribe meeting.wav notes.mp3   # transcribe files, no GUI
```

| Model | Size (int8 / fp32) | Word error rate* | Speed, 5 s of speech** (CPU / GPU) | Get it |
|---|---|---|---|---|
| **base** (default) | 76 MB / 290 MB | **20.0%** | ~0.9 s / ~0.4 s | downloaded once on first run |
| **tiny** | 41 MB / 151 MB | 24.5% | ~0.5 s / ~0.2 s | int8 ships with the repo |

\* average over 14 test sets, see [Benchmarks](#benchmarks). \*\* Ryzen 5 5600H laptop / GTX 1650, int8.

**int8 or fp32?** int8 is the default because it is 4x smaller and fast on any CPU, and it costs almost
nothing in accuracy. Measured in the app on 2,560 held-out clips (word error rate):

| | int8 (CPU) | int8 (GPU) | fp32 (GPU) |
|---|---|---|---|
| base | 25.3% | 25.1% | 24.9% |
| tiny | 30.2% | 29.6% | 29.5% |

Downloaded models live in `~/.yapper/models/`. If a download fails (no internet), Yapper keeps working
with the bundled tiny model.

## Settings

Optional. Create or edit `~/.yapper/config.json` (command-line flags override it for one run):

```json
{
  "model": "base",
  "precision": "int8",
  "device": "auto",
  "hotkey": "ctrl_r",
  "silence_peak": 0.02,
  "auto_paste": true,
  "mascot": true,
  "size": "small"
}
```

- **model** `base` | `tiny`. **precision** `int8` | `fp32`. **device** `auto` (GPU if available) | `cuda` | `cpu`.
- **hotkey** `ctrl_r` (default), `ctrl_l`, `alt_r`, `f9`, `f8`, `pause`, ... Right Ctrl avoids clashing with Ctrl+C / Ctrl+V.
- **silence_peak** clips quieter than this count as "no speech"; raise it if background noise gets typed.
- **mascot** `false` for tray-only (also a tray toggle). **size** `small` | `medium` | `large`.

## Benchmarks

Word / character error rate in %, lower is better. Full-precision models, greedy decoding,
text lower-cased with punctuation removed, Hindi romanized. The v2 checkpoints are on Hugging Face:
[whisper-base-hinglish-v2](https://huggingface.co/abhishekgautamm/whisper-base-hinglish-v2) and
[whisper-tiny-hinglish-v2](https://huggingface.co/abhishekgautamm/whisper-tiny-hinglish-v2).

**Public benchmarks, full test sets** (never used for training)

| Dataset | Clips | v1 tiny | v2 tiny | v2 base |
|---|---|---|---|---|
| Svarah - Indian English | 6,656 | 29.5 / 15.2 | 28.6 / 16.4 | **24.1 / 13.9** |
| Monsoon - Indian English | 2,102 | 18.8 / 9.0 | 20.3 / 11.0 | **16.4 / 8.7** |
| CoSHE - long-form Hinglish | 1,985 | 39.6 / 22.5 | 44.0 / 25.4 | **36.6 / 19.8** |
| FLEURS - Hindi | 418 | 49.5 / 21.5 | 40.9 / 18.3 | **34.5 / 16.0** |

**Held-out test sets of the training corpora** (unseen speakers / prompts)

| Dataset | Clips | v1 tiny | v2 tiny | v2 base |
|---|---|---|---|---|
| wSPIRE - English incl. whispered | 150 | 56.5 / 29.4 | 4.2 / 2.6 | **2.4 / 1.2** |
| SPIRE-SIES - spontaneous English | 150 | 32.9 / 20.1 | 29.4 / 18.7 | **23.9 / 14.8** |
| MUCS - Hindi-English code-switch | 250 | 40.0 / 26.4 | 32.0 / 21.1 | **28.4 / 19.3** |
| MUCS - Hindi | 250 | 66.2 / 29.9 | 36.3 / 15.6 | **29.2 / 12.6** |
| HiACC - Hinglish (adults) | 150 | 28.7 / 13.4 | 22.3 / 10.0 | **18.1 / 8.4** |
| HiACC - Hinglish (children) | 150 | 33.2 / 16.4 | 22.5 / 11.1 | **17.8 / 7.8** |
| VoiceBench - spoken prompts | 250 | 27.6 / 14.3 | 20.9 / 10.8 | **16.9 / 8.7** |
| SLURP - assistant commands | 250 | 62.8 / 42.7 | 33.4 / 21.6 | **25.3 / 16.2** |
| Fluent Speech - commands | 100 | 27.9 / 16.9 | 5.0 / 2.9 | **2.9 / 1.9** |
| Timers and Such - numbers | 200 | 31.9 / 16.9 | **2.6 / 2.4** | 2.9 / 2.4 |
| **Average of all 14 sets** | | 38.9 / 21.0 | 24.5 / 13.4 | **20.0 / 10.8** |

v2 base beats v1 on every set. v2 tiny is much better than v1 on Hindi, code-switching, commands
and numbers, but slightly worse on clean Indian English (Monsoon) and long-form Hinglish (CoSHE), so
**base is the recommended model**; pick tiny for the lowest latency.

## Troubleshooting

- **"needs Python 3.9-3.13"** - install it from python.org and run `python run.py` again.
- **GPU not used** - the startup line says `on cuda` or `on cpu`. GPU mode needs an NVIDIA driver that
  supports CUDA 12 or newer; Yapper falls back to the CPU otherwise. After updating the driver, delete
  `.venv/.installed` so the GPU setup runs again. Use `--cpu` to skip the GPU entirely.
- **Background noise gets typed** - raise `silence_peak` in the settings.
- **Start over** - delete the `.venv` folder (reinstalls dependencies) and/or `~/.yapper` (settings and
  downloaded models).
- **macOS / Linux** - should work; you may need to allow microphone and accessibility (keyboard) access.
  Tested on Windows 11.

## How it works

```
hold key -> mic -> Whisper (fine-tuned, CTranslate2) -> romanized text -> pasted into the focused field
```

The speech models are OpenAI Whisper (tiny / base) fine-tuned to write Hindi and Hinglish directly in
Roman script, running on [faster-whisper](https://github.com/SYSTRAN/faster-whisper) /
CTranslate2 (no PyTorch). A short pre-roll keeps your first syllable; near-silent clips are ignored.

## Credits & license

Speech recognition: [OpenAI Whisper](https://github.com/openai/whisper), fine-tuned. Runtime:
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) / CTranslate2. Training-target
romanization: [LIPI](https://github.com/ABHISHEKgauti25/lipi). [MIT](LICENSE) (c) 2026 Abhishek Gautam.