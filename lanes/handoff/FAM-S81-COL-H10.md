# FAM-S81-COL-H10 handoff (split from FAM-S81-COL-R3; started 11-21 04:2x PST; updated 05:0x)
Family: S81 col_h10_r1, col_h10_r2, col_h10_r0_p1, col_h10_r0_p4 (36 unsigned types). R3 keeps col_h9_r1/r2 + shared J7 col relay/ft rows (its proof C on col_h10_r0_p1 pvb095fa2f = relay_mid rows; I take its result, no duplicate). H9R0 has col_h9_r0_*.
## Census (J5 event 224567138ab, plan 913a7026b922; J6 dc92652f0d5 now current, J6 col_h10 types == J5 byte-for-byte except r0_p1 pvb095fa2f + 3 clock diffs)
Live J5 route jobs (sealed ot-jobs on intel1 key-cardinal unless noted), GRT TT wns:
- col_h10_r2__t1__cl99efd374__pv1619ecc6 (ap 4dbbbc4cb44f): GRT TT -56.54, DRT iter 3 ~8k viol. REPRESENTATIVE (baseline A).
- col_h10_r0_p4__t1__pv07945c1e (2a3115c4eca7): GRT -64.53 (FF rpt), DRT iter 1.
- col_h10_r1__t1__cl95b37463__pv0713a75a (900d02e58e5b): GRT -127.06, DRT.
- col_h10_r1__t1__cld01bb4ae (0c4abfb40abd): GRT TT -137.90, DRT.
- col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f (b2d76f42cf4b): in GRT, CTS post-hook setup -68.5.
- col_h10_r2 cl1f5d6c2a pv418d3dc0 (intel1) + r1 pva3a8bfd1 (epyc2): CTS.
## Finding: ROM-PVAL class is the family's setup wall
Worst TT path on every ROM-bank col_h10 type = falling-edge ROM elem u_eK.u_w/u_e pval (clk->q ~615 ps) -> dsfd_qbank_N u_bnK e_r0/e_r1, a half cycle over 230-300 um unbuffered (r2 e12->bn12 251 um -56; r1 e8->bn8 ~320 um -138; r0_p4 pv5b623e07 e2->bn2 -85.6 FF / -134.8 TT). Bank sits under one ROM's pval strip, the other ROM is 270 um away. J5 and J6 carry no bn sink rows.
Fix = R2 lever-1 OUTPUT half (ROM-PVAL): relay_depth sink D=1 on bnK e_r0 (u_w pval), e_r1 (u_e pval), e_st (u_w busy), site at ROM pval face +5.32 um. The rows ALREADY EXIST for 216 col types: epyc10 /srv/opentallas-scratch/claude/s81-j6/rows/rom_pval/j6_delta_rom_pval.json (R2, 11-20 23:10, not applied in J6). Inst naming: r1/r2 types use netlist names u_bnK (no u_rN_ prefix), r0 types u_r0_u_bnK. My mkplan_h10.py had u_r2_ prefix = WRONG, discarded (bind cancelled 04:5x). Proof uses the exact delta rows via mkplan_h10b.py.
## Known items
- col_h10_r0_p4__t1__pv5b623e07 "FAILED hold after CTS" is a stale label: last attempt_11 (ap f2f355a1cf36, AP_RC=6) GRT hold was repaired to +30 (guard); it failed TT setup -134.8 (TT repair restored, worse) = ROM-PVAL e2->bn2. Hold is not the blocker; fix = ROM-PVAL rows (+ R3 relay rows for r0). No ECO.
- col_h10_r1 pv1a6ec9c2 (GRT-0116 M8 overflow 4263, route FLOW -> J7 south-strip rows) and pv86f5e3b9 (place PLAN; ideal-TT CTS-only diag post-hook setup -109) = R3 deliberate holds, kept; both are r1 ROM-bank types too.
## Running (mine)
- Proof A: tree intel1 fam-s81-col-h10/src1 (J5 src + rt f3db2d0e628f tools, plan 321f4e3369c3 = J5 + exact j6_delta_rom_pval rows for r2 pv1619ecc6 + r1 cld01bb4ae, 24 rows). Strict bind + LATCHECK via ot-run intel1 (bind2_otrun.log, out bind2/; bind/ is a cancelled partial, delete via ot-delete). Hub chain intel2 fam-s81-col-h10/chain.sh -> kit_wave run-item wave/spec.json (= J5 attempt_4 spec, src_manifest off, hosts intel1+epyc8) to place+geom. Then route privately, A/B against live J5 pv1619ecc6.
## Next
1. bind/LAT result; place/geom; route+signoff A vs B.
2. If B signs: rows for every ROM-bank col_h10 type (mkplan_h10.py) as J7 rows -> S81-J6-ASSEMBLY-R2; rebuild from src_manifest tree for export.
