# TYPE-GUNIT-L1F handoff

## 2026-11-14 00:37 PST S81-CORES-2 -> TYPE-GUNIT-L1F hand-over (COORD: one lane per problem)
- Core dsdv_gunit_l1f_bf, one of the last 2 S81 counted cores (S81 at 62/64 after the T51 W re-sign).
- Live: GF5 F2 finish on epyc8, unit oth-ubuntu-2649106-1794640208. Kit /srv/opentallas-scratch2/claude/s81-cores-2/gunit_f2/dsdv_gunit_l1f_bf_gf5f2; log intel2 ~/s81-cores-2-logs/gunit_f2_finish.otrun.log. I no longer have a waiter on it; it is yours.
- F2 vs F1: gf5_locality.tcl drops the sc[] and g_e[] owner lines, and the bank x pitch is 112.32 (was 43.2). The F1 original is gf5_locality.tcl.F1, and F1's stage 3/4/5 outputs are in ../f1_stage_outputs.
- F1 history: GRT TERMINAL exit 21 (OT_GRT_STOP congested, extra iteration 15/30, W cachewrite buses).
- A0 and A1 are signed off with the GF5 recipe: A1 at epyc8 /srv/opentallas-scratch2/claude/s81-cores-2/gunit_a1/dsdv_gunit_l1f_ba1_gf5bias_sort2cmp. ba0 and ba1 are already credited via gf3.
- To count: judge under R-MINIMAL (DRC0, TT >= -42 ps, internal hold >= 0, bind/LATCHECK), then add an AUTO-RESIGN.tsv row with the build commit; the autopilot re-signs it (as it did T51 W at 23:38).
- Background: lanes/S81-CORES-2.md (RESULT 11-13 23:11 and the earlier gunit entries).
