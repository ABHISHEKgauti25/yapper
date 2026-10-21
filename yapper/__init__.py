"""Yapper - open-source, on-device voice dictation for English / Hindi / Hinglish."""
import os as _os
from pathlib import Path as _Path

__version__ = "2.0.0"

# Yapper keeps its own Hugging Face cache under ~/.yapper/hf. A global HF_HOME / HF_HUB_CACHE on the
# user's machine (a removed drive, a read-only or network folder, ...) must never break the model
# download. Set before anything imports huggingface_hub, which reads these paths at import time.
for _k in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_XET_CACHE", "HF_ASSETS_CACHE", "HF_TOKEN_PATH"):
    _os.environ.pop(_k, None)
_os.environ["HF_HOME"] = str(_Path.home() / ".yapper" / "hf")
_os.environ.setdefault("HF_HUB_VERBOSITY", "error")       # hide "unauthenticated requests" noise (public repos)
_os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
