"""Hosted demo entry point (Hugging Face Space or any container).

1. Get the demo bundle made by deploy/pack_release.py, from one of:
     MPLADS_BUNDLE_PATH  a file already inside the container, or
     mplads-demo-bundle.tar.gz next to this script (uploaded into the Space), or
     MPLADS_BUNDLE_REPO  a (private) Hugging Face dataset repo, read with HF_TOKEN, or
     MPLADS_BUNDLE_URL   any direct HTTPS link.
2. If MPLADS_BUNDLE_SHA256 is set, refuse a bundle whose checksum differs.
3. Unpack it safely and start the server in read-only mode on 0.0.0.0:$PORT.
   The server itself re-checks every sealed release file before serving.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = Path(os.environ.get("MPLADS_RUN_DIR", HERE / "run"))
BUNDLE_NAME = os.environ.get("MPLADS_BUNDLE_FILE", "mplads-demo-bundle.tar.gz")


def log(msg: str) -> None:
    print(f"[start] {msg}", flush=True)


def fetch() -> Path:
    local = os.environ.get("MPLADS_BUNDLE_PATH")
    if local:
        return Path(local)
    beside = HERE / BUNDLE_NAME  # simplest setup: bundle uploaded into the (private) Space itself
    if beside.is_file():
        log("Using the bundle stored in this Space.")
        return beside
    repo = os.environ.get("MPLADS_BUNDLE_REPO")
    url = os.environ.get("MPLADS_BUNDLE_URL") or (f"https://huggingface.co/datasets/{repo}/resolve/main/{BUNDLE_NAME}" if repo else "")
    if not url:
        sys.exit("Set MPLADS_BUNDLE_REPO (Hugging Face dataset repo), MPLADS_BUNDLE_URL or MPLADS_BUNDLE_PATH.")
    target = Path(os.environ.get("TMPDIR", "/tmp")) / BUNDLE_NAME
    request = urllib.request.Request(url)
    token = os.environ.get("HF_TOKEN")
    if token and "huggingface.co" in url:
        request.add_header("Authorization", f"Bearer {token}")
    log(f"Downloading data bundle ({'private repo' if token else 'public link'})…")
    with urllib.request.urlopen(request, timeout=600) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out, 1024 * 1024)
    return target


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def unpack(bundle: Path) -> None:
    expected = os.environ.get("MPLADS_BUNDLE_SHA256", "").strip().lower()
    if expected:
        got = checksum(bundle)
        if got != expected:
            sys.exit(f"Bundle checksum mismatch: expected {expected}, got {got}. Not starting.")
        log("Bundle checksum matches.")
    if RUN.exists():
        shutil.rmtree(RUN)
    RUN.mkdir(parents=True)
    with tarfile.open(bundle, "r:gz") as tar:
        tar.extractall(RUN, filter="data")  # rejects absolute paths, '..', links outside RUN
    log(f"Unpacked to {RUN}")


def main() -> None:
    unpack(fetch())
    port = os.environ.get("PORT", "7860")
    hosts = [h for h in os.environ.get("MPLADS_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if os.environ.get("SPACE_HOST"):
        hosts.append(os.environ["SPACE_HOST"])  # set automatically by Hugging Face Spaces
    if not hosts:
        log("Warning: no public hostname configured (SPACE_HOST / MPLADS_ALLOWED_HOSTS); only localhost requests will be accepted.")
    command = [sys.executable, "-B", str(RUN / "six_source" / "serve.py"), "--host", "0.0.0.0", "--port", port,
               "--read-only", "--no-verify", "--local", str(RUN / "six_source" / "local")]
    for host in hosts:
        command += ["--allowed-host", host.strip()]
    log(f"Starting read-only server on port {port} for: {', '.join(hosts) or 'localhost only'}")
    raise SystemExit(subprocess.call(command, cwd=RUN / "six_source"))


if __name__ == "__main__":
    main()
