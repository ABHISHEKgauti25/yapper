#!/usr/bin/env python3
"""Yapper launcher - sets itself up on first run, then starts the app.

    python run.py                       most accurate model (base); uses your NVIDIA GPU if you have one
    python run.py --model tiny          fastest model (bundled, works offline)
    python run.py --fp32                full-precision weights (bigger one-time download)
    python run.py --cpu                 never use the GPU
    python run.py --transcribe a.wav    transcribe audio files and exit (no GUI)

First run creates ./.venv and installs the dependencies (plus the CUDA runtime if an NVIDIA GPU
is found). Needs a python.org Python 3.9-3.13. The Anaconda Python breaks the native libraries on
Windows, so run.py builds the venv from a python.org Python if one is installed.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQ, REQ_GPU = ROOT / "requirements.txt", ROOT / "requirements-gpu.txt"
STAMP = VENV / ".installed"
PY_OK = ((3, 9), (3, 13))


def log(msg: str) -> None:
    print(f"[yapper] {msg}", flush=True)


# ---------------------------------------------------------------- python / venv
def _venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _in_venv() -> bool:
    try:
        return Path(sys.prefix).resolve() == VENV.resolve()
    except Exception:
        return False


def _is_conda(exe: str) -> bool:
    e = exe.lower()
    return "conda" in e or "continuum" in e or (Path(exe).resolve().parent / "conda-meta").exists()


def _py_version(exe: str) -> tuple[int, int] | None:
    try:
        out = subprocess.run([exe, "-c", "import sys; print(*sys.version_info[:2])"],
                             capture_output=True, text=True, timeout=20).stdout.split()
        return int(out[0]), int(out[1])
    except Exception:
        return None


def _find_pythons() -> list:
    """python.org (non-conda) Pythons in the supported range: the current one first, then newest first."""
    cands = [sys.executable]
    if os.name == "nt":
        drive = os.environ.get("SystemDrive", "C:") + os.sep
        for r in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("PROGRAMFILES", ""), drive):
            if r:
                cands += glob.glob(os.path.join(r, "Programs", "Python", "Python3*", "python.exe"))
                cands += glob.glob(os.path.join(r, "Python3*", "python.exe"))
    else:
        cands += [p for p in (shutil.which(f"python3.{m}") for m in range(13, 8, -1)) if p]
    found = []
    for c in dict.fromkeys(cands):
        if c and os.path.exists(c) and not _is_conda(c):
            v = _py_version(c)
            if v and PY_OK[0] <= v <= PY_OK[1]:
                found.append((c != sys.executable, tuple(-x for x in v), c))
    return [c for *_, c in sorted(found)]


def _make_venv() -> bool:
    """Create ./.venv with the first Python that produces a working venv (with pip)."""
    for base in _find_pythons():
        log(f"creating .venv with {base} ...")
        ok = subprocess.call([base, "-m", "venv", str(VENV)], env=_clean_env()) == 0
        ok = ok and subprocess.call([str(_venv_python()), "-m", "pip", "--version"], env=_clean_env(),
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
        if ok:
            return True
        log("that Python could not create a working venv; trying another ...")
        shutil.rmtree(VENV, ignore_errors=True)
    return False


def _clean_env() -> dict:
    """Drop conda from PATH - on Windows its DLLs shadow Qt / CTranslate2."""
    env = dict(os.environ)
    roots = [os.path.normcase(os.path.abspath(r)) for r in (env.get("CONDA_PREFIX"), env.get("CONDA_PREFIX_1")) if r]

    def keep(p):
        return p and "conda" not in p.lower() and not any(os.path.normcase(p).startswith(r) for r in roots)

    env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep) if keep(p))
    for k in ("CONDA_PREFIX", "CONDA_PREFIX_1", "CONDA_DEFAULT_ENV", "CONDA_EXE", "CONDA_SHLVL", "PYTHONPATH", "PYTHONHOME"):
        env.pop(k, None)
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return env


# ---------------------------------------------------------------- GPU
def _driver_cuda() -> tuple | None:
    """CUDA version supported by the NVIDIA driver (from nvidia-smi), or None if there is no NVIDIA GPU."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    try:
        out = subprocess.run([smi], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        return None
    m = re.search(r"CUDA Version:\s*(\d+)\.(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _device_setting() -> str:
    sys.path.insert(0, str(ROOT))
    try:
        from yapper.config import Config   # stdlib-only module
        return Config.load().device
    except Exception:
        return "auto"
    finally:
        sys.path.pop(0)


def _linux_cuda_paths(py: str) -> list:
    if os.name == "nt":
        return []
    code = "import site, sys; sys.stdout.write(chr(10).join(site.getsitepackages()))"
    out = subprocess.run([py, "-c", code], capture_output=True, text=True).stdout.split()
    return [d for sp in out for d in glob.glob(os.path.join(sp, "nvidia", "*", "lib"))] + glob.glob("/usr/local/cuda*/lib64")


# ---------------------------------------------------------------- install
def _stamps() -> dict:
    """What is already set up in .venv: {"cpu": <req hash>, "gpu": <req hash> | "system"}."""
    try:
        return dict(x.split(":", 1) for x in STAMP.read_text().split() if ":" in x)
    except OSError:
        return {}


def _stamp(kind: str, value: str) -> None:
    st = _stamps()
    st[kind] = value
    STAMP.write_text(" ".join(f"{k}:{v}" for k, v in sorted(st.items())))


def _sha(f: Path) -> str:
    return hashlib.sha1(f.read_bytes()).hexdigest()


def _child_env(py: str) -> dict:
    env = _clean_env()
    libs = _linux_cuda_paths(py)
    if libs:
        env["LD_LIBRARY_PATH"] = os.pathsep.join(libs + [env.get("LD_LIBRARY_PATH", "")])
    return env


def _gpu_works(py: str) -> bool:
    code = f"import sys; sys.path.insert(0, {str(ROOT)!r}); from yapper.asr import gpu_works; sys.exit(0 if gpu_works() else 1)"
    try:
        return subprocess.run([py, "-c", code], env=_child_env(py), capture_output=True, timeout=180).returncode == 0
    except Exception:
        return False


def _install(py: str, gpu: bool) -> None:
    st = _stamps()
    pip = [py, "-m", "pip", "install", "--disable-pip-version-check", "-q"]
    if st.get("cpu") != _sha(REQ):
        log("installing dependencies (one time, a few minutes) ...")
        subprocess.check_call(pip + ["--upgrade", "pip"], env=_clean_env())
        subprocess.check_call(pip + ["-r", str(REQ)], env=_clean_env())
        _stamp("cpu", _sha(REQ))
    if not gpu or st.get("gpu") in ("system", _sha(REQ_GPU)):
        return
    log("NVIDIA GPU found - checking for CUDA libraries already on this computer ...")
    if _gpu_works(py):
        log("found them - using your existing CUDA install (nothing to download).")
        return _stamp("gpu", "system")
    log("not found - downloading the CUDA runtime for Yapper (~1 GB, one time) ...")
    if subprocess.call(pip + ["-r", str(REQ_GPU)], env=_clean_env()) == 0 and _gpu_works(py):
        return _stamp("gpu", _sha(REQ_GPU))
    log("the GPU could not be set up; Yapper will run on the CPU (to retry, update the NVIDIA driver and delete .venv/.installed).")
    _stamp("gpu", _sha(REQ_GPU))      # do not retry the download on every launch


def _bootstrap() -> None:
    py = str(_venv_python())
    if not _venv_python().exists() and not _make_venv():
        log("Yapper needs Python 3.9-3.13 from https://python.org (the Anaconda Python is not supported).")
        sys.exit("Install it, then run:  python run.py")
    gpu = False
    if os.environ.get("YAPPER_DEVICE", _device_setting()) != "cpu":
        cuda = _driver_cuda()
        if cuda and cuda < (12, 0):
            log(f"NVIDIA driver supports CUDA {cuda[0]}.{cuda[1]}; GPU mode needs 12+ - update the driver. Using the CPU.")
            os.environ["YAPPER_DEVICE"] = "cpu"
        gpu = bool(cuda and cuda >= (12, 0))
    _install(py, gpu)
    env = _child_env(py)
    env["YAPPER_CHILD"] = "1"
    sys.exit(subprocess.call([py, str(ROOT / "run.py"), *sys.argv[1:]], env=env))


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(prog="python run.py",
                                 description="Yapper - offline voice dictation for English, Hindi & Hinglish.")
    ap.add_argument("--model", choices=["base", "tiny"], help="base = most accurate (default), tiny = fastest")
    ap.add_argument("--fp32", action="store_true", help="use full-precision weights instead of int8")
    dev = ap.add_mutually_exclusive_group()
    dev.add_argument("--cpu", action="store_true", help="run on the CPU even if a GPU is available")
    dev.add_argument("--gpu", action="store_true", help="use the NVIDIA GPU (already the default when one is available)")
    ap.add_argument("--transcribe", nargs="+", metavar="FILE", help="transcribe audio files and exit")
    args = ap.parse_args()
    if args.model:
        os.environ["YAPPER_MODEL"] = args.model
    if args.fp32:
        os.environ["YAPPER_PRECISION"] = "fp32"
    if args.cpu or args.gpu:
        os.environ["YAPPER_DEVICE"] = "cpu" if args.cpu else "cuda"

    if not (_in_venv() and os.environ.get("YAPPER_CHILD")):
        return _bootstrap()
    sys.path.insert(0, str(ROOT))
    if args.transcribe:
        from yapper.transcribe import main as transcribe
        return transcribe(args.transcribe)
    from yapper.app import main as app
    app()


if __name__ == "__main__":
    main()