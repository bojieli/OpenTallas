# QW-RSTRLY 10-20: reset-lane relay kits for the g5r2b release die (dv2f20g5r2b) frames without a view

The die binds 3 one-bit forwarded reset-lane masters (4 instances) that had no closed view
(QW-TRIAGE "Truly open" 2; class table results/arch/qw_fwdlane_1020/class_table_g5r2b.json on claude/qw-fwdlane-merge-1020):

| die master | inst | class (orient) | class kit (main route) | exact kit (parallel fallback) |
|---|---|---|---|---|
| qfd_rlyr_1_ES_65x30  | 2 | rlyr_1_EN (MX)  | qfwd_rlyr_1_en_65x30  | qfwd_rlyr_1_es_65x30 (GEN pins g5pins_le600) |
| qfd_rlyrl_1_NE_65x30 | 1 | rlyrl_1_NE (R0) | qfwd_rlyrl_1_ne_65x30 (also exact) | - |
| qfd_rlyrl_1_NW_65x30 | 1 | rlyrl_1_NE (MY) | qfwd_rlyrl_1_ne_65x30 | qfwd_rlyrl_1_nw_65x30 (GEN pins) |

No existing closed class covers them: the legal orientations (R0/MX/MY/R180) of the closed rlyr_1_NE / rlyrl_1_EN
classes give in-face/out-face NE,NW,SE,SW resp. EN,ES,WN,WS -- in-E/out-S (ES station) and in-N/out-E,W (NE/NW landing)
are not among them (in/out swap needs a transpose, illegal for horizontal rows). So kits, not a GEN remap.
Class kits need GEN class emission (or the die_element_table alias); the exact kits bind as-is. Bind whichever closes first.

Kits: tools/qwen_split/gen_fwd_lane_kits.py (same generator/RTL as the closed Q-H16C reset-lane kits qfwd_rlyr_1_ne / rlyrl_1_en),
RTL rtl/qwen_split/qfd_fwd_lane.sv ot_qfd_rlane_st / ot_qfd_rlane_land, wrappers physical/qwen_fwd_lane/qfd_fwd_lane_masters.sv (+4 modules, add-only).
Pins: class_pins/ (class rep faces), exact_pins/ (GEN-assigned).

Benches (Verilator 5.050, fleet ot-epyc5, bench/run_bench.sh + run_bench_exact.sh, tools/qwen_split/bench_fwd_rst_lane.sh):
every kit PASS 0 errors / 3354 checks; mutants: station full-cycle forward FAIL 1238/3354, landing double register (land2) FAIL 1198/3354.
Witnesses bench/<kit>_{pass,full,land2}.log.

## Safe-design checklist / pre-gate native census (by construction, 1-bit frame; the gate's synthesis confirms)
1 Pins: lane frame = exactly one flop per bit between its pins (pin regs opted out, owner rule 19:50, as every closed qfwd kit);
  these frames ARE the reset lane: the landing re-registers the level on the receiving root, the receiving block's reset_landing adds its 2 stages. PASS
2 Reach: frame 64.8 x 30.2 um, all wires << 405 um. PASS
3 Fanout: station 1 flop + 1 kept inverter (ck_o), landing 1 flop; max driver load 1 (<= 32). PASS
4 Depth: no logic between pin and flop; no comb in->out. PASS
5 Storage: 1 bit, no arrays. PASS
6 Floorplan: no macros; exact die frame (closed sibling outline); full std-cell band; aspect 2.1:1 = the die frame (waived: frame fixed by die). PASS/waived
7 Clock: forwarded half-cycle (station ck_o = ~ckf) / receiving root (landing); io_hold_margin 0.03. PASS
8 Schedule: static, fixed latency from geometry (bench derives L per lane); no added cycle vs the priced lane. PASS
