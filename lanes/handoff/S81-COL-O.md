# S81-COL-O handoff (Opus successor of FABLE-FIX-S81-COL; Fable weekly limit to 11-21)

Read first: lanes/handoff/FABLE-FIX-S81-COL.md, lanes/FABLE-FIX-S81-COL-SPECS.md. Goal: setup closure of the 216 S81 col types.

## 11-16 02:5x state
- F2s (DIE-S81-92, epyc10 s81-b3-clk/chain_f2s.sh, logs log/B6gF2s*.log): try1 compose stopped at RINGFF accept (82 lost / 52 wide, ALL on 10 svc types, ring_place dropped on band-use resized svc bands; 0 col). try2 (pre fff4f5ae68f4) stopped at cp permission (reused cmp dir). Posted both.
- F2s pre review (posted 02:41 + 02:5x): rrf 216 OK, tap_group/pair_affinity deleted OK, type tap_max_sinks now 3000 (fixed in try2). STILL MISSING on 216 col: clock.tap_core_etap, clock.tap_core_src tree, clock.core_pin_lead_ps ROM 255. Windows: all 216 col flat per_type 165 (per-port rows come from the F2s pilot CTS).
- Col wide rings (lpad_frame_int_i0 4 ranks, frame_int_o0 2 ranks) are internal_stations (istations.tcl is_place), not landing bands: ring_place ff does not apply; f2s2 GRT 0 overflow.
- IMPL proof kit (epyc10 s81-col-clk-impl/proof, main tools + F2r copy) CTS: windows p50 10 / p90 38 / max 49 (log mode), tap means 415..542 (upper above 380..490 accept band).
- f2s2 (F2r evidence pilot) still in 5_1_grt hold repair (WNS -186 on u_bn11/e_r0, 165 window). Read signoff when it ends.

## Next
1. On DIE-S81-92 COMPOSED: r199 verdict (col clock rows, relay stations in relay/B6gF2s_event.json, ring ff), post.
2. Pilot: epyc10 fable-fix-s81-col/f2s3_gen.sh WORK [ROWS.json] (TAG=B6gF2s; ROWS adds the 3 keys / per_port_ps on a plan copy if DIE-S81-92 does not fold them). Then ot-run --mem 64 --threads 16 --dir <work> -- bash <work>/gen/run_kit.sh <kit> cts 64 16.
3. Windows: tap_window_measure.py (main 0c49f5c6af1; clone epyc10 s81-col-clk-impl/wt) --log 4_1_cts.log (or tcl odb mode). Rows -> DIE-S81-92.
4. Regenerate with per_port_ps rows, route via ot-run, read signoff (an/mk.sh + cls.py census).
- Watcher: localhost scratchpad s81colo/watch.sh (background).

## 05:3x 11-16
- REVIEW posted 03:43 (re-posted 05:3x): lanes/FABLE-PD-S81-F2s.md. F2s NONE; F2s1 (80 ps) BLOCKING; lever 3 (upper taps) = main-tool early core tap price, needs a tool fix (IMPL).
- Window STA on f2s2 r2 4_cts.odb (an/cts_f2s2_w80, _w8020, _w4010, _wpp; SDC dirs ks80, ks8020, ks4010, kspp): below -42 = 341 / 118 / 14 / 12.
- F2s + F2s1 binds refused (BIND_RC=1, TOOLS-SKEW, DIE-S81-92 04:0x). Pilot gen waits for the bind (run/b/B6gF2s/out).
- Pilot rows ready: epyc10 fable-fix-s81-col/rows_clk3pp_r2.json (3 clock keys + measured per_port); run f2s3_gen.sh WORK rows_clk3pp_r2.json, then run_kit.sh cts via ot-run.
