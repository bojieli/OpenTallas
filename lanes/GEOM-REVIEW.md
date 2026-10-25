# GEOM-REVIEW (independent design reviewer, 2026-10-24)
Branch claude/geom-review-1024, worktree localhost:/srv/opentallas-scratch/claude/wt/geom-review (base origin/main 4ab1ec1399).
Owner order 08:05: visual die + tile review before routing/STA. Records: results/geom_review/<die-or-kit>__<sha>.json + README per batch.
## Current step
08:07 started. 08:55 batch 1 (die level) DONE; merged main f1964316b9 (09:20). 09:05 tile batch running: sub-reviews GR-S81F (S81 + ELEM-S81 frames),
GR-S81S (34 slice_station, S81-CORES vs/vq/hrow + svc hcore, head hd_tile), GR-HBM (ELEM-HBM cores, HBM G2 probes); GR-QK done.
## Run dirs
- renders: localhost:/srv/opentallas-scratch/claude/geom-review/
## Verdicts
- die (results/geom_review/die_1024/README.md): S81 v4.8 ea36999b PASS-COND | S81-XDIE e2299c43 PASS-COND (G0C 108 not 91) | S81 head 6b6620d0 PASS-COND |
  QC P6 0028ad53 PASS-COND | KV v3.8v bc4edcd4 PASS-COND | HBM B2r2 c1bc2d0f PASS-COND, G3 BLOCKED q_sm*/q_hub/root
- tile (GR-QK): QC A0 v7 NK/NL PASS-COND (pathfinding; equivalence + clock contract) | KV hub_Ei vC FAIL (ft out legs 500-720 um, empty taps) |
  astk x4, head_eighth x8, pv_pair PASS-COND | kvs_pc, ahub, ectlk, kvs_pc_h_head_p NOT REVIEWED (no placement)
## OWNER?

## CODEX notes
- 08:58: common gen_phys defects fixed in main d311adaf53: missing face_keep/release hooks caused head g3r4 synth_odb failure; copied now. LEF without Liberty rejected before partial kit. Three focused tests pass. FF macro sibling copying follows (59047bf0cd). No physical closure claimed.

## CODEX notes
- CODEX root: main8232aca585 renders actual snapped R4 grid+sinks instead of only tap_um; tiny and CP1r10c images viewed. Shared flow patches do not waive any failed geometry.

## RESUMED 12:12 PDT (after usage-limit stop 08:50-12:04)
- adopted: none (GEOM-REVIEW had no Codex live jobs; Codex notes read). Committed GR-S81S's 34 slice_station records (29 PASS-COND / 5 FAIL) left uncommitted at the stop.
- 13:10 die batch 2 (Codex candidates) merged main 410d3d1712: S81 26-slot ledger PASS-COND, S81 xdie fe3d259091 PASS-COND, KV reach405 PASS-COND, HBM B2l PASS-COND (batch-1 q_sm/q_hub/root blocks lifted at plan level). README results/geom_review/die_1024b2/README.md. Findings posted S81, KV-G3, HBM-ARCH, ELEM-S81.
- running: sub-agent GR-B2 tile reviews (KV hub_Ei retry4, CP1 reach405 r0/r1, head hd_tile tap160c7, station405c1 kits).
- open: GR-S81S cleanup claim (empty root-owned dir in ELEM-S81 kits) - none found at top level of /srv/opentallas-scratch/claude/elem-s81/kits.
- 13:40 tile batch 2 merged main da5213b0b3: KV hub_Ei reach405 PASS-COND, CP1 reach405 r0/r1 FAIL (unpinned proof-leaf regs), head hd_tile tap160c7 FAIL (elemA_cv clock pin 24 nm access + best_key -627), slice_station 405c1 t3/t9/t25/t33 PASS-COND, t4/t32 NOT REVIEWED (no ODB). Posted KV-G3, CP1-R10, S81-HEAD, ELEM-S81.

## OWNER?
- (13:40) Reset distribution: KV hub_Ei and every S81 slice_station have one arst_n pin feeding per-tap synchronisers 2-2.6 mm away, checked as single-cycle recovery without false_path (-550..-846 ps); no buffer tree closes this at 833 ps. Need a shared rule: per-tap arst_n from the die spine (like clk_tN) or a false_path/multicycle into the synchronisers (async assert, synchronous local deassert).
- (13:40) CP1 coreless proof leaves are not valid timing evidence (unpinned regs across 1.2-1.5 mm); seam geometry passes.
- next: KV unplaced cores (kvs_pc, ahub, ectlk, kvs_pc_h_head_p); t4/t32 405c1 when placed; re-review regenerated frame kits on the 26-slot ledger.
- (S81 13:55) Reset distribution OWNER? item: S81 frames show the same thing. One interior arst_n (180,186) -> 16 per-tap rsync up to 1.97 mm: DPL async h10_r0_p1 -1449, h10_r1 -639 ps; CP1 reach405L same frames CTS -1019 / finish -34. Frames can't sign without the rule. S81 author review results/geom_review/s81_g3_frames_g3k3__author_1024.json (F1 forest INV + F2 relay chain fixed 43e8e5321a; g3k5 placing for your re-review).
- 18:58 KV hub_Ei vJ second review (KV-G3 request): FAIL-to-route (reset not per OWNER DECISION 2; predicted GRT hotspot ft24 st2 + clk_t31); datapath geometry PASS; record kv3_hub_Ei__kvg3_g5_vJ__c38439fd5a78.json, main e39037d67f. Checklist (TILE_BRIEF) now has "reset distribution matches the owner rule"; margins INFO only.
- 19:0x running sub-reviews: GR-S81G (S81 frame kits g3k5 - g3k4 was stopped/superseded by S81), GR-KVC (KV cores kvs_pc, kvs_pc_h_head_p, ahub, ectlk, head_eighth 216, pv_pair m7).

## PARKED 2026-10-24 18:57 PDT
State: all records committed + merged (last GEOM-REVIEW merge main e39037d67f; branch claude/geom-review-1024 clean, nothing ahead of main). No jobs running; sub-agents GR-S81G / GR-KVC parked with NO records written (nothing judged).
Pending reviews (resume here):
- S81 frame kits g3k5 (g3k4 was stopped by S81; no g3k6): 7 kits NOT REVIEWED. ODB copies + dumps ready in localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-S81G/{odb,dump,kits}/<kit>; next = layout_review.py on dump.json, look, propagated-clock STA (GR-S81F sta/*.tcl), 7 records. Input-level notes (not visual): ROM lib fixed; elem_q/bf_col early clk_c* taps fixed; ROM macros still get NO early tap (h9_r2 read path -56); tap load imbalance (h9_r2: clk 2541 / t1 1513 / t6 1524 sinks vs 6 taps 0-10); reset_taps.tcl = per-tap async rsync -> FAILS owner reset rule. h9_r0_p1/p3, h9_r1 only 3_place.
- KV cores NOT REVIEWED: qkd_ahub 6_final (epyc3, webp ready) first; kvs_pc / kvs_pc_h_head_p only 09:xx GRT-failed ODBs (no newer run); ectlk: no variant passes CTS (ELEM-QK e1-e3 RSZ-0060 max buffer count) + plan S-face detour unresolved; head_eighth 216 e4 dumped only; pv_pair m7 6_final. Scripts in tiles/GR-KVC/tools (reset_audit.tcl needs fixing: TIEHI counted as reset source, NULL compare crash).
- hub_Ei vK delta re-review (reset rule + ft24 st2/clk_t31 hotspot, GRT-only gate) when KV-G3 builds it.
- slice_station 405c1 t4/t32 (no ODB at last look); regenerated frame kits on the 26-slot ledger.
Open findings per lane:
- KV-G3: hub_Ei vJ FAIL-to-route (reset rule; hotspot (560-600,800-840)); reach405 plan: 8 in-core stations need regs_um, +1..4 cyc re-price.
- S81: 26-slot ledger PASS-COND (canonical regen, latency receipt NOT RUN, frame kits consume bit sites); xdie fe3d259091 needs rebase on ledger; 12 v4.8 frame FAIL stand; frames fail reset rule.
- ELEM-S81: v4.8 slice_station t3/t4/t9/t25/t32 FAIL (405c1 t3/t9/t25 fix them, PASS-COND); t33 NOT SIGNED (weak repeaters, spread 86.75); station-0 insertion >= 250; reset rule.
- CP1-R10: reach405 r0/r1 FAIL (unpinned proof-leaf regs) - stop as timing evidence.
- S81-HEAD: hd_tile tap160c7 FAIL (elemA_cv clock pin 24 nm access -> regen LEF; best_key 14-level path -627 needs RTL stage).
- HBM-ARCH: B2l PASS-COND (RTL relay binding + token re-run; clock root driver off core u_tkm_SW_tile19; root crossing band + q_sm channels as blockages; halos). Earlier bankq0/gq_land/gq_issue FAIL stand.
- QC-A0 / KVG3-CORES: batch-1 PASS-COND conditions stand (A0 clock contract/equivalence; KV cores straps-as-constants).
Checklist now includes "reset distribution matches the owner rule" (TILE_BRIEF.md); margins INFO only.

## RESUMED 2026-10-24 19:28 PDT (rtx-pro coordinator; lane agent)
2026-10-24 19:28 PDT GEOM-REVIEW: resumed. Worktree epyc1:/srv/opentallas-scratch/claude/wt/geom-review (claude/geom-review-1024, ff to main d13ff7c783). Running: S81 g3k5 frame reviews (7 kits; layout_review + propagated STA TT/FF in docker grgeom_* on epyc1). Watching this file for GEOM REQ lines.
2026-10-24 19:34 PDT GEOM REQ [KV 19:34] kv3_hub_Ei vK delta (reset + hotspot only; datapath carried as PASS from vJ second review c38439fd5a78): plan-level picture epyc1:~/scratch/kv-g3/plans/vK/bits.png (+ rtx-pro /tmp/kv/bits_s25c3_crop.png), sites report plans/vK/bits.json; reset tree = kit_rtl/g5/vK/kv3_hub_Ei/reset_tree.tcl (root at arst_n (91.4,101.8), relays at taps, D=7). Placement/CTS/GRT pictures will follow from epyc2:/srv/opentallas-scratch2/claude/kv/g5/vK/kv3_hub_Ei (running to GRT only; no DRT before your PASS).

2026-10-24 19:37 PDT GEOM REQ [S81/KITS] 3 new S81 legacy hard cores, stage-1 placed, before route (branch claude/s81-kits-geom-1024r @a854c5530, records results/geom_review/s81_kits_1024r/<kit>.json + img/<kit>.png; placed ODB epyc1:/srv/opentallas-scratch/claude/elem-s81-cores/<rnd>/<kit>/run/results/asap7/*/base/3_place.odb):
  - r2 dsdv_gunit_l5f_c (151.2x151.2, author PASS-COND: rst_n recovery risk over 150 um / 10.6k flops)
  - r2 dsfd_node_LLd_c (43.2x77.76, author PASS)
  - r4 ot_s81_cfg7_seq_c (17.28x51.84, author PASS-COND: W face 356 pins 7.5/um, W-edge GRT)
  Please reply PASS/FAIL here; S81/KITS routes on PASS (same host epyc1).
2026-10-24 19:38 PDT GEOM-REVIEW: VERDICT S81 frame kits g3k5 (7) = all FAIL - do not route g3k5; build g3k6. Records results/geom_review/col_*__g3k5_*__<hash12>.json + tile_1024g3k5/README.md on claude/geom-review-1024@44d36293aa (READY). Images epyc1:/srv/opentallas-scratch/claude/geom-review/tiles/GR-S81G/rev/<kit>/{review,clock_latency_taps}.png.
  Common: (1) reset = per-tap async rsync from one arst_n tree (decision 2; arst_n -257..-994 ps). (2) clock (decision 5): nearest-tap only, 0..3007 sinks/tap, flop latency 176..489 ps TT (placement RC), face flops 205-489 vs 250 budget, related-pair skew (flop->flop, CPPR) max 123-259 ps, 273-5005 pairs >80 at TT/FF; ROMs still no early tap. Geometry otherwise OK (face flops p90 7-10 um, gaps >= 6.5, density <= 0.56, PDN edge to edge).
  Per kit: h10_r0_p1 x broadcast 284/267 b from ONE station to bs0 ~650 um / bs2 ~510 um (-381); h10_r1 face flops 339-489 ps -> 15-19 hold bufs/bit, n13->n12 736 um; h10_r2 only ROM->seq -141 (closest); h9_r2 rt_24a relay cuts elem corner (-43.5) + 4 empty N taps; h9_r0_p1/p3 u_s0->u_t0.c0 905 um (RTL stage); h9_r1 3_place only.
2026-10-24 19:39 PDT GEOM REQ [S81/ST405] slice_station B routed NOT SIGNED t1 t2 t11 t13 t24 t30 t31 t34 (author review FAIL, branch claude/elem-s81-st405-1024@c46038b443, record results/geom_review/elem_s81_station405B_fail_review_1024.json, images epyc1:/srv/opentallas-scratch/claude/elem-s81-st405/review_fail_1024/t*_final_{placement,clocks}.png, routed ODBs in kitsB/slice_station__tN/run/results on epyc3 (t1 t2 t11 t24) / intel1 (t30 t31 t34) / epyc1 (t13)). Classes: DRV (t1 t11 t31 t34: single-driver ~150 um BUFx3->INVx1 M2/M3 segments -> --max-wire-um 100), CLOCK (t1 t2 t24 t31 t34: fixed-grid taps far from thin station lines, unbalanced tap trees, routed early taps -> CLOCK decision-5 tool), RESET (t13 t30 + all kits: per-tap async rsync -> RESET tool). No re-route asked except ONE: t11 warm DRV-only re-route from its own 4_cts.odb with the max-wire hook (placement/CTS identical to the PASS-COND kit; TT +12.94 / FF +9.90 / spread 64.3 already pass; reset non-conforming like every station kit) as hook validation on epyc2 -- please PASS-COND or FAIL that one.
