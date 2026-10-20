#!/usr/bin/env python3
"""L2H-IDXSCORE 2026-10-19: write the r4 IDX quarter scorer kit specs (leaf_c1, qw_r4, qe_r4) for a leaf row pitch ROW.
Pin plan = the shared leaf face table (TW3-IDXSCORE pinplan.py, generalised to ROW): every qw E / qe W row section faces
the leaf's W / E pins bit for bit.  Usage: mk_r4_kits.py ROW QW_W QE_W SUFFIX   (writes physical/ref_tile/<kit>/spec.json)"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ORDER = [("qv", 1), ("q", 568), ("kv", 1), ("kkv", 4), ("key", 2176), ("aux", 30), ("bus", 552)]
MINW = 1.08


def table(row):
    lo, hi = 2.16, row - 2.16
    tot = sum(b for _, b in ORDER)
    small = sum(MINW for n, b in ORDER if b * ((hi - lo) / tot) < MINW)
    big = sum(b for n, b in ORDER if b * ((hi - lo) / tot) >= MINW)
    k = (hi - lo - small) / big
    out, y = {}, lo
    for n, b in ORDER:
        w = MINW if b * ((hi - lo) / tot) < MINW else b * k
        out[n] = (round(y, 3), round(y + w, 3)); y += w
    return out


def r(a, b):
    return [round(a, 3), round(b, 3)]


BENCH_ENV = {"threads": 16, "peak_ram_gb": 54, "needs": ["verilator"]}
QS = "results/rtl/hbm_idx_quarter_split_1018/qs_r4"
LE = "results/rtl/hbm_idx_quarter_split_1018/leaf_l"


def qs_benches():
    b = [dict(name="qsplit_r4_pos", cmd="bash rtl/test/hbm_idx_static/run_quarter_split_r4.sh {RUN}/qs_pos pos", expect="pass",
              pass_regex="^IDX_QUARTER_SPLIT_GATE_PASS$", pass_witness=f"{QS}/pos.log", **BENCH_ENV)]
    for m, row in (("keyline", 0), ("auxearly", 0), ("rowswap", 1)):
        b.append(dict(name=f"qsplit_r4_{m}", cmd=f"QS_BENCH=1 bash rtl/test/hbm_idx_static/run_quarter_split_r4.sh {{RUN}}/qs_{m} {m}",
                      expect="fail", fail_regex=f"^\\[{m}\\] QSPLIT_BAD cyc", fail_witness=f"{QS}/{m}.log", **BENCH_ENV))
    return b


def le_benches():
    env = {"threads": 8, "peak_ram_gb": 28, "needs": ["verilator"]}
    b = []
    for m in ("pos", "gap4"):
        b.append(dict(name=f"chunk_rt_l_{m}", cmd=f"bash rtl/test/hbm_idx_static/run_chunk_rt_l_equiv.sh {{RUN}}/le_{m} {m}", expect="pass",
                      pass_regex="^CHUNK_RT_EQUIV PASS checks ", pass_witness=f"{LE}/{m}.log", **env))
    for m in ("qlate1", "seam", "swap"):
        b.append(dict(name=f"chunk_rt_l_{m}", cmd=f"bash rtl/test/hbm_idx_static/run_chunk_rt_l_equiv.sh {{RUN}}/le_{m} {m}", expect="fail",
                      fail_regex="^MISMATCH cyc", fail_witness=f"{LE}/{m}.log", **env))
    return b


COMMON_SRC = ["rtl/lib/ot_rst_relay.sv", "rtl/lib/ot_rst_relay_l.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_delay_rf.sv",
              "rtl/hdc/ot_hdc_delay_auto.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
              "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_prefix.sv"]
ROUTE = {"threads": 16, "peak_ram_gb": 32, "hold_margin_ns": 0.03, "io_hold_margin_ns": 0.03, "pin_h": "M4", "pin_v": "M3 M5",
         "macro_halo_um": 5.4, "pin_balance": {"group_max": 1, "h": "M4", "v": "M3 M5"}}
REL = {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0}


def base(name, top, owner_purpose, sources, w, h, pd, mem, benches, why):
    route = dict(ROUTE, pd=pd, peak_ram_gb=mem)
    return {"kind": "tile", "layer_cap": "M5", "recipe": 4, "route": route, "inhold": False, "outhold": False,
            "keep_pin_regs": True, "macros": [], "children": [], "inter": [], "hold_budget": "die",
            "job": {"owner": "Claude LEAD2-HBM/L2H-IDXSCORE 1019", "purpose": owner_purpose,
                    "branch": "claude/l2h-idxscore-1019", "benches": benches},
            "name": name, "top": top, "sources": sources, "reset_ports": ["rst_n"], "params": {},
            "outline": {"w": w, "h": h, "exact": True}, "structural_change": why,
            "reset_landing": {"enable": False, "reason": "the RTL lands it: rst_n reaches only the 2 synchroniser flops of "
                              "ot_rst_relay_l (relay copies clear from the last stage); physical stages would shift the "
                              "scheduled reset release"}}


def leaf(row, suffix, pd):
    T = table(row)
    s = base(f"hidx_score_leaf_c1{suffix}", "ot_hbm_idx_score_leaf_c1", "IDX-SCORE leaf master, one clock root (8 per quarter)",
             ["rtl/hbm_accel/index/ot_hbm_idx_score_leaf_c1.sv", "rtl/hdc/v41x/ot_hbm_idx_chunk_rt_l.sv"] + COMMON_SRC,
             row, row, pd, 96, le_benches(),
             f"L2H-IDXSCORE 2026-10-19 successor of hidx_score_leaf_1017 (r10 FAIL: CTS clk_pair[0] internal-root pin-flop spread "
             f"176.2 ps, reset_landing 40, util 68%): ONE centre-fed root clk (no internal-only roots), core "
             f"ot_hbm_idx_chunk_rt_l (landed relays, segmented valid-line resets, ring-buffer delays), outline {row} um "
             f"square sized from the r10 synthesis area 209,848 um2 (~{209848 / (row * row) * 100:.0f}% util); same data "
             f"ports and cycles.")
    s["clock_port"] = "clk"
    s["io_flop_at_pins"] = {"cols": 4, "allow_none": True}
    s["pins"] = {"W": ["w_qv", "w_q", "w_kv", "w_kkv", "w_key", "w_aux", "w_bus"],
                 "E": ["e_qv", "e_q", "e_kv", "e_kkv", "e_key", "e_aux", "e_bus"], "N": ["clk", "rst_n", "hb"]}
    s["pin_regs"] = {"enable": False, "reason": "the RTL registers every leaf pin: W pin regs f_*/hb_p/b_w (flop-first), "
                     "E outputs from the E pin regs g_*/e_bus"}
    pr = {}
    for n, _ in ORDER:
        pr["w_" + n] = list(T[n]); pr["e_" + n] = list(T[n])
    c = row / 2
    pr["clk"] = r(c - 0.54, c + 0.54); pr["rst_n"] = r(c + 5.4, c + 6.48); pr["hb"] = r(c - 16.2, c - 5.4)
    s["pin_ranges"] = pr
    return s


def qw(row, w, suffix, pd):
    T = table(row)
    src = ["rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_wo2.sv", "rtl/hbm_accel/index/ot_hbm_idx_score_leaf_c1.sv",
           "rtl/hdc/v41x/ot_hbm_idx_chunk_rt_l.sv", "rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv",
           "rtl/hdc/v41x/ot_hbm_idx_owned_native.sv"] + COMMON_SRC
    s = base(f"hidx_score_qw4{suffix}", "ot_hbm_idx_score_qw_r4", "IDX quarter scorer W glue tile r4 (wires-only quarter wo2, x4 per die)",
             src, w, 2 * row, pd, 32, qs_benches(),
             "L2H-IDXSCORE 2026-10-19 successor of hidx_score_qw_1018 (r3 FAIL GPL-0305 at 4% util, reset_landing 4, one root "
             "over 1.12 mm, row-1 outputs one ~560 um hop from the row-0 input capture): A pin capture -> B mid stage per row -> "
             "C output pin regs (+2 edges, was +1; compiler --score-chain +1), row clocks clk_w0 / clk_w1 (die clk_engine[0/1]), "
             "landed reset ot_rst_relay_l, wf split per row, width cut to the pin-flop columns.")
    s["clock_port"] = "clk_w0"; s["clock"] = "multiple_cts_roots"; s["clock_ports"] = ["clk_w0", "clk_w1"]
    s["clock_data_paths"] = "related_same_frequency"; s["clock_relationship"] = REL
    w0_in = ["rst_n", "half", "rank", "first_ord", "nkeys", "keep_en", "keep_bitmap", "ql_v", "ql_head", "ql_codes", "ql_sc",
             "ql_w", "beat_v", "beat_index", "key_lines0"]
    s["clock_entry_domains"] = {
        "core": {"ratio": [1, 1], "ports": ["clk_w0"], "inputs": w0_in,
                 "outputs": ["rst_c0", "rst_c1"] + [f"o_{n}0" for n, _ in ORDER]},
        "r1": {"ratio": [1, 1], "ports": ["clk_w1"], "inputs": ["key_lines1"], "outputs": [f"o_{n}1" for n, _ in ORDER]}}
    s["io_flop_at_pins"] = {"cols": 2, "allow_none": True}
    s["pins"] = {"W": ["clk_w0", "clk_w1", "rst_n", "ql_v", "ql_head", "ql_codes", "ql_sc", "ql_w", "beat_v", "key_lines0",
                       "keep_bitmap", "beat_index", "nkeys", "first_ord", "rank", "half", "keep_en", "key_lines1"],
                 "E": [f"o_{n}{e}" for e in (0, 1) for n, _ in ORDER] + ["rst_c0", "rst_c1"]}
    s["pin_regs"] = {"enable": False, "reason": "every input lands in an A-stage capture flop, every output launches from a "
                     "C-stage flop (RTL); o_bus0/1 are the head rows' constant zero sum-bus words"}
    q0, q1 = T["q"]; qs = (q1 - q0) / 568
    pr = {"ql_v": list(T["qv"]), "ql_head": r(q0, q0 + 8 * qs), "ql_codes": r(q0 + 8 * qs, q0 + 520 * qs),
          "ql_sc": r(q0 + 520 * qs, q0 + 552 * qs), "ql_w": r(q0 + 552 * qs, q1), "beat_v": list(T["kv"]),
          "key_lines0": r(T["kkv"][0], T["aux"][1]), "key_lines1": r(row + T["kkv"][0], row + T["aux"][1])}
    b = T["bus"][0]
    for n, a, z in (("keep_bitmap", 0, 52.511), ("beat_index", 52.511, 57.511), ("nkeys", 57.511, 62.511),
                    ("first_ord", 62.511, 67.511), ("rank", 67.511, 72.511), ("half", 72.511, 73.591), ("keep_en", 73.591, 74.671)):
        pr[n] = r(b + a, b + z)
    pr["clk_w0"] = r(b + 80, b + 81.08); pr["rst_n"] = r(b + 84, b + 85.08); pr["clk_w1"] = r(row + 50, row + 51.08)
    for e in (0, 1):
        for n, _ in ORDER:
            pr[f"o_{n}{e}"] = r(T[n][0] + e * row, T[n][1] + e * row)
    # both reset relay copies (clk_w0 domain) at the row seam on the E face: r4 gate 1 had rst_c1 on the N face, a clk_w0
    # boundary flop 650 um from the rest of its domain (clk_w0 TT pin-flop spread 333.8 ps)
    pr["rst_c0"] = r(row - 1.62, row - 0.54); pr["rst_c1"] = r(row, row + 1.08)
    s["pin_ranges"] = pr
    return s


def qe(row, w, suffix, pd):
    T = table(row)
    src = ["rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_wo2.sv", "rtl/hbm_accel/index/ot_hbm_idx_score_leaf_c1.sv",
           "rtl/hdc/v41x/ot_hbm_idx_chunk_rt_l.sv", "rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv",
           "rtl/hdc/v41x/ot_hbm_idx_owned_native.sv"] + COMMON_SRC
    s = base(f"hidx_score_qe4{suffix}", "ot_hbm_idx_score_qe_r4", "IDX quarter scorer E glue tile r4 (wires-only quarter wo2, x4 per die)",
             src, w, 2 * row, pd, 32, qs_benches(),
             "L2H-IDXSCORE 2026-10-19 successor of hidx_score_qe_1018 (r3 FAIL: ONE root over 1.12 mm, TT/FF pin-flop spread "
             "177.7 / 156.8 ps; reset_landing 3; util 16%): row clocks clk_e0 / clk_e1 (die clk_tail[0/1]) beside each row's "
             "E glue, per-row score registers + pins (score0 / score1, the parent re-assembles the flat 306-bit bus), "
             "keep delay as ring buffer, landed reset ot_rst_relay_l, width cut toward 40% util. Same cycles.")
    s["clock_port"] = "clk_e0"; s["clock"] = "multiple_cts_roots"; s["clock_ports"] = ["clk_e0", "clk_e1"]
    s["clock_data_paths"] = "related_same_frequency"; s["clock_relationship"] = REL
    s["clock_entry_domains"] = {
        "core": {"ratio": [1, 1], "ports": ["clk_e0"], "inputs": ["rst_n", "r0_qv", "r0_kv", "r0_aux", "r0_bus"],
                 "outputs": ["score0", "fault"]},
        "r1": {"ratio": [1, 1], "ports": ["clk_e1"], "inputs": ["r1_qv", "r1_kv", "r1_aux", "r1_bus"], "outputs": ["score1"]}}
    s["io_flop_at_pins"] = {"cols": 2, "allow_none": True}
    s["pins"] = {"W": ["clk_e0", "clk_e1", "rst_n"] + [f"r{e}_{n}" for e in (0, 1) for n in ("qv", "kv", "aux", "bus")],
                 "E": ["score0", "fault", "score1"]}
    s["pin_regs"] = {"enable": False, "reason": "outputs score0/score1/fault are registers (as the flat quarter); inputs land in "
                     "the keep ring / tail / meta input stages and the settle/online/fault registers (E glue verbatim)"}
    pr = {}
    for e in (0, 1):
        for n in ("qv", "kv", "aux", "bus"):
            pr[f"r{e}_{n}"] = r(T[n][0] + e * row, T[n][1] + e * row)
    k = T["key"][0]; b = T["bus"][0]
    pr["clk_e0"] = r(k + 150, k + 151.08); pr["rst_n"] = r(k + 160, k + 161.08); pr["clk_e1"] = r(row + k + 150, row + k + 151.08)
    pr["score0"] = r(b - 60, b); pr["fault"] = r(b - 63.24, b - 62.16); pr["score1"] = r(row + b - 60, row + b)
    s["pin_ranges"] = pr
    return s


if __name__ == "__main__":
    row, qw_w, qe_w, suffix = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    lpd = float(sys.argv[5]) if len(sys.argv) > 5 else 0.6
    for s in (leaf(row, suffix, lpd), qw(row, qw_w, suffix + f"_w{int(round(qw_w * 10))}", 0.55),
              qe(row, qe_w, suffix + f"_w{int(round(qe_w * 10))}", 0.55)):
        d = ROOT / "physical/ref_tile" / s["name"]; d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(d)
