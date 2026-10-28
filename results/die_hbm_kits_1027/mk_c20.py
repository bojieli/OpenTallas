#!/usr/bin/env python3
"""DIE-HBM/KITS: core kits from the C20 (or C19) HBM plan WITH the 12.2a1 pushdown section.
  mk_c20.py PLANDIR VIEWS SLICEDIR KITDIR WT mod1,mod2,...   [--islands-only] [--tag _c20]
Same method as mk_c18.py (HBM-STREETS-3 KIT): slice = plan clock entry (identical for every instance, else refused
ENTRY_NOT_UNIQUE), TT 250 / FF 202.5 +-20, master_plan_sha256 TRIAL-no-frozen-master-plan, kit =
gen_core_kit_hbm.py --trial.  NEW: the core slice carries the 12.2a1 pushdown section exactly as
tools/die_plan/master_plan.py writes core slices: clock_entry island (pushdown_island role clock_entry) + one
tree_leaf pushdown island per leaf of master_plan.restructure_islands (12.8b grid; only when the entry->farthest
corner exceeds --core-reach-um, default 200 as master_plan).  Island rects come from the plan (entry island_um) and
master_plan.entry_island (leaves); nothing is re-sited here.
Also writes SLICEDIR/core_islands.json {module: {rule, frame: "core", instances, rects_um}} (schema
die_plan.schema.json clock.mesh.core_islands) for the plan event."""
import json, sys, subprocess, os, argparse, math
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("views"); ap.add_argument("sdir"); ap.add_argument("kdir"); ap.add_argument("wt")
ap.add_argument("mods"); ap.add_argument("--tag", default="_c20"); ap.add_argument("--islands-only", action="store_true")
ap.add_argument("--core-reach-um", type=float, default=200.0)
a = ap.parse_args()
plan, views, sdir, kdir, wt = [os.path.abspath(x) for x in (a.plan, a.views, a.sdir, a.kdir, a.wt)]
sys.path.insert(0, f"{wt}/tools/die_plan")
import master_plan as MP  # noqa: E402  (shared tool: pushdown_island, restructure_islands, entry_island)
mods = a.mods.split(",")
VL = json.load(open(views))["view_list"]
CE = json.load(open(f"{plan}/clock_entries.json"))
Path(sdir).mkdir(parents=True, exist_ok=True); Path(kdir).mkdir(parents=True, exist_ok=True)
cip = Path(sdir) / "core_islands.json"
core_islands = json.loads(cip.read_text()) if cip.is_file() else {}
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
        far = max(abs(cx - xy[0]) + abs(cy - xy[1]) for cx in (0, W) for cy in (0, H))
        sub = MP.restructure_islands(W, H, a.core_reach_um) if far > a.core_reach_um else {}
        leaves = sub.get("islands", [])
        # entry on the core edge (IP_DECLARED native pin, e.g. serdes y=0.019): the +-2.16 ft ports would leave the
        # outline -> island drivers/ports at the plan island rect centre (same plan island); clock pin unchanged
        fits = isl[0] <= xy[0] - 2.16 and xy[0] + 2.16 <= isl[2] and isl[1] <= xy[1] - 2.16 and xy[1] + 2.16 <= isl[3]
        pc = list(xy) if fits else [MP.r3((isl[0] + isl[2]) / 2), MP.r3((isl[1] + isl[3]) / 2)]
        pd = [MP.pushdown_island(0, list(isl), pc, "clock_entry",
                                 (far if not leaves else max(abs(q["centre_um"][0] - xy[0]) + abs(q["centre_um"][1] - xy[1])
                                                             for q in leaves)), max(1, len(leaves)))]
        for i, q in enumerate(leaves):
            pd.append(MP.pushdown_island(i + 1, q["rect_um"], q["centre_um"], "tree_leaf", sub.get("leaf_reach_um", 0.0), 0))
        sl = {"schema": MP.SLICE_SCHEMA, "die": "hbm", "kind": "core", "type": m, "module": m,
              "instances": [], "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False,
              "outline_um": [W, H], "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20,
              "early_taps": False},
              "keepouts": [dict(name="clock_entry_island", rect_um=list(isl), kind="island", use=["placement"])],
              "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [],
              "gates": {}, "core_clock_port": port or (merged[0] if merged else "clk"),
              "islands": [{"name": "clock_entry", "rect_um": list(isl), "centre_um": list(xy), "use": "clock_driver+reset",
                           "via_stack": ["M9", "M5"], "clock_pin": {"layer": "M5", "xy_um": list(xy)},
                           "pg_rails": "die M8/M9 stripes on the 4.32 lattice"}]
                         + [{"name": f"tree_leaf{i}", "rect_um": q["rect_um"], "centre_um": q["centre_um"],
                             "use": "clock_driver+reset", "via_stack": ["M9", "M5"], "clock_pin": None,
                             "pg_rails": "die M8/M9 stripes on the 4.32 lattice"} for i, q in enumerate(leaves)],
              "pushdown": dict(rule="12.2a1: island drivers are core-netlist cells at these fixed coordinates, "
                                    "identical for every instance; die connects only via the mp_isl* ft ports",
                               islands=pd),
              "in_core_islands": dict(grid=sub.get("grid"), leaf_reach_um=sub.get("leaf_reach_um"),
                                      farthest_corner_um=MP.r3(far), core_reach_um=a.core_reach_um,
                                      source="tools/die_plan/master_plan.restructure_islands (12.8b grid)"),
              "note": f"DIE-HBM/KITS mk_c20 slice: {os.path.basename(plan)} clock_entries.json ({len(ents)} inst identical); "
                      f"merged ports {list(merged)}; 12.2a1 pushdown {len(pd)} islands"}
        tag = a.tag if len(vs) == 1 else f"{a.tag}_{v['pins_sha256'][:6]}"
        core_islands[m] = dict(rule="12.2a1 pushdown in-core islands (clock entry + 12.8b tree leaves), core-local, "
                                    "identical for every instance (DIE-HBM/KITS mk_c20)", frame="core",
                               instances=max(1, sum(int(x.get("placed") or len(x.get("instances") or [])) for x in vs)), rects_um=[list(map(float, q["rect_um"])) for q in pd])
        json.dump(sl, open(f"{sdir}/{m}.json", "w"), indent=1)
        if a.islands_only:
            out.append(dict(view=v["view"], cls="SLICE_ONLY", islands=len(pd))); continue
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
                        islands=len(pd), log=log, msg=tail[:400]))
    res[m] = out
    print(m, "|", json.dumps(out)[:300], flush=True)
cip.write_text(json.dumps(dict(sorted(core_islands.items())), indent=1))
json.dump(res, open(f"{kdir}/mk_c20_result{os.environ.get('MKTAG', '')}.json", "w"), indent=1)
