# HARD-S81-SERDES-1 handoff (COORD is the coordinator)

## Scope
Targets: s81/serdes__t2 (a27), seqhost__t1, serdes__t1 (2 cohorts), serdes__t14. Redesign, not rebuild. Also owns RULEBOOK-1113 section R-RTL (written 11-13, committed).

## Where things are
- Worktree: epyc9 /srv/opentallas-scratch2/claude/hard-s81-serdes-1/wt, branch claude/hard-s81-serdes-1-1113 off origin main fbfb4fc6a6 (not pushed yet).
- Lane dir: epyc9 /srv/opentallas-scratch2/claude/hard-s81-serdes-1 (probe scripts, bench outputs bench1/, kits).
- ot-run logs: intel2 ~/hard-s81-serdes-1-logs/.
- Reference kit (read-only): epyc9 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/e9eda32d41c/items/serdes__t2/attempt_27.

## Findings (serdes__t2 a27, 4_cts_final.rpt + geom.tsv)
- Lot 2885.76 x 1226.88, fill 1.4 %. PMA pair along the top (x 245..2490; rx q pins y 951.6, tx d pins y 1093 in the 11.9-um gap), dchn + 2 SRAMs at x 864..1552 y 60..231, coll pins on the E face y 6..228.
- All worst paths are bare wire, 0..6 logic cells: u_txl r[0] -> q (1674 ps repeaters), PMA face -> u_syn am_ok/xs (-1443 at CTS), rs_t -> u_rm recovery (-555), u_rm r_d -> u_bout, u_bin -> u_enc, cland tc fanout (-182). GPL put u_enc at (2297, 834), u_syn at (1232, 249), u_rm at (1659, 69), u_bin at (2511, 523).
- RELAY-PLACE-1 (FT-LANE) says serdes is NOT its class (03:08 post). All 11 serdes types share ot_pdie_serdes_col, so the fix is a family fix.
- serdes__t14 CRASH 01:32 = PIN_AUDIT FAIL "extra 1" (same as serdes__t2 a22): a flow/pin-table error, not timing. Its last timing result (a11) was the same wire class (-764).
- Earlier lanes (DIE-S81-85/87 vT2..vT5 on t14) added rows one at a time with a post-GPL spacing hook; vT5 still failed -195 on an unplaced u_rmo row.

## Design (form LANE)
- RTL: ot_pdie_serdes_col parameters LANE_PIN / LANE_TXA / LANE_RXI / LANE_RXO (defaults 0 = unchanged), defines OT_S81_SERDES_LANE_*=N. Rows are ot_pl_pad instances u_lpin, u_txl, u_lrxi, u_lrxo. rs_r grows by LANE_RXI stages so the whole rck domain shifts together.
- Planned rows for the shore lot: PIN 3, TXA 4 (u_txl 6 rows), RXI 4, RXO 3. TX +7 clk, RX +4 rck +3 clk.
- Placement (to write): kit hook serdes_lanes.tcl at PRE_GLOBAL_PLACE: rows FIRM on per-bit lanes <= 405 um apart, placement blockage outside the KP4 island + lane corridors.
- Bench: rtl/dsrom_sys/s81_link/col/tb_s81_col_lane.sv, tools/s81_link/run_serdes_lane_bench.sh (verilator/verilator:v5.032 docker on epyc9, lane dir bench_all.sh).

## State 11-13 06:18 PST
- COORD directives received: (1) RULEBOOK R-RTL (done, committed 04:0x); (2) DIEVIEW-S81 F5: collapse PMA / KP4 core / port bar into one island, ONE template for all 14 serdes, proper recovered-clock tree, then READY.
- Branch claude/hard-s81-serdes-1-1113 (epyc9 worktree, local commits a143ecdc82, 024764f538, d9f915fb92, 01197b5d5d; NOT pushed yet).
- serdes RTL form LANE (define OT_S81_SERDES_LANE = PIN 3 / TXA 4 / RXI 5 / RXO 3): proof done. bench3/: lane PASS (TX 9251 edges, RCK 9299 edges, 6000 RX beats, 0 bad); mut8/9/10 and xtx/xrx FAIL as required; loopback 88 -> 103 (bench4/ with the bare define). lane_asbuilt_latency on r12bA PASS 873/873 (lat/).
- Placement tools: tools/die_plan/serdes_lanes.tcl (+ release), type key serdes_lanes (schema, gen_phys), serdes_template.py (one template: island under the PMA at the port end; 11 types / 14 instances PASS, max hop 337.5 um, one row set; lane dir tmpl/). Tests: test_serdes_lanes.py 4, test_serdes_template.py 5 pass.
- Kits (epyc9 lane dir): kitA = island at today's plan site (v1 evidence kitA_v1_reports/: lanes fine, place TT -3055 from smeared island logic; v2 = tighter island + density 0.65, placing). kitB = template v3, island under the PMA E end, dchn/SRAMs moved (+902.016, +587.52), placing from floorplan. Logs intel2 ~/hard-s81-serdes-1-logs/kitA_place4 / kitB_place.
  NEXT: for each, read 3_detailed_place.rpt + view run/layout_review/place/density.png; pick the better; write resume.json {"start":"cts", ...} (new text = new done-list key) and run_kit.sh route; read 4_cts (rck tree skew / latency), GRT, sign-off.
  To re-run a step in the same kit the resume.json TEXT must change (done list is keyed by its cksum).
- seqhost__t1: depth class. dsdv_mu_hwin LA=1 (define OT_S81_SH_WIN_LA), exact, 0 cycles: lookahead compares, select at the use edge, kept pointer copies, registered payload. Proof hwin5/: 5 runs x 1.2 M edges 0 mismatches; mutants LA 2 / 3 caught; run small_s21 has bad = 0 but misses its clean-epoch coverage threshold (20, needs > 20).
  Placements: a9 base TT -586 / 5270 endpoints; kitS (LA v1) -500 / 1232; kitS2 (v2) -337; kitS3 (v3, registered payload) placing.
  NOT fixed (host engine, other RTL): ap0_local -> ap1_lp 26 cells, cq_rd -> cx_w 18, ofree -> sp_acc 21, st_rem; fanout u_iss.hh (593 ep), u_sd.n; wire u_l2.cw_d -> u_bout_unit_o4.
- serdes__t14 CRASH 01:32 = PIN_AUDIT "extra 1" (flow), not timing.

## Log
- 11-13 03:1x start. 04:0x RULEBOOK R-RTL committed. Bench run 1 launched via ot-run (log bench1.otrun.log).

## Next
1. Read bench1 results; fix until lane PASS, mutants FAIL, rlat = base + 14.
2. Write serdes_lanes.tcl; copy the a27 kit (without run/), add defines + hook; place via ot-run; view render; route to sign-off.
3. seqhost__t1: read attempt_9 (epyc9, event 7073a6b4a59) once it has a place result; no path report existed before.
4. Latency rows + plan verilog_defines delta + lane_asbuilt_latency; READY.
