"""Launcher readiness check: source hashes, release bytes, code and required outputs."""
from releases import LOCAL, REQUIRED, resolve_active, integrity_reason
from serve import stale_reason
import json

def check():
    try:
        active=resolve_active(LOCAL)
        for name in REQUIRED:
            if not (active/name).is_file():return f"Missing output: {name}"
        meta=json.loads((active/"audit.json").read_text(encoding="utf-8"))
        return stale_reason(meta) or integrity_reason(active)
    except (OSError,ValueError,KeyError):return "No readable verified release"

if __name__=="__main__":
    reason=check()
    print(reason or "Verified active release")
    raise SystemExit(1 if reason else 0)
