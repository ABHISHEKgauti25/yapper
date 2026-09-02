#!/usr/bin/env python3
"""
Yapper launcher — the single command to get started after cloning:

    python run.py

Yapper needs a standard **python.org** Python (3.9-3.12). Anaconda/conda Python on Windows
crashes native ML libraries (CTranslate2 / onnxruntime), so if you launch this with a conda
Python, run.py finds a python.org install, builds an isolated ./.venv from it, installs the
(CPU-only) dependencies there, and relaunches inside it.
"""
import glob
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def _venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _in_our_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except Exception:
        return False


def _is_conda(exe: str = None) -> bool:
    exe = (exe or sys.executable).lower()
    return "conda" in exe or "continuum" in exe or bool(os.environ.get("CONDA_PREFIX"))


def _deps_import() -> bool:
    try:
        import numpy, faster_whisper, sounddevice, pynput, PySide6  # noqa
        return True
    except Exception:
        return False


def _find_pythonorg() -> str | None:
    """Locate a standard python.org Python 3.9-3.12 (never a conda one)."""
    if not _is_conda() and os.name == "nt":
        return sys.executable  # already a fine non-conda interpreter
    cands = []
    if os.name == "nt":
        roots = [os.environ.get("LOCALAPPDATA", ""), os.environ.get("PROGRAMFILES", ""),
                 os.environ.get("PROGRAMFILES(X86)", ""), "C:\\"]
        for r in roots:
            if not r:
                continue
            cands += glob.glob(os.path.join(r, "Programs", "Python", "Python31*", "python.exe"))
            cands += glob.glob(os.path.join(r, "Python31*", "python.exe"))
    else:
        cands += [f"/usr/bin/python3.{m}" for m in range(12, 8, -1)]
    good = []
    for c in cands:
        cl = c.lower()
        if os.path.exists(c) and "conda" not in cl and "continuum" not in cl:
            good.append(c)
    if not _is_conda():
        good.insert(0, sys.executable)
    good.sort(reverse=True)  # prefer the newest Python3xx
    return good[0] if good else None


def _clean_env() -> dict:
    env = dict(os.environ)
    env.pop("CONDA_PREFIX", None)            # so the child venv isn't mistaken for conda
    env.pop("PYTHONPATH", None)
    return env


def _launch_here() -> None:
    sys.path.insert(0, str(ROOT))
    from yapper.app import main as run
    run()


def main() -> None:
    # If we're already inside our venv, just run (it was built from python.org).
    if _in_our_venv():
        _launch_here()
        return
    # A working, non-conda interpreter with deps present can run directly.
    if not _is_conda() and _deps_import():
        _launch_here()
        return

    base = _find_pythonorg()
    if base is None:
        sys.exit(
            "Yapper needs a standard python.org Python 3.9-3.12 (Anaconda's Python crashes the\n"
            "native speech engine on Windows). Install one from https://python.org and re-run\n"
            "with it, e.g.:  py -3.11 run.py"
        )
    if not _venv_python().exists():
        print(f"[yapper] creating .venv from {base} ...")
        subprocess.check_call([base, "-m", "venv", str(VENV)], env=_clean_env())
    try:
        py = str(_venv_python())
        subprocess.check_call([py, "-m", "pip", "install", "--upgrade", "pip"], env=_clean_env())
        subprocess.check_call([py, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
                              env=_clean_env())
    except subprocess.CalledProcessError as e:
        sys.exit(f"[yapper] dependency install failed: {e}")
    print("[yapper] launching ...")
    sys.exit(subprocess.call([str(_venv_python()), str(ROOT / "run.py")], env=_clean_env()))


if __name__ == "__main__":
    main()
