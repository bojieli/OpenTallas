# FABLE-TYPES-HEAD 2026-11-14: one structural fix per unclosed HEAD type

Scope: hd_serdes, hd_host_w, hd_mesh, hd_lep0N, hd_ctl, hd_tile, hd_mesh_e, elemA/elemB cores. (hd_spn_end, hd_host_e, hd_ctl_n, hd_spn: FABLE-HARD-QCHEAD.md.) Owner lane: HEAD-99.
Method: read only. Kit logs, reports, sign-off records, placement dumps, macro LEFs, the adopted plan rp21z16, and one read-only database probe (hd_host_w, 2 threads, epyc2). No job was touched, nothing shared was changed.

Status words: MEASURED = read from a log, report, LEF, plan or database. INFERENCE = fits the numbers, not proven.

## 0. Verdict in one table

| type (replicas) | what is in flight | root cause | the one fix | status |
|---|---|---|---|---|
| hd_serdes (12) | wave a4 "routing"; secondary-clock radius forms | wave a4 is dead (CTS killed by host memory 18:11). The floorplan splits the logic into two islands 750 um apart on either side of the kp4_dchn macro; pma_rck enters 660-1300 um from its sinks | re-site the three macros and the pma_rck entry so the data flow is one way (section 1) | MEASURED |
| hd_host_w (1) | outline forms z6c, z9; LEC form z14; wave a8 | SRAM pairs abut on pin faces: the pins of two different nets touch on the seam, and a seam pin under an M6 PG pair has no way out | open every pin-face seam to a street (section 2) | MEASURED (probe) |
| hd_mesh (3) | wave a5 (same plan) | same SRAM bank layout: 3 seams x 12 rows | same event as hd_host_w | seams MEASURED, failure link INFERENCE |
| hd_lep0N (1) | wave a1, private z16, a 21-h GRT | tx SRAM rows sit on the pin faces of all four lep_pair cores and leave 3.4-um slits for 405 pins each; GRT overflow 24,813, flat | stack the two tx rows back to back in mid corridor, widen the slits (section 3) | MEASURED |
| hd_ctl (1) | plan rp21z18 (macro column, taps); wave a6 | reach and clock (FABLE-PLAN-EVENTS 4); wave a5 died of the DRT-0255 pair-row class and a6 is the same kit | z18 plus the face-pair registers; nothing new (section 4) | MEASURED |
| hd_tile (264) | late ECO 2 on the a6 database; wave a8 | near miss: DRC 0, TT -11.09, hold -1.91 ps on 2 endpoints after ECO 1 | finish ECO 2; no plan change (section 5) | MEASURED |
| hd_mesh_e (3) | +10 % height event planned | none: the type is signed off. The "rule C" plan change comes from a plan cell count of 3 | drop the height event; set plan cells (section 6) | MEASURED |
| elemA_cv, elemB_cv | 4 rebuild forms queued for memory since the morning | no design failure: 64 GB requests on hosts that admit 0-61 GB | request the measured size; gate the new .lib against hd_tile (section 7) | MEASURED / INFERENCE |

Class note for every row: all HEAD kits I read (hd_ctl a6, hd_host_w z6c and z14, hd_mesh a2, hd_serdes, hd_lep0N) carry `SLEW_MARGIN 50`, `CAP_MARGIN 20`, `OT_MAXWIRE_UM 120` in config.mk, also the types that are not in `type_args`. They add 5,070-5,806 buffers at GRT (15,495 on hd_serdes). Dropping `type_args` alone does not remove them; check the generated config.mk.

## 1. hd_serdes: two logic islands and a clock that enters at the wrong end

MEASURED, state
- Wave a4 (intel1 `ot-jobs/hd_serdes-route-key-cardinal-2538093-1794708264`): `do-4_1_cts Error 241` at 18:11, peak 14 GB, host load 440-540. Only the LEC container `dpkit-hd_serdes-2543723-lec` is alive. The explorer row "routing / sign-off running" is wrong. No hd_serdes build has ever reached detail route.
- The only CTS result on record is the private pd3 kit (epyc7 `head-97/kitsserdespd3/g_hd_serdes/hd_serdes`, same macro sites): `4_cts_final.rpt` WNS -2524.96 ps, TNS -1,996,690 ps. `pma_rck period_min = 3357.96`, `clk period_min = 1188.43`.

MEASURED, geometry (wave a4 `geom/geom.tsv`, kit LEFs, plan rp21z16)
- Outline 2885.76 x 1226.88. 271,081 standard cells, 44,275 um2, fill 1.1 %. All cells lie in a ribbon x 270-2609, y 5-144 (the band under the PMA area).
- Macros, all inside that band: `kp4_dchn` 276.48 x 138.24 at x 967.68-1244.16; `cmem` SRAM at x 1252.9-1430.7; `dmem` SRAM at x 1486.2-1664.8. Together they close the band from x 968 to 1665.
- Pins: all 2,116 on the S face between x 1603 and 2412 (`pma_rx` 1766-2412, `pma_tx` 1654-2136, `coll_i0` 1825-2030, `coll_o0` 1603-1808).
- Cells per 100 um of x: 3,039 / 10,897 / 14,433 / 15,851 / 13,721 / 8,920 at x 200-800, then 2,356 / 1,153 / 504 / 820 at x 800-1200, then 5,208-23,848 at x 1200-2600. So 71,000 cells form a west island at x 200-800, cut off from the pins by the macro wall. 2,381 of the 5,718 named `u_dec.u_syn` cells (42 %) are in the west island, the rest at x 1200-2100.
- Why: `kp4_dchn` has its 320 inputs (`k_lo`, `k_L`, `k_v`, `k_any`) on the W face and its 559 outputs (`cw_q`) on the N face. It is the west end of the wall, so its input face looks away from the receiver. The syndrome and key-equation logic follows that face to the west; the data runs pins (x 1766-2412) -> west island (x 300-800) -> dchn -> back east to `u_out` and `u_rm` (x 1433-1823).
- The worst path shows it: `u_syn.ldr[0][0]` -> `u_syn.g_bm[0].u_bm.dz[1][5]`, data 3,253 ps with 16 wire repeaters in two runs (5 and 10 in a row), a 539 ps AOI stage and a 297 ps wire stage.
- Clock: `pma_rck` enters at an interior M7 pin at (1106.0, 148.3), over the dchn clock pin (1106.04, 75.07). Its 13,524 sinks are at x 1200-2400 and in the west island. The CTS tree is a chain: 15 `clkbuf_1_0_N` buffers, then runs of 8-18 `delaybuf` cells. Insertion 1,736 ps at the launch flop and 2,515 ps at the capture flop of the worst path; `report_clock_skew` gives 1,417 (dchn) against 1,849 ps. Hold in `u_prx` -132 ps, in `u_ptx` (clk) -104 ps.
- Legalization after the GRT repair (15,495 buffers from `-max_wire_length 120 -slew_margin 50`): `DPL-0701 did not fully converge. Violations remain: 2409` at 3.2 % utilization. GRT itself is empty: usage 2.29 %, overflow 0.

Dead ends
- Relaunching a4 unchanged: it repeats pd3 and the 2.5 ns miss.
- The secondary-clock radius forms (200, 210, 220): the wave kit already passes that check (max radius 121.85 um, 88 leaves). The radius was never the problem; the tree length is.
- Density 0.25 against 0.5, M9 grant: GRT usage is 2.3 %.

Fix (one plan event, hd_serdes only; cores are moved or mirrored, never reshaped)
1. Put the receiver in data order above the `pma_rx` pins. `kp4_dchn` moves to the east end of the macro group, mirrored (MY) so its 320-pin input face looks east at the syndrome logic; the two SRAMs go west of it, next to `coll_o0` (x 1603-1808). No logic remains west of the macros except the relay flops on the S face.
2. Move the `pma_rck` / `pma_tck` / `pma_lock` entry from x 1106 to the centre of the sinks (x about 2090, same y 148.3); it is an area pin under the off-model PMA.
3. If the 154-um band cannot hold the macros and the logic over x 1400-2600 at density 0.5 (44k um2 of cells need about 600 x 150), raise the band over that x range; the outline is 1,227 um tall and growth is pre-approved.
4. Drop the three margin flags for this type.
Proof in one build: place + CTS only (about 1.5 h, 14 GB). Pass = no named `u_syn` cell at x < 1400, `pma_rck` insertion under 600 ps, `pma_rck period_min` under 1,000 ps before repair. Then route.
INFERENCE: the `clk` path `u_enc.ch_q[112]` -> `pp0[173]` (-355 ps before repair, encoder spread over 470 um) closes in repair once the west island is gone; if not, it is the next item, not this one.
Coordination: FABLE-SERDES-STRUCT is reading the same type from the RTL side; this section is the floorplan side.

## 2. hd_host_w and hd_mesh: SRAM pairs abut on their pin faces

MEASURED (hd_host_w z6c, epyc2 `head-99/kits21z6c/g_hd_host_w/hd_host_w`; probe log epyc2 `/srv/opentallas-scratch2/claude/fable-types-head/probe_hw_z6c.log`)
- The 36 `ot_sram_1r1w2c_256x64_m1` macros are 34.584 x 41.352 with 106 M4 pins on the W face and 106 on the E face. Each pin is a 24 x 24 nm stub flush with the macro edge; the macro blocks M1-M4.
- They are placed in pairs at x 69.228 / 103.812, 190.188 / 224.772, 311.148 / 345.732. 69.228 + 34.584 = 103.812: the pair members touch. Database: bank 5 bbox x 190.188-224.772, bank 6 x 224.772-259.356, both R0, same y.
- Both faces use the same y ladder (W: `wd_in[16]` at y 381.900-381.924; E: `w_mask_in[58]` at y 381.900-381.924). So on every seam the E pin of the left macro (x 224.748-224.772) and the W pin of the right macro (x 224.772-224.796) share an edge: two different nets in contact on M4, 106 times per seam and row. hd_host_w has 3 seams x 6 rows = 1,908 touching pin pairs.
- The failing net of z6c, `net69174`, is `wd_in[21]` of bank 6 depth 0 and depth 1. Its pin is at x 224.772-224.796, y 382.380-382.404: on the seam and under the M6 VDD stripe 382.368-382.656 (VSS 381.984-382.272). M4 is closed on both sides, the only way out is up, M6 above is PG, and the one M5 column is shared with the neighbours at 96 nm pitch.
- Same failure on three forms: wave a3 `net62843` and z6c `net69174` in routeBox (230.28, 381.90)-(234.27, 385.89); z9 (macros shifted) `net4401` at (349.98, 381.90). Outline growth north (z6c) and east (z9) did not move it. The PG-track hook was on (783 obstructions).
- Detail route pass 0 ends with 76,316-77,566 violations at GRT usage 6.2-7.8 %. M5 eolKeepOut 10,054-10,102, M5 short 3,481-3,583, V5 CutSpcTbl 2,396-2,439. hd_ctl a5, whose SRAMs do not abut, has 66 / 148 / 35 on the same rows.
- hd_mesh (wave a2 kit, epyc10): 110 macros, same x origins, 3 seams x 12 rows = 3,816 touching pin pairs; 456 seam-face pins per seam lie under an M6 PG pair. Pass 0: 142,385 violations, V5 CutSpcTbl 4,857. Its DRT-0255 net is `g_fifo_safe.u_m.wdata[426]`, access points 96 nm under a PG pair at y 792.288.
- The adopted plan rp21z16 still has the origins 69.12 / 103.68, 190.08 / 224.64, 311.04 / 345.6 for hd_host_w. The running wave builds (hd_host_w a8, hd_mesh a5) and the private z14 route (in pass 0, 66,022 violations at 90 %) carry the seams.
INFERENCE: hd_mesh fails for the same reason (seams measured, its failing pin not probed).

Dead ends
- Outline forms z6c and z9, density, margins, hook: none opens a seam. A seam with touching pins cannot reach DRC 0 by routing.
- z14 proves the LEC fix only; its route will end like a3.

Fix (one plan event for both types)
- A pin face may abut nothing. Open each seam to a street: move the right member of every pair east by 17.28 um (four PG pitches; 8.64 is the minimum I would try). hd_host_w needs 3 x 17.28 = 51.84 um; x 380-449 is free, so no outline change. Same rule for hd_mesh.
- Rule for `street_rule` / `hw_relayout.py` / `mesh_relayout.py` (R-STREET-1 reads "abut or 43.2 um"): abutment is legal only between faces without pins. Add the scan to the prep gate: two macros whose facing edges are closer than 2.16 um and carry pins on either face.
- Side A/B only: drop the margin flags.
Proof in one build: hd_host_w from the new plan to detail route pass 1. Pass = pass 0 M5 eolKeepOut under 1,000 and no DRT-0255 at x 103.8 / 224.8 / 345.7.
Scan the other dies for the same construct (S81 and QC bank arrays use the same macro family); not done here.

## 3. hd_lep0N: SRAM rows on the pin faces of the four pair cores

MEASURED (epyc7 `phys-kvhead/kits/g_hd_lep0N/hd_lep0N`: `congestion-5/10/15.rpt`, `macro_place.tcl`, LEFs; plan rp21z16 has the same tx origins)
- Global route does not converge: 19,000 congested gcells, total overflow 24,813 at iteration 15; the report had 77,264 / 76,628 / 76,000 lines at iterations 5 / 10 / 15. The job sat in GRT for about 21 h (started 11-13; the ot-run client reports exit 143).
- Four `ot_s81hd_lep_pair` cores, 777.6 x 492.48, blocked M1-M7: two at y 17.28-509.76 (MX and R180), two at y 665.28-1157.76 (R0). Each has 1,116 pins (`k_li_d`, `k_lo_d`, M5/M7) on its S face, which is the top edge for the lower cores and the bottom edge for the upper ones, and 1,026 pins on the W face.
- Twenty `ot_sram_1r1w_512x128_m4` (169.368 x 29.16, 203 pins W, 202 pins E, M4) in two rows: y 509.772-538.932 and y 635.052-664.212, pitch 172.8 in x.
- So the lower row starts 12 nm above the pin edge of the lower cores, the upper row ends 1.07 um below the pin edge of the upper cores, and the gap between neighbours in a row is 3.432 um for 405 pins.
- Overflow by region: vertical over the tx rows 8,099, vertical in the slits and row ends 2,072, horizontal just under the rows inside the lower core footprint 4,780, corridor between the rows 1,024, mid street at the rx column 1,176. 8,401 of the congested gcells have capacity 0. Hot bins: (x 1700-1900, y 500-600) 7,556; (x 900-1000, y 600-700) 3,189.
- The 20 rx memories at x 846.828 start 0.108 um from the E edge of the west cores (x 846.72).

Dead ends
- The wave a1 launched 19:16 and the private z16 kit use this floorplan (z16 only snapped the straps): both will stop in GRT near 25,000.
- More GRT iterations: flat from 5 to 15.

Fix (one plan event, hd_lep0N only)
- Stack the two tx rows back to back in the middle of the corridor (N and S faces of this SRAM carry no pins): rows at about y 558.4 and 587.6. That leaves two 48-um streets between the SRAM stack and the pin edges of the pair cores, where the `k_li_d` / `k_lo_d` logic can sit.
- Widen the slits: 10 macros of 169.368 in 1,892 um leave 198 um, so pitch 187.2 gives 17.8-um slits.
- Move the rx column off the core edge by a street (x 846.8 -> about 864, the mid street is 69 um wide).
- If the corridor is short, grow the outline in y; growth is pre-approved.
Proof in one build: place + GRT (about 3 h). Pass = overflow 0 within 30 iterations and no capacity-0 gcell in the report.

## 4. hd_ctl: nothing new beyond rp21z18

- Wave a5 (epyc10) died with DRT-0255 on `net33012`, access points at y 192.552 (inside the PG pair 191.904-192.576) and 192.672 (96 nm above it), hook on: the measured pair-row class of FABLE-HARD-QCHEAD 5.
- Wave a6 (epyc7, in GRT at 19:5x) is the same plan and config (SLEW_MARGIN 50, 5,806 buffers). INFERENCE: it ends like a5.
- The path to closure is rp21z18 (macro column in write-pair order, taps 34 -> 68) with the face-pair registers of TYPE-HDCTL-REGS; see FABLE-PLAN-EVENTS 4. Check the z18 SRAM column for pin faces closer than 2.16 um (section 2 rule); z18 streets are 47.5 um, so it should pass.

## 5. hd_tile: near miss, no plan change

- Private route (intel1 wave a6 kit): DRC 0, TT +74.83, FF hold -19.44 on 56 core endpoints. All are flops against the elemA/elemB hard cores (`g_ais.u_ad1/q[161]` -> `u_eA0`, pair skew 147-185 ps).
- ECO 1 (16,140 s): TT -11.09 on 2 endpoints (`row0_q[6]` -> `g_rir.rir_q[16]`, inside the -42 gate), FF -1.91 on 2 endpoints (`u_eA3` -> `flt_q[3]`), DRC 0. ECO 2 runs on that database (`eco99_tile_c`, container up since 18:55).
- Fix: let ECO 2 finish; it needs 2 ps on 2 endpoints. The wave a8 rebuild is the fallback. If elemA/elemB are replaced by rebuilt cores, see section 7.

## 6. hd_mesh_e: signed off; the planned height event is not needed

- Wave a2 (epyc10): `LOCAL_PASS_NEEDS_PARENT`, TT +135.13, internal hold 0 violations (the 6-12 failing endpoints all start at ports), 3,862 standard cells, 893 flops.
- The rule C line reads "measured/plan cells 977 > 1.5 ... carries 2931 cells; grow the soft area x0.10 (to 6979 um2)". The plan has `cells = 3` for hd_mesh_e (rp21z16); 2,931 / 3 = 977. The ratio measures a stale plan number, and "x0.10" of 72,410 um2 is a reduction, not +10 %.
- Fix: set `cells` to about 3,900 in the plan block at the next event; do not change 838.08 x 86.4. Archive and count the a2 record. The a3 relaunch (18:20) adds nothing.

## 7. elemA_cv / elemB_cv: queued, not failing

- The four rebuild forms (A1/B1 intel1, A2/B2 epyc9) have waited all day: each asks 64 GB; intel1 admitted 61 GB and epyc9 20 GB at 19:10. Cores are 319.68 x 319.68 with two ROM macros, M5 ceiling. INFERENCE: the real peak is far below 64 GB (hd_tile ECO on 912k instances measured 13.6 GB); ask 24 GB and they start.
- Risk to check before adoption (INFERENCE): hd_tile is timed against the signed libs (`results/head_core_clockfreeze_release/elem{A,B}_signed/*_tc.lib`, `*_BC.lib`). Its remaining hold endpoints are exactly the core boundary. A rebuilt core with other clock-to-pin delays changes those numbers. Gate: run the hd_tile sign-off STA on its routed database with the new libs (minutes, no route) before the new records replace the old ones.

## 8. Evidence

- hd_serdes: epyc7 `head-97/kitsserdespd3/g_hd_serdes/hd_serdes/run/reports/asap7/dp_hd_serdes/base/4_cts_final.rpt`, `logs/.../5_1_grt.log`; intel1 `.../items/hd_serdes/attempt_4/geom/geom.tsv` and `gen/hd_serdes/macros/*.lef`.
- hd_host_w: epyc2 `head-99/kits21z6c`, `kits21z9`, `kits21z14`; epyc10 wave `items/hd_host_w/attempt_3`; probe epyc2 `/srv/opentallas-scratch2/claude/fable-types-head/` (`probe_hw.tcl`, `probe_hw_z6c.log`), client log intel2 `~/fable-types-head/hw_z6c.heavy.log`.
- hd_mesh: epyc10 wave `items/hd_mesh/attempt_2`.
- hd_lep0N: epyc7 `phys-kvhead/kits/g_hd_lep0N/hd_lep0N`.
- hd_tile: intel1 wave `items/hd_tile/attempt_6/gen/hd_tile` (`signoff/`, `eco99_tile_b/`, `eco99_tile_c/`).
- Not done: a build of any fix; the hd_mesh failing pin probe; the scan of other dies for abutted pin faces; the elemA/B memory measurement.
