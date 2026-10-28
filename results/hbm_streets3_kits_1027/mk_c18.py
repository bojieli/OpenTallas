#!/usr/bin/env python3
"""HBM-STREETS-3 KIT: trial core kits from the C18 plan (mk_kits.py of HBM-KITS-1 / R7, unchanged method).
  mk_c18.py PLANDIR VIEWS SLICEDIR KITDIR WT mod1,mod2,...
Slice = plan clock entry (identical for every instance, else refused ENTRY_NOT_UNIQUE), TT 250 / FF 202.5 +-20,
master_plan_sha256 TRIAL-no-frozen-master-plan (HBM plan not frozen).  Kit = gen_core_kit_hbm.py --trial --tag _c18.
Views with several pin tables (MULTI_TABLE) get one kit per table (tag _c18_<sha6>)."""
import json, sys, subprocess, os
from pathlib import Path
plan, views, sdir, kdir, wt = [os.path.abspath(x) for x in sys.argv[1:6]]
mods = sys.argv[6].split(",")
VL = json.load(open(views))["view_list"]
CE = json.load(open(f"{plan}/clock_entries.json"))
Path(sdir).mkdir(parents=True, exist_ok=True); Path(kdir).mkdir(parents=True, exist_ok=True)
res = {}
for m in mods:
    vs = [v for v in VL if v["module"] == m]
    if not vs:
        res[m] = dict(rc=None, cls="NO_VIEW_ROW", msg="module not in views table"); continue
    ents = [e for part in CE.values() if isinstance(part, dict) for e in part.values()
            if isinstance(e, dict) and e.get("module") == m]
    keys = {(tuple(e["xy_um"]), tuple(e["island_um"]), e["port"], tuple(e.get("merged_clock_ports") or [])) for e in ents}
    if len(keys) != 1:
        res[m] = dict(rc=None, cls="ENTRY_NOT_UNIQUE", msg=f"{len(ents)} entries {len(keys)} forms"); continue
    xy, isl, port, merged = next(iter(keys))
    out = []
    for v in vs:
        W, H = v["outline_um"]
        sl = {"schema": "opentallas.master_plan_slice.v1", "die": "hbm", "kind": "core", "type": m, "module": m,
              "instances": [], "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False,
              "outline_um": [W, H], "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20,
              "early_taps": False}, "keepouts": [], "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [],
              "gates": {}, "core_clock_port": port or (merged[0] if merged else "clk"),
              "islands": [{"name": "ck_entry", "rect_um": list(isl), "centre_um": list(xy), "use": "clock_driver",
                           "via_stack": ["M9", "M5"], "clock_pin": {"layer": "M5", "xy_um": list(xy)}}],
              "note": f"HBM-STREETS-3 trial slice: C18 clock_entries.json ({len(ents)} inst identical); merged ports {list(merged)}"}
        json.dump(sl, open(f"{sdir}/{m}.json", "w"), indent=1)
        tag = "_c18" if len(vs) == 1 else f"_c18_{v['pins_sha256'][:6]}"
        log = f"{kdir}/gen_{m}{tag}.log"
        cmd = ["python3", f"{wt}/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py", "--views", views, "--view", v["view"],
               "--out", kdir, "--master-slice", sdir, "--trial", "--tag", tag]
        r = subprocess.run(cmd, cwd=f"{wt}/physical/die_plan/hbm_arch_cores", stdout=open(log, "w"), stderr=subprocess.STDOUT)
        lines = open(log).read().strip().splitlines()
        tail = lines[-1] if lines else ""
        cls = "OK" if r.returncode == 0 else next((c for c in ("NO_RECIPE", "PORT_MISMATCH", "MAP_AMBIGUOUS", "MACRO_PLACEMENT",
                                                               "off the plan lattice", "Traceback") if c in tail or c in "".join(lines[-5:])), "GEN_FAIL")
        kit = None
        if r.returncode == 0:
            try:
                kit = json.loads(tail).get("kit")
            except ValueError:
                pass
        out.append(dict(view=v["view"], rc=r.returncode, cls=cls, kit=kit, entry=list(xy), port=port, merged=list(merged),
                        log=log, msg=tail[:400]))
    res[m] = out
    print(m, "|", json.dumps(out)[:300], flush=True)
json.dump(res, open(f"{kdir}/mk_c18_result{os.environ.get("MKTAG","")}.json", "w"), indent=1)
