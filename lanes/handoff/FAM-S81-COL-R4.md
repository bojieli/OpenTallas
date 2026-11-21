# FAM-S81-COL-R4 handoff (updated 2026-11-21 06:2x PST, Opus; successor of FAM-S81-COL-R3)
Scope: col_h9_r1 + col_h9_r2 (60 + 60 types on J5, held for J7) + shared J7 col rows. Lever 1 (RDX/ROM rows, OT_S81_CFG7_RDX) = FABLE-FIX-S81-COLROM (gen_colrom_rows.py, tree1). h9_r0 = FAM-S81-COL-H9R0-R2. h10 = FAM-S81-COL-H10. J7 = S81-J6-ASSEMBLY-R3.
Work: epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-r4 (all my jobs); intel1 fam-s81-col-r3 (R3 logs, bind4 out); epyc2 /srv/opentallas-scratch3/claude/fam-s81-col-r4 (net/hops reads).
## Done
- XALIGN proven: bind4 (J5+XALIGN, plan e5beb386) strict bind + LATCHECK PASS. L02 schedule (frame_schedule_asb selected copy, l02/ctl reproduces schedule_L02_r5; l02/xal): all 12 stations x==control, e1 2/2. L02 compile (l02/comp2) passes plan_phase, 36 phases 0 faults; only the fixture's 35-ffn.down assert trips (extra attn.a_proj phase) -> token owner.
- bind5 (R3 mkplan2 rows) failed strict bind on 139 rows with u_r1_ names: lever 1 belongs to COLROM. Deleted src5/bind5/src4 (ot-delete).
- Family class beyond lever 1 (V, routed sign-offs): lane FIFO relays feed a far bs and the next lane station from one site. h9_r1 pv047ea3b3: t4/xai -291, t5/xbi -185, t4/cci -109. h9_r2 (6 kits): t7/xai, t8/xbi -220 to -470, bs10-12 i_x -138 to -257. Net read: one relay -> bs5 (310,104) + max_cap BUF -> t4 (719,449), 481 um unbuffered (OT_MAXWIRE_POST_SKIP=1). relay_depth.py: 0 depth rows (not a depth fix).
- Fix = relay_branch.py at the owner 300-um cap, --fix named relays, legs from placed_hops on the routed kits. cbc_rules.reach_leg drops core-spanning legs, so wrapper rb/rb_corelegs.py counts them ('core-measured'). relay_branch replaces an existing row of the same relay, so rb/merge_rb.py keeps earlier copies + adds new ones (note carries the new kept list for mkxalign). h9_r1 relays: xa_4, xb_4, xa_5, xb_5, cc_4, cc_5. h9_r2: xa_7, xb_7, xa_8, xb_8, cc_7. All D=0, 0 cycles.
## Running
- bind_rb: strict bind + LATCHECK of J5+XALIGN+RLYBR on the h9_r1 rep (tree src_rb, plan 1f6d7ad7), epyc10 bind_rb_otrun.log. Then: private kit (run-item, exact wave env per COORD d442c09bb6e; diff config.mk vs scratchpad wave_config.mk = J6 kit epyc9 dc92652f0d5 attempt_2) -> route -> read t4/t5 classes. Timing proof only (no lever 1).
- g0_x: G0 of J5+XALIGN vs J5 (epyc10 g0_x/).
- rb/all_r1.sh, rb/all_r2.sh: rows for all 60+60 types -> rows_rb_r1all.json / rows_rb_r2all.json.
## Next
- Post rows to S81-J6-ASSEMBLY-R3 for J7 (regenerate on J7 base with the same recipe; bound RTL of the J7 bind).
- When COLROM tree1 is green: stack h9_r1 RLYBR rows on its plan for the signable rep.
- h9_r2 x2_8 -> t8_payload (11 core legs) not covered by relay_branch: read after the first RLYBR kit.
