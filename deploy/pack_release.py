"""Pack the active release into a read-only demo bundle for hosting.

The bundle holds everything the hosted server needs, byte for byte:
  six_source/*.py                     analysis + server code (exact sealed bytes)
  six_source/local/active_release.json
  six_source/releases/<id>/...        sealed release files (minus large CSV downloads)
  mplads-prototype/dist/...           the built web interface

Nothing else is included: no raw Dataset files, no review notes, no job results.
The release is verified before packing, and the finished archive is re-read and
checked against the release manifest before it is reported as ready.

Usage (from the repository root):
    .venv/Scripts/python.exe -B deploy/pack_release.py
    .venv/Scripts/python.exe -B deploy/pack_release.py --keep-large   # include every CSV
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIX = ROOT / "six_source"
DIST = ROOT / "mplads-prototype" / "dist"
APP_SOURCES = ROOT / "mplads-prototype"
sys.path.insert(0, str(SIX))
from releases import BUNDLE_NOTE, digest, integrity_reason, resolve_active  # noqa: E402

# Large record-level downloads the hosted demo does not need; the app shows
# "not generated yet" for these links. All analysis runs on the SQLite database.
LARGE = ("Work_Features.csv", "Payment_Features.csv")
# Local-only state that must never leave this computer.
NEVER = {"reviews.sqlite3", "test_result.json", "reproducibility.json", ".maintenance.lock"}


def newest(paths):
    return max((p.stat().st_mtime for p in paths if p.is_file()), default=0)


def add_bytes(tar, name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = int(datetime.now(timezone.utc).timestamp())
    info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))


def pack(out: Path, keep_large: bool = False, local: Path = SIX / "local") -> dict:
    active = resolve_active(local)
    if active == local.resolve():
        raise SystemExit("No sealed release is active. Run six_source/prepare_release.py first.")
    reason = integrity_reason(active)
    if reason:
        raise SystemExit(f"Active release failed verification, not packing: {reason}")
    if not (DIST / "index.html").is_file():
        raise SystemExit("mplads-prototype/dist is missing. Run: cd mplads-prototype && npm run build")
    src = [p for p in (APP_SOURCES / "app").rglob("*") if p.is_file()] + [p for p in (APP_SOURCES / "components").rglob("*") if p.is_file()] + [p for p in (APP_SOURCES / "lib").rglob("*") if p.is_file()]
    if newest(src) > (DIST / "index.html").stat().st_mtime:
        raise SystemExit("The built interface is older than its source. Run: cd mplads-prototype && npm run build")

    manifest = json.loads((active / "release_manifest.json").read_text(encoding="utf-8"))
    omitted = [] if keep_large else [n for n in LARGE if n in manifest["artifacts"]]
    rel = active.relative_to(SIX)  # releases/<id>
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".partial")
    with tarfile.open(tmp, "w:gz", compresslevel=6) as tar:
        for path in sorted(SIX.glob("*.py")):
            tar.add(path, arcname=f"six_source/{path.name}", recursive=False)
        tar.add(SIX / "requirements.txt", arcname="six_source/requirements.txt")
        tar.add(local / "active_release.json", arcname="six_source/local/active_release.json")
        for path in sorted(active.iterdir()):
            if path.is_file() and path.name not in omitted and path.name not in NEVER:
                tar.add(path, arcname=f"six_source/{rel.as_posix()}/{path.name}", recursive=False)
        note = {"release": active.name, "packed": datetime.now(timezone.utc).isoformat(), "omitted": omitted,
                "purpose": "Read-only hosted demo copy. Not an official record; review signals, not findings of fraud."}
        add_bytes(tar, f"six_source/{rel.as_posix()}/{BUNDLE_NOTE}", json.dumps(note, indent=2).encode("utf-8"))
        for path in sorted(DIST.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=f"mplads-prototype/dist/{path.relative_to(DIST).as_posix()}", recursive=False)
    verify(tmp, manifest, rel, omitted)
    tmp.replace(out)
    sha = digest(out)
    (out.parent / (out.name + ".sha256")).write_text(f"{sha}  {out.name}\n", encoding="utf-8")
    return {"bundle": str(out), "bytes": out.stat().st_size, "sha256": sha, "release": active.name, "omitted": omitted}


def verify(archive: Path, manifest: dict, rel: Path, omitted: list) -> None:
    """Re-read the archive: sealed files and code must match the manifest exactly."""
    prefix = f"six_source/{rel.as_posix()}/"
    seen = {}
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            if member.name.startswith("/") or ".." in Path(member.name).parts:
                raise SystemExit(f"Unsafe path in bundle: {member.name}")
            if Path(member.name).name in NEVER:
                raise SystemExit(f"Local-only file leaked into bundle: {member.name}")
            if member.name.startswith(prefix) or member.name.startswith("six_source/") and member.name.count("/") == 1:
                seen[member.name] = hashlib.sha256(tar.extractfile(member).read()).hexdigest()
    for name, expected in manifest["artifacts"].items():
        got = seen.get(prefix + name)
        if got is None and name not in omitted:
            raise SystemExit(f"Bundle is missing sealed file: {name}")
        if got is not None and got != expected:
            raise SystemExit(f"Bundle file differs from the sealed release: {name}")
    for name, expected in manifest["code"].items():
        if seen.get("six_source/" + name) != expected:
            raise SystemExit(f"Bundle code differs from the sealed release: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "deploy" / "build" / "mplads-demo-bundle.tar.gz")
    parser.add_argument("--keep-large", action="store_true", help="Also include the large Work/Payment feature CSV downloads")
    args = parser.parse_args()
    result = pack(args.out, args.keep_large)
    print(json.dumps({**result, "megabytes": round(result["bytes"] / 1e6, 1)}, indent=2))
