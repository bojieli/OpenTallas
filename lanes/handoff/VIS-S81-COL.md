# VIS-S81-COL handoff (Opus, started 11-22 22:4x PST)
Briefs: scratchpad visual_brief.txt + visual_brief2.txt. Lane dir intel2/epyc9/epyc10 /srv/opentallas-scratch2/claude/vis-s81-col.
## Step 1 DONE 23:0x: 214/214 VIS-COVERAGE rows (386a024f); post 481c91c9.
Classes: EDGE-STRIP (frame bus >=1167b through 43-52um strip), VIEW-CROSS (56um bf_front_roots/col3_c gap), EAST-CORRIDOR (x_i0 past u_cf / onto node column).
J8 E15E-CHAN covers h9_r1/h9_r2/h10_r2 (IN-EVENT). J9 planR2 = no geometry; ROM pin edges 0 ovf.
## Row COL-H9R0-STRIP+E4E-CHAN (J9 manifest row 3b)
- generator intel2 vis-s81-col/colstrip_row.py: p4-p6 interior -25.92 y (N strip 43->69), all h9_r0 e4e view +25.92 x halo 2.16.
- COMPOSE ORDER (H9R0-R4 condition): J8 -> H9R0 v3 rows -> run colstrip_row.py on that -> RANKSEAT apply_r2.py. NOT the static ops file.
  composed by H9R0: epyc10 fam-s81-col-h9r0-r4/tmp/plan_v3_strip.json (+ ops_strip_on_v3.json).
- PRE: ot-run epyc10, log intel2 vis-s81-col/pre_v3strip.otrun.log, json epyc10 vis-s81-col/tmp/pre_v3strip.json.
- PROBE: p4 clcb2fbfe8 full-row plan on J7 base (tmp/plan_probe_p4_full.json), spec intel2 vis-s81-col/probe/spec_p4, run-item pid 1866922 log probe/runitem_p4.log, goal grt, work epyc9 .../private/VIS-S81-COL/col_h9_r0_p4__t1__clcb2fbfe8__pvec137455_1122231835. Read: congestion.rpt + layout_review/grt PNG; base GRT10 ovf 4928 (hot x600-900 y1100-1300, x1300-1500 y600-700).
- Strict bind + LATCHECK: needed by ASSEMBLY on ONE plan with planR2 (asked RANKSEAT j9r2 driver to bind the composed plan).
## Drafts for J10: h10_r1 outline +60.5 (die column shift); h10_r0_p1 ECORR; h10_r0_p4 strip shift (H10-R4 deciding after L1t).
## Attribution jobs (diagnostic, optional): ot-run attr_run.sh h9r0p4 epyc7 / h10r1 epyc9 / h9r2 epyc8 (load/disk holds).
## 23:5x update
- PRE PASS 0 on plan_v3_strip (ac3a5c74d618). h9_r0 rows PRE-PASS (2031e017).
- COL-H10R0-E1E-CHAN (col_h10_r0_p1, 6 types) ACCEPTED by H10-R4 for J9; composed: epyc10 vis-s81-col/tmp/plan_v3_strip_e1e.json ba87ca31a34b = j9r2 graft source (RANKSEAT restarted 23:44). PRE on it: ot-run epyc10, log intel2 vis-s81-col/pre_e1e.otrun.log.
- COL-H10-GROW (J10 die-level, growth pre-approved): grow_row.py; ops j9/rows_COL-H10-GROW_J8.json (18 types: h10_r0_p4 H+25.92 N strip->69; h10_r1 H+60.48, interior +34.56, S->86.4 N->69, e10e chan). Probes (J7 base, goal grt, epyc9): h10_r0_p4 pvcc166a6d run-item pid 2640926 (probe/runitem_colh10r0p.log); h10_r1 pv0713a75a pid 2666053 (probe/runitem_colh10r1.log).
- p4 h9_r0 probe pid 1990740 (probe/runitem_p4b.log). Self-pass rule f95aac4: read congestion.rpt + PNG at GRT, set PROBE-PASS.
## 00:0x update (11-23)
- All 3 private probes (p4b, colh10r0p, colh10r1) DIED at kit_topology: KIT_TOPOLOGY_BIND_STALE (private plan changes stations/relays; kit reused J7 tree bind 1122064402). --allow-bind-stale does not reach kit_topology. Fix = own bind.
- New path: combined probe plan intel2 vis-s81-col/tmp/plan_probe_combo.json (1e431c3917df; J7 base + h9_r0_p4 strip + h10_r0_p4 grow + h10_r1 grow). Fork J7 tree -> intel1 /srv/opentallas-scratch2/claude/vis-s81-col/treeJ7V (54 GB, ot-tree-fork), plan replaced, then ot_build_hub --goal bind once, then --goal finish per type (place..route, renders en route).
- E1E PRE on plan_v3_strip_e1e still pending (waiter b7u271jsf). RANKSEAT j9r2 driver pid 2662682 waiting for J8 tree (>400G host).
## 02:xx update (11-23)
- Probe 1: combined plan 1e431c3917df (J7 + h9_r0_p4 strip + h10_r0_p4/h10_r1 grow) on fork intel1 vis-s81-col/treeJ7V. ot_build_hub --goal finish, rt 02f464834f6d. Log intel2 vis-s81-col/bld/p4.log, pid in p4.pid. Bind out intel1 /srv/opentallas-scratch2/claude/VIS-S81-COL/ot-build/s81/treeJ7V/b_b7093ee5bc75. pre rc0, elab done. NEXT: once the bind finishes, launch the same command for col_h10_r0_p4__t1__pvcc166a6d and col_h10_r1__t1__cl95b37463__pv0713a75a.
- RC-GAP (FABLE-RC-REVIEW): replied fe401909, then a correction post.
  - (2) Row COL-H9R12-SSTRIP. Generator vis-s81-col/sstrip_row.py: t<n>__payload/t<n> +25.92 y; lpad r[k] y 0 -> 30.24. Ops j9/rows_COL-H9R12-SSTRIP_J8.json.
  - J9 candidate: epyc10 tmp/plan_v3_strip_e1e_ss.json (3c285d644712). PRE log pre_ss.otrun.log. Probe 2: cl774 pvea45273b, combo2 ec0fc94977a0, on fork intel1 treeJ7V2. Log bld/cl774.log.
  - (3) clk_t13: J10, owner TAP-GRID-R5; still to send them the per-tap span census.
  - (1) porous: launch dir data comes from the rt. Sealed J7 kits are pinned to the old rt d6f543, so they get stale views. Check the kit gb_hw sha at gen.
- PROBE-PASS now needs the full-cause census (fe8a2a5): every cluster of >=50 ovfl or >=1% of total, total <10% of baseline, and every path class below -42 TT or hold <0 at CTS has a row.
- FIX-LEDGER wants COL-H10-GROW in J9 (cut 18:00, rule 6079af4). Asked H10-R4 to accept.
