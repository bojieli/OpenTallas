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

## State 11-13 03:50 PST
- serdes RTL form LANE: DONE in the worktree (uncommitted): ot_pdie_serdes_col LANE_PIN/TXA/RXI/RXO, bare define OT_S81_SERDES_LANE = 3/4/5/3.
  Proof (epyc9 lane dir bench3/, bench3r/): lane PASS (TX 9251 edges, RCK 9299 edges, 6000 RX beats, 0 bad); mut8/mut9/mut10/xtx/xrx FAIL as required; loopback latency 88 -> 103 (+15).
- serdes placement form: tools/die_plan/serdes_lanes.tcl + serdes_lanes_release.tcl, type key serdes_lanes (schema + gen_phys + test_serdes_lanes.py, 4 pass).
- serdes__t2 proof kit: epyc9 lane dir kitA/gen/serdes__t2 (a27 kit + patched column + value defines 3/4/5/3 + hooks). Place launched via ot-run (log kitA_place.otrun.log). NEXT: read OT_SERDES_LANES log lines, view run/layout_review/place/*.png, then resume.json {"start":"cts"} and run_kit.sh route.
- seqhost__t1: NOT the serdes class. a9 placement (wave job dir epyc9 /srv/opentallas-scratch2/claude/ot-jobs/seqhost__t1-place-renewed-glider-677733-1794552059/work) is compact; STA (lane dir sta_seqhost_a9/, a9b/): TT -586, 5270 endpoints. Cones: u_win pe 24 cells (-586, 606 ep), u_win rp 21 cells (-457), u_win lw 18 cells (-239, 3488 ep), host engine ap0_local -> ap1_lp 26 cells (-182), cq_rd -> cx_w 18 (-173), ofree -> sp_acc 21 (-117), plus wire/fanout: u_sd.n -> h (-94), u_iss.hh (-90, 743 ep), u_l2.cw_d -> u_bout_unit_o4 787 ps wire (-43).
  Fix done for u_win only: dsdv_mu_hwin LA=1 (define OT_S81_SH_WIN_LA), exact two-candidate lookahead, 0 cycles. Proof lane dir hwin2/: 5 runs x 1.2 M edges 0 mismatches, mutants LA 2/3 caught (small_s21 run misses its clean-epoch coverage threshold 20 vs > 20, bad = 0).
  Proof kit kitS/gen/seqhost__t1 (a9 kit + LA) placing (kitS_place.otrun.log). The host-engine cones are NOT fixed.
- serdes__t14 CRASH = PIN_AUDIT "extra 1" flow error, not timing; t14 and t1 share the column, so form LANE applies with their own lane cfg (not built yet).

## Log
- 11-13 03:1x start. 04:0x RULEBOOK R-RTL committed. Bench run 1 launched via ot-run (log bench1.otrun.log).

## Next
1. Read bench1 results; fix until lane PASS, mutants FAIL, rlat = base + 14.
2. Write serdes_lanes.tcl; copy the a27 kit (without run/), add defines + hook; place via ot-run; view render; route to sign-off.
3. seqhost__t1: read attempt_9 (epyc9, event 7073a6b4a59) once it has a place result; no path report existed before.
4. Latency rows + plan verilog_defines delta + lane_asbuilt_latency; READY.
