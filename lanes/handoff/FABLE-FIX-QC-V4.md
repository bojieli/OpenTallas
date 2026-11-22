# FABLE-FIX-QC-V4 handoff (Fable; started 2026-11-22 04:1x PST by COORD). Goal: compose + pre-prove QC plan event V4; QC-PLAN-R13 applies it.
Brief: scratchpad fable_fix_brief.txt + family_brief.txt + rules.txt. V3 = R13 (pick cr > b2r > n3; cut 06:00; apply >= 11:16). V4 slot = V3 apply + 4 h.
## Work dir: epyc8 /srv/opentallas-scratch2/claude/fable-fix-qc-v4 (rt c9b8d5f226ca)
- in/ = R13 e10/in bind inputs (side.json, r8_final, extras, asbuilt merge, split_report, SRD sv, rr_tools, census). rows/ = family row files + pd_v2_d.json (su_c cap2b) + zz_ftc_axis_r4.json.
- prep.sh (ot-tree-fork of kw45 v1r6 + installs + rt_launch_tree) / bindrun.sh (strict bind R8 loop + LATCHECK) / chain.sh TAG PLAN [SIDE] (latency -> plan_gate_pre --tree W -> static G0 || bind -> post-bind G0).
- W/ = real event tree + launch (plan cr) for every static check (TAPNAME needs physical/).
- merge3.py (3-way type merge BASE THEIRS OURS), rows_small.py (FEFW, FIX-SYNC r1 RLEG, r2 LAUNCH), compose_v4a.py + side_v4a.py (SLE freg), rows/compose_suc.py.
## Layers
- L0 = plan_v3p7d5r e69de4a70060 (cr + bandmove + rev5) + tapfix (8 st_a) + retap vs cr. Driver l0b.sh -> chain l0 (log l0b.log, l0_bind.out, l0_bound/).
- L1 = L0 + SLE freg (+side) + su_c cap2b + coll_ftc axis_r4 + FEFW clf110fab2 + r1 RLEG + r2 LAUNCH. Driver l1.sh (waits on plans/tapname_l0.txt), log l1.log, l1_bind.out, l1_bound/.
- L2 (not composed): cb capture_tap key (LOCKUP-STATION-R3 2077e5e210, not on main), sle_ctl lever-3, cbx i30 sites, cb stations, coll_core v4, st_a pad stage, hc0 station, anchors, thin bands, TAP-GRID-R5 pkg.
## Intake table: lanes/handoff/FABLE-FIX-QC-V4-intake.tsv
## Rulings (mine): slw_fw_v1 strap sites, CLASS-SWEEP A default and B bands NOT carried (no unsigned type gains; would supersede running/signed kits).
## NEXT
1. Read l0b.log / l1.log; on bind errors fix rows and rerun (new TAG; ot-delete old *_bound).
2. After R13 06:00 pick post: if pick != cr, recompose (bandmove.py + rev5.py on the pick).
3. L2 rows one by one through W gate; hand R13 the highest clean layer + table.
4. Sealed private kits on the clean V4 plan for cb (cbf_q00), st_a, su_c (private-spec --tree <bound tree fork> --goal finish; run-item; ot-wait --durable).
