"""QK-CORES-11: kv3_pv_pair in-core clock tree (METHODOLOGY 12.8b, KV master clock slice KV-CORE-SLICE-1 core_tree,
re-sited SRAM-aware by tools/die_plan/core_islands.py because the slice [2,1] island (95.04,95.04) lies ON the W SRAM
stack of the static macro sites).  Shared core_infra pushdown: s1__clk centre entry -> 4 co-located branch buffers
in the entry island -> one point-to-point wire each -> 4 FIRM island nodes (k=4, W/E symmetric, equal-load) ->
CTS-open leaves (sinks named from the pass-1 placement census).  Installed at PRE_GLOBAL_PLACE (after face_flops.tcl)
so the nodes are fixed before placement.  No cycles, no RTL change.
usage: build_pv_tree.py REPO KIT CLK_DUMP.json ISLANDS.json [--mirror-y H]"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
repo, kd, dump, islp = Path(sys.argv[1]), Path(sys.argv[2]), json.load(open(sys.argv[3])), sys.argv[4]
sys.path.insert(0, str(repo / "tools/die_plan"))
import core_infra as CI, core_islands as CIS
W, H = 380.16, 190.08
isl = json.load(open(islp))["kv3_pv_pair"]["islands"]
mir = "--mirror-y" in sys.argv
def my(y): return round(H - y, 3) if mir else y
port = "s1__clk[0]"
entry = [190.488, 95.04]
ent_rect = [185.76, 90.72, 194.4, 99.36]
# 4 branch buffers in the entry island, one row below/above the M5 pin row, distinct x
br_xy = [[187.92, 92.88], [187.92, 97.2], [192.24, 92.88], [192.24, 97.2]]
centres = [[q["centre_um"][0], my(q["centre_um"][1])] for q in isl]
rects = [[q["rect_um"][0], my(q["rect_um"][3]) if mir else q["rect_um"][1], q["rect_um"][2], my(q["rect_um"][1]) if mir else q["rect_um"][3]] for q in isl]
# pair each branch with the island on its side (W branches x<190 -> W islands)
order = sorted(range(4), key=lambda i: (centres[i][0] > entry[0], centres[i][1]))
regs = [s for s in dump["sinks"] if not s["macro"]]
macs = [s for s in dump["sinks"] if s["macro"]]
P = np.array([[s["x"], s["y"]] for s in regs]); C = np.array(centres)
cost = np.abs(P[:, None, 0] - C[None, :, 0]) + np.abs(P[:, None, 1] - C[None, :, 1])
a = CIS.balanced(cost)
Mp = np.array([[s["x"], s["y"]] for s in macs])
mcost = np.abs(Mp[:, None, 0] - C[None, :, 0]) + np.abs(Mp[:, None, 1] - C[None, :, 1])
ma = CIS.balanced(mcost)
nodes, leaves = [], []
for j, i in enumerate(order):
    b = f"mp_pv_ck_br{j}"
    nodes.append(dict(name=b, master="BUFx12f_ASAP7_75t_R", xy_um=br_xy[j], island_rect_um=ent_rect, parent="port:" + port))
for j, i in enumerate(order):
    n = f"mp_pv_ck_isl{j}"
    nodes.append(dict(name=n, master="BUFx12f_ASAP7_75t_R", xy_um=centres[i], island_rect_um=rects[i], parent=f"mp_pv_ck_br{j}"))
    rs = [regs[k]["path"] for k in np.where(a == i)[0]]
    leaves.append(dict(node=n, sinks=rs, cts_open=True, domain_sinks=len(rs)))
    ms = [macs[k]["path"] for k in np.where(ma == i)[0]]
    if ms:
        leaves.append(dict(node=n, sinks=ms, load_class="macro"))
reach = []
for j, i in enumerate(order):
    idx = np.where(a == i)[0]
    reach.append(float(cost[idx, i].max()))
plan_file = repo / "physical/die_plan/qwen_kvsys/cores/macro_sites/kv3_pv_pair.json"
sl = dict(schema="opentallas.master_slice.v1", die="qwen_kvsys", kind="core", type=kd.name, module="kv3_pv_pair",
          outline_um=[W, H], core_clock_port=port, plan="KV-CORE-SLICE-1 kv3_pv_pair core_tree (kv-cores-r6/slice24) "
          "+ core_islands.py k=4 --sym re-site on the static macro sites", plan_sha256=hashlib.sha256(Path(islp).read_bytes()).hexdigest(),
          master_plan_sha256="hm_r26q5c39 (KV slice)", frozen=False,
          islands=[dict(name="entry", rect_um=ent_rect, clock_pin=dict(layer="M5", xy_um=entry))], bays=[], entry_pins=[],
          pushdown={"islands": []},
          core_tree=dict(clock_port=port, form="entry -> 4 branch buffers -> 4 FIRM quadrant islands -> CTS-open leaves (12.8b)",
                         nodes=nodes, leaves=leaves, trunk_layers=["M4", "M5"]),
          pg_obstructions_um={"M4": dump["pg"]["M4"], "M5": dump["pg"]["M5"]},
          plan_prediction=dict(source="core_islands.py maze reach (geometry only, no timing input)",
                               leaf_reach_max_um=[round(r, 1) for r in reach], view="fMX (MX image)" if mir else "R0"))
if "--dry" in sys.argv:
    plan = CI.compile_slice(sl, None); print("COMPILE OK depth", plan["core_tree"]["depth"], "reach", sl["plan_prediction"]); sys.exit(0)
CI.install(kd, sl)
(kd / "pv_tree_slice.json").write_text(json.dumps(sl, indent=1) + "\n")
(kd / "pv_tree_pre_gpl.tcl").write_text(
    "# QK-CORES-11: face_flops (pass-1 reserve + island ft + face regs), then the plan in-core clock tree (FIRM nodes)\n"
    "source /work/face_flops.tcl\nsource /work/master_core_infra.tcl\nputs \"PV_TREE_INSTALLED 4 branch + 4 island nodes\"\n")
cfg = (kd / "config.mk").read_text().splitlines()
cfg.append("override export PRE_GLOBAL_PLACE_TCL = /work/pv_tree_pre_gpl.tcl")
CI.kit_cts_hook(kd, cfg)
(kd / "config.mk").write_text("\n".join(cfg) + "\n")
print("PV_TREE_SLICE_INSTALLED", len(regs), "regs", len(macs), "macros", [len(l["sinks"]) for l in leaves], "reach", sl["plan_prediction"]["leaf_reach_max_um"])
