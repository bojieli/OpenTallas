#!/usr/bin/env python3
"""DIE-S81-85 svc provider form A step 3 (11-09): re-site the svc_lo ft station bits that event v2 put inside the new
hard boxes (G0 geometry "actual-bit station cells/sites intersect physical macros": svc_lo_dsdv_svc_rs__t1 ft0 / ft1,
svc_lo_dsdv_svc_rs__t7 ft0 / ft4, svc_lo_dsdv_svc_rs_w__t1 ft0).

Runs tools/die_plan/ft_nudge.py (least change: only the bit sites inside a box move, to the nearest free legal row
site; station counts, windows, pins, outlines, boxes unchanged) on the event v2 plan with --no-snap, then takes the
ft_slots of the svc_lo types ONLY (ft_nudge also re-sites pre-existing hits in other owners' types; those are not part
of this event and stay as in the base).

    svc_prov_step3_ft_1109.py PLAN_V2.json OUT_PLAN.json LEDGER.json
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SVC_LO = ("svc_lo_dsdv_svc_rs__t1", "svc_lo_dsdv_svc_rs__t7", "svc_lo_dsdv_svc_rs_w__t1")


def main():
    plan, out, ledger = sys.argv[1:4]
    with tempfile.TemporaryDirectory() as td:
        nud, led = Path(td) / "plan_ft.json", Path(td) / "ledger.json"
        subprocess.run([sys.executable, str(ROOT / "tools/die_plan/ft_nudge.py"), plan, str(nud), str(led), "--no-snap"],
                       check=True, cwd=ROOT)
        a, b = json.loads(Path(plan).read_text()), json.loads(nud.read_text())
        rows = [r for r in json.loads(led.read_text()) if r.get("type") in SVC_LO]
    for tn in SVC_LO:
        a["partition_types"][tn]["ft_slots"] = b["partition_types"][tn]["ft_slots"]
        a["partition_types"][tn]["note"] = (a["partition_types"][tn].get("note", "") +
                                            " | DIE-S81-85 step 3 11-09: ft bits inside the new boxes re-sited (ft_nudge, least change)")
    Path(out).write_text(json.dumps(a) + "\n")
    Path(ledger).write_text(json.dumps(rows, indent=1) + "\n")
    for r in rows:
        print(f"{r['type']} {r['slot']}: {r['bits_moved']} bits moved, max {r['max_move_um']} um")


if __name__ == "__main__":
    main()
