# FAM-S81-COL-H9R0-R4 handoff (successor of FAM-S81-COL-H9R0-R3; started 11-21 12:2x PST)
Family: S81 col_h9_r0_p1..p6. History: lanes/handoff/FAM-S81-COL-H9R0-R3.md (cause census, J7 inputs), -R2, base.
Lane dir intel2 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0-r4 (logs). R3 lane dirs still used for R3 kits.

## Findings 11-21 (R4)
- J6 STAGGER kit (cl0045af7b pva2793873, epyc8, private/FAM-S81-COL-H9R0-R3/..._1121120240): placed; OT_RELAY_MID_STAGGER sets 12, moved 19, kept 5.
  All 4 xo chains (xo0..xo3) KEPT on the line: J6 xo chains are 2 stations, hop ~541-597 um > 405 STAGGER hop check -> no offset passes.
  So this kit does NOT test fix 3 (ROM e2 strip). I cancelled its geom (rc 143, my ot-run --cancel ~13:2x); COORD 13:2x ordered it resumed to CTS/GRT anyway:
  ot-run unit oth-ubuntu-2597693-1795296458 on epyc8 (client pid 859642 intel2, log fam-s81-col-h9r0-r4/stag_j6_route.log), GOAL=route, resumed at CTS.
- Real STAGGER proof = same type on J7c seg405 base (offsets ~11/34 um). private-spec --host epyc10 refused (DRAINING); candJ7c only on epyc10. Command ready:
  kit_wave.py private-spec s81 col_h9_r0_p2__t1__cl0045af7b__pva2793873 --plan candJ7c/.../plan_h2_2249.json --tree candJ7c --bind-out candJ7c/.../native_bind/out --src-manifest off --host epyc10 --rt 404887a342b0 --ab OT_RELAY_MID_STAGGER=1 --why ... --lane FAM-S81-COL-H9R0-R4
- J7 wave rt 8d1cff9b1bb6 + tree tools a9ed808a98d5 LACK STAGGER (c54a7596fc); rt 404887a342b0 has it.
- Rep J7c keep proof (run-item pid 1553808 intel2, R3 spec _1121121601): stuck at kit_rtl since 12:16, ot-run HOLD epyc10 disk-ETA / DRAIN (105 GB). Waiter armed.
## 18:3x update (after weekly limit / Codex 14:23-18:1x)
- J6 STAGGER kit DIED at GRT: GRT-0116, 5,401 overflow (4,330 M8). Not a STAGGER test (xo kept). Done.
- Rep J7c keep run-item ENDED kit_rtl rc 78 (epyc10 69 GB < floor 100). Not built.
- Lever 4 (xo depth) is already in J7c/a6771d: j7_h9r0_classes.json xo 3 vs 2 stations. No J8 depth rows needed; need placed J7-form proof.
- BLOCKER to COORD: all J7 trees only on epyc10 (drained); private-spec refuses epyc10/7/8, accepts intel2 only. Asked: (a) admit one J7 rep on epyc10 or (b) copy one J7 tree to intel2.
- LIVE: J6 keep proof on intel2: spec private_specs/FAM-S81-COL-H9R0-R4/s81_col_h9_r0_p2__t1__cl0045af7b__pva2793873_1121182823, run-item pid 3418257 intel2, log fam-s81-col-h9r0-r4/keep_j6_runitem.log. A/B OT_KEEP_WIRES = wave list + ot_s81_rly:rq. Read: rq flop count in 1_2_yosys.v (expect 8 xo rq, was 1 driving 2,210), then route, TT recovery class at final 5_1_grt.odb.
- J7c STAGGER spec retry loop (intel2 bash fam-s81-col-h9r0-r4/tmp/stagj7.sh) retries every 15 min until epyc10 admits.
- item_env caution: OT_KEEP_WIRES must be the full wave list + ot_s81_rly:rq (A/B replaces the list).
## Done
- R3 dead specs _1121120604/_1121120930 ot-deleted (hub); 8K kit stubs on epyc10 guard-protected, left.
## Next
1. Read J6 STAGGER post-hook CTS + final 5_1_grt.odb TT, then DRT count/strip.
2. Rep keep proof: when kit_rtl admits, place -> route; read TT ends (xo RESETN class should vanish). Hand OT_KEEP_WIRES ot_s81_rly:rq (or RTL (* keep *) on g_rsreg rq in rtl/dsrom_sys/s81_glue/ot_s81_rly.sv) to S81-J6-ASSEMBLY-R4 + FLOW-OPS-1300 (fleet no-merge default; do not do twice).
3. When epyc10 admits: launch J7c STAGGER spec above.
4. On published J7d (u_cf view + guarded ROM-input stage): signable rep from the manifest tree.

## 11-22 03:05 update
- Kit C (J8 row proof only, src-manifest off): j8c_tree, spec s81_col_h9_r0_p2__t1__cl9f71e63d__pva4376595_1122022216 (env_only OT_GRT_CONG_ITERS added; orig spec tmp/spec_orig_1122022216.json), run-item pid 2263742, log kitc_runitem.log.
- 7 SEALED counting reps (COORD 03:xx): tmp/sealed_launch.sh ITEM HOST; specs *_11220301..0304; logs sealed_<item>_runitem.log. pids p6 2641923, p1 2669012, p2/cl9f 2688258, p2/cl0045 2711310, p3/cl8ce 2723998, p3/cl0cd 2740564, p3/cl31d 2751065.
- Old p3/p6 rt404887 kits (pids 55162/43388) = row proofs only.
- j8s_tree rebind cancelled; j8s_tree partial copy on epyc8 is dead (ot-delete when convenient).
- Due: combined p1-p6 J8 col row set to S81-J6-ASSEMBLY-R5 by 14:00 (cut 16:00).

## 11-22 17:3x update (after the 11:1x-17:2x limit)
- J8 rows posted late to R5 (3044937458): R1 p1 macro moves (live in J7), R2 family env keep+STAGGER+RE+GRT50. Not ready: kit C seat-fix rebind (TT -158.79), p3 cl31d0dc4b (-207.9 est), p2 cl0045af7b (-92.8), p1 GRT pending.
- Live sealed: p6 2641923 route, p1 2669012 GRT (intel1), p2 cl0045 2711310 route, p3 cl0cd 2740564 route, fresh p2 434285 geom (event 18a2688b741), fresh p3 455182 place.
- Race copies (old placed kits, run_kit route epyc8): p2 cl9f 526974, p3 cl8ce 526975; detailed route. First copy to sign off wins; cancel the other by exact unit.
- Ended: kit C (FAIL_POSTCTS TT), sealed p3 cl31d0dc4b (FAIL_POSTCTS TT), old row proofs p3/p6 (rc 21).

## 11-22 20:5x PST J9 rows S81-HC-INPUT-REACH (COORD 21:3x approved)
- Rows: intel2 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0-r4/j9/rows_COL-H9R0-HC-INPUT-REACH_J8.json (01d8c337986a, 468 ops, 42 types) on J8 f65f62779bef; PRE PASS 0 on J8 tree (plan 178c3c611c3a); generator h9r0_j9_rows.py + jpatch.py next to it. Handed to R5 (post f8100c35).
- (a) bs0 i_x0/i_x1 D bump (all p1/p2/p3/p6); (c) p2 t2 aligned group D=1; (b) env OT_KEEP_WIRES += ot_dp_dly:r (opt_merge folded per-half ROM input stations; yosys test 8->24 flops).
- Probe: OT_PROBE_THROUGH=1 sealed p2 pva4376595 with (b), rt 345ac19b04b3, epyc8, run-item pid 2055609 (intel2), log probe_*_runitem.log. Check: u_y_xd_u_r0_u_e1_u_w_* cells > 0 in geom.tsv; e1 u_w TT.
- Open: t0 -> xa/xb_1_bs0_0 branch-copy legs 650-760 (p3/p6), p1 t2 503, p3/p6 xb_2->t2 448 (existing rows).
- Waiter b7y6yb3gc: digest on 2641923 2669012 2711310 2740564 434285 455182 526975 2055609.

## 11-22 21:2x PST COORD 23:0x actions
- Rows v2 25172302ded3 (804 ops; bs0 chain FIRM seats + D=3, t2 p2) in j9/; PRE PASS 0 plan 8798460c88ee.
- item_env col_h9_r0_* OT_KEEP_WIRES=ot_dp_dly:r (2dadd51b4aa9). Classes posted: S81-HC-INPUT-REACH, S81-DUPSTN-MERGE.
- Private bind: epyc10 fam-s81-col-h9r0-r4/j9bind.sh -> j9tree (fork of s81-j6-r5/j8_cut_tree), out j9tree/physical/die_plan/s81/plan_of_record/native_bind/h9r0_j9_out, gate logs j9gate/. ot-run client 2381456 (intel2), log j9bind.otrun.log.
- Chain tmp/j9_chain.sh (intel2) waits for 2381456, then runs tmp/j9_launch.sh p2 pva4376595 on epyc10 -> log j9_chain.log / j9_*_runitem.log. If BIND_NOT_DONE, read j9gate/*.log.
