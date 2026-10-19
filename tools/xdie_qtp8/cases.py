#!/usr/bin/env python3
"""TOKEN-XDIE-QTP8 (owner 10-18): Qwen ROM TP8 array-collective vehicle = the composed 8-die bench
tools/qwen_coll_tp8_static_links_bench.py on the dv2f14 die RTL (claude/q-die13-1018 lineage): per die the die-bound master
qfd_collective_static_io_production (ot_coll_tp8_static + linkcal + static CDC + UCIe six_five gearbox + 3 SerDes codecs),
4 packages x 2 dies (UCIe pair in a package, SerDes full mesh between the 4 packages: port j of package P -> package
(P+1+j)%4, no switch), only the PHY frame pipes modelled (UCIe 20 core edges incl. registered pin, SerDes 339).

Die lanes (dv2f14bf GEN fwd_lanes.json, results/arch/qwen_split_compute_1014/landfix_q_1018/dv2f14bf_gen):
  io_collective <-> io_serdes   (port 0): tx/txv/rx/rxv E 2      -> ET0 = ER0 = 2
  io_collective <-> io_serdes_1 (port 1): no lane (abutting)     -> 0
  io_collective <-> io_serdes_2 (port 2): tx E 5, txv E 6 (!), rx/rxv E 5 -> ET2 = ER2 = 5, valid skew 1
  UCIe: no lane.  These lanes are NOT in the compiled collective calendar (LS 376 counts only the internal RU 5 / RS2 5
  relays), so the as-built die is expected to FAIL its static schedule; the opt-in parent LX0..2 absorbs them.
Each case = one bench invocation (one Verilator build).  `cases.py list` prints names, `cases.py args NAME` the bench args.
"""
import shlex
import sys

BASE = ["--production", "--six-five", "--relays", "5", "0", "0", "5", "--latu", "53"]
DIE = ["--lanes", "2", "0", "5", "2", "0", "5"]
LX = ["--lx", "7", "0", "7"]           # face S0: peer port 2 ET 5 + own ER0 2; S1: 0; S2: peer port 0 ET 2 + own ER2 5
LS_SWEEP = list(range(380, 391))
LSX = "390"

CASES = {
    # 10-15 s4_fanout reproduction on the current RTL + Verilator 5.050 (no die lanes; production calendar LS 376)
    "base_ls376": BASE + ["--lats", "376"],
    "base_ls376_tok": BASE + ["--lats", "376", "--tok-reg", "1"],
    # as-built dv2f14 die lanes, calendar unchanged: must FAIL (witness of the unscheduled lanes)
    "asbuilt_ls376": BASE + ["--lats", "376", "--valid-skew", "1", "--expect-fail"] + DIE,
    "asbuilt_noskew_ls376": BASE + ["--lats", "376", "--expect-fail"] + DIE,
}
for ls in LS_SWEEP:   # lanes absorbed by the calendar (opt-in LX) + hardened face form: the minimum passing LS is the price
    CASES[f"lx_ls{ls}"] = BASE + ["--lats", str(ls), "--tok-reg", "1"] + DIE + LX
CASES.update({
    # negatives/functional variants at a passing recompiled point LSX = 390 (top of the sweep; the price is the sweep minimum)
    "lx_skew": BASE + ["--lats", "LSX", "--tok-reg", "1", "--valid-skew", "1", "--expect-fail"] + DIE + LX,
    "lx_mut_rank": BASE + ["--lats", "LSX", "--tok-reg", "1", "--mutant-define", "OT_TP8S_MUT_RANK", "--only", "qwen_ar_256w|qwen_layer_2x256w$", "--expect-fail"] + DIE + LX,
    "lx_mut_gather": BASE + ["--lats", "LSX", "--tok-reg", "1", "--mutant-define", "OT_TP8S_MUT_GATHER", "--only", "argmax", "--expect-fail"] + DIE + LX,
    "lx_mut_rxearly": BASE + ["--lats", "LSX", "--tok-reg", "1", "--mutant-define", "OT_LCAL_MUT_RX_EARLY", "--expect-fail"] + DIE + LX,
    "lx_mut_peerage": BASE + ["--lats", "LSX", "--tok-reg", "1", "--mutant-define", "OT_LCAL_MUT_PEER_AGE", "--expect-fail"] + DIE + LX,
    "lx_seqsu": BASE + ["--lats", "LSX", "--tok-reg", "1", "--seqsu"] + DIE + LX,
    "lx_seqsu_tokmut": BASE + ["--lats", "LSX", "--tok-reg", "1", "--seqsu", "--plusarg", "TOKMUT=1", "--expect-fail"] + DIE + LX,
    "lx_fdiphase3": BASE + ["--lats", "LSX", "--tok-reg", "1", "--fdi-phase", "3"] + DIE + LX,
})

# batch 2 (10-18 08:40, after batch 1: LS 380..390 all PASS -> sweep lower; FDI phase 3 FAILED with lanes+LX+TOK_REG=1 while
# 10-15 phases 0..5 passed at LS 376 without them -> isolate; unit fault cases; RANK re-run with a quoted --only)
for ls in range(370, 380):
    CASES[f"lx_ls{ls}"] = BASE + ["--lats", str(ls), "--tok-reg", "1"] + DIE + LX
for ph in (1, 2, 3, 4, 5):
    CASES[f"base_phase{ph}"] = BASE + ["--lats", "376", "--fdi-phase", str(ph)]
    CASES[f"base_tok_phase{ph}"] = BASE + ["--lats", "376", "--tok-reg", "1", "--fdi-phase", str(ph)]
    CASES[f"lx_tok0_phase{ph}"] = BASE + ["--lats", "LSX"] + DIE + LX + ["--fdi-phase", str(ph)]
CASES["lx_unit"] = ["--six-five", "--relays", "5", "0", "0", "5", "--latu", "53", "--lats", "LSX", "--tok-reg", "1"] + DIE + LX
CASES["base_unit"] = ["--six-five", "--relays", "5", "0", "0", "5", "--latu", "53", "--lats", "376"]

# batch 3 (10-18 08:45): FDI phases 1..5 FAILED even on the baseline (no lanes, TOK_REG 0) on the current RTL, while the 10-15
# r10-gearbox runs passed: the r11..r15 gearbox adds NEGEDGE half-cycle registers and the 1-tick pulse harness is not a clock
# for them.  d50_* = the same cases on 50 %-duty clocks (--duty50).  REC = configuration of record: dv2f14 lanes + LX 7/0/7 +
# hardened face (TOK_REG 1) at the production calendar LS 376.
D50 = ["--duty50"]
REC = BASE + D50 + ["--tok-reg", "1"] + DIE + LX
CASES.update({
    "d50_base_ls376": BASE + D50 + ["--lats", "376"],
    "d50_asbuilt_ls376": BASE + D50 + ["--lats", "376", "--expect-fail"] + DIE,
    "d50_rec_ls376": REC + ["--lats", "376"],
    "d50_rec_ls374": REC + ["--lats", "374"],
    "d50_rec_ls373": REC + ["--lats", "373"],
    "d50_rec_skew": REC + ["--lats", "376", "--valid-skew", "1", "--expect-fail"],
    "d50_rec_seqsu": REC + ["--lats", "376", "--seqsu"],
    "d50_rec_seqsu_tokmut": REC + ["--lats", "376", "--seqsu", "--plusarg", "TOKMUT=1", "--expect-fail"],
    "d50_rec_mut_rank": REC + ["--lats", "376", "--mutant-define", "OT_TP8S_MUT_RANK", "--only", "qwen_ar_256w|qwen_layer_2x256w$", "--expect-fail"],
    "d50_rec_mut_gather": REC + ["--lats", "376", "--mutant-define", "OT_TP8S_MUT_GATHER", "--only", "argmax", "--expect-fail"],
    "d50_rec_mut_rxearly": REC + ["--lats", "376", "--mutant-define", "OT_LCAL_MUT_RX_EARLY", "--expect-fail"],
    "d50_rec_mut_peerage": REC + ["--lats", "376", "--mutant-define", "OT_LCAL_MUT_PEER_AGE", "--expect-fail"],
    "d50_rec_unit": ["--six-five", "--relays", "5", "0", "0", "5", "--latu", "53", "--lats", "376", "--tok-reg", "1"] + D50 + DIE + LX,
})
for ph in (1, 2, 3, 4, 5):
    CASES[f"d50_base_phase{ph}"] = BASE + D50 + ["--lats", "376", "--fdi-phase", str(ph)]
    CASES[f"d50_rec_phase{ph}"] = REC + ["--lats", "376", "--fdi-phase", str(ph)]

# Q-COLLCAL 10-18: the REAL forwarded lanes (rtl/qwen_split/qfd_fwd_lane.sv, N / K straps per port and direction) of the
# next Qwen compute GEN in place of the fixed delays, and the calendar LX0..2 the GEN emits (case/coll_lane_latency.json;
# the bench takes LX from it).  Inputs results/rtl/q_collcal_1018/gen_*/coll_lane_latency.json = tools/qwen_split/
# lane_groups.py emit on the dv2f14bhd GEN lanes (frames unchanged by the bus-group fix): gen_bhd (estimate E, LX 10/0/9),
# gen_bhd_lp (+ the dv2f14bg land plan bhd/final.sh takes, LX 11/0/10), gen_bhd_asbuilt (the netlist as generated today).
RLB = BASE + D50 + ["--tok-reg", "1"]
QC = "results/rtl/q_collcal_1018"
for g_ in ("gen_bhd", "gen_bhd_lp"):
    J_ = ["--real-lanes", f"{QC}/{g_}/coll_lane_latency.json"]
    CASES.update({
        f"rl_{g_}_ls376": RLB + J_ + ["--lats", "376"],
        f"rl_{g_}_ls376_tok0": BASE + D50 + J_ + ["--lats", "376"],
        f"rl_{g_}_seqsu": RLB + J_ + ["--lats", "376", "--seqsu"],
        f"rl_{g_}_unit": ["--six-five", "--relays", "5", "0", "0", "5", "--latu", "53", "--lats", "376", "--tok-reg", "1"] + D50 + J_,
        # negatives: the qtp8 fixed-delay calendar (lane = E, not E + 1), no calendar LX, the as-built valid K (skew),
        # the land plan's residual K (E_sta instead of the total E), the collective mutants
        f"rl_{g_}_lx707": RLB + J_ + ["--lats", "376", "--lx", "7", "0", "7", "--expect-fail"],
        f"rl_{g_}_lx000": RLB + J_ + ["--lats", "376", "--lx", "0", "0", "0", "--expect-fail"],
        f"rl_{g_}_mut_rank": RLB + J_ + ["--lats", "376", "--mutant-define", "OT_TP8S_MUT_RANK", "--only", "qwen_ar_256w|qwen_layer_2x256w$", "--expect-fail"],
        f"rl_{g_}_mut_rxearly": RLB + J_ + ["--lats", "376", "--mutant-define", "OT_LCAL_MUT_RX_EARLY", "--expect-fail"],
        f"rl_{g_}_seqsu_tokmut": RLB + J_ + ["--lats", "376", "--seqsu", "--plusarg", "TOKMUT=1", "--expect-fail"],
    })
    for ls_ in (377, 378, 380):
        CASES[f"rl_{g_}_ls{ls_}"] = RLB + J_ + ["--lats", str(ls_)]
CASES["rl_gen_bhd_skew"] = RLB + ["--real-lanes", f"{QC}/gen_bhd/coll_lane_latency.json", "--real-lanes-override", "KTV2=6", "--lats", "376", "--expect-fail"]
CASES["rl_gen_bhd_lp_residualk"] = RLB + ["--real-lanes", f"{QC}/gen_bhd_lp/coll_lane_latency.json", "--real-lanes-override",
                                          "KT2=2", "KTV2=3", "KR2=3", "KRV2=2", "--lats", "376", "--expect-fail"]
CASES["rl_asbuilt_lx000"] = RLB + ["--real-lanes", f"{QC}/gen_bhd_asbuilt/coll_lane_latency.json", "--lx", "0", "0", "0", "--lats", "376", "--expect-fail"]

if __name__ == "__main__":
    if sys.argv[1] == "list":
        print("\n".join(CASES))
    else:
        print(shlex.join(LSX if x == "LSX" else x for x in CASES[sys.argv[2]]))   # quoted: --only regexes carry '|' / '$'
