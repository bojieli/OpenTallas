# CLKSITE-RESERVE-1115 handoff (2026-11-15 10:18 PST)
Branch claude/clksite-reserve-1115 @31d6e203e4 on hub (base main 22c217df54 + DIE-ROUTE-ABS-1 b19230ba6d/1e32ea5682). Clone epyc2 /srv/opentallas-scratch3/claude/clksite-reserve-1115/repo.
## Done (tests pass: test_clksite_reserve 5, test_clksite_kit 3, test_clksite_stamp 5, test_abstract_cutout 6)
- tools/die_plan/clksite_reserve.py: plan -> rows_apply row file, per type clock.reserved_sites_um [{rect_um, kind die_clock_tree, route_layers M1-M7}]. Sources: --tree (kit tree.json) or --from-islands (plan die_islands_um, row deletes it). MERGED rects: lossless containment drop, then greedy least-waste agglomeration to <= --max-rects (100) within a waste budget (0.2 % of outline); never merges across a hard core; reports over_cap per type (OBS count of a cut master stays near the cap, not 5,355).
- gen_phys.reserved_sites_tcl: route_layers opt-in -> dbObstruction M1-M7 on top of the placement blockage (absent -> kit bytes unchanged).
- die_trial.write_kit: plan reserved windows cut the plan abstract (M1-M3 + M7 PG) AND the closed view LEF (M1-M7 + implants + M7 PG) via abstract_cutout.cut_lef_text; cut = plan list, not tree.json.
- clksite_stamp.py: 2.70x0.81 box, slide_off_pg (<=1.3 um, no PG cut), orient_rect (box mirrored; isometry => legs preserved), stamp(), start_stage_rows (<=7 per tile, 5.40x0.81).
- HEAD dry run on nf7_plan --from-islands: epyc2 /srv/opentallas-scratch3/claude/clksite-reserve-1115/head_rows.json(+.report.json). NF7 template only; superseded by stamped tree (FABLE-PD-HEAD-0945).
## NOT done
- stamped region tree generator (one entry, parity site, type-frame legalise, stamp by transform) in the die clock kit region-tree step: next, hd_tile first.
- start-stage emit with island list as legal set; type rebuild proof (hd_tile DRC0, setup>=-42, hold>=0) NOT run; no READY yet (GATE stamp pending).
- KV: windows from a 7j clock kit with stamp mode, own delta, not in 7u. QC/S81 after HEAD.
