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

## State 11-13 11:41 PST (HARD-S81-SERDES-1 back after SERDES-FIN-2's HANDBACK; read lanes/handoff/SERDES-FIN-2.md too)
Branch claude/hard-s81-serdes-1-1113 on hub, tip 7bc91da2bdca (+ uncommitted in the epyc9 worktree: serdes_lanes.tcl regions, tools/die_plan/serdes_groups.py). No READY posted (freeze to 11-15 04:00).
Lane dir epyc9 /srv/opentallas-scratch2/claude/hard-s81-serdes-1, logs intel2 ~/hard-s81-serdes-1-logs.

serdes__t2 kits (all = LANE rows + cone set RST_TREE RM_STAGED RM_LOCAL4 RM_WFULL8 KP4_SYN_LOCAL KP4_AM_FACE3 CLAND_WCHK unless noted):
- kitC2 (island under PMA E end, no anchors): place TT -2372 / 4142 ep (Sl -> RiBM 2247 ep, enc rem_q 300 -1492, ld2 464 -985). POST-CTS: setup -2389, hold -606 (PMA q -> lane row 0), rck tree 28,628 sinks, 30-33 levels, avg sink wire 1339 um, macro pin latency 1543 vs row 0 2169 ps. In GRT repair (log kitC2_route). LEC: kitC (same netlist sha b4c0a986a91d593a) runs it in the foreground.
- kitD (+ENC_LA +BM_PE_LOCAL, island 1000x450, register raster anchors): place -5231. kitE (kitD + SPCYC + PPCYC): -6219. Both DEAD: anchor boxes ~10x too large, registers spread, logic in saturated blobs. ENC_LA removed the encoder rem_q class.
- kitF (kitC2 geometry + ENC_LA + folded RiBM OT_S81_KP4_BM_IT2, no BM_PE_LOCAL): first two builds refused by the 400k cell cap (522k with 7 units; 405.6k interleaved with PE_LOCAL). Third build running (log kitF_place3).
- kitG (kitD netlist + placement REGIONS from tools/die_plan/serdes_groups.py membership, registers free): running (log kitG_place). Unknown whether this OpenROAD GPL honours dbGroup regions: read 3_3_place_gp.log.
- kitH (COORD option (a): island under the PMA W end where io_pma_rck enters; rows PIN 6 / RXO 6; + ENC_LA): running from synth (log kitH_place). Bench bench13 (LANE 6 4 5 6) running.
Benches done (lane dir): bench7 kitD set PASS, loopback 110; bench8 kitE set PASS 112; bench11 + kp4g3 + kp4g4 folded RiBM PASS, 142, mutant (15 iterations) FAIL; bench12 (kitF exact set) running.
To re-run a step in a kit the resume.json TEXT must change. A kit copy must keep lec_async.sh (else blocking LEC) and signoff.py (else preflight FAIL).

seqhost__t1: kitS5 (= kitS4 netlist sha 1316154b3716b175, hwin LA + SS): place -216 / 1884 ep (u_iss.hh 1232, f_code 277, u_win.vld 125); in GRT repair (log kitS5_route). Host-engine cones not fixed.

NEXT: (1) post-CTS numbers for kitH / kitG / kitF as they place: resume.json start cts, run_kit.sh route. Compare rck tree (4_1_cts.log CTS-0098 block of io_pma_rck[0]_regs, 4_cts_final.rpt clock skew). (2) if kitH's tree is sane, fold the winning cone/region form into it. (3) option (b) (trunk to a local root) only if the pin side must stay. (4) READY after the freeze: RTL + tools + plan delta (serdes_template.py must learn the pin-end rule and rows 6/4/5/6 if kitH wins).

## Log
- 11-13 03:1x start. 04:0x RULEBOOK R-RTL committed. Bench run 1 launched via ot-run (log bench1.otrun.log).

## Next
1. Read bench1 results; fix until lane PASS, mutants FAIL, rlat = base + 14.
2. Write serdes_lanes.tcl; copy the a27 kit (without run/), add defines + hook; place via ot-run; view render; route to sign-off.
3. seqhost__t1: read attempt_9 (epyc9, event 7073a6b4a59) once it has a place result; no path report existed before.
4. Latency rows + plan verilog_defines delta + lane_asbuilt_latency; READY.

## CODEX notes 2026-11-13 07:0x PST
Direct takeover in the existing epyc9 tree/branch. kitA v2 PLACE finished exit0: flow TT WNS -1101.39 ps, FAIL. Viewed actual run/layout_review/place/{layout,density}.png: KP4 logic remains in south island far from north PMA; local density .834; route HOLD. kitB template-v3 PLACE and kitS3 PLACE remain healthy, not restarted. Read-only current-A STA launched through ot-run, intel2 frontend1583795, epyc9 unit oth-ubuntu-3165769-1794582058, output sta_kitA_v2, log ~/hard-s81-serdes-1-logs/sta_kitA_v2.otrun.log. This diagnostic uses the inherited helper (different report context than flow; TT WNS -932.23, not signoff): worst PMA face register -> decoder syn.am_ok -932ps; FIFO rp_g2 -> memory -856ps; read pointer -> read data -625ps. Causes remain long-wire/fanout inside misplaced island; no blanket ECO. Wait for template-v3 actual placement before next redesign/route. Existing exact+mutant receipts preserved. PIN_AUDIT extra1 requires exact failed capsule identity from shared wave owner, requested via parent.
