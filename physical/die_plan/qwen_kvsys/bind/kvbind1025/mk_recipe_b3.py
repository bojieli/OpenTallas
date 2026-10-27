#!/usr/bin/env python3
"""PATH-KV-BIND 10-25: KV strict-bind recipe b3 = TOK-SCHED b2 (kvtok1025/recipe_b2.json) made repo-relative + the
TYPE_SPLIT fixes of this lane:
  * every input is a path inside this repo at the bind commit (base = repo root; ASAP7 cell models = the committed ORFS
    copies under results/arch/s81_hb1_cell_semantics_1019/official, md5-identical to the codex-kv45 scratch copies; the
    1024-head + 4-ASTK composition spec is committed gzipped next to this file, sha256 of the JSON in STATUS.txt);
  * internal_stations_types = EVERY plan type with planned OUT-bus internal stations (P class: a receiver pad that
    differs per instance by exactly the source's planned forward stations is realised at the source, 0 added cycles);
  * prefer rtl/qwen_sys/kv_plan_leaves_1025/qkd_astk_zn_head_p.sv (ASTK5 zn0 read-select pin-landing +1 edge, so the
    bound native source -- and the compiler -- carries it);
  * inner_uniform = the PC family (I class: per-instance as-built slg<->kvpc_k relay depth -> type max, every added
    stage recorded as an INNER group for pricing).
usage: mk_recipe_b3.py PLAN RECIPE_B2 OUT_RECIPE"""
import json
import sys
from pathlib import Path

plan_p, b2_p, out_p = sys.argv[1:]
plan = json.loads(Path(plan_p).read_text())
r = json.loads(Path(b2_p).read_text())
OLD = "/srv/opentallas-scratch2/claude/tok-sched/kvbind/tree/"
CELLS = "/srv/opentallas-scratch2/claude/codex-kv45/asap7_cells/"
r["base"] = "../../../../.."
r["netlist"] = [x.replace(OLD, "") for x in r["netlist"]]
r["files"] = [x.replace(CELLS, "results/arch/s81_hb1_cell_semantics_1019/official/") for x in r["files"]]
r["map_file"] = "../asbuilt_map_binder2.json"
r["compose"] = "physical/die_plan/qwen_kvsys/bind/kvbind1025/composition_heads_astk_1clk.json.gz"   # head_clk_merge.py output
zn = "rtl/qwen_sys/kv_plan_leaves_1025/qkd_astk_zn_head_p.sv"
r["prefer"] = [zn] + [x for x in r.get("prefer", []) if not x.endswith("/qkd_astk_zn_head_p.sv")]
T = plan["partition_types"]
sel = []
for tn, t in T.items():
    bs = {b["name"]: b for b in t.get("buses", [])}
    if any(e.get("conn", "").startswith("bus:") and bs.get(e["conn"][4:], {}).get("dir") == "out"
           for e in t.get("internal_stations", [])):
        sel.append(tn)
# the hroot->ectl cfg DAISY o_kvs_hroot_Q_o_cN (kv3_hg*) is a pass-through with no face register in the bound module
# (kit_istations: "no u_bout_o_kvs_hroot_Q_o_cN face register line to feed"): it keeps receiver padding (priced as
# before); it is the S-class kv3_hg_v1 split (per-position slice widths), fixed by the ectl cfg ID-strap proposal.
r["internal_stations_skip_buses"] = ["o_kvs_hroot_Q_o_cN"]
r["internal_stations_types"] = sorted(set(sel) | {"kv3_sys_c"})
r["plan_cells"] = "physical/die_plan/qwen_kvsys/bind/kvbind1025/plan_cells_b3.json"   # explicit_split.py --plan-cells
r["inner_uniform"] = [t for t in ("kv3_pc", "kv3_pc_v1", "kv3_pc_v3") if t in T]
r["note"] = r["note"] + " | PATH-KV-BIND b3 10-25: repo-relative; source stations on all OUT-station types; ASTK5 zn0 +1; PC inner_uniform; dead pv row-0 vo lanes removed from the plan"
def walk(x):
    if isinstance(x, dict):
        for v in x.values(): walk(v)
    elif isinstance(x, list):
        for v in x: walk(v)
    elif isinstance(x, str) and x.startswith("/srv"):
        raise SystemExit(f"absolute path left in recipe: {x}")
walk(r)
Path(out_p).write_text(json.dumps(r, indent=1) + "\n")
print(len(r["internal_stations_types"]), r["inner_uniform"])
