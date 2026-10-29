#!/usr/bin/env python3
"""DIE-KV-14b (2026-10-28) kv3_pv_pair PLAN DELTA (b1): the 8 SRAM clock pins become plan MACRO LEAVES at the SAME
stage count as the register leaves (COORD ruling 16:54 on KV-KITS-14 ASK 16:52; METHODOLOGY 12.8 b/d1, no CTS
delay-buffer rescue, no kit tweak).

Root cause (KV-KITS-14, CHECKED from 4_1_cts.log + signoff.json of fMX b5c218253de1): the QK-CORES-11 plan tree hangs
the SRAM clock pins on the island outputs mp_pv_ck_isl*_out together with the 7429-register CTS-open leaf; TritonCTS
splits the net into a 'for macros' net (1 level) and a '_regs' net (6 buffered stages) and does not balance them
(CTS-0179), so the macros are clocked ~150 ps early (TT ~106 vs regs 237-296).

Delta (die-local, opt-in shared core_infra stage_basis="total"):
  port -> br_j -> isl_j -> [TritonCTS S stages] -> 7429 regs           (register leaf: 2 planned + S CTS stages)
  port -> br_j -> mac_j_0 .. mac_j_{S} (S+1 planned BUFx24) -> 2 SRAM clk (macro leaf: 1 + (S+1) planned stages)
  * the macro chain hangs from the branch buffer, NOT from the CTS-open island net: the island net then carries only
    registers, TritonCTS no longer sees a macro group, and every macro stage is a planned FIRM dont_touch cell;
  * S = the register leaf's CTS stage count, plan-computed from the census (tritoncts_stages), not from a measurement;
  * chain master = BUFx24 (the TritonCTS register-tree buffer), so both leaves carry the same cell type per stage;
  * chain cells sit in the island rect (the plan's reserved clock station), on rows below the island node.

usage:
  pv_macro_leaves.py estimate SLICE.json LIBDIR [--out estimate.json]   # predict_tree NLDM, both leaves, TT/FF
  pv_macro_leaves.py apply SLICE.json OUT.json                         # write the delta slice (compile-checked)
  pv_macro_leaves.py install KIT                                       # KV-KITS: apply to KIT/pv_tree_slice.json + core_infra.install
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/die_plan"))
import core_infra as CI  # noqa: E402

CHAIN_MASTER = "BUFx24_ASAP7_75t_R"
ROW_UM = 0.27
SITE_UM = 0.054
CTS_CLUSTER = CI.CTS_FANOUT      # TritonCTS register sink cluster (fMX log: 7429 sinks -> 310 clusters = ceil(7429/24))
CTS_LEAF_SINKS = 15              # TritonCTS H-tree stop criterion ('max number of sinks is 15', 4_1_cts.log)
SRAM_CLK_CAP = {"TT": 9.3458, "FF": 9.3458}   # ot_sram_1r1w_32x128_m1 pin (clk) capacitance (tt/ff lib)
SRAM_W, SRAM_H, SRAM_CLK = 51.408, 20.790, (0.012, 0.780)   # LEF SIZE + PIN clk rect centre (R0 frame)
WIRE_R, WIRE_C = (1.80365e-2 + 1.89935e-2) / 2, (1.275e-1 + 9.8e-2) / 2   # kit setRC_rcx M4/M5 mean (kohm, fF / um)


def tritoncts_stages(n_sinks, cluster=CTS_CLUSTER, leaf_sinks=CTS_LEAF_SINKS):
    """Buffered stages TritonCTS builds below a CTS-open driver for n register sinks (census only):
    1 macro/register split root + 1 H-tree root + ceil(L/2) buffered branch levels + 1 leaf buffer,
    L = H-tree levels until <= leaf_sinks clusters per sub-region, clusters = ceil(n / cluster)."""
    c = math.ceil(n_sinks / cluster)
    lv = max(0, math.ceil(math.log2(c / leaf_sinks))) if c > leaf_sinks else 0
    return 1 + (1 + math.ceil(lv / 2)) + 1


def sram_clk_xy(site):
    """clock-pin centre (core um) of a macro at site (x_ll, y_ll, orient), bbox lower-left placement."""
    x, y, o = site
    px, py = SRAM_CLK
    fx = {"R0": px, "MX": px, "R180": SRAM_W - px, "MY": SRAM_W - px}[o]
    fy = {"R0": py, "MY": py, "R180": SRAM_H - py, "MX": SRAM_H - py}[o]
    return [round(x + fx, 3), round(y + fy, 3)]


def apply(sl):
    sl = copy.deepcopy(sl)
    t = sl["core_tree"]
    if t.get("stage_basis") == "total":
        raise SystemExit("slice already carries the macro-leaf delta")
    nodes = {n["name"]: n for n in t["nodes"]}
    new_nodes, new_leaves, report = list(t["nodes"]), [], []
    opened = {l["node"]: l for l in t["leaves"] if l.get("cts_open")}
    stages = {n: tritoncts_stages(l["domain_sinks"]) for n, l in opened.items()}
    if len(set(stages.values())) != 1:
        raise SystemExit(f"register leaves have unequal CTS stage counts {stages}")
    S = next(iter(stages.values()))
    for leaf in t["leaves"]:
        if leaf.get("cts_open"):
            new_leaves.append(dict(leaf, cts_stages=S))
            continue
        if leaf.get("load_class") != "macro":
            raise SystemExit(f"unexpected leaf {leaf['node']}")
        isl = nodes[leaf["node"]]
        j = isl["name"].rsplit("isl", 1)[1]
        x0, y0, x1, y1 = isl["island_rect_um"]
        parent, chain = isl["parent"], []
        for k in range(S + 1):
            name = f"mp_pv_ck_mac{j}_{k}"
            xy = [round(round((x0 + 0.54) / SITE_UM) * SITE_UM, 3), round(y0 + ROW_UM * (2 * k + 2), 3)]
            if not (xy[1] < isl["xy_um"][1] - ROW_UM and xy[1] < y1):
                raise SystemExit(f"{name}: island rect {isl['island_rect_um']} has no free row below the island node")
            new_nodes.append(dict(name=name, master=CHAIN_MASTER, xy_um=xy, island_rect_um=list(isl["island_rect_um"]),
                                  parent=parent))
            parent = name
            chain.append(name)
        new_leaves.append(dict(node=chain[-1], sinks=list(leaf["sinks"]), load_class="macro"))
        report.append(dict(island=isl["name"], branch=isl["parent"], chain=chain, sinks=leaf["sinks"]))
    t.update(nodes=new_nodes, leaves=new_leaves, stage_basis="total",
             form=t["form"] + " | DIE-KV-14b: SRAM clk = planned macro leaves br -> (S+1) x BUFx24 chain in the island "
                  f"rect, S = {S} = TritonCTS register stages below the island (census); equal total stage count")
    sl["plan"] = sl.get("plan", "") + " + DIE-KV-14b macro leaves (pv_macro_leaves.py)"
    sl.setdefault("plan_prediction", {})["macro_leaves"] = dict(cts_stages=S, chain_stages=S + 1, chains=report)
    plan = CI.compile_slice(sl, None)
    return sl, plan, S


def estimate(sl_old, libdir, macro_sites):
    import core_infra_plan as CP
    import die_clock_128 as C128
    sl_new, plan, S = apply(sl_old)
    libs = {c: C128.lib_cells(c, libdir) for c in ("TT", "FF")}
    pts, caps = {}, {}
    mems = sorted({s for l in sl_old["core_tree"]["leaves"] if l.get("load_class") == "macro" for s in l["sinks"]})
    for s, site in zip(mems, macro_sites):
        pts[s] = sram_clk_xy(site)
        caps[s] = dict(SRAM_CLK_CAP)
    W, H = sl_old["outline_um"]
    out = {}
    for tag, sl in (("old", sl_old), ("new", sl_new)):
        sl = copy.deepcopy(sl)
        for l in sl["core_tree"]["leaves"]:
            if l.get("cts_open"):
                n = next(q for q in sl["core_tree"]["nodes"] if q["name"] == l["node"])
                x, y = n["xy_um"]
                l["region_rect_um"] = [0 if x < W / 2 else W / 2, 0 if y < H / 2 else H / 2,
                                       W / 2 if x < W / 2 else W, H / 2 if y < H / 2 else H]
                if tag == "new":
                    l.pop("cts_stages", None)
        if tag == "new":
            sl["core_tree"].pop("stage_basis", None)   # re-added by _compile_any_depth (stage check is apply()'s)
        r = _predict(CP, sl, libs, pts, caps)
        out[tag] = r
    return sl_new, S, out


def _predict(CP, sl, libs, pts, caps):
    real = CI.compile_slice
    CI.compile_slice = lambda s, kd=None: _compile_any_depth(real, s)
    try:
        r = CP.predict_tree(sl, libs, pts, caps, WIRE_R, WIRE_C)
    finally:
        CI.compile_slice = real
    res = {}
    for c, a in r["corners"].items():
        rows = a["leaf_means"]
        reg = [x for x in rows if x["kind"] == "cts_open"]
        mac = [x for x in rows if x["kind"] == "macro"]
        res[c] = dict(reg_mean_ps=[round(x["mean_ps"], 1) for x in reg], reg_min_ps=[round(x["min_ps"], 1) for x in reg],
                      reg_max_ps=[round(x["max_ps"], 1) for x in reg], reg_calibration=[x.get("calibration") for x in reg],
                      macro_mean_ps=[round(x["mean_ps"], 1) for x in mac])
    return res


def _compile_any_depth(real, s):
    s = copy.deepcopy(s)
    s["core_tree"]["stage_basis"] = "total"
    nodes = {n["name"]: n["parent"] for n in s["core_tree"]["nodes"]}

    def depth(n):
        return 0 if n.startswith("port:") else 1 + depth(nodes[n])
    lv = {l["node"]: depth(l["node"]) for l in s["core_tree"]["leaves"] if not l.get("cts_open")}
    top = max(lv.values())
    if all(depth(l["node"]) == top for l in s["core_tree"]["leaves"]):
        s["core_tree"].pop("stage_basis")
        return real(s)                       # legacy tree (macro leaf on the island node): unchanged compile
    for l in s["core_tree"]["leaves"]:
        if l.get("cts_open"):
            l["cts_stages"] = top - depth(l["node"])
    return real(s)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("estimate"); e.add_argument("slice"); e.add_argument("libdir"); e.add_argument("--sites", required=True)
    e.add_argument("--out")
    a_ = sp.add_parser("apply"); a_.add_argument("slice"); a_.add_argument("out")
    i = sp.add_parser("install"); i.add_argument("kit")
    a = ap.parse_args()
    if a.cmd == "apply":
        sl, plan, S = apply(json.loads(Path(a.slice).read_text()))
        Path(a.out).write_text(json.dumps(sl, indent=1) + "\n")
        print("PV_MACRO_LEAVES", a.out, "S", S, "depth", plan["core_tree"]["depth"], "open", plan["core_tree"]["cts_open"])
    elif a.cmd == "install":
        kd = Path(a.kit)
        sl, plan, S = apply(json.loads((kd / "pv_tree_slice.json").read_text()))
        CI.install(kd, sl)
        (kd / "pv_tree_slice.json").write_text(json.dumps(sl, indent=1) + "\n")
        print("PV_MACRO_LEAVES_INSTALLED", kd.name, "S", S, "total stages", plan["core_tree"]["depth"],
              "cts_open", plan["core_tree"]["cts_open"])
    else:
        sites = json.loads(Path(a.sites).read_text())
        sl_new, S, out = estimate(json.loads(Path(a.slice).read_text()), a.libdir, sites)
        res = dict(cts_stages=S, total_stages=2 + S, chain_master=CHAIN_MASTER, wire_rc=[WIRE_R, WIRE_C], **out)
        txt = json.dumps(res, indent=1)
        if a.out:
            Path(a.out).write_text(txt + "\n")
        print(txt)


if __name__ == "__main__":
    main()
