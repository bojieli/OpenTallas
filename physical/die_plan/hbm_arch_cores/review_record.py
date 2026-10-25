#!/usr/bin/env python3
"""ELEM-HBM: write one GEOM-REVIEW-format record for a core kit review (owner order 2026-10-24 08:05).
    review_record.py KITDIR STAGE VERDICT "reasons" "fixes" [--pics p1,p2]  -> results/geom_review/<module>__<kitdir>__<hash12>.json
STAGE plan (pre-place: pins/outline/context) | placed (post-place: fill, macros, density, face flops).  A FAIL is never
overwritten (the file name carries the stage; an existing FAIL record for the same kit+stage is kept, exit 3)."""
import datetime
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def main(kd, stage, verdict, reasons, fixes, pics=""):
    kd = Path(kd)
    fz = json.load(open(kd / "freeze.json"))
    assert verdict in ("PASS", "PASS-COND", "FAIL"), verdict
    h = fz["kit_hash"]
    out = REPO / "results" / "geom_review" / f"{fz['module']}__{kd.name}_{stage}__{h[:12]}.json"
    if out.is_file() and json.load(open(out)).get("verdict") == "FAIL":
        print("KEEP FAIL", out)
        sys.exit(3)
    rec = dict(element=fz["module"], view=fz["view"], kit=f"physical/die_plan/hbm_arch_cores (kit {kd.name}, B2r2 pins "
               f"{fz['pins_sha256'][:12]}, plan {fz['plan_sha256'][:12]})", stage=stage, verdict=verdict, hash=h,
               reasons=reasons, fixes=fixes, pictures=[p for p in pics.split(",") if p], reviewer=__import__("os").environ.get("OT_REVIEWER", "ELEM-HBM (author review)"),
               at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
               rule="OWNER 2026-10-24 08:05 review before you route (BRIEFING)")
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    pics = ""
    if "--pics" in a:
        i = a.index("--pics"); pics = a[i + 1]; del a[i:i + 2]
    main(*a, pics=pics)
