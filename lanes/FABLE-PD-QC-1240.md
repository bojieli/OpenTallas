# FABLE-PD-QC 1240: QC N3/N4 type failures outside st_a/st_b, root causes from kit reports

2026-11-18 12:40 PST, FABLE-PD-QC, read-only. Evidence was read 10:37-11:00 and refreshed 12:37 (a usage limit paused the lane in between). Sources: failure_breakdown.py, autopilot/log.txt KIT-WAVE FAIL lines since 07:50, kit_wave_stages.tsv, OWNERS-SWEEP 09:50, lane posts, and the live ot-jobs work dirs on epyc9 / intel1 / epyc2 / epyc8 (run_route.log, 4_cts_final.rpt, congestion.rpt, tt_setup_repair.log, hold_guard_grt.tcl). Two read-only OpenROAD queries on 4_cts.odb for cell positions (cbx_q10__cl94a12200 on epyc9, sle_stm_v3 on intel1). st_a / st_b are FABLE-FIX-QC-STA's and are left out. **V** = read this round, **E** = estimate.

## Verdict

- The 07:50 blocker is gone: the vclk stop no longer occurs. 14 kits print `OT_VCLK_MEASURED_BAND ... PASS` (dev 9-26 ps of tol 40) (V).
- First routed N3 results: sle_hc0__cl929603c0__cl38badc56 and __cl4baa7c9c finished detailed route with 0 violations (111,617 -> 16,651 -> 11,139 -> 296 -> 4 -> 0; 15,291 s and 13,551 s) and are in 6_report at 12:37 (V). Sign-off numbers are not out yet.
- Three families will fail on timing for a structural reason that N4 does not change: cbx_q10 (4 types), sle_stm_v3, sle_hc1__cl7d360508. One is marginal: coll_ftc.
- The largest time loss on every other kit is the GRT hold repair: 1.5 h on hc, 4-6 h on sc, most of it after hold is already >= 0.
- No design FAIL row was posted by the wave since 07:50. All QC KIT-WAVE FAIL lines in that window are flow, plan-data or host: FT bit-site collision (9 types, folded into N4), disk full on epyc2 at 09:49 (9 types), KIT_TOPOLOGY_BIND_STALE on N4 (5 types, FAIL-ROUTE-1115 already asked QC-PLAN-R3 at 10:38).

Count note: failure_breakdown prints QC types 26/130 signed and cores 70/70; the brief said 70 types plus 26 tiles. I did not reconcile the two.

## What the 07:50 levers did

| 07:50 lever | result |
|---|---|
| 1 swap vclk file in live work dirs | done by QC-TYPES-R3 08:00; works, 14 BAND PASS, 0 new vclk stops (V) |
| 2 N4 gen from rt/current | wave gens from a launch tree with rt tools (FABLE-FIX-QC-STA 10:22) |
| 3 builder for 16 child cores | 33 signed child views bound to 21 parents in N4 (QC-PLAN-R3 09:22); su_c btab/prog still provisional |
| 4 port_in hold padding | main ee7566bd8b7 08:04, new kits only. Running kits still carry it: slw_fe_v1__cl95cd1d0c 28,001 pre-GRT hold cells, slw_fw_v1 19,775, sle_hc0 15,927 / 15,490 (V) |
| 5 cbf_q01_s2 FT site | deduped on 9 types in N4 |
| 7 duplicate containers | cancelled 08:00 |

## 1. Root causes, ranked

### R1 cbx_q10 (cl89936551, cl89936551_h, cl94a12200, cl94a12200_h): ID-strap register 1.45 mm from its station. Owner QC-PLAN-R3

- TT setup after CTS -983 / -990 / -1117 ps, 128 endpoints each, tns -72 to -84 ns (V). GRT setup repair on cl89936551_h has ground for 960+ iterations and sits at -545 ps (V, 12:37).
- Worst path (V, 4_cts_final.rpt): `u_fab_u_x_3_1.u_st.g_seg[3].sx[0]` -> 25 single-load buffers -> XOR2 / OR4 / AO221 / AOI22 -> `tap_d[502]`. Arrival 2,109 ps against 909 required. About 1.6 ns of it is the buffer chain.
- Positions (V, odb query): the chain starts at (642, 1333), runs north along x 688 from y 1527 to 2222, then crosses the full width of tile u_t31 (x 691-1149) in one 463 um hop to (1151, 2240); the compare logic is at (1155-1173, 2263-2283). Manhattan length about 1,450 um.
- Why: `sx` is the registered copy of the station ID strap (`sx <= sidx`, qfd_c_stn.sv ot_qfd_xcst_rep). All 12 `strap_u_fab_u_x_{2_0,2_1,3_0,3_1}_sidx` pins are placed as interior pins in one cluster at the block centre, x 609-635, y 1292-1318 (V, io.tcl). The port is false-pathed, so nothing pulls the flop to its loads; the sx -> hold-bank path is single-cycle. QC-CBGLUE-1116 split sx per segment for slew (was -1,093); the distance was never removed.
- Same cause for the GRT overflow: 1,666-1,998 total, 100 % in gcells of capacity 0 over the four tiles, from 17 nets (V, congestion.rpt of cl94a12200: t21 854, t31 692, t20 114, t30 16). These are the long repeater nets crossing a tile on M6 / M8.
- The kit says so itself: `OT_XSTN_KEEP u_u_fab_u_x_3_1 face E ... boundary_reg_um 1001 (an output of the xstn leaves across the tile; plan event needed)`, also for u_x_2_0 and u_x_2_1 (V).
- Fix 1 (plan data, no bind change): place each station's 3 sidx strap pins at that station (u_x_3_1 near x 1160, y 2270 on the E face of t31; the others at their own station). The flops then sit next to their compare logic. Not verified by a build.
- Fix 2 if pins cannot move: the strap is tied and static, so the sx registers may be dropped and the compare fed from the strap net directly (RTL, same function). Needs a bind change.
- N4 does not touch this; the four N4 relaunches will repeat it.
- The three epyc9 kits also hit the tt_setup_repair.tcl line-135 Tcl error (fixed on main 922c27887ac by WAVE-FLOW-R2). It is not the cause: repair_timing had already reported "Unable to repair all setup violations" (V).

### R2 sle_stm_v3 (attempt 19): 1.27 mm unregistered hop xb -> so_e. Owner QC-PLAN-R3

- TT setup -212 before, -203 after repair, tns -68 ns (V).
- Worst path (V): `u_core.u_stream.xb[4]` -> OAI21 -> 26 single-load buffers -> `so_e[4]`. The chain runs from (202, 1309) to (496, 329) in a 613 x 1832 block (V, odb query). The stream core sits by the ROMs at y 1486-1661; the so_e capture flops sit at the east face near y 330.
- slw_stm_v3 signed on 11-16, so this is the east variant's pin position, not the RTL.
- Fix: move the so_e pin band up to the stream core (about y 1300), or add stations on the so_e bus (3 hops at the 405 um reach; changes latency). Pin move first. The so_e pin coordinates themselves were not read.
- sle_stm_v1 / v2 are in CTS / GRT now; not yet measured.

### R3 sle_hc1__cl7d360508: write-enable fanout, routed -59.5. Owner QC-TYPES-R3

- Last routed result (Q6D kit on epyc10, signoff.json, V): TT setup -59.5 ps, 80 endpoints, tns -1.8 ns; hold -19.8 TT. GRT estimate was -28.6, so route cost 31 ps. The late ECO fixed FF hold (-43.8 / 168 ends -> 0) and pushed TT to -141.
- Worst path (V, signoff/tt/sta.log): `u_u_xl1_1.wep` -> `g_t[1].g_e[52].m[10]` enable: one write-enable register driving a register-array bank.
- Fix: duplicate `wep` per g_t bank (RTL, same cycle). Until then the N4 relaunch (retry key @1, QC-STRAGGLERS 09:54) most likely repeats -60. The 17.5 ps it misses by is not reachable with repair: the GRT pass already ran.

### R4 GRT hold repair time, all kits. Owner QC-TYPES-R3 (flow file hold_guard_grt.tcl)

- First chunk cap is 0.25 % of instances (1,075-1,351 buffers). Rate is 3-5 buffers per minute, one thread.
- hc0: chunks 3,269 + 1,365 + 1,040 s. Hold was met after chunk 1; chunks 2 and 3 added 2 ps in 40 min. End state ws +6.6 (V).
- sc: slw_sc_v1__cl63e5a7a2 started 08:23, crossed ws 0 at about 280 buffers (about 09:15), and is still in chunk 1 at 12:37 with 1,318 buffers, ws +18 (V). sle_st_b_v1__pv0e7b1dcc chunk 1 took 7,946 s.
- The 40 ps margin is never reached: finished kits end at +5.0 to +8.2 (coll_ftc +26.5) (V).
- Fix: first chunk = OT_HOLD_CHUNK_BUF_MIN (200) so the existing "ws >= 0 and gain < 1 ps" stop can act, and end the chase at a fixed small pad (10 ps) rather than 40. Saves about 3 h per sc kit and 40 min per hc kit (E). Check first: the two routed hc0 kits give GRT +6.6 against routed FF hold. If routed hold is >= 0 there, apply it; if it is negative, keep 40 and only shrink the chunk.

### R5 coll_ftc: -48.9 TT, 7 ps outside the gate. Owner QC-TYPES-R3

- After repair -48.9, tns -568 (V). Worst classes in the CTS report (V): input port `arl_wo_in_last_i[1]` -> 8 buffers -> first ring flop (-39), `cland_tstart_in` -> origin flop (-19), ring dsel (-24). All three are port-to-first-flop distance in the landing rings.
- Fix: none yet. Read the routed number first; if still below -42, site the arl_wo_in_last ring flops at their pins (the OT_CLAND pinslot pass covers a22_i-style rings only).

### R6 flagged types

- slw_hc0__cl1bc59e1c: its only failure was the vclk stop. That class is fixed; no design evidence against it. Sister slw_hc0__cl4f54b7a3 is at TT +20.0, hold chunk 1 ws +3.75 (V).
- slw_hc1__cl68f9248e__cl144ee7b3: TT -11.0 -> +5.6 after repair, hold +6.56 (V). Fine.
- sc family: TT +11 to +19 during GRT; overflow 0 at 14-16 % usage (V).
- PHYs (phy_serdes, phy_serdes_b, phy_ucie_kv) and coll_ft__cla4a25d77: no build since S3M2. Last errors are gen errors ("hard wrapper requires a placed macro with LEF and TT/FF views"; "native clock table must resolve inside its declared native base"), not design (V). Keyed for N4 by QC-STRAGGLERS; expect the same gen errors.

## 2. Fix order

| # | fix | evidence | owner |
|---|---|---|---|
| 1 | cbx_q10: sidx strap pins to their stations (plan pins), one pilot type | -983 to -1117 ps; chain 1,450 um from block centre; 1.7-2.0k overflow all over tiles | QC-PLAN-R3 |
| 2 | sle_stm_v3: so_e pin band to the stream core | -203 ps, 26-buffer hop 1.27 mm | QC-PLAN-R3 |
| 3 | GRT hold guard: 200-buffer first chunk, 10 ps pad, after the hc0 routed hold check | 4 h+ in chunk 1 on sc, ends at +5 to +8 anyway | QC-TYPES-R3 |
| 4 | sle_hc1__cl7d360508: duplicate wep per bank | routed -59.5, 80 ends | QC-TYPES-R3 |
| 5 | Read sign-off of the two routed sle_hc0 kits; use them as the GRT-to-route reference | DRT 0 at 12:37 | QC-TYPES-R3 |
| 6 | coll_ftc: read routed TT, then ring-flop siting if < -42 | -48.9 | QC-TYPES-R3 |
| 7 | PHY / coll_ft gen errors | gen text above | QC-STRAGGLERS |
| 8 | N4 KIT_TOPOLOGY_BIND_STALE x5 | wave 10:16 | QC-PLAN-R3 |

## 3. Stop list

- Do not relaunch cbx_q10 on N4 unchanged; 4 kits x about 8 h for the same -1 ns. The three live N3 kits can be cancelled once fix 1 is in a plan row.
- Do not start congestion or re-floor work on cbx_q10: usage is 5 %, the overflow is 17 nets over the tiles.
- Do not add setup repair passes to cbx_q10 or sle_stm_v3; both are wire length.
- Do not run a second late ECO on sle_hc1__cl7d360508; the first one cost 82 ps of setup.
- Do not split or re-floor hc0 / hc1 / sc / fe / fw: GRT overflow 0, DRT 0 on the first two.
- Do not judge sle_stm_v1 / v2 by v3 before their own CTS numbers.

## Not checked

- No sign-off (routed TT, hold, DRC count in signoff.json) exists yet for any N3 kit; the two hc0 kits were in 6_report.
- Fix 1 and fix 2 are not proven by a build.
- so_e pin coordinates of sle_stm_v3; station positions of u_x_2_0 / 2_1 / 3_0 (only u_x_3_1 was located).
- epyc8 jobs after 10:43 (the 12:37 refresh timed out there); epyc8 scratch2 was at 53 GB free and sle_sc_v1__cl115da35f in WAIT-DISK at 10:43.
- fe / fw routed behaviour; glue, tt_ctlm, native59, cbf, cbn are still in place / CTS / early GRT with no timing number read.
