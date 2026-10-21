#!/usr/bin/env python3
"""QW-SLICE2W 10-21: specs for the VM8 group P3 kits qfd_dv_slice2_vm8q (main) / vm8qb (parallel fallback).

P3 = structural successor of the P2 gates vm8p / vm8pb (FAIL 10-21: pin -> hard-child pin flops spread 202-455 ps,
966-1050 stages beyond reach from shared broadcast relays, rst_n unlanded, GRT-0183).  Two-row floorplan: row 1 (S band
side) = the three VM replicas + PROG, row 2 = CROM lo / hi + BTAB; every leaf's input lands on its own kept parent relay
copy; S pins in per-column disjoint ranges (<= 4.4 pins/um) under the leaf they feed.
  python3 tools/qwen_dv/s5_vm8q_spec.py   (writes physical/ref_tile/qfd_dv_slice2_vm8q{,b}/spec.json from vm8p's)
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "physical/ref_tile/qfd_dv_slice2_vm8p/spec.json"

BITS = {"a_re": 8, "a_addr": 192, "a_q": 256, "f_va": 1, "b_re": 8, "b_addr": 192, "b_q": 256, "f_vb": 1,
        "c_re": 8, "c_addr": 192, "c_q": 256, "f_vc": 1, "cr_re": 8, "cr_addr": 192, "cr_q": 512, "f_crl": 1,
        "f_crh": 1, "vm_we": 8, "vm_waddr": 192, "vm_wdata": 256, "w16_we": 1, "w16_addr": 24, "w16_data": 512,
        "w1_we": 1, "w1_addr": 24, "w1_data": 32, "tw_we": 1, "tw_kind": 2, "tw_addr": 24, "tw_data": 1024,
        "bs_re": 1, "bs_addr": 24, "bs_q": 256, "f_bt": 1, "p_re": 1, "p_idx": 9, "p_q": 457, "rst_n": 1, "ck": 1}
# S-face columns, left to right, each under the leaf column it feeds (row 1 / row 2)
COLS = [["a_re", "a_addr", "a_q", "f_va", "cr_re", "cr_addr", "cr_q", "f_crl", "f_crh"],          # va / cl
        ["b_re", "b_addr", "b_q", "f_vb", "vm_we", "vm_waddr", "vm_wdata", "w16_we", "w16_addr", "w16_data",
         "w1_we", "w1_addr", "w1_data"],                                                            # vb / ch (+VM writes)
        ["ck", "c_re", "c_addr", "c_q", "f_vc", "tw_we", "tw_kind", "tw_addr", "tw_data"],          # vc / bt (+tables)
        ["bs_re", "bs_addr", "bs_q", "f_bt", "p_re", "p_idx", "p_q", "rst_n"]]                      # pg

KEEP = ["qfd_dv_s5_vm8q_rst", "qfd_dv_s5_vm8q_vrd", "qfd_dv_s5_vm8q_vwr", "qfd_dv_s5_vm8q_twb", "qfd_dv_s5_vm8q_twp",
        "qfd_dv_s5_vm8q_twc"]

VIEWS = {"vmr": "physical/ref_tile/qfd_dv_s5_vmr/views/qfd_dv_s8x_vmr",
         "crh": "physical/ref_tile/qfd_dv_s5_crh/views/qfd_dv_s8x_crh",
         "btab": "physical/ref_tile/qfd_dv_s5_btab/views/qfd_dv_s8x_btab",
         "prog": "physical/ref_tile/qfd_dv_s5_prog/views/qfd_dv_s8x_prog"}

# variant: (W, H, row1 y, row2 y, column x list, column boundaries along S)
VARIANTS = {
    "vm8q": dict(w=1425.6, h=993.6, y1=129.6, y2=561.6, xs=[86.4, 432.0, 777.6, 1080.0],
                 cuts=[5.4, 345.6, 691.2, 1036.8, 1420.2],
                 why="MAIN: 2 rows, 43.2/86.4 channels (read-port W/E faces on 86.4 channels), S band 129.6"),
    "vm8qb": dict(w=1468.8, h=1080.0, y1=172.8, y2=648.0, xs=[86.4, 432.0, 777.6, 1123.2],
                  cuts=[5.4, 388.8, 734.4, 1080.0, 1463.4],
                  why="PARALLEL FALLBACK: 2 rows, 86.4 channels everywhere, S band 172.8, 198.7 um inter-row relay channel"),
}


def ranges(cuts):
    out = {}
    for col, (lo, hi) in zip(COLS, zip(cuts[:-1], cuts[1:])):
        tot = sum(BITS[p] for p in col)
        mn = 1.728                                   # every port >= 1.728 um (a few pin tracks), rest by bit count
        x = lo
        for p in col:
            w = mn + (hi - lo - mn * len(col)) * BITS[p] / tot
            out[p] = [round(x, 3), round(x + w, 3)]
            x += w
        out[col[-1]][1] = hi
    return out


def main():
    base = json.loads(BASE.read_text())
    for name, v in VARIANTS.items():
        s = copy.deepcopy(base)
        s["name"] = f"qfd_dv_slice2_{name}"
        s["top"] = "qfd_dv_s5_vm8q"
        s["sources"] = [p.replace("rtl/qwen_dv/s5/p2/qfd_dv_s5_vm8p.sv", "rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv")
                        for p in s["sources"]]
        s["outline"] = {"w": v["w"], "h": v["h"], "exact": True}
        s["pins"] = {"S": [p for col in COLS for p in col], "N": [], "E": [], "W": []}
        x = v["xs"]
        place = [("u_va", "vmr", x[0], v["y1"]), ("u_vb", "vmr", x[1], v["y1"]), ("u_vc", "vmr", x[2], v["y1"]),
                 ("u_pg", "prog", x[3], v["y1"]),
                 ("u_cl", "crh", x[0], v["y2"]), ("u_ch", "crh", x[1], v["y2"]), ("u_bt", "btab", x[2], v["y2"])]
        s["children"] = [{"view": VIEWS[m], "count": 1, "inst": i, "at": [xx, yy], "orient": "R0", "at_exact": True}
                         for i, m, xx, yy in place]
        s["pin_ranges"] = ranges(v["cuts"])
        s["route"]["pin_balance"] = {"group_max": 1}
        s["route"]["synth_keep_modules"] = KEEP
        s["reset_landing"] = {"enable": True, "stages": 2}
        s["pin_regs"] = {"enable": False, "reason": (
            "P3 one clock region (owner 10-20 09:05: pin registers only at region crossings and on wires > 405 um): every "
            "input lands on its leaf's own kept parent relay copy (qfd_dv_s5_vm8q_* / _rly, d_in >= 1), every output is "
            "the S-face capture register qfd_dv_s5_vm8out (flop-last); rst_n lands in 2 stages (reset_landing)")}
        s["structural_change"] = (
            "QW-SLICE2W 10-21 P3 successor of P2 vm8p / vm8pb (gates FAIL 10-21: clock_rule pin-flop spread TT/FF 202/246 "
            "and 384/455 ps from pins landing on hard-child pin registers; wire_reach 966/1050 stages > 500 um from the "
            "single-cycle VM broadcast writes (pin -> u_vc 819 um) and ONE shared table-write trunk per tier; rst_n 4 "
            "sinks unlanded; GRT-0183 boxed-in net in repair; S face 10.5 pins/um cluster). P3: every leaf input lands on "
            "its OWN kept parent relay copy (VM d_in 1), per-leaf broadcast copies, 2-stage reset landing, two-row "
            "floorplan (row 1 VM x3 + PROG, row 2 CROM lo/hi + BTAB), per-column disjoint S pin ranges <= 4.4 pins/um. "
            "Lockstep == vm8fh with VM answers +1, BTAB/PROG +2, CROM +4. " + v["why"])
        j = s["job"]
        j["tag"] = name
        j["branch"] = "claude/qw-slice2w3-1021"
        j["purpose"] = "slice2 VM8 leaf group P3 (one region, per-leaf kept relay copies): critical, gate only -> COORD-REVIEW-QUEUE"
        j["extra_paths"] = ["rtl/test/qwen_dv/s5", "rtl/qwen_dv/s5/p3"]
        j["benches"] = [{"name": "p3_vm8q",
                         "cmd": "SIM=verilator VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator bash "
                                "rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q_bench.sh {RUN}/bench/p3_vm8q",
                         "expect": "pass", "threads": 8, "peak_ram_gb": 24, "needs": ["verilator"],
                         "pass_regex": "BENCH_EXIT 0"}]
        out = ROOT / f"physical/ref_tile/qfd_dv_slice2_{name}/spec.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(s, indent=1) + "\n")
        dens = {i: round(sum(BITS[p] for p in c) / (b - a), 2)
                for i, (c, a, b) in enumerate(zip(COLS, v["cuts"][:-1], v["cuts"][1:]))}
        print(out.relative_to(ROOT), "pins/um per column", dens)


if __name__ == "__main__":
    main()
