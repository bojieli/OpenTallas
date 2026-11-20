# FABLE-PD-HEAD-0015: HEAD die physical-design review (r12, hd_tile, hd_lep0N, hd_host_w)

2026-11-19 23:37 to 23:52 PST. Reviewer lane, read-only: no job launched, stopped or patched; no plan, kit or main change. Plan reviewed: the r12 candidate `head_rp21z20NF15f_r12` (private tree `tree_r12x`, not yet gated when I read it). Predecessor: `lanes/FABLE-PD-HEAD-2040.md`.

All host paths are epyc10 unless a host is named. `HC` = `/srv/opentallas-scratch2/claude/head-crossing-1119`, `FM` = `/srv/opentallas-scratch2/claude/fable-fix-head-mesh`, `KW` = `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head`. Log times on the gen hosts are UTC.

## Summary

1. **r12 has two row gaps, both fixable before publish.** Die clock run f moved 12 trunk repeaters onto sites in hd_host_e, hd_lep0N and hd_mesh that have no reserved row. The hd_serdes per-port window rows still describe the old 22-tap table. Everything else in r12 checks out: reach passes, and every non-serdes tap has the same tree depth and path length as in e5c.
2. **hd_tile: form A windows should go into the plan now.** At placement RC they give +15.6 ps of setup, 9,200 fewer hold cells and 2,350 fewer failing FF ends than the r8 windows, and they are the only form in which the pre-GRT hold build survives. The setup repair is at its sizing limit (it was asked for 40 ps and stopped at +16.83), so the routed number will be close to the -42 gate either way.
3. **hd_lep0N is both.** No attempt finished because the route job re-runs floorplan and placement (2 h 46 min on the r8b kit before CTS started). But the placed r8b kit also has 26 register groups that need a station and have no plan row, 149 bits of one face bus estimated beyond one cycle. The route will finish and will most likely fail TT.
4. **hd_host_w: the tap table covers the south-west quarter of the outline.** All 40 taps sit at x 10..364, y 67..294 of a 734 x 570 um type. Seven taps carry about 3,000 sinks each with trees too deep to balance to 450 ps, and 12 taps carry 1 to 3 sinks. The fix is the r12 hd_serdes method: a density tap table from a fresh placed census.
5. **New fact:** the r8b hd_host_w wave kit finished and is NOT SIGNED (TT -56.32, FF hold -21.08, DRC 0). It fails for the reason in item 4.

## A. r12 structural review

### What r12 changes
Plan diff r11b to r12 (`s81_head_r11b_s0` prep `source_plan.json` against `HC/r12/source_plan.json`): 5 leaves, all in hd_serdes.
- `clock.taps` 22 to 37 rows
- `clock.reserved_sites_um` 537 to 177 rows
- `clock.native_domains` census file and two digests

Plus the die clock directory (run f: `HC/clock_early/tree_e5c12f`, e5c config, kit_tree 15a37008) and three tool patches (ring reset fan copy, stage-ODB keep, gen_phys). No pin, lane, latency, window or offset row changes.

Gate state when I read it: `gen12.sh` (gen pass, republish, bind, LATCHECK, G0) had waited 21 min for 96 GB on epyc10 and had not started. So bind, LATCHECK and G0 on r12 are not yet evidence. The plan diff contains no lane or latency row, and the reset copy is a +0 cycle form, so I expect LATCHECK 329/329 unchanged; that is an expectation, not a result.

### Findings

| # | Area | Finding | Evidence |
|---|---|---|---|
| A1 | Clock rows | 12 die clock cells have no reserved row. Run f re-built the trunk feeds to the 12 hd_serdes regions and moved repeaters that sit over other types: hd_host_e 2 (r223_0, r223_1), hd_lep0N 5 (r403_0 to r403_3 and b403; b403 moved 118 um, r403_3 is new), hd_mesh 5 (r467_1, r531_1, r531_2, r587_0, r587_1). The row script regenerates only hd_tile, hd_spn_wshim_rx and hd_serdes. | intel2 `~/hc1119/r12_rows.log`: hd_host_e 59 cells / 57 inside, hd_lep0N 581 / 576, hd_mesh 752 / 747. `r10_rows.log` (e5c): 59/59, 580/580, 750/750. Cell names from my re-run of the contain check on `HC/r12/rows/plan_nudge.json` + `kit_tree_nudge.json`. `HC/r12/r12_rows.sh` line `TYPES="hd_tile hd_spn_wshim_rx hd_serdes"` |
| A2 | Windows | `clock.tap_window.per_port_ps.hd_serdes` still holds the 22 rows (50..94 ps) measured on the old table. The new table reuses the names clk and clk_t1..t21 at different places, so those values now sit on the wrong taps. clk_t22..t36 have no row and take the type value 94 ps; all 15 are in the dense PHY cluster (x 1240..1466, y 141..236). | plan row; `HC/r12/taps_new.json`; `tree_r12x/tools/die_plan/gen_phys.py` lines 2827-2828 (a port missing from the table takes W_t) |
| A3 | Die STA | No related-pair STA has run on run f: `HC/runs/s81_head/` ends at `l1119e5d`. The hd_serdes kit window need on r12 and the kit-contract hold are unmeasured. | directory listing |
| A4 | Clock, other types | Good. All 12,858 taps outside the hd_serdes regions have the same stage count and the same root-to-tap path length in run f as in e5c. hd_tile windows, form A and the hd_lep0N offsets therefore stand on run f. | my walk of `parent_of`/`sites` in `tree_e5c/kit/clock/tree.json` and `tree_e5c12f/kit/clock/tree.json` |
| A5 | Clock, hd_serdes | Good. In each serdes region the 37 taps are within 160 um of path length (0.9 %) and 2 stages of each other; any two taps share all but at most 13 stages. Longest tap leg 89.6 um. | same walk, regions lk_ES1 and lk_HOST0 |
| A6 | Reach | PASS. Die clock worst edge 386.2 um, 0 over 405, 0 missing sites. Tap radius at most 162 um, at most 662 sinks per tap, 0 empty. | `tree_e5c12f/kit/clock/actual_reach.json`; HEAD-CROSSING 22:19 post |
| A7 | Pins | The hd_serdes `clk` port moves from (1439.3, 20.4) to (1454.4, 107.9). The pma_tck leg from that port to the pin at (1114.7, 148.3) is now 380 um Manhattan, inside the 405 um hop (it was 399 to 453). The `export_insertion_ps` estimate 135/110 was made for the old leg and is still marked `measured: false`. | plan `pad_clock.pins[pma_tck]`, `taps[0]` |
| A8 | Stations | Good. The two coll_i0 stations keep a tap nearby in the new table: st0 (1815, 40) is 57 to 67 um from clk_t13 / clk_t8, st1 (1646.5, 79) about 75 um from clk_t11 / clk_t7. | `taps_new.json` |
| A9 | Reset fan copy | Not verifiable yet: the regenerated hd_serdes wrapper does not exist until gen12 runs. The copy flop and the original must sit on one tap or be covered by the window; with A2 open, a cross-tap copy would be charged 94 ps. | main 4691070201 per the 22:19 post |

### Ranked fix
1. **Put the 12 moved cells back inside existing rows** (A1). Ten of them are 3.5 to 14 um from their e5c site, so pinning them to the e5c sites, or sliding each to the nearest free site in a current row of that type, then re-running `actual_reach`, changes no kit. The alternative, new rows for the three types, asks signed hd_mesh for five new holes and makes the hd_lep0N kits in flight stale. Worst reach has 19 um of room (386.2 against 405). Owner: HEAD-CROSSING-1119.
2. **Run the related-pair STA on run f and write the hd_serdes window rows from it** (A2, A3): `die_sta_related --kit-window-out`, 37 ports. Do it in r12 if the STA finishes before the gates do; otherwise delete the 22 stale rows in r12 so the type falls back to one flat value, and bring the measured table in the next event. A flat 94 ps on 37 taps over 14,991 flops is expensive (see B for what a window costs in hold cells), so the measured table matters. Owner: HEAD-CROSSING-1119.
3. **Related-pair windows for hd_serdes after its first CTS** (the form A method: `kit_tap_related_pairs.tcl` on the placed kit, then `--kit-window-related`). Owner: HEAD-MESH-O derives, HEAD-CROSSING-1119 applies.
4. **Re-estimate pma_tck for the 380 um leg, and measure it at the first hd_serdes CTS** (A7). Owner: HEAD-CROSSING-1119.
5. **Put the reset copy and its source in one tap group** if the regenerated wrapper shows them on different taps (A9). Owner: HEAD-CROSSING-1119.

### Stop list
- Stop regenerating reserved rows for a fixed type list after a die clock rerun; take the list from the contain check (every type whose inside count is below its cell count).
- Stop carrying per-port window rows across a tap table change of that type.
- Do not count an hd_serdes kit built on r12 as window-proven until fix 2 lands.

## B. hd_tile: what limits routed TT and FF hold

### Measured, placement RC, one CTS pass each
I confirmed one `flow.sh 4_1_cts` in each `run_route.log`.

| Run | Windows | Ring regs + flt sites | TT after repair | Pre-GRT hold build | Hold cells | TT after hold build | FF hold before repair |
|---|---|---|---|---|---|---|---|
| tilecomb3 | r8, 84..123 | no | -52.63 | kept | 26,274 | -52.63 | -143.04, 10,704 ends |
| tilecomb3s | r8, 84..123 | yes | +1.18 | **fell back** | 0 | would be -46.75 | -154.47, 10,503 ends |
| tilecomb3sa | form A, 28..90 | yes | +16.83 | kept | 17,047 | +0.61 | -123.17, 8,352 ends |

Sources: `FM/<run>/gen/hd_tile/run_route.log` lines `OT_TT_SETUP_REPAIR`, `OT_HOLD_GATE`, `OT_PREGRT_FF_HOLD`; `tt_setup_repair.log`; `pregrt_ff_hold.log`.

GRT has finished on 3s and 3sa with 0 overflow (total usage 6.83 %). The in-flow hold repair and the GRT-RC TT lines had not printed when I stopped reading (07:50 UTC).

One trap for readers: `tilecomb3` and `tilecomb3sa` each contain a `pregrt_ff_hold_fallback.log` dated 02:55 UTC with the text "-52.16 -> -57.42". It was copied in with the tilecomb2 kit. Neither run fell back; only 3s did (its file has a second line, 06:53 UTC).

### Root causes
1. **The setup repair is at its sizing limit.** All three kits ask for 40 ps of margin. The repair ends with `RSZ-0062 Unable to repair all setup violations` at +16.83 (form A) and +1.18 (r8 windows). The 15.6 ps between them is pure window charge. No knob setting gets more out of this netlist at these windows.
2. **The hold window is paid twice.** Each cross-tap pair is padded to window + 25 ps uncertainty + 45 ps guard. On the r8 windows that padding costs 48 ps of setup (3s: +1.18 to -46.75), which trips the fallback, so the whole FF debt (-154 ps on 10,503 ends) goes to the in-flow GRT repair in an FF-only session. On form A it costs 16 ps and the build is kept. The same sequence on hd_host_w r8b ended at TT -153 after the GRT hold repair and -56.32 routed (section D).
3. **Port-in hold is by contract, not a defect.** The 2,300 residual ends after the pre-GRT build are all class `port_in`: 2,263 on the data bus `i[*]` (worst -61.5), 26 `cland_fstart_in_i`, 4 + 4 `cland_dn_fault_i` / `cland_dn_ready_i`, and `start_i` (-89.3), `arst_n` (-81.8), `cland_tstart_in`. Same-tap and cross-tap are 0. These are the input contract (in_min -90 ps against the type clock) and are left to the GRT repair on purpose. Source: `FM/tilecomb3sa/gen/hd_tile/pregrt_ff_hold_open.tsv`.
4. **One tap has a 144 to 165 ps range inside itself.** clk_t5 (156 sinks) reads skew 149.9 / 164.5 / 144.4 in the three runs; the next worst taps are 80 (clk_t1, 44 sinks) and 77 (clk_t14, 1,500 sinks). Tap means spread 393..481 against target 450. This is the hd_host_w class (section D) on a small scale: some of that tap's sinks are far from its port. I did not read which flops they are.

### What to expect routed (inference, not measured)
- 3sa enters GRT at +0.61. The measured placement-to-GRT loss on HEAD host types is about 54 ps before repair (hd_host_e, `tt_setup_repair.tcl` header). A routed TT between about -20 and -50 is likely, so it may pass or miss the -42 gate by a few ps.
- 3s enters GRT with no hold cells and 10,503 failing FF ends. Its hold repair runs with no TT view. I expect it to end worse than 3sa on TT.
- The two private r11b kits use windows 24..106, wider than form A by 10 to 58 ps on every port, so they sit between 3s and 3sa. They carry A_INPUT_STAGES 2 and TEN_HOP 3, which 3s and 3sa lack.

### Should form A go into r12 or r13?
**Yes, as early as possible; r12 if its gates have not finished, else r13 at once.** Reasons:
- It is better on every measured quantity and worse on none (table above).
- It is rows only: `clock.tap_window.per_port_ps.hd_tile`, no RTL, no lane, no bind change.
- It is valid on the r12 clock as it stands: the tile part of run f is identical to e5c (A4).
- Waiting for the routed number does not change the choice between form A and the r11b rows; it only tells whether more is needed.

One condition: judge the die side with `--kit-window-related`. Form A is the related-pair need with no added 10 ps, so the all-pair kit-contract figure will read negative and must not be used for it.

### Ranked fix
1. **Form A rows into r12 / r13** (`intel2 ~/fable-fix-head-mesh/e5c/hd_tile_win_e5c_rel.json`). Owner: HEAD-CROSSING-1119 applies, HEAD-MESH-O supplies.
2. **Relaunch the wave hd_tile kit on that event with `OT_TT_SETUP_MARGIN` 40 and `.keep_stage_odbs`.** Owner: HEAD-CROSSING-1119.
3. **If routed 3sa misses -42: form B** (seven spine taps at 55 ps; measured +14.43 with zero negative ends on the predecessor's DB) needs the die-side spine sub-branch that e5d failed to deliver without hurting the rest of the tile. Before that, try the cheap kit-side lever: lower the pre-GRT cross-tap guard from 45 ps for hd_tile, since guard plus uncertainty (70 ps) is as large as the form A window itself. Owner: HEAD-MESH-O.
4. **Name the far sinks of clk_t5** and move them to the nearest tap or add a tap. Owner: HEAD-MESH-O.

### Stop list
- Stop reading `pregrt_ff_hold_fallback.log` without its timestamp.
- Stop waiting on the extra hd_tile route job `ot-jobs/hd_tile-route-civil-redfish-1685567-1795154183` (window 123, launched 21:56 PST, most likely the private r9 kit; I did not confirm its plan). It reads TT -367.93 after repair and its hold build fell back. It cannot sign.
- No PICK_SPLIT, no new window form, no die-clock change for hd_tile until 3sa has a routed number.

Owner lane for B: HEAD-MESH-O (FABLE-FIX-HEAD-MESH).

## C. hd_lep0N: infrastructure or design?

Both. The infrastructure explains why nothing finished; the design explains why the next finish will probably fail.

### Infrastructure (measured)
- The r8b wave "route" job (`ot-jobs/hd_lep0N-route-civil-redfish-285021-1795150613/work/run_route.log`) started at 04:56 UTC and re-ran the whole front end: `2_1_floorplan` at log line 15, `face_flops.tcl` 4,887 s, global placement 2,869 s. It reached `4_1_cts` at 07:42 UTC, 2 h 46 min after launch. The place job before it had already done the same work (`face_flops.tcl` 4,336 s, placement 1,421 s; `KW/head_rp21z20NF15f_r8b/items/hd_lep0N/gen/hd_lep0N/run_place.log`).
- Cause: the r8b kit was generated with tools 27f1360d, before the route-start fix (main de25a4bcef8, 77973bd52d2). The stage ODBs are 0-byte placeholders, so make rebuilds from floorplan.
- epyc10 load is 234 on 96 cores, 106 GB free of 1 TB. The same placement takes twice as long in the route job as in the place job.
- The private r11b kit has `.keep_stage_odbs` and will not repeat this. It is in its place job (launched 06:26 UTC).

### Design (measured on the placed r8b kit)
Source: `KW/head_rp21z20NF15f_r8b/items/hd_lep0N/geom/placed_scan.tsv` and `auto_geom.json` (verdict FAIL, advisory).

- 49 register groups over 405 um; 26 are class NEED-STATION and none has a plan row. The r12 plan has no `internal_stations`, `relay_sites` or `reach_pairs` key on hd_lep0N at all.
- 1,372 of 91,013 register-to-register captures are over 405 um; the longest is 1,311 um.

| From | To | Bits | Over 405 | Over one cycle | Max um | Estimate ps |
|---|---|---|---|---|---|---|
| u_bin_coll_i0 | u_core.u.g_c0i station q | 514 | 189 | 149 | 851 | 1,056 |
| u_bin_unit_i0 | u_core.u.g_pin station q | 45 | 45 | 45 | 640 | 794 |
| u_core.u.g_c0o station q | u_bout_coll_o0 | 512 | 162 | 36 | 630 | 781 |
| reset group_r | reset local_r (u_rstr) | 954 | 60 | 22 | 932 | 1,155 |
| u_rrl_657 (reset relay) | eight station groups | 4..56 each | 98 | 77 | 1,311 | 1,625 |
| u_core.u.g_pout station q | u_bout_ctrl_o0 | 32 | 32 | 17 | 602 | 746 |
| clk_t41 pin | fclk_out_coll_o2 pin | 1 | 1 | 1 | 1,793 | 2,223 |

- Six forwarded clock exports run 891 to 1,793 um from their source tap to the output pin (fclk_out_coll_o1/o2/o3, ctrl_o0, fault_o0, lw_o). The data they travel with launches from face flops next to the pin. The export insertion is then set by a wire the plan does not site.
- Channel demand at placement is 2.3x (horizontal, y 601..604), 1.9x (vertical, x 1190..1198) and 2.6x (column) of the track estimate. The estimator's GRT did not finish, so overflow is unknown.
- Size: 292,498 non-tap cells, 73 % of the 400k advisory cap; 191 taps, 80,162 sinks.
- Tap offsets: the r8b kit is built on the offsets that the die tree misses on 329 of 390 checks (predecessor A5). r11 re-derived them, so only the private r11b kit is built on offsets the die delivers.

Reading: the coll_i0 group alone has 149 bits whose placed distance needs more than one 833 ps cycle. Unless these are multi-cycle by constraint, which I did not check in the SDC, the r8b route ends with TT setup worse than -42. The reset relay hops are recovery paths and may be relaxed; the three data groups are not.

### Ranked fix
1. **Station rows for the face buses, in the next event** (cycles are pre-approved): coll_i0 to the g_c0i station (514 b), g_c0o station to coll_o0 (512 b), unit_i0 to g_pin (45 b), g_pout to ctrl_o0 (32 b). One station at the midpoint is enough for the three 600 to 640 um groups (hops about 300 to 320 um); coll_i0 at 851 um needs two. Use the r9 hd_serdes coll_i0 event as the template, lane latency rows refreshed in the same event. Owner: HEAD-CROSSING-1119.
2. **Reset relay sites** for u_rrl_657 and the u_rstr group to local hop (`reach_rules.py fix --rules 1`, boot cycles only). Owner: HEAD-CROSSING-1119.
3. **Site the forwarded clock exports**: source each fclk_out from the tap nearest its pin, or give the leg sited repeaters so the insertion is fixed by the plan. Owner: HEAD-CROSSING-1119.
4. **Let the private r11b kit run to the end as the measurement** (current offsets, one placement). Read its `OT_TT_SETUP_REPAIR` line at CTS: if it shows the coll_i0 path, fix 1 is confirmed before route. Owner: HEAD-CROSSING-1119 (kit), with a lep0N type owner if COORD names one.
5. **Regenerate the wave kit on tools with the route-start fix** so the wave copy stops paying 2.75 h per route start. Owner: WAVE-FLOW-R2.

### Stop list
- Stop treating the r8b wave route as the sign-off candidate: old offsets, no stations, re-placed DB (the routed DB is not the DB the geometry scan read).
- Stop relaunching hd_lep0N unchanged after an interrupt; each relaunch on the old tools costs a full placement and tests the same unstationed plan.
- Do not move the lep0N kits to make room; let them finish.

## D. Die hold -248 and hd_host_w

### Root cause
The tap table does not cover the type.

- hd_host_w outline is 734.4 x 570.2 um. All 40 explicit taps lie in x 10..364, y 67..294 (plan `partition_types.hd_host_w.clock.taps`). There is no tap in the east half or the north half.
- G0 already reports it on the plan census: 30 of 40 taps empty, clk_t38 load 1,505 at radius 700.7 um against a 180 um limit (`HC/g0_r11.log`, `TAP-LIMIT-INFO hd_host_w`, information only).
- In the kit, the nearest-tap pass then loads the taps on the east rim of the table to the 3,000 cap: clk 2,988, clk_t1 2,992, clk_t30 2,998, clk_t36 3,000, clk_t37 2,984, clk_t38 2,968, clk_t39 2,994, clk_t21 2,132. Twelve taps get 1 to 3 sinks. (`KW/head_rp21z20NF15f_r8b/items/hd_host_w/gen/hd_host_w/run_route.log` line 3276 and lines 5704-5744.)
- Tap balancing can only add delay. The big taps' own trees are already above the 450 ps target (clk mean 493, range 468..580) and cannot come down; the small taps are padded up. Result: tap means 405..494, and inside the big taps 70 to 141 ps of range (clk 113, clk_t21 141, clk_t39 134, clk_t30 111, clk_t37 109, clk_t1 92, clk_t38 85, clk_t36 70). Every tap under 2,100 sinks with local sinks is within 22 ps.
- The 16 `u_bin_l1_rx_i` flops are the input face register of a bus on the east edge (x about 728). Their nearest tap is clk_t36 at (268, 218), 509 um away, which is where the depth-18 leaf and the 509 ps come from.
- The boundary flops end 115 ps late against the type contract: pin-register mean 564.7 TT against bound 450, 455.5 FF against 342 (`OT_POSTCTS_GATE` lines). That is the 116 ps port-mean difference DIE-LEVEL-CHECK measured on the older signed record.

### The same cause fails the type on its own
The r8b hd_host_w wave kit finished (`.../gen/hd_host_w/signoff.log`, 04:50 UTC): **NOT SIGNED. TT setup -56.32, FF hold -21.08 (internal), DRC 0, pair skew TT/FF 256.0 / 236.7.** On the way: port-in hold -240.93 on 2,781 ends after the pre-GRT build (28,963 hold cells, 6,110 s), 30,158 pad cells after the GRT hold repair, TT -153.46 at GRT RC, repaired to -65.01 with 2,100 cells. The late face flops create the port-in hold debt, and the padding that pays it costs the setup.

So hd_host_w is not signed on the current plan. The record the die run uses is the older `outpad5_fast2` ECO build.

### Ranked fix
1. **New hd_host_w tap table by density from a fresh placed census**: `taps.density_taps` on the r8b placed DB (`3_place.odb` of the kit above), cap 1,000 sinks, radius at most 180 um, exactly what `HC/r12/taps12.py` did for hd_serdes. About 30,400 sinks give about 40 taps, so the die port count stays near today's; the 12 near-empty taps go. Then the die clock rerun for the host region, reserved rows, and per-port windows from the related-pair STA, in one event. Check with the contain check that no neighbour type loses a cell (finding A1). Owner: HEAD-CROSSING-1119.
2. **Keep each face register bus on one tap** (`OT_TAP_GROUP_RE` on the `u_bin_*` / `u_bout_*` groups, as hd_mesh does for its credit counters), so a bus's capture flops share one leaf range and the port-in hold is one number per bus. Owner: HEAD-MESH-O for the kit line, HEAD-CROSSING-1119 for the row.
3. **Re-time die hold with the per-port view after the new kit signs.** With taps that balance, the type range should drop from 211 ps to the 26..71 ps of the other types, and -248 with it. Owner: DIE-LEVEL-CHECK-1119.
4. **Same check on hd_host_e** (12 taps on a 657 x 570 um type; its tap bbox does span the outline, so I expect less) and on hd_lep0N, where G0 shows taps at load 1,953 against a cap of 800. Owner: HEAD-CROSSING-1119.

### Stop list
- Stop balancing clk_t1 and clk_t36 by tap latency targets: the big taps cannot be slowed evenly (70 to 141 ps inside each), and padding the rest up to them moves the type mean further from 450.
- Stop re-clustering leaf_74 alone; the flops are 509 um from their tap and will be late in any clustering.
- Stop relaunching hd_host_w on the current tap table; r8b has shown where it ends.
- Stop quoting -248 as the die hold; it is this one type's range.

Owner lane for D: HEAD-CROSSING-1119.

## What I ran
- Read-only reads of logs, plans and trees on intel2 and epyc10.
- Three small python3 -I scripts on epyc10 (no ot-run, a few seconds each, nothing written): the plan diff r11b to r12, the tap depth and path-length walk on the two die clock trees, and a re-run of the contain check that prints the cell names.
- One early post to HEAD-CROSSING-1119 (23:44 PST, commit 9aede127) with A1 and A2, because r12 was about to gate.

## Not checked
- Bind, LATCHECK and G0 on r12 (not started when I read).
- The regenerated hd_serdes wrapper with the reset copy.
- Any routed number for tilecomb3 / 3s / 3sa or the r11b kits; the routed expectations in B are inference.
- Which flops make the clk_t5 range in hd_tile.
- Whether the hd_lep0N face-bus paths are multi-cycle in the kit SDC.
- The plan behind the extra hd_tile route job named in the B stop list.
- Stage-count parity inside the die tree (taps of one region differ by up to 2 stages on an inverter tree; e5c has the same spread and passed its crossing check, so I left it).
