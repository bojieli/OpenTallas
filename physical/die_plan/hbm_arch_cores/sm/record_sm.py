#!/usr/bin/env python3
"""ELEM-HBM/SM: verdict record of one routed half kit (run_kit_hbm.sh outputs) -> results/<module>.json
(a FAIL record is never overwritten; when results/<module>.json exists, the record goes to <module>.<kit_hash>.json).

    python3 record_sm.py KITDIR HOST:DIR [--bench BENCH.json] [--write]

PASS iff route DRC 0, pin audit PASS, sdc_lint PASS, TT setup WNS >= 0, FF hold WNS >= 0, face-flop CK spread <= 80 ps at
TT and FF (AGENTS.md c7ce2ed69a, owner 2026-10-24: TT setup + FF hold sign-off; SS is information only, never gates).  face_guard is recorded separately (not part of the verdict).
"""
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
kd = Path(sys.argv[1])
where = sys.argv[2]
fz = json.loads((kd / "freeze.json").read_text())
r = dict(schema="opentallas.elem_hbm.core_result.v1", module=fz["module"], view=fz["view"], kit_hash=fz["kit_hash"],
         run=where, src_commit=fz.get("src_commit"), src_spec=fz.get("src_spec"), flow=fz.get("flow"),
         orfs_overrides=fz.get("orfs_overrides"), period_ps=fz["period_ps"], unc_setup_ps=60, unc_hold_ps=25,
         plan=fz["plan"], plan_sha256=fz["plan_sha256"], pins_sha256=fz["pins_sha256"], pins=fz["pins"])
txt = lambda p: Path(p).read_text(errors="replace") if Path(p).is_file() else ""
sl = txt(kd / "sdc_lint.log")
r["sdc_lint"] = "PASS" if "SDC_LINT PASS" in sl else ("FAIL" if sl else "NOT RUN")
fg = kd / "face_guard.json"
if fg.is_file():
    F = json.loads(fg.read_text())
    r["face_guard"] = dict(verdict=F["verdict"], checked=F.get("checked"), ok=F.get("ok"),
                           fails={k: len(v) for k, v in F["fails"].items()},
                           examples={k: v[:4] for k, v in F["fails"].items()})
else:
    r["face_guard"] = dict(verdict="NOT RUN")
logs = sorted(glob.glob(str(kd / "run/logs/asap7/*/base/5_2_route.log")))
drc = None
if logs:
    m = re.findall(r"(?:Total number of violations|Number of violations) = (\d+)", txt(logs[-1]))
    drc = int(m[-1]) if m else None
r["route_drc"] = drc
pa = kd / "pin_audit.json"
r["pin_audit"] = json.loads(pa.read_text())["verdict"] if pa.is_file() else "NOT RUN"
sta = {}
for c in ("ss", "ff", "tt"):
    p = kd / "views" / f"sta_{c}.json"
    if p.is_file():
        sta[c] = json.loads(p.read_text())
r["sta"] = sta
rep = glob.glob(str(kd / "run/reports/asap7/*/base/synth_stat.txt"))
if rep:
    m = re.findall(r"Chip area for (?:top )?module.*?:\s*([\d.]+)", txt(rep[0]))
    r["synth_area_um2"] = float(m[-1]) if m else None
fin = glob.glob(str(kd / "run/reports/asap7/*/base/6_finish.rpt"))
if fin:
    m = re.search(r"Design area ([\d.]+) um\^2 ([\d.]+)% utilization", txt(fin[0]))
    if m:
        r["design_area_um2"], r["util_pct"] = float(m.group(1)), float(m.group(2))
why = []
if r["sdc_lint"] != "PASS": why.append(f"sdc_lint {r['sdc_lint']}")
if drc != 0: why.append(f"route DRC {drc}")
if r["pin_audit"] != "PASS": why.append(f"pin audit {r['pin_audit']}")
if "tt" not in sta or sta["tt"]["setup_ws_ps"] < 0: why.append(f"TT setup WNS {sta.get('tt', {}).get('setup_ws_ps')}")
if "ff" not in sta or sta["ff"]["hold_ws_ps"] < 0: why.append(f"FF hold WNS {sta.get('ff', {}).get('hold_ws_ps')}")
for c in ("tt", "ff"):
    sp = sta.get(c, {}).get("ck_spread_ps")
    if sp is None or sp < 0 or sp > 80: why.append(f"{c.upper()} face-flop spread {sp}")
r["verdict"] = "PASS" if not why else "FAIL"
r["signoff_rule"] = "TT setup + FF hold + face-flop spread <= 80 ps at TT/FF, 833 ps, 60/25 ps; SS info only (AGENTS.md c7ce2ed69a)"
r["flow_corner"] = fz.get("corner")
r["fail_reasons"] = why
if "--bench" in sys.argv:
    r["exactness_bench"] = json.loads(Path(sys.argv[sys.argv.index("--bench") + 1]).read_text())
print(json.dumps({k: r[k] for k in ("module", "kit_hash", "verdict", "fail_reasons", "route_drc", "pin_audit", "sdc_lint")}))
print(json.dumps({c: {k: v for k, v in s.items() if k in ("setup_ws_ps", "setup_tns_ps", "hold_ws_ps", "ck_spread_ps", "face_flops")} for c, s in sta.items()}))
if "--write" in sys.argv:
    out = HERE.parent / "results"
    out.mkdir(exist_ok=True)
    p = out / f"{r['module']}.json"
    if p.is_file():
        p = out / f"{r['module']}.{r['kit_hash']}.json"
        if p.is_file() and json.loads(p.read_text()).get("verdict") == "FAIL":
            raise SystemExit(f"{p} is a FAIL record: never overwritten")
    p.write_text(json.dumps(r, indent=1) + "\n")
    print("wrote", p)
