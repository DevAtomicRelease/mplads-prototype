"""The single allow-listed maintenance entry point used by frontend controls."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from releases import LOCAL, HERE, activate, atomic_json, integrity_reason, maintenance_lock, new_directory, release_version, resolve_active, seal

def run_tests(active, local):
    env={**os.environ,"MPLADS_DATA_DIR":str(active),"PYTHONDONTWRITEBYTECODE":"1"}
    result=subprocess.run([sys.executable,str(HERE/"tests.py")],env=env,cwd=HERE)
    atomic_json(local/"test_result.json",{"passed":result.returncode==0,"release_version":release_version(active),"checked":datetime.now(timezone.utc).isoformat()})
    if result.returncode:raise ValueError("Regression tests failed; see job log")

def main(action,local=LOCAL):
    local=Path(local).resolve()
    with maintenance_lock(local):
        if action=="prepare_release":
            from prepare_release import prepare
            return prepare(local=local)
        active=resolve_active(local)
        if action=="tests":return run_tests(active,local)
        if action=="reproduce":
            from reproduce import main as reproduce
            from common import ROOT
            return reproduce(active,new_directory(local),ROOT/"Dataset",local/"reproducibility.json")
        reason=integrity_reason(active)
        if reason:raise ValueError(reason+". Prepare a complete release instead.")
        # Ancillary refreshes are staged too; never mutate a release under readers.
        rel=new_directory(local)
        for source in active.iterdir():
            if source.is_file() and source.name not in {"release_manifest.json","active_release.json","reviews.sqlite3","reproducibility.json","test_result.json"} and not source.name.startswith("."):
                shutil.copy2(source,rel/source.name)
        if action=="validate":
            from validate import build
        elif action=="workbook":
            from workbook import build
        else:raise ValueError("Unknown maintenance action")
        build(rel)
        seal(rel)
        activate(rel,local)
        print("New verified analytical release activated; previous releases and reviews retained.",flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["tests","validate","workbook","reproduce","prepare_release"])
    parser.add_argument("--local",type=Path,default=LOCAL)
    args=parser.parse_args()
    main(args.action,args.local)
