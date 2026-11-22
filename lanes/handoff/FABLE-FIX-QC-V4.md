# FABLE-FIX-QC-V4 handoff (Fable; started 2026-11-22 04:1x PST by COORD). Goal: compose + pre-prove QC plan event V4; QC-PLAN-R13 applies it.
Brief: scratchpad fable_fix_brief.txt + family_brief.txt + rules.txt. V3 = R13 (pick cr > b2r > n3; cut 06:00; apply >= 11:16). V4 slot = V3 apply + 4 h.
## Work dir: epyc8 /srv/opentallas-scratch2/claude/fable-fix-qc-v4 (rt c9b8d5f226ca)
- in/ = R13 e10/in bind inputs (side.json, r8_final, extras, asbuilt merge, split_report, SRD sv, rr_tools, census). rows/ = family row files + pd_v2_d.json (su_c cap2b) + zz_ftc_axis_r4.json.
- prep.sh (ot-tree-fork of kw45 v1r6 + installs + rt_launch_tree) / bindrun.sh (strict bind R8 loop + LATCHECK) / chain.sh TAG PLAN [SIDE] (latency -> plan_gate_pre --tree W -> static G0 || bind -> post-bind G0).
- W/ = real event tree + launch (plan cr) for every static check (TAPNAME needs physical/).
- merge3.py (3-way type merge BASE THEIRS OURS), rows_small.py (FEFW, FIX-SYNC r1 RLEG, r2 LAUNCH), compose_v4a.py + side_v4a.py (SLE freg), rows/compose_suc.py.
## Layers (drivers in the work dir; statics on Ws/launch = launch over the v1r6 snapshot, binds on their own ot-tree-fork)
- L0 = plan_v3p7d5r e69de4a70060 (cr + bandmove + rev5) + addtap.py --fix (drop added tap coincident with a new base tap on 3 sle_st_a_v2; move the in-core one on 2 slw_st_a_v1; rename tables)
  + fwdretap.py (forwarded clock sources re-pointed by site, old = cr; reset names untouched: the 10 st_a types carry reset.consumer_sites_um) + treechk.py --fix (localized types = 9 sc types; republish collector_tree = reset_tree.for_type).
  Driver l0e.sh -> chain.sh l0 (l0e.log, l0_bind.out, l0_bound/). tapfix-by-name (QC-SLE-R5) is NOT enough: base taps renumber (58-157 per type).
- L1 = L0 + SLE freg (+side) + su_c cap2b + coll_ftc axis_r4 + FEFW clf110fab2 + r1 RLEG + r2 LAUNCH. Driver l1.sh (waits plans/tapname_l0.txt).
- L2 = L1 + sle_ctl lever-3 (merge3: 18 landing pins + 2 ft slots) + cb zero-cycle site delta (rows/cbx_i30/cb_sites_delta.json, made on d5r; overrides r1 inst_taps on cbn_q11 cl5cc92dfe with CB-R4 form 17/16/62/90)
  + coll_core XEPRE define + xev seats (RTL in/ot_coll_tp8_static.xepre.sv = main bac6bcfd79, passed as SRD=). tap_reset_split HELD until the split LEC is EQUIVALENT (OPUS-FIX-QC-COLL-R3). Driver l2.sh (waits plans/tapname_l1.txt).
- Not composed yet: cb capture_tap key (clock.zl_lockup.<type>.capture_tap; LOCKUP-STATION-R3 2077e5e210, needs rt with it), cb +1 stations, st_a pad stage / origin->rstart_tx, hc0 station, anchors (from bind report), TAP-GRID-R5 pkg. Thin bands WITHDRAWN (COORD).
## Risks to re-read on kits: frozen reset consumer sites of the 10 moved st_a types sit on the pre-move tap sites.
## Intake table: lanes/handoff/FABLE-FIX-QC-V4-intake.tsv
## Rulings (mine): slw_fw_v1 strap sites, CLASS-SWEEP A default and B bands NOT carried (no unsigned type gains; would supersede running/signed kits).
## NEXT
1. Read l0e.log / l1.log / l2.log; on bind errors fix rows and rerun under a new TAG (ot-delete old *_bound).
2. R13 base: cr gets a republished sle_sc_v1__cl7479a5ec tree (crt); my treechk does the same on L0 - compare the type block with R13's crt once it differs from cr.
3. Hand R13 the highest clean layer (plan pre + post-latency, side.json, r8_final, bound dir, intake table).
4. Sealed private kits on the clean plan: cbf_q00__cl1b5a6458, one st_a (sle_st_a_v2__pv4242de79), slw_su_c__cl92142dac, sle_ctl (private-spec --tree <bound>/tree --bind-out <bound>/bind --goal finish --host epyc8; run-item; ot-wait --durable).

## 09:3x PST state (read this first after compression)
- MEASURED l0x (probe = L0 without sc republish) strict bind: 1 error = EMIT sle_sc_v1__cl7479a5ec (known). d lineage with my tap fixes is otherwise bind-clean. LATCHECK not reached.
- Binds running on epyc8 (chain.sh TAG; MEMB default 96 G now; R8IN = refreshed table so one pass): l0 (8 sc republished; 48 G, 2nd pass), l0y (hedge: only cl7479a5ec republished; plan plans/l0y), l1b (L1 again; first L1 bind OOM at 48 G), l2b (L1 + cb site delta + coll_core XEPRE/xev seats).
- DROPPED: sle_ctl lever-3 (static G0 13 errors on V3 geometry). L2 bind cancelled.
- plan_gate_pre vs v2r10 = LANDREMAP noise on V3-changed types; rerun vs cr: l0/pgp_vs_cr.log.
- TAP-GRID-R5 items are mine: rm5b not mergeable (other lineage); method = anchor-mode remap on my bound tree only for types the bind lists as errors (none so far). coll_ftc anchor + cbf_q00 rr_t103 port relay: not seen in l0x (0 errors there).
- cbn_q00 cl622f65d2 / cldbcda913: I cover; release = first applied plan with rev5 (V3 c5rt or V4).
- Waiting pattern: foreground loops are cut at 180 s; use bounded for-loops (5 x 30 s) and direct status reads.
- HANDOVER when clean: post plan pre sha + post-latency plan path, side.json, r8_final.json, bound dir, LATCHECK + post-bind G0, intake table rev 2; then kits (step 4 of NEXT).
