#!/usr/bin/env python3
"""Assemble the v9 spine SS/FF sign-off record from the route terminals (physical/dsrom_field_spine/phys.sh).
Usage: ssff.py OUT.json 'TAG=PATH_TO_terminal.json'...   (each terminal from terminal.py)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("screens", nargs="+")
    ap.add_argument("--source-commit", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    rows, missing = {}, []
    for s in a.screens:
        tag, path = s.split("=", 1)
        p = Path(path)
        if not p.exists():
            missing.append(tag)
            continue
        d = json.loads(p.read_text())
        rows[tag] = dict(path=path, sha256=sha(p), verdict=d["verdict"], SS_ps=d["SS_ps"], SS_pins=d["SS_pins"],
                         FF_ps=d["FF_ps"], FF_pins=d["FF_pins"], SI=d["SI"], drc=d["drc"], antenna=d["antenna"],
                         area_um2=d["area_um2"], replicas=d["replicas"])
    closed = {t: r["verdict"] for t, r in rows.items()}
    rec = dict(schema="opentallas.dsrom.field_spine.v9_ssff.v1", source_commit=a.source_commit, note=a.note,
               screens=rows, verdicts=closed, pending=missing,
               rtl_source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (
                   ROOT / "rtl/v41die/ot_v41_spine_pqc_w17w10.sv", ROOT / "rtl/hdc/v41x/ot_dsrom_aq12.sv",
                   ROOT / "physical/dsrom_field_spine/ot_v41_pqc_spine_screen.sv",
                   ROOT / "physical/dsrom_field_spine/phys.sh")})
    rec["all_pass"] = bool(rows) and not missing and all(v == "PASS" for v in closed.values())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdicts=closed, pending=missing, all_pass=rec["all_pass"])))
    return 0 if rec["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
