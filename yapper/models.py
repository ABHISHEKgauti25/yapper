"""Where the speech models come from.

  tiny int8   bundled in the repo (models/), works offline out of the box
  the rest    downloaded once from Hugging Face into ~/.yapper/models/
"""
from __future__ import annotations

from pathlib import Path

REPOS = {
    "tiny": "abhishekgautamm/whisper-tiny-hinglish-v2",
    "base": "abhishekgautamm/whisper-base-hinglish-v2",
}
SIZES_MB = {("tiny", "int8"): 41, ("tiny", "fp32"): 151, ("base", "int8"): 76, ("base", "fp32"): 290}
BUNDLED = Path(__file__).resolve().parent.parent / "models" / "whisper-tiny-hinglish-v2-int8"
CACHE = Path.home() / ".yapper" / "models"
_NEEDED = ("model.bin", "config.json", "tokenizer.json", "preprocessor_config.json", "vocabulary.json")


def _complete(d: Path) -> bool:
    return all((d / f).exists() for f in _NEEDED)


def local_path(model: str, precision: str) -> Path:
    if model == "tiny" and precision == "int8" and _complete(BUNDLED):
        return BUNDLED
    return CACHE / REPOS[model].split("/")[1] / "ct2" / precision


def resolve(model: str, precision: str) -> Path:
    """Return a CTranslate2 model dir, downloading it from Hugging Face if needed."""
    d = local_path(model, precision)
    if _complete(d):
        return d
    repo = REPOS[model]
    print(f"[yapper] downloading {model} ({precision}, ~{SIZES_MB[(model, precision)]} MB) "
          f"from huggingface.co/{repo} - one time only ...", flush=True)
    from huggingface_hub import snapshot_download
    snapshot_download(repo, allow_patterns=[f"ct2/{precision}/*"], local_dir=CACHE / repo.split("/")[1])
    if not _complete(d):
        raise FileNotFoundError(f"download incomplete: {d}")
    return d
