#!/usr/bin/env python3
"""QW2-VM8P4 10-21 (Q.STA.SLICE.2): kits of the VM8 group P4 = LANDED parent qfd_dv_s5_vm8r.

P4 = structural successor of the P3 gates qfd_dv_slice2_vm8q / vm8qb (in-flow ep6 10-21: ONE clock root over 1.43 mm, parent
flop clock arrival 1.2..2.2 ns vs hard-child insertion 333-485 ps -> post-CTS setup -460 / -522 ps SS on ~9.6k endpoints,
repair inserted 0 buffers = skew).  P4: one CTS root per leaf column (va vb vc pg / cl ch bt) + S-face regions (fc CROM
reads + cr_q capture, fb BTAB reads + bs_q capture, fv VM-write broadcast entry); every cross-region net is an lp landing
(tools/landed_parent/specs/qfd_dv_s5_vm8r.json, D 4 / E 2, landing_chunk_bits 24, share_rings, regional_reset_copies).
Hard children + 2-row floorplan as P3; S pins in per-column disjoint ranges; row-1 / face regions clocked from the S face,
row-2 regions (cl ch bt) from the N face above their column.
  python3 tools/qwen_dv/s5_vm8r_kit.py   (writes physical/ref_tile/qfd_dv_slice2_vm8r{,b}/spec.json from vm8q's)
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/landed_parent"))
import lp  # noqa: E402

BASE = ROOT / "physical/ref_tile/qfd_dv_slice2_vm8q/spec.json"
LP_SPEC = "tools/landed_parent/specs/qfd_dv_s5_vm8r.json"
TOP = "qfd_dv_s5_vm8r"
REC = f"results/arch/qw2_vm8p4_1021/lp/{TOP}_record.json"

BITS = {"a_re": 8, "a_addr": 192, "a_q": 256, "f_va": 1, "b_re": 8, "b_addr": 192, "b_q": 256, "f_vb": 1,
        "c_re": 8, "c_addr": 192, "c_q": 256, "f_vc": 1, "cr_re": 8, "cr_addr": 192, "cr_q": 512, "f_crl": 1,
        "f_crh": 1, "vm_we": 8, "vm_waddr": 192, "vm_wdata": 256, "w16_we": 1, "w16_addr": 24, "w16_data": 512,
        "w1_we": 1, "w1_addr": 24, "w1_data": 32, "tw_we": 1, "tw_kind": 2, "tw_addr": 24, "tw_data": 1024,
        "bs_re": 1, "bs_addr": 24, "bs_q": 256, "f_bt": 1, "p_re": 1, "p_idx": 9, "p_q": 457, "rst_n": 1,
        "ck_va": 1, "ck_vb": 1, "ck_vc": 1, "ck_pg": 1, "ck_fc": 1, "ck_fv": 1, "ck_fb": 1}
# S-face columns, left to right, each under the leaf column it feeds; region clock entries inside their port group
COLS = [["a_re", "a_addr", "ck_va", "a_q", "f_va", "cr_re", "cr_addr", "ck_fc", "cr_q", "f_crl", "f_crh"],     # va | fc
        ["b_re", "b_addr", "ck_vb", "b_q", "f_vb", "vm_we", "vm_waddr", "ck_fv", "vm_wdata", "w16_we", "w16_addr",
         "w16_data", "w1_we", "w1_addr", "w1_data"],                                                           # vb | fv
        ["c_re", "c_addr", "ck_vc", "c_q", "f_vc", "bs_re", "bs_addr", "ck_fb", "bs_q", "f_bt"],                # vc | fb
        ["tw_we", "tw_kind", "tw_addr", "tw_data", "ck_pg", "p_re", "p_idx", "p_q", "rst_n"]]                   # pg (+tables)
NCK = ["ck_cl", "ck_ch", "ck_bt"]          # row-2 region roots: N face above their column centre

# hard-child modules are views; the relay copies are kept (one instance = one physical copy beside its leaf)
KEEP = ["qfd_dv_s5_vm8q_vrd", "qfd_dv_s5_vm8q_vwr", "qfd_dv_s5_vm8q_twb", "qfd_dv_s5_vm8q_twp", "qfd_dv_s5_vm8q_twc"]
VIEWS = {"vmr": "physical/ref_tile/qfd_dv_s5_vmr/views/qfd_dv_s8x_vmr",
         "crh": "physical/ref_tile/qfd_dv_s5_crh/views/qfd_dv_s8x_crh",
         "btab": "physical/ref_tile/qfd_dv_s5_btab/views/qfd_dv_s8x_btab",
         "prog": "physical/ref_tile/qfd_dv_s5_prog/views/qfd_dv_s8x_prog"}
LEAF_W = 259.2

VARIANTS = {
    "vm8r": dict(w=1425.6, h=993.6, y1=129.6, y2=561.6, xs=[86.4, 432.0, 777.6, 1080.0],
                 cuts=[5.4, 345.6, 691.2, 1036.8, 1420.2],
                 why="MAIN: P3 geometry (1425.6 x 993.6, S band 129.6, 86.4 column channels, 155-um inter-row channel); "
                     "landing rings in the S band / channels"),
    "vm8rb": dict(w=1555.2, h=1123.2, y1=216.0, y2=691.2, xs=[86.4, 475.2, 864.0, 1252.8],
                  cuts=[5.4, 388.8, 777.6, 1166.4, 1549.8],
                  why="PARALLEL FALLBACK: ENLARGED 1555.2 x 1123.2 (S band 216, 129.6 column channels, 121-um inter-row "
                      "channel, 86.4 N band) for the ~29k landing-ring flops"),
}


def ranges(cuts):
    out = {}
    for col, (lo, hi) in zip(COLS, zip(cuts[:-1], cuts[1:])):
        tot = sum(BITS[p] for p in col)
        mn = 1.728
        x = lo
        for p in col:
            w = mn + (hi - lo - mn * len(col)) * BITS[p] / tot
            out[p] = [round(x, 3), round(x + w, 3)]
            x += w
        out[col[-1]][1] = hi
    return out


def port_regions():
    S = lp.load(LP_SPEC)
    P = lp.Parent(dict(S, schedule="reference", _spec_path=LP_SPEC)).plan()
    return {n[5:]: r for n, r in P["nreg"].items() if n.startswith("port:")}


def main():
    base = json.loads(BASE.read_text())
    rec = json.loads((ROOT / REC).read_text())
    preg = port_regions()
    dirs = {}
    t = (ROOT / f"rtl/qwen_dv/s5/p4/lp/{TOP}.sv").read_text()
    hdr = t[t.index(f"module {TOP} "):t.index(");", t.index(f"module {TOP} "))]
    import re
    for m in re.finditer(r"(input|output)\s+wire\s+(?:\[[^\]]+\]\s+)?(\w+)", hdr):
        dirs[m.group(2)] = m.group(1)
    regions = list(rec["regions"])
    core = regions[0]
    dom = {}
    for r in regions:
        ins = sorted(p for p, rr in preg.items() if rr == r and dirs.get(p) == "input")
        outs = sorted(p for p, rr in preg.items() if rr == r and dirs.get(p) == "output")
        if r == core:
            ins = sorted(set(ins) | {"rst_n"})
        dom["core" if r == core else r] = dict(ratio=[1, 1], ports=[rec["regions"][r]["clock_port"]], inputs=ins, outputs=outs)
    for name, v in VARIANTS.items():
        s = copy.deepcopy(base)
        for k in ("params", "reset_landing", "spine_ins"):
            s.pop(k, None)
        s["name"] = f"qfd_dv_slice2_{name}"
        s["top"] = TOP
        s["params"] = {"MUT": 0}
        s["sources"] = [f"rtl/qwen_dv/s5/p4/lp/{TOP}.sv", "rtl/common/landed_parent/ot_pl_land.sv",
                        "rtl/common/landed_parent/ot_pl_land_rst_copy.sv", "rtl/common/landed_parent/ot_pl_land_split.sv",
                        "rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv"] + [p for p in base["sources"] if p != "rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv"]
        s["clock"] = "multiple_cts_roots"
        s["clock_port"] = rec["regions"][core]["clock_port"]
        s["clock_ports"] = [rec["regions"][r]["clock_port"] for r in regions]
        s["clock_data_paths"] = "related_same_frequency"
        s["clock_relationship"] = dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0)
        s["clock_entry_domains"] = dom
        s["landed_record"] = REC
        s["child_clock_ref"] = "boundary"
        s["reset_ports"] = ["rst_n"]
        s["outline"] = {"w": v["w"], "h": v["h"], "exact": True}
        s["pins"] = {"S": [p for col in COLS for p in col], "N": list(NCK), "E": [], "W": []}
        x = v["xs"]
        place = [("u_va", "vmr", x[0], v["y1"]), ("u_vb", "vmr", x[1], v["y1"]), ("u_vc", "vmr", x[2], v["y1"]),
                 ("u_pg", "prog", x[3], v["y1"]),
                 ("u_cl", "crh", x[0], v["y2"]), ("u_ch", "crh", x[1], v["y2"]), ("u_bt", "btab", x[2], v["y2"])]
        s["children"] = [{"view": VIEWS[m], "count": 1, "inst": i, "at": [xx, yy], "orient": "R0", "at_exact": True}
                         for i, m, xx, yy in place]
        pr = ranges(v["cuts"])
        for c, xx in zip(NCK, x[:3]):
            mid = round(xx + LEAF_W / 2, 3)
            pr[c] = [round(mid - 0.864, 3), round(mid + 0.864, 3)]
        s["pin_ranges"] = pr
        s["route"]["pin_balance"] = {"group_max": 1}
        s["route"]["synth_keep_modules"] = KEEP
        s["recipe"] = 3
        s["inhold"] = False
        s["outhold"] = False
        s["hold_budget"] = "tile"
        s["reset_landing"] = {"enable": False, "reason": (
            f"the lp.py RTL lands it: rst_n -> regional reset runs from region {rec['reset']['root_region']} (depth "
            f"{rec['reset']['depth']}, 1-bit hops <= 405 um), last stage = kept copies <= 32 loads "
            "(regional_reset_copies) -> leaf rst_n pins; the port net has ONE sink")}
        s["pin_regs"] = {"enable": False, "reason": (
            "landed parent: every input lands on a flop of its own region beside its pin range (the leaf's kept relay copy "
            "in a column region, or the landing ring writer in an S-face region fc / fb / fv); every output is a vm8out "
            "capture flop in its region; lp offsets are the compiler record")}
        s["landed"] = dict(record=REC, landings=len(rec["landings"]), landing_flops=rec["flops"]["landing"],
                           reset_depth=rec["reset"]["depth"], lp_spec=LP_SPEC, D=rec["D"], E=rec["E"],
                           landing_chunk_bits=24, regional_reset_copies=True,
                           offsets=rec["compiler"]["output_port_offset_edges"])
        s["structural_change"] = (
            "QW2-VM8P4 10-21 P4 successor of P3 vm8q / vm8qb (in-flow ep6: ONE clock root over 1.43 mm, parent flop arrival "
            "1.2..2.2 ns vs hard-child insertion 333-485 ps -> post-CTS setup -460 / -522 ps SS on ~9.6k endpoints, repair "
            "0 buffers = skew). P4 = landed parent: 10 regional CTS roots (va vb vc pg | cl ch bt | fc fb fv), every "
            "cross-region net an lp landing (D4/E2, chunk 24, shared rings), regional reset runs with kept copies. Lockstep "
            "landed == flat qfd_dv_s5_vm8rf (lp bench) and flat == vm8fh (P3 tb). Price vs flat vm8rf: VM answers +3 "
            "(writes +3, write->read distance unchanged), PROG +0, BTAB / CROM +6, reset release +5. " + v["why"])
        s["safe_design_checklist"] = {
            "1_pins": "every port lands on a flop of its own small region beside its S pin range; outputs flop-last",
            "2_reach": "row-2 / broadcast traffic only through landings (multicycle 2 per window); no pin -> far-leaf wire",
            "3_fanout": "kept per-leaf relay copies; landing_chunk_bits 24 + shared rings + reset copies <= 32; census in gate",
            "4_depth": "relays + ring select only",
            "5_storage": "all arrays inside the 7 closed hard children",
            "6_floorplan": "P3 lattice placement (MAIN) / enlarged (FALLBACK)",
            "7_clock": "10 regional roots, child clock pins sinks of their region root (landed_cluster), crossings landed",
            "8_reset": "lp regional reset runs, leaf rst_n only; datapath unreset"}
        j = s["job"]
        j["owner"] = "Claude:QW2-VM8P4"
        j["tag"] = name
        j["branch"] = "claude/qw2-vm8p4-1021"
        j["purpose"] = "slice2 VM8 leaf group P4 (landed regions): critical, gate only -> COORD-REVIEW-QUEUE"
        j["hold_merge"] = "QW2-VM8P4 proof vehicle; the slice2 W parent (w6 VM8Q_VIEW) absorbs it"
        j["extra_paths"] = ["rtl/test/qwen_dv/s5", "rtl/qwen_dv/s5/p3", "rtl/qwen_dv/s5/p4", "rtl/common/landed_parent",
                            "tools/landed_parent", "results/arch/qw2_vm8p4_1021"]
        vl = "SIM=verilator VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
        j["benches"] = [
            {"name": "p4_lp_lockstep", "cmd": f"{vl} MUTS=0 bash rtl/qwen_dv/s5/p4/lp/{TOP}_bench.sh {{RUN}}/bench/lp0",
             "expect": "pass", "threads": 8, "peak_ram_gb": 24, "needs": ["verilator"], "pass_regex": "BENCH_EXIT 0"},
            {"name": "p4_lp_mut1_unland", "cmd": f"{vl} bash rtl/qwen_dv/s5/p4/run_vm8r_mut.sh {{RUN}}/bench/lp1 1",
             "expect": "fail", "threads": 8, "peak_ram_gb": 24, "needs": ["verilator"], "fail_regex": "LP_LOCKSTEP FAIL"},
            {"name": "p4_flat_vs_fh", "cmd": f"{vl} bash rtl/qwen_dv/s5/p4/qfd_dv_s5_vm8rf_p3_bench.sh {{RUN}}/bench/fh",
             "expect": "pass", "threads": 8, "peak_ram_gb": 24, "needs": ["verilator"], "pass_regex": "BENCH_EXIT 0"}]
        out = ROOT / f"physical/ref_tile/qfd_dv_slice2_{name}/spec.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(s, indent=1) + "\n")
        dens = {i: round(sum(BITS[p] for p in c) / (b - a), 2)
                for i, (c, a, b) in enumerate(zip(COLS, v["cuts"][:-1], v["cuts"][1:]))}
        print(out.relative_to(ROOT), "pins/um per column", dens, "domains", len(dom))


if __name__ == "__main__":
    main()
