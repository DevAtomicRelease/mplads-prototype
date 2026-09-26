"""Immutable local releases. Activation replaces one pointer, never live data files."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
LOCAL = HERE / "local"
CODE_FILES = ("build.py", "common.py", "isolation.py", "validate.py", "patterns.py", "forecast.py", "workbook.py")
REQUIRED = ("audit.json", "artifact_hashes.json", "mplads.sqlite3", "Work_Features.csv", "ab_metrics.json", "AB_Report.md", "DATA_PATTERNS.md", "forecast.json", "MPLADS_Review.xlsx")

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if Path(name).exists(): Path(name).unlink()

def resolve_active(local=LOCAL):
    local = Path(local).resolve()
    pointer = local / "active_release.json"
    if not pointer.is_file(): return local
    p = json.loads(pointer.read_text(encoding="utf-8"))
    if "dir" not in p and "release" in p: return local  # legacy copy-based marker
    rel = (local.parent / p["dir"]).resolve()
    if not rel.is_relative_to((local.parent / "releases").resolve()): raise ValueError("Active release is outside releases directory")
    if not (rel / "release_manifest.json").is_file(): raise ValueError("Active release manifest missing")
    if digest(rel / "release_manifest.json") != p.get("manifest_sha256"): raise ValueError("Active release manifest changed")
    return rel

def release_version(directory, meta=None):
    directory = Path(directory)
    if (directory / "release_manifest.json").is_file(): return "release:" + digest(directory / "release_manifest.json")
    meta = meta or json.loads((directory / "audit.json").read_text(encoding="utf-8"))
    return meta["version"] + ":" + meta["source_fingerprint"] + ":" + meta.get("work_features_sha256", meta["as_of"])

def integrity_reason(directory, check_code=True):
    directory = Path(directory)
    try:
        meta = json.loads((directory / "audit.json").read_text(encoding="utf-8"))
        if not meta.get("all_checks_passed") or not all(meta.get("checks", {}).values()): return "Reconciliation failed"
        hashes = json.loads((directory / "artifact_hashes.json").read_text(encoding="utf-8"))
        manifest = directory / "release_manifest.json"
        codes = {n: meta.get(k) for n, k in (("build.py", "pipeline_sha256"), ("common.py", "common_sha256"), ("isolation.py", "isolation_sha256"))}
        if manifest.is_file():
            m = json.loads(manifest.read_text(encoding="utf-8")); hashes.update(m["artifacts"]); codes = m["code"]
        for name, expected in hashes.items():
            if Path(name).name != name or not (directory / name).is_file() or digest(directory / name) != expected: return f"Artifact missing or changed: {name}"
        if check_code:
            for name, expected in codes.items():
                if Path(name).name != name or not (HERE / name).is_file() or digest(HERE / name) != expected: return f"Analysis code changed or unrecorded: {name}"
        if not (directory / "mplads.sqlite3").is_file(): return "Analytical database missing"
    except (OSError, ValueError, KeyError, TypeError) as exc: return f"Unreadable release: {exc}"
    return ""

def seal(directory):
    directory = Path(directory).resolve()
    for name in REQUIRED:
        if not (directory / name).is_file(): raise ValueError(f"Incomplete release: {name} missing")
    reason = integrity_reason(directory)
    if reason: raise ValueError(reason)
    with closing(sqlite3.connect((directory / "mplads.sqlite3").as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok": raise ValueError("Database integrity check failed")
    files = {p.name: digest(p) for p in sorted(directory.iterdir()) if p.is_file() and p.name != "release_manifest.json"}
    atomic_json(directory / "release_manifest.json", {"schema": 1, "artifacts": files, "code": {name: digest(HERE / name) for name in CODE_FILES}})

def activate(directory, local=LOCAL, version=None):
    directory, local = Path(directory).resolve(), Path(local).resolve()
    if not directory.is_relative_to((local.parent / "releases").resolve()): raise ValueError("Only isolated releases can be activated")
    if not (directory / "release_manifest.json").is_file(): raise ValueError("Release must be sealed")
    reason = integrity_reason(directory)
    if reason: raise ValueError(reason)
    atomic_json(local / "active_release.json", {"dir": directory.relative_to(local.parent).as_posix(), "manifest_sha256": digest(directory / "release_manifest.json"), "activated": datetime.now(timezone.utc).isoformat()})

def new_directory(local=LOCAL):
    path = Path(local).resolve().parent / "releases" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
    path.mkdir(parents=True)
    return path

@contextmanager
def maintenance_lock(local=LOCAL):
    """Nonblocking OS lock; automatically released when its process exits."""
    Path(local).mkdir(parents=True, exist_ok=True)
    stream = (Path(local) / ".maintenance.lock").open("a+b")
    acquired = False
    try:
        stream.seek(0, 2)
        if stream.tell() == 0: stream.write(b"0"); stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc: raise ValueError("Another maintenance operation is running") from exc
        acquired = True
        yield
    finally:
        if acquired:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)
        stream.close()
