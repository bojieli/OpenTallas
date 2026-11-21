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
## FABLE-CLOSURE-0600 levers (answered 05:4x, post REPLY FABLE-CLOSURE-0600)
- Lever 3 (pvcc166a6d -131 GRT -> -391 sign-off): net y_x2_2_0.o[347] is unbuffered at GRT and at final (INVx4 -> e1/xb_data + t2_payload/i, HPWL 615 um). The GRT estimate already showed 1.2 ns slew. Repair was skipped (OT_MAXWIRE_POST_SKIP=1 in the J5 spec, so DRV is advisory). The routed wire C is 1.5x the estimate (86 -> 130 fF), so wire delay goes 386 -> 830 ps. Same corner, TT. Evidence: epyc8 fam-s81-col-h10/gap_pvcc166a6d/sta_{grt,final}.log. mkdepth405 ^col_h10_ on J5: 90 rows / 24 types; mkxalign: 24 / 6 (intel1 fam-s81-col-h10/lev3/). The x2_2_0 sink-span (573 um) is NOT covered and needs a RLYBR branch for the t2_payload sink.
- Lever 6: u_cf faces are inverted relative to their feeders. Row = u_r0.u_cf R0 -> MX on the 12 r0_p1 + r0_p4 types (precedent col_h9_r0_p2).
- Lever 1: name rule as-built = netlist minus u_bound.u_ (r0: u_r0_u_eN_u_w; r1/r2: u_eN_u_w). R3 + J6-R3 generate the RDX rows.
- J7 rows owner is now S81-J6-ASSEMBLY-R3 (J6-R2 stood down).
## Rep plan
pv1619ecc6 J5 DRT at 13 violations; FABLE read TT after repair -46.8 (u_s13/q6, RDX class). If the sign-off is within ~10 ps of -42 on that path -> final near-miss ECO. cld01bb4ae (-32.0) is the alternate rep.
## STAND-DOWN 11-21 ~06:0x PST (context limit) -> successor FAM-S81-COL-H10-R2
COORD 05:5x: OT_MAXWIRE_POST_SKIP drop -> S81-J6-ASSEMBLY-R3 (J7); name rule -> FABLE-FIX-S81-COLROM; final ECO on pv1619ecc6 OK if near -46.8.
### Live units / processes (all mine unless noted)
- Strict bind2 + LATCHECK: ot-run unit oth-ubuntu-1874109-1795265321 on intel1 (key-cardinal); log intel1 /srv/opentallas-scratch2/claude/fam-s81-col-h10/bind2_otrun.log (+ bind2.log, latcheck2.*). Pass = BIND_RC=0 and LATCHECK_RC=0. NOTE: bind.sh's failure branch greps bind.log (stale name); read bind2.log on failure.
- Hub chain intel2: nohup bash /srv/opentallas-scratch2/claude/fam-s81-col-h10/chain.sh (log chain.log there). It waits for bind2, then runs kit_wave.py run-item wave/spec.json (rt 3553de9af815, J5 attempt_4 spec, src_manifest off, hosts intel1+epyc8), then prints RESULT. The work dir is wave/root/items/col_h10_r2__t1__cl99efd374__pv1619ecc6/attempt_1. Route afterwards is NOT automatic: run `bash <W>/gen/run_kit.sh <W>/gen/<T> route 48 8` via ot-run on the kit host (pattern of autopilot jobs).
- Baseline rep (autopilot, not mine): col_h10_r2 pv1619ecc6 J5 route job ap 4dbbbc4cb44f (intel1 ot-jobs/col_h10_r2__t1__cl99efd374__pv1619ecc6-route-key-cardinal-3781851-*), DRT at 13 violations at 05:4x. Alt rep cld01bb4ae ap 0c4abfb40abd (intel1), -32.0 after repair.
- Copies for the gap study: epyc8 /srv/opentallas-scratch2/claude/fam-s81-col-h10/gap_pvcc166a6d (~2.6 GB, delete via ot-delete when done). Partial cancelled bind dir intel1 fam-s81-col-h10/bind/ (delete via ot-delete).
### Re-arm waiters
- `until ssh intel2 grep -q AP_RC ~/coord/autopilot/jobs/4dbbbc4cb44f/a1.log; do sleep 240; done` (same for 0c4abfb40abd); then read sign-off: <ot-job work>/signoff/tt/ep_tt.tsv + signoff.json.
- `until ssh intel1 grep -q "^ot-run: RAN" /srv/opentallas-scratch2/claude/fam-s81-col-h10/bind2_otrun.log; do sleep 240; done`
- `until ssh intel2 grep -qE "CHAIN_DONE|BIND_FAIL" /srv/opentallas-scratch2/claude/fam-s81-col-h10/chain.log; do sleep 300; done`
### Successor TODO (in order)
1. pv1619ecc6 sign-off: if TT is within ~10 ps of -42 on the u_s13/q6 (RDX) path, apply a final near-miss ECO (COORD-approved) and re-sign. Otherwise use cld01bb4ae (-32) as the rep. Any J5 sign-off counts.
2. WRITE the t2_payload branch-copy row (COORD asked; not written yet). On col_h10_r0_p4 (all 6 types, u_r0 prefix), relay u_r0_u_y_x2_2_0 has its last stage serving u_r0_u_e1.xb_data (623,760) and u_r0_u_t2_payload.i (1040,916), 573 um apart, and no relay_depth row exists. Add a relay_branch entry in the S81-RLYBR-1 format (see the existing u_r0_u_y_xa_1_0 entry in the same type: copies [{name u_r0_u_y_x2_2_t2p_0, sinks [u_r0_u_t2_payload], D 1, path_um}] + kept [u_r0_u_e1]), or a +1 sink stage at u_r0_u_t2_payload.i with its site at ~(1000,880). Check the same span on r0_p1 (u_y_x2_3_0) and on col_h9_r0. Prove it with strict bind + LATCHECK, then add it to the J7 rows for S81-J6-ASSEMBLY-R3.
3. Proof A result: place/geom, then private route, A/B against the J5 baseline (ROM-PVAL e_r rows).
4. Lever 6 row: u_r0.u_cf R0 -> MX on 12 col_h10_r0_p1/p4 types (regenerate the u_cf-pin station sites), to J7.
