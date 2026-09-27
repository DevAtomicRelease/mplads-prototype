"""Hosted demo entry point (Render, Hugging Face Space or any container).

1. Get the demo bundle made by deploy/pack_release.py, from one of:
     MPLADS_BUNDLE_PATH    a file already inside the container, or
     mplads-demo-bundle.tar.gz next to this script (uploaded into a Space), or
     MPLADS_BUNDLE_GITHUB  "owner/repo@tag": a release asset in a (private) GitHub
                           repo, read with GITHUB_TOKEN, or
     MPLADS_BUNDLE_REPO    a (private) Hugging Face dataset repo, read with HF_TOKEN, or
     MPLADS_BUNDLE_URL     any direct HTTPS link.
2. If MPLADS_BUNDLE_SHA256 is set, refuse a bundle whose checksum differs.
3. Unpack it safely and start the server in read-only mode on 0.0.0.0:$PORT.
   The server itself re-checks every sealed release file before serving.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.error
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
    target = Path(os.environ.get("TMPDIR", "/tmp")) / BUNDLE_NAME
    github = os.environ.get("MPLADS_BUNDLE_GITHUB")
    if github:
        log(f"Downloading data bundle from GitHub release {github}…")
        with github_asset(github, os.environ.get("GITHUB_TOKEN", "")) as response, target.open("wb") as out:
            shutil.copyfileobj(response, out, 1024 * 1024)
        return target
    repo = os.environ.get("MPLADS_BUNDLE_REPO")
    url = os.environ.get("MPLADS_BUNDLE_URL") or (f"https://huggingface.co/datasets/{repo}/resolve/main/{BUNDLE_NAME}" if repo else "")
    if not url:
        sys.exit("Set MPLADS_BUNDLE_GITHUB, MPLADS_BUNDLE_REPO, MPLADS_BUNDLE_URL or MPLADS_BUNDLE_PATH.")
    request = urllib.request.Request(url)
    token = os.environ.get("HF_TOKEN")
    if token and "huggingface.co" in url:
        request.add_header("Authorization", f"Bearer {token}")
    log(f"Downloading data bundle ({'private repo' if token else 'public link'})…")
    with urllib.request.urlopen(request, timeout=600) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out, 1024 * 1024)
    return target


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def github_asset(spec: str, token: str):
    """Open the bundle asset of a GitHub release ("owner/repo@tag", or latest release).

    The asset URL redirects to pre-signed storage; the token is sent only to
    api.github.com and never forwarded to the storage host.
    """
    repo, _, tag = spec.partition("@")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "mplads-demo"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    api = f"https://api.github.com/repos/{repo}/releases/" + (f"tags/{tag}" if tag else "latest")
    try:
        with urllib.request.urlopen(urllib.request.Request(api, headers=headers), timeout=60) as response:
            release = json.load(response)
    except urllib.error.HTTPError as exc:
        sys.exit(f"Cannot read GitHub release {spec} (HTTP {exc.code}). Check the tag and that GITHUB_TOKEN can read this repository.")
    asset = next((a for a in release.get("assets", []) if a.get("name") == BUNDLE_NAME), None)
    if not asset:
        sys.exit(f"Release {spec} has no asset named {BUNDLE_NAME}.")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        return opener.open(urllib.request.Request(asset["url"], headers={**headers, "Accept": "application/octet-stream"}), timeout=600)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
            return urllib.request.urlopen(urllib.request.Request(exc.headers["Location"], headers={"User-Agent": "mplads-demo"}), timeout=600)
        raise


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
    for name in ("SPACE_HOST", "RENDER_EXTERNAL_HOSTNAME"):  # set automatically by Hugging Face / Render
        if os.environ.get(name):
            hosts.append(os.environ[name])
    if not hosts:
        log("Warning: no public hostname configured (SPACE_HOST / RENDER_EXTERNAL_HOSTNAME / MPLADS_ALLOWED_HOSTS); only localhost requests will be accepted.")
    command = [sys.executable, "-B", str(RUN / "six_source" / "serve.py"), "--host", "0.0.0.0", "--port", port,
               "--read-only", "--no-verify", "--local", str(RUN / "six_source" / "local")]
    for host in hosts:
        command += ["--allowed-host", host.strip()]
    log(f"Starting read-only server on port {port} for: {', '.join(hosts) or 'localhost only'}")
    raise SystemExit(subprocess.call(command, cwd=RUN / "six_source"))


if __name__ == "__main__":
    main()
