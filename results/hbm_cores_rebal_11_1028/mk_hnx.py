#!/usr/bin/env python3
"""HBM-CORES-REBAL-11: hnx_lane_x hard-child kit from the C24 plan view (DIE-HBM-10 c24_side.json core_views,
pins file cores/hnx_lane_x__285.12x302.4__c24.json).
  * views row: the C24 view is a side-data view (the child is not a plan hard_core yet), so it is appended to a copy of
    the views table with the same fields views_b2r2.py writes (pins_sha256 of the plan pins file).
  * slice: mk_c20.py form (12.2a1 pushdown: clock_entry island + 12.8b tree leaves from master_plan.restructure_islands),
    clock entry = the plan's centre M5 pin `clk` (142.584, 151.2) and its 8.64-um 4.32-lattice island.
  * recipe: hnx_rp3lp3h_n recipe (same defines / source commit) with the selfcontained leaf replaced by the REBAL-5
    lane-cut file (verbatim text transform, yosys equiv 13164/13164 PROVEN), top hnx_lane_x, no SRAM macros.
  * --face-shell off: every hnx_lane_x input lands on an XREL station flop and the 50-bit output g is the registered
    gather (REBAL-5 cut contract); a face shell would add a cycle per crossing and break the proven cut equivalence.
  mk_hnx.py WT PLANDIR(c24 copy) VIEWS_IN VIEWS_OUT SLICEDIR KITDIR TAG SRC_SHA
"""
import copy, hashlib, json, os, sys
from pathlib import Path
WT, PD, VIN, VOUT, SD, KD, TAG, SRC = sys.argv[1:9]
sys.path.insert(0, f"{WT}/tools/die_plan")
sys.path.insert(0, f"{WT}/physical/die_plan/hbm_arch_cores")
import master_plan as MP  # noqa: E402

M = "hnx_lane_x"
side = json.load(open(f"{PD}/c24_side.json"))["core_views"]
cv = side["hnx_rp3lp3h_n"]["child"]
assert cv["module"] == M and side["hnx_rp3lp3h_s"]["child"]["pins_file"] == cv["pins_file"]
W, H = cv["outline_um"]
pf = cv["pins_file"]
pins = json.load(open(f"{PD}/{pf}"))
assert len(pins) == cv["pins"] == 1670, len(pins)
sha = hashlib.sha256(open(f"{PD}/{pf}", "rb").read()).hexdigest()
inst = [f"{h}.{c['inst']}" for h in ("hnx_rp3lp3h_n", "hnx_rp3lp3h_s") for c in side[h]["children"]]
V = json.load(open(VIN))
assert not any(v["module"] == M for v in V["view_list"])
row = dict(view=f"{M}@{sha[:12]}", module=M, outline_um=[W, H], pins_file=pf, pins_sha256=sha, pins=len(pins),
           family="SM", instances=inst, placed=len(inst), tables_for_module=1, canonical_type=None, recipe_keys=[],
           blockers=[], note="HBM-CORES-REBAL-11: C24 side-data hard-child view (c24_side.json core_views.*.child)")
V["view_list"].append(row)
json.dump(V, open(VOUT, "w"), indent=1)

# slice (mk_c20.py core form) at the plan centre clock pin
ck = [p for p in pins if p["name"] == "clk"]
assert len(ck) == 1 and ck[0]["layer"] == "M5", ck
xy = [ck[0]["x"], ck[0]["y"]]
lat = 4.32
x0 = int(xy[0] // lat) * lat; y0 = int(xy[1] // lat) * lat
isl = [MP.r3(x0 - lat if xy[0] - x0 < 2.16 else x0), MP.r3(y0 - lat if xy[1] - y0 < 2.16 else y0)]
isl = [isl[0], isl[1], MP.r3(isl[0] + 2 * lat), MP.r3(isl[1] + 2 * lat)]
assert isl[0] + 2.16 <= xy[0] <= isl[2] - 2.16 and isl[1] + 2.16 <= xy[1] <= isl[3] - 2.16, (isl, xy)
reach = 200.0
far = max(abs(cx - xy[0]) + abs(cy - xy[1]) for cx in (0, W) for cy in (0, H))
sub = MP.restructure_islands(W, H, reach) if far > reach else {}
leaves = sub.get("islands", [])
PDX = dict(pin_dx_um=1.08)
pd = [MP.pushdown_island(0, list(isl), list(xy), "clock_entry",
                         (far if not leaves else max(abs(q["centre_um"][0] - xy[0]) + abs(q["centre_um"][1] - xy[1])
                                                     for q in leaves)), max(1, len(leaves)), **PDX)]
for i, q in enumerate(leaves):
    pd.append(MP.pushdown_island(i + 1, q["rect_um"], q["centre_um"], "tree_leaf", sub.get("leaf_reach_um", 0.0), 0, **PDX))
sl = {"schema": MP.SLICE_SCHEMA, "die": "hbm", "kind": "core", "type": M, "module": M, "instances": [],
      "master_plan_sha256": "TRIAL-no-frozen-master-plan", "frozen": False, "outline_um": [W, H],
      "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 20, "early_taps": False},
      "keepouts": [dict(name="clock_entry_island", rect_um=list(isl), kind="island", use=["placement"])],
      "bays": [], "entry_pins": [], "hard_cores": [], "corridors": [], "gates": {}, "core_clock_port": "clk",
      "islands": [{"name": "clock_entry", "rect_um": list(isl), "centre_um": list(xy), "use": "clock_driver+reset",
                   "via_stack": ["M9", "M5"], "clock_pin": {"layer": "M5", "xy_um": list(xy)},
                   "pg_rails": "die M8/M9 stripes on the 4.32 lattice"}]
                 + [{"name": f"tree_leaf{i}", "rect_um": q["rect_um"], "centre_um": q["centre_um"],
                     "use": "clock_driver+reset", "via_stack": ["M9", "M5"], "clock_pin": None,
                     "pg_rails": "die M8/M9 stripes on the 4.32 lattice"} for i, q in enumerate(leaves)],
      "pushdown": dict(rule="12.2a1: island drivers are core-netlist cells at these fixed coordinates, "
                            "identical for every instance; die connects only via the mp_isl* ft ports", islands=pd),
      "in_core_islands": dict(grid=sub.get("grid"), leaf_reach_um=sub.get("leaf_reach_um"),
                              farthest_corner_um=MP.r3(far), core_reach_um=reach,
                              source="tools/die_plan/master_plan.restructure_islands (12.8b grid)"),
      "note": "HBM-CORES-REBAL-11 mk_hnx slice (mk_c20 form): C24 centre clock pin clk; "
              f"12.2a1 pushdown {len(pd)} islands"}
Path(SD).mkdir(parents=True, exist_ok=True)
json.dump(sl, open(f"{SD}/{M}.json", "w"), indent=1)

import gen_core_kit_hbm as G  # noqa: E402
R = G.load_recipes()
rec = copy.deepcopy(R["hnx_rp3lp3h_n"])
LEAF = "physical/die_plan/hbm_arch_cores/rtl/hnx_rp4lp4_leaf_selfcontained.sv"
CUT = "results/hbm_cores_rebal_5_1028/hnx_rp4lp4_leaf_selfcontained_lanecut.sv"
assert rec["files"].count(LEAF) == 1
rec["files"] = [CUT if f == LEAF else f for f in rec["files"]]
rec["files"] = [f for f in rec["files"] if not f.endswith("_bb.v")]          # the child has no SRAM macro
fat = dict(rec.get("files_at", {})); fat.pop(LEAF, None); fat[CUT] = SRC
rec.update(top=M, macros=[], files_at=fat, src_spec=f"{CUT}@{SRC}",
           source=("HBM-CORES-REBAL-11: hnx_rp3lp3h_n recipe (defines, source commit) with the selfcontained leaf "
                   "replaced by the REBAL-5 per-lane cut (gen_lane_cut.py, verbatim text transform; yosys equiv "
                   "13164/13164 PROVEN); top hnx_lane_x; no SRAM macros"))
os.chdir(f"{WT}/physical/die_plan/hbm_arch_cores")
sys.argv = ["gen_core_kit_hbm.py", "--views", VOUT, "--view", row["view"], "--out", KD, "--master-slice", SD, "--trial",
            "--tag", TAG, "--recipe-key", M, "--face-shell", "off"]
G.main(recipe_overrides={M: rec})
