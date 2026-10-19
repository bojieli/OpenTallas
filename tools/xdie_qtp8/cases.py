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

# Q-COLLCAL-RL 10-18 (Q.STA.GEN.6 bench): the FIRST GEN that ran the Q-COLLCAL code = netlist-only compute GEN dv2f14bq
# (claude/qlb-gen-1018 @9634b2b0d; ot-epyc4 qlb-gen-1018/dv2f14bq/out/case/coll_lane_latency.json copied, LX 10/0/9,
# port 2 K tx/txv 6/6 rx/rxv 5/5).  PASS = as built at LS 376; negatives = the qtp8 fixed-delay calendar LX 7/0/7 and a
# port-2 TX valid K one off its data K (KTV2=7; this GEN already has KTV2=6 = KT2, so the bhd KTV2=6 mutant is as built here).
QR = "results/rtl/qcollcal_rl_1018/gen_dv2f14bq/coll_lane_latency.json"
CASES.update({
    "rl_dv2f14bq_ls376": RLB + ["--real-lanes", QR, "--lats", "376"],
    "rl_dv2f14bq_lx707": RLB + ["--real-lanes", QR, "--lats", "376", "--lx", "7", "0", "7", "--expect-fail"],
    "rl_dv2f14bq_ktv2skew": RLB + ["--real-lanes", QR, "--real-lanes-override", "KTV2=7", "--lats", "376", "--expect-fail"],
})

# Q-COLLCAL-RL batch 2: rl_dv2f14bq_ls376 FAILED (mismatches 0, every die cdc bit 11 = face f2 = SerDes port 0 RX xfifo
# r_fault; port 2 face clean) -> the GEN LX0 10 is off for port 0: sweep LX0 with LX1/LX2 as emitted (0 / 9)
for lx0_ in (8, 9, 11, 12):
    CASES[f"rl_dv2f14bq_lx0_{lx0_}"] = RLB + ["--real-lanes", QR, "--lats", "376", "--lx", str(lx0_), "0", "9"]

# batch 3: LX0 10 is the best point (8/9/11/12 add mismatches + abort); the port 0 RX valid lane is N 2 vs its data lane N 3
# (same K 2) -> diagnostic: equal the valid lane to the data lane (NRV0=3) / the other way (NR0=2)
CASES["rl_dv2f14bq_nrv0_3"] = RLB + ["--real-lanes", QR, "--real-lanes-override", "NRV0=3", "--lats", "376"]
CASES["rl_dv2f14bq_nr0_2"] = RLB + ["--real-lanes", QR, "--real-lanes-override", "NR0=2", "--lats", "376"]
# batch 4: NRV0/NR0 equalised still FAIL (data exact, cdc bit 11 only) -> port 2 TX valid lane N 10 vs data N 8 (K 6/6)
CASES["rl_dv2f14bq_ntv2_8"] = RLB + ["--real-lanes", QR, "--real-lanes-override", "NTV2=8", "--lats", "376"]
CASES["rl_dv2f14bq_nofwd_fixed"] = RLB + ["--real-lanes", QR, "--real-lanes-override", "NTV2=8", "NRV0=3", "--lats", "376"]
# batch 5: lane N equalisation does not clear cdc bit 11 (port 0 RX read fault, data exact) -> does the calendar need LS > 376
for ls_ in (378, 380, 384, 390):
    CASES[f"rl_dv2f14bq_ls{ls_}"] = RLB + ["--real-lanes", QR, "--lats", str(ls_)]
# batch 6: LS 378..390 PASS -> LS 377 bound + the negatives at the passing LS 378 (discriminating witnesses)
CASES["rl_dv2f14bq_ls377"] = RLB + ["--real-lanes", QR, "--lats", "377"]
CASES["rl_dv2f14bq_ls378_lx707"] = RLB + ["--real-lanes", QR, "--lats", "378", "--lx", "7", "0", "7", "--expect-fail"]
CASES["rl_dv2f14bq_ls378_ktv2skew"] = RLB + ["--real-lanes", QR, "--real-lanes-override", "KTV2=7", "--lats", "378", "--expect-fail"]
# batch 7: LS 377 PASS (376 FAIL) = the price on dv2f14bq; negatives at the priced point
CASES["rl_dv2f14bq_ls377_lx707"] = RLB + ["--real-lanes", QR, "--lats", "377", "--lx", "7", "0", "7", "--expect-fail"]
CASES["rl_dv2f14bq_ls377_ktv2skew"] = RLB + ["--real-lanes", QR, "--real-lanes-override", "KTV2=7", "--lats", "377", "--expect-fail"]

# Q-COLLCAL3 10-18 (DRIVE-1800): the calendar is COMPILED from the lanes (--lats cal = tools/qwen_split/lane_groups.
# collective_calendar: LS = max_j KC + KW + 17 + PS + LX_j + RS_j + RS_peer(j); dv2f14bq 377, dv2f14bi 378), not hand-set.
# Per GEN: PASS at cal, FAIL at cal-1 (the compiled value is the minimum), mutants lx707 / KTV2 skew at cal FAIL.
QI = "results/rtl/qcollcal_rl_1018/gen_dv2f14bi/coll_lane_latency.json"
for g_, j_, kv_ in (("dv2f14bq", QR, 7), ("dv2f14bi", QI, 6)):   # kv_ = port 2 TX valid K one off its data K (as built 6 / 7)
    J_ = ["--real-lanes", j_]
    CASES.update({
        f"cal_{g_}": RLB + J_ + ["--lats", "cal"],
        f"cal_{g_}_seqsu": RLB + J_ + ["--lats", "cal", "--seqsu"],
        f"cal_{g_}_minus1": RLB + J_ + ["--lats", "cal-1", "--expect-fail"],
        f"cal_{g_}_lx707": RLB + J_ + ["--lats", "cal", "--lx", "7", "0", "7", "--expect-fail"],
        f"cal_{g_}_ktv2skew": RLB + J_ + ["--real-lanes-override", f"KTV2={kv_}", "--lats", "cal", "--expect-fail"],
        f"cal_{g_}_mut_rxearly": RLB + J_ + ["--lats", "cal", "--mutant-define", "OT_LCAL_MUT_RX_EARLY", "--expect-fail"],
    })

# MU-QWEN 10-18: 4-user compiled calendar on the dv2f14bi collective (LS = calendar 378): every user's all-reduce at its
# compiled cycle (overlapping epochs), the latency user's commands alone (identity), one filler command moved onto the
# previous command's issue window (must FAIL: engine calendar fault), and the RLAT mutant on the MU window (must FAIL).
_MU = ["--mu-cal", "results/rtl/mu_qwen_1018/coll/mu_cal.json"]
_MUB = CASES["cal_dv2f14bi"] + _MU
CASES.update({
    # Current source-bound SAFE profile; retain the old fixture as a diagnostic,
    # with its original positive expectation so a failure remains visible.
    "mu_bi": RLB + ["--real-lanes", "results/rtl/qwen_coll_safe_1019/dv2f18dh2_coll_lane_latency.json",
                    "--safe-face-hard", "--lats", "cal"] + _MU + ["--only", "mu_window($|_ref)"],
    "mu_bi_dv2f14bi_diagnostic": _MUB + ["--only", "mu_window($|_ref)"],
    "mu_bi_neg_overlap": _MUB + ["--only", "mu_window_neg_overlap", "--expect-fail"],
    "mu_bi_mut_rlat": _MUB + ["--only", "^mu_window$", "--mutant-define", "OT_TP8S_MUT_RLAT", "--expect-fail"],
    "mu_bi_mut_rank": _MUB + ["--only", "^mu_window$", "--mutant-define", "OT_TP8S_MUT_RANK", "--expect-fail"],
})


if __name__ == "__main__":
    if sys.argv[1] == "list":
        print("\n".join(CASES))
    else:
        print(shlex.join(LSX if x == "LSX" else x for x in CASES[sys.argv[2]]))   # quoted: --only regexes carry '|' / '$'
