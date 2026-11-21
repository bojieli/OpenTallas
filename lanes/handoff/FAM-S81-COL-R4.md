# FAM-S81-COL-R4 handoff (updated 2026-11-21 08:4x PST, Opus; successor of FAM-S81-COL-R3)
Scope: col_h9_r1 + col_h9_r2 (60 + 60 types on J5, held for J7) + shared J7 col rows. Lever 1 (RDX/ROM rows, OT_S81_CFG7_RDX) = FABLE-FIX-S81-COLROM (gen_colrom_rows.py, tree1). h9_r0 = FAM-S81-COL-H9R0-R2. h10 = FAM-S81-COL-H10. J7 = S81-J6-ASSEMBLY-R4.
Work: epyc10 /srv/opentallas-scratch2/claude/fam-s81-col-r4 (all my jobs); intel1 fam-s81-col-r3 (R3 logs, bind4 out); epyc2 /srv/opentallas-scratch3/claude/fam-s81-col-r4 (net/hops reads).
## Done
- XALIGN proven: bind4 (J5+XALIGN, plan e5beb386) strict bind + LATCHECK PASS. L02 schedule (frame_schedule_asb selected copy, l02/ctl reproduces schedule_L02_r5; l02/xal): all 12 stations x==control, e1 2/2. L02 compile (l02/comp2) passes plan_phase, 36 phases 0 faults; only the fixture's 35-ffn.down assert trips (extra attn.a_proj phase) -> token owner.
- bind5 (R3 mkplan2 rows) failed strict bind on 139 rows with u_r1_ names: lever 1 belongs to COLROM. Deleted src5/bind5/src4 (ot-delete).
- Family class beyond lever 1 (V, routed sign-offs): lane FIFO relays feed a far bs and the next lane station from one site. h9_r1 pv047ea3b3: t4/xai -291, t5/xbi -185, t4/cci -109. h9_r2 (6 kits): t7/xai, t8/xbi -220 to -470, bs10-12 i_x -138 to -257. Net read: one relay -> bs5 (310,104) + max_cap BUF -> t4 (719,449), 481 um unbuffered (OT_MAXWIRE_POST_SKIP=1). relay_depth.py: 0 depth rows (not a depth fix).
- Fix = relay_branch.py at the owner 300-um cap, --fix named relays, legs from placed_hops on the routed kits. cbc_rules.reach_leg drops core-spanning legs, so wrapper rb/rb_corelegs.py counts them ('core-measured'). relay_branch replaces an existing row of the same relay, so rb/merge_rb.py keeps earlier copies + adds new ones (note carries the new kept list for mkxalign). h9_r1 relays: xa_4, xb_4, xa_5, xb_5, cc_4, cc_5. h9_r2: xa_7, xb_7, xa_8, xb_8, cc_7. All D=0, 0 cycles.
- RLYBR gate: bind_rb (J5+XALIGN+RLYBR, plan 1f6d7ad7) strict bind 0 + LATCHECK 873/873, all 10 copies in bound RTL. G0 of XALIGN: 0 new.
- J7 step posted to S81-J6-ASSEMBLY-R4 (FABLE-PD-S81-0830 #4): 'GEN mkrlybr python3 -I epyc10 .../fam-s81-col-r4/rb/mkrlybr.py {IN} {OUT} <rows_out> rb/rows_rb_r1all.json rb/rows_rb_r2all.json' between mkdepth405 and mkxalign; dry run on v4 gen18_out: 660 rows, 120 types.
- Main 1ba6a4eb948: relay_branch.merge_branch_rows (re-run keeps earlier copies). reach_leg core-span rule NOT changed (flagged to COORD).
- Bank taps <=1000 (#8): tc/solve.py on J5 regs dumps (tap-grid-r2 colcap/regs): h9_r1 +9 taps (60 types), h9_r2 +7/+7 (17+43 types), all 0 over. Rows tc/rows_tc_r1.json, rows_tc_r2a.json, rows_tc_r2b.json. Re-solve on J7 placement for J7.
- Private kits MUST come from `kit_wave.py private-spec` (copied spec.json fails ENV-PROVENANCE at place). rt f3db2d0e628f was pruned; use rt current.
## Running
- chain_rb3.sh (hub, log chain_rb3.log): RLYBR rep private-spec kit wave_rb2 (work epyc10 kw43-wave-1109n/.../dc92652f0d5/private/FAM-S81-COL-R4/col_h9_r1..._1121081940) run-item -> route (ot-run epyc10/8/7) -> posts. Read t4/xai, t5/xbi, t4/cci at sign-off (final db).
- bind_tc (epyc10 bind_tc_otrun.log; tree src_tc plan f04a482cf3ef = src_rb + bank taps) -> hub chain_tc.sh (log chain_tc.log): private-spec wave_tc -> run-item -> route -> posts. Compare CTS post-hook + TT/FF vs the RLYBR-only kit.
## Next
- Signable rep: stack RLYBR rows + bank taps on COLROM tree1 plan once its 216-type gate passes (gen_colrom_rows.py, hub lanes/handoff/FABLE-FIX-S81-COLROM-gen_colrom_rows.py).
- h9_r2 x2_8 -> t8_payload (11 core legs) not covered by relay_branch; h9_r2 FF hold -25 (22) after setup.
- Stray: epyc10 /tmp/claude_r4_j7rb*.json (my dry-run, 95 MB; ot-delete refused files) and tc/col_h9_r0_*.json extra regs copies.
