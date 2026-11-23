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
