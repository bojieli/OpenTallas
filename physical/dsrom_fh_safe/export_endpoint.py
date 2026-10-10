#!/usr/bin/env python3
"""Export an accepted endpoint route under its current boundary and pinned tool."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/w18"))
from export_view import script
from corner_sta import extra_vts

IMAGE = "openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29"
NAME = "ot_hdc_v41_fh_ep_view"
POST = "physical/dsrom_fh_safe/export_boundary.sdc"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--orfs-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    orfs = args.orfs_dir.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = f"/work/{base.relative_to(orfs)}"
    record = {"schema": "opentallas.fh.current_boundary_export.v1",
              "name": NAME, "orfs_dir": str(orfs), "image": IMAGE,
              "post_sdc": POST, "route_files_sha256": {}}
    for suffix in ("odb", "spef", "sdc", "v"):
        path = base / f"6_final.{suffix}"
        record["route_files_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for corner in ("ss", "ff", "tt"):
        tcl = out / f"export_{corner}.tcl"
        tcl.write_text(script(corner, rel, NAME, [], POST, extra_vts(base / "6_final.odb")))
        command = ["docker", "run", "--rm", "-v", f"{orfs}:/work:ro",
                   "-v", f"{ROOT}:/src:ro", "-v", f"{out}:/out", IMAGE,
                   "bash", "-lc", "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "
                   f"/out/{tcl.name}"]
        result = subprocess.run(command, capture_output=True, text=True)
        log = result.stdout + result.stderr
        (out / f"export_{corner}.log").write_text(log)
        slack = re.search(r"OT_WS_MAX (\S+) OT_WS_MIN (\S+)", log)
        record[corner] = {"done": result.returncode == 0 and "OT_EXPORT_DONE" in log,
                          "exit_code": result.returncode,
                          "ws_max": slack.group(1) if slack else None,
                          "ws_min": slack.group(2) if slack else None}
    record["files"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in sorted(out.iterdir()) if path.suffix in (".lef", ".lib", ".tcl")}
    (out / "export.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    if not all(record[corner]["done"] for corner in ("ss", "ff", "tt")):
        raise SystemExit("Endpoint export failed; preserve logs and reject this view")


if __name__ == "__main__":
    main()
