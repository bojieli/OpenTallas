# FAM-S81-COL-R3 handoff - STAND-DOWN 11-21 05:3x PST (context). Successor needed: FAM-S81-COL-R4 (Opus)
Scope: col_h9_r1 + col_h9_r2 (118 types held for J7) + the shared J7 col rows (relay_mid depth, FIT CHAIN, XALIGN; v3 FT and lever-7 still to fold).
Lever 1 (RDX/ROM) -> FABLE-FIX-S81-COLROM. col_h9_r0_* -> FAM-S81-COL-H9R0. col_h10_* -> FAM-S81-COL-H10.
Dir: intel1 /srv/opentallas-scratch2/claude/fam-s81-col-r3 (chains on intel2, same path). The lane clone is deleted; make a fresh one with ot-lane-clone.
## Done
- FIT CHAIN flow fix: main 39d243610bd + schema 87f8bb96ef. Opt-in via budgets.relay_mid_fit_chain or relay_mid_fit_chain_types, or GEN env OT_RELAY_MID_FIT_CHAIN=1.
- relay_mid depth rows (col_h10_r0_p1): mkplan3.py, 10 rows, +15 cycles. Proof C: strict bind PASS and LATCHECK PASS.
- XALIGN cause found and rows made: mkxalign.py IN OUT ROWS gives 96 rows on 42 col types on J5 (xalign_rows_j5.json).
- RDX generator gen_rdx_rows.py: its rows equal the J7 donor. Handed to COLROM.
- OWNERS-SWEEP 5 FAILED rows: holds posted. Prune: 16.4 GB freed.
## Running (all write to files; they survive this lane)
1. Proof C G0: g0_c.otrun.log, g0_c/g0cmp.out (pass = new 0). Then hub chain3.log: run-item to place, then read relay_mid coverage. Owner: FAM-S81-COL-H10.
2. XALIGN gate: bind4_otrun.log (src4 = J5 + XALIGN). When it is green: run g0.sh src4 g0_x (script in dir), then ask TOKEN-1121 to regenerate the L02 col_h9_l4_lp_asb_x_schedule.json from bind4 and confirm e1 x == control. Post the result to S81-J6-ASSEMBLY-R2/R3. For J7: rerun mkxalign.py on the J7 base plan.
3. h9_r1 rep col_h9_r1__t1__cl49d7a23e__pv047ea3b3: bind5_otrun.log (src5 = J5 + mkplan2 lever-1/RDX + XALIGN). Hub chain5.sh (setsid) goes on to run-item wave5/spec.json and posts its own result. Its gen_env was copied from the h10 spec, so diff it against the h9_r1 kit_wave item_env before reading a failure. RDX without the define is timing-only, so COLROM takes the RDX side.
## Next (successor)
- Delete src3, src4, src5, bind, bind4 and bind5 with ot-delete when their jobs end; keep the logs and reports.
- Fold the J7 col set for S81-J6 assembly on the J6 base (event dc92652f0d5, plan 44be605129cb): XALIGN (regenerated), the H10 lane's depth rows, FIT CHAIN types, and the v3 FT delta (slice types only). Then lanefix.py + strict bind; derive the t4.xai/t5.xbi rows with relay_depth.py.
- Lever-7 pin-bank rows (FABLE-CLOSURE-STRATEGY row 7) are not built.
- h9_r1/h9_r2 have no relay_mid groups (expected=0). Their failure class is post-CTS setup at ROM go_tag (lever 1 = COLROM).
