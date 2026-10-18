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

if __name__ == "__main__":
    if sys.argv[1] == "list":
        print("\n".join(CASES))
    else:
        print(" ".join(LSX if x == "LSX" else x for x in CASES[sys.argv[2]]))
