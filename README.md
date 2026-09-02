<div align="center">

<img src="assets/yapper-header.png" alt="Yapper" width="620" />

**Open-source voice dictation for English, Hindi & Hinglish — offline, on your CPU.**
Hold a key, talk, and it types into any app.

[![license](https://img.shields.io/badge/license-MIT-2f2927.svg)](LICENSE)
![python](https://img.shields.io/badge/python-3.9–3.12-e87553.svg)
![engine](https://img.shields.io/badge/engine-CTranslate2-b84e36.svg)
![offline](https://img.shields.io/badge/100%25-offline-3b9a73.svg)

</div>

---

A free, local alternative to paid dictation apps like [Wispr Flow](https://wisprflow.ai),
superwhisper, [Aqua Voice](https://withaqua.com) and Willow — for people who **mix English and
Hindi** and want their voice as **Roman text** to paste straight into Claude, ChatGPT, a chat
box, an editor, anywhere. No account, no subscription, no cloud.

Yapper transcribes with a fine-tuned **Whisper-tiny** that outputs **romanized Hinglish**
directly (`aaj movie dekhne chalein kya`, not Devanagari), running on **CTranslate2** on the
CPU — fast on ordinary laptops, no GPU. The model ships **in the repo**, so it works offline the
moment you clone it.

## Quick start

```bash
git clone https://github.com/ABHISHEKgauti25/yapper.git
cd yapper
python run.py
```

`run.py` installs the (small, CPU-only) dependencies into an isolated `.venv` on first launch,
then starts Yapper in your system tray. Put your cursor in any text field, **hold Right Ctrl,
speak, release** — your words get typed in. A small mascot in the corner shows the state.

> **Use a standard [python.org](https://python.org) Python 3.9–3.12 — not Anaconda/conda.**
> Anaconda's Python crashes the native speech engine on Windows. If you launch `run.py` from a
> conda prompt, it automatically finds a python.org Python and builds `.venv` from that.

## Accuracy vs. speed

The bundled model is **int8** (46 MB, ~0.3 s/clip on CPU) — fast and small, great for dictation.
For a bit more accuracy, use the **full-precision** model instead, in `~/.yapper/config.json`:

```json
{ "download_from_hf": true, "compute_type": "float32" }
```

That downloads the float32 model from Hugging Face once (cached). You can also raise
`"beam_size": 5` for slightly better output at some cost in speed.

## How it works

```
  microphone ──► Whisper-tiny (CTranslate2, CPU) ──► romanized text ──► pasted into the focused field
```

One stage, **no language model after transcription** — the output is the raw romanized
transcription. (Optional LLM cleanup is on the roadmap.)

## Configuration — `~/.yapper/config.json`

```json
{
  "hotkey": "ctrl_r",
  "compute_type": "int8",
  "download_from_hf": false,
  "auto_paste": true,
  "trailing_space": true,
  "mascot": true,
  "size": "small"
}
```

- **hotkey**: `ctrl_r` (default), `ctrl_l`, `alt_r`, `f9`, … (Right Ctrl avoids clashing with Ctrl+C/V).
- **compute_type**: `int8` (bundled) · `int8_float32` · `float32` (with `download_from_hf`).
- **mascot**: `false` to run tray-only. Also toggleable from the tray menu.
- **size**: mascot size — `small` · `medium` · `large`.

## Roadmap

Early, in-development. Planned next:

- [ ] **Better rare words** in the Hinglish STT — names, technical terms, brands, jargon.
- [ ] **Optional post-transcription spelling correction** via a small local LLM (opt-in).
- [ ] `whisper.cpp` backend option + a single-file packaged build.
- [ ] Tested builds for macOS and Linux; start-on-login; a small settings window.

## Requirements

- A standard **python.org Python 3.9–3.12** (see the note above), a microphone. **CPU only — no GPU, no PyTorch.**
- Deps (installed by `run.py`): `faster-whisper` (CTranslate2), numpy, sounddevice, pynput, PySide6.
- Primarily tested on **Windows**; macOS/Linux should work (hotkey/paste vary by desktop).

## The model

A fine-tune of `openai/whisper-tiny` for romanized Hindi/English/Hinglish, exported to
CTranslate2. The int8 build is bundled here; the full-precision build and model card are on
Hugging Face: **`abhishekgautamm/whisper-tiny-hinglish-ct2`**.

## Credits & license

Speech recognition: [OpenAI Whisper](https://github.com/openai/whisper) (tiny), fine-tuned ·
runtime: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) / CTranslate2 ·
transliteration of training targets: [LIPI](https://github.com/ABHISHEKgauti25/lipi).
[MIT](LICENSE) © 2026 Abhishek Gautam.
