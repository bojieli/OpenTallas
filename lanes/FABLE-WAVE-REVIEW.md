# FABLE-WAVE-REVIEW 2026-11-14: why the kit wave signs off nothing, and what to change

Scope: all 247 wave route jobs that ended 07:50-17:55 PST (autopilot `jobs/*/a*.log`), kit logs of 160 of them read on the build hosts (GRT/DRT/CTS logs, congestion reports, config.mk, pdn.tcl, io.tcl, run_place.log), two read-only database probes of DRT-0255 failures, and the 466 `KIT-WAVE FAIL` lines of the same window. Read-and-diagnose only; nothing shared was changed.

Status of each statement: MEASURED = read from logs or a probe; HYPOTHESIS = fits the numbers, not yet proven; details marked "parallel study" are deliberately left to a lane.

## 1. Verdict

The wave does not have one failure. It has four recipe faults that hit every family, on top of four structural faults that hit specific families. The recipe faults alone account for about 60 % of the ends, so today's picture ("151 flow errors, mostly global route congestion") overstates congestion by a wide margin.

- Recipe, everyone: (R1) hosts run out of memory and kill builds; (R2) a clean global route is thrown away after a kill or a wrapper error; (R3) global route is fatal on an overflow that detail route would absorb; (R4) kits still carry gates the owner deleted, and the QC wave generates from a source older than the flow fixes.
- Structural, by family: (S1) the clock-landing ring is packed into a 10-um strip at the pin face; (S2) signal pins and repeater cells collide with the PG grid and the M8 die-reserve rows (DRT-0255); (S3) hard tiles whose pin face looks away from their logic (QC cbn) and macro rows without an east-west street under an M7 cap (S81 col_h9); (S4) types that do not fit: structural hold of -385 to -441 ps and types of 420-630 k cells.

## 2. Where the 247 ends went (MEASURED)

| class | builds | build-h lost | families | evidence |
|---|---|---|---|---|
| A host OOM kill (SIGTERM, make `Error 241`), booked as exit 2 | 56 | 241 | all | earlyoom journal: 203 SIGTERMs on 6 hosts in 10 h, 125 of them openroad; hosts at 897-967 of 1007 GB; 25 killed in GRT, 17 in DRT, 10 in CTS |
| F wrapper error after a clean GRT (`OT_LEGACY_GATE grt FAIL ... PASS exit -15`, or missing `postcts_gate_tt.json`) | 4 | 32 | QC sle/slw hc, st_b | gate verdict PASS, the gate process itself was SIGTERMed; same cause as A |
| B GRT-0116/0232 on overflow 31-3,077 at 2-11 % routing use, kit has no allow-congestion | 18 | 107 | S81 slice_station 9, KV hgi 6, col_h9 2, leaf 1 | slice_station: 100 % of congested gcells within 40 um of the edge, 64-71 % clock-landing ring nets |
| C real overflow (12,928-90,044) | 12 | 74 | S81 col_h9 r1/r2 7, QC cbn/cbx 4, S81 eng 1 | cbn: 9,998 of 10,000 congested gcells have capacity 0 (over the hard tiles); col_h9 r1: 93 % of overflow on M6 at 8-9 % M6 use |
| GRT failed, kit dir overwritten by a later attempt | 19 | 68 | col_h9 7, slice_station 4, hgi 4 | same families as B and C |
| D1 DRT-0255 "maze route cannot find path", GRT overflow 0 | 25 | 183 | QC sle/slw 11, S81 leaf 5, KV io_cor 2, HEAD 2 | dies in iteration 1; resistance-aware off on all 20 inspected, PG-track hook on for 7 of them; identical on rerun |
| D2 DRT-0206 checkConnectivity | 10 | 92 | QC fw/sc/stm | off-track strap pins (DRT-0421), kits generated before the strap snap |
| E deleted gates still firing | 42 | 272 | hold stop 28 (KV kv3_pc 13), repair time cap 12 (col_h9 9), congested stop 2 | 16 hold stops after 15:00 |
| G 400 k cell budget stop at CTS | 10 | 14 | KV hg/pv/hub_Ei, S81 dsdv_slice_iq_C | movable 406-632 k |
| H DRT-0073 no access point on a macro clock pin | 4 | 4 | S81 dsdv_slice lep*, gunit | pin `ck[0]` / `sv_lo` of a hard core |
| I routed, not signed off | 14 | 77 | QC su_l0 7, KV io_ft 2, sys_SD 1, HEAD 2 | section 5 |
| cancelled by the wave, dedup, other | 33 | 36 | col_h9 r0 p6 10 | |

Not in the 247: 466 `KIT-WAVE FAIL` lines on about 150 items that never reached place and route. Top signatures: `gen_lint src_skew` 89 (QC, kit source older than the queue lint), `kit_topology` ValueError 77 (QC), `pipeline` TypeError dict / str 68 (9 items, looping), clock-landing band too small 33 (KV pv), kit_rtl 28, infra at place 24.

## 3. Recipe faults (everyone)

### R1 Memory admission lets hosts fill, earlyoom kills (60 builds, 273 build-h per 10 h)
- MEASURED: ot-heavy prints `expected growth of 70 running (x0)`: a job is admitted against MemAvailable now, and running jobs are assumed never to grow. A route job is charged 16-33 GB; detail route peaks at 27-37 GB (5_2_route.log), GRT with repair at 19-27 GB. 44-74 openroad processes per host hold 824-878 GB. Load is 110-334 on 96-128 threads.
- This is the largest single class and it also explains the 4.5 h median: every kill returns 2-10 h of work to the queue.
- It follows directly from the 11-14 order to remove admission reservations. I say so plainly: that order costs about a quarter of all ends.
- Fix: (a) ot-heavy growth term = sum over running jobs of (stage-class peak - RSS now), stage peaks from measured logs, not from completed-run p90 (completed runs are the survivors); (b) an NVMe swap file per host plus an earlyoom swap threshold, so a transient peak pages instead of killing; (c) book `Error 241` / `exit -15` as INFRA.
- This is accounting, not a conservative limit: it admits as many builds as fit at their real peak.

### R2 A clean global route is discarded (4 wrapper + 17 DRT kills + part of 25 GRT kills)
- MEASURED: sle_hc0 `cl38badc56` and slw_hc0 `cl4f54b7a3` (intel1) have `5_1_grt.odb` (486 MB) and `route.guide` intact, overflow 0, gate lines PASS (setup_est -33 / -11 ps). The wave opened attempt 7 / 6 from scratch instead of resuming.
- Fix: in kit_wave.py, when the run dir holds a `5_1_grt.odb` newer than `4_cts.odb` and the end was a kill or wrapper error, relaunch the same dir at `5_2_route`. Never a new attempt.

### R3 Global route fatal on tiny overflow (18 builds measured, up to 37 with the unreadable ones)
- MEASURED: overflow 31-3,077 against 3.2e8 resource (below 0.001 %), upper layers M4-M8 under 1 % used on slice_station. Form c (density 0.35, M9, allow-congestion) signed slice_station t30; it is being applied type by type after each type burns about 6 h.
- Fix: allow-congestion on in `die_gen_env` of every die, M9 top layer for every S81 kit without an M9 claim. This is the stock ORFS practice, not a tweak.
- Limit, MEASURED by TYPE-SLICET30: form b (density 0.4, M8, allow-congestion) cleared GRT and then died with DRT-0255. R3 moves builds to detail route; S1 and S2 decide whether they sign off.

### R4 Stale kits and stale source (42 + 10 + 10 builds, 466 FAIL lines)
- MEASURED: hold stop still fires 16 times after 15:00; `OT_CELL_BUDGET ... above the R-CAP place budget 400000` 10 times; QC kits of events s29q102B0 / s29q103S have no `OT_PG_TRACK_TRUTH` and no strap snap; `src_skew` 89 lines.
- The 48 h freeze (no src switch until 11-15 04:00) is what keeps QC generating from the old source.
- Fix: lift the freeze for flow-only source bumps, regenerate every kit that has not passed CTS, and stop the `pipeline` TypeError loop (9 items, 68 lines).

## 4. Structural faults and the fundamental fix for each

### S1 Clock-landing ring at the pin face (S81 slice_station, eng; QC sle/slw; KV pv)
- MEASURED: a 515-bit bus gets a ring of 2,970 FIRM flops plus 10,387 logic cells (26 cells per bit). The flops go into a strip 10 um deep by 110 um wide: 2.58-2.64 flops/um2 on every S81 kit. Ring cells are 12-36 % of a kit's cells.
- MEASURED: QC cbn carries the same 515-bit ring as a hard, signed macro `sle_cland_w515_n` of 88.56 x 51.84 um. The form that signs off uses 4,591 um2; the wave's soft form gives the flops 1,100 um2.
- The tool's own note (LAND-RING-2, 11-12) records that every rows-1 strip that reached GRT carried the overflow within 20 um of its band and that rows 2-3 routed; the knob `OT_CLAND_STRIP_DENS` is opt-in and unset on S81.
- Fundamental fix: one hard landing macro per bus width (515, 259, 71), signed once, placed at the pin face on every die; the plan reserves a 52-um band per landing face (outline growth is pre-approved). Kits lose 13 k cells per bus, which also brings several types back under 400 k.
- Until the macros exist: strip density from the plan as the default (rows 2 or more), band depth to match. That is the same structure at lower density, not a setting.

### S2 Pins and repeaters collide with the PG grid and the M8 reserve rows (DRT-0255, 25 builds)
- MEASURED, probe of S81 leaf t69 (`5_1_grt.odb`): the unroutable net ends on repeater `wire97392` at (40.61, 382.05). That cell sits under the crossing of the M5 PG pair (x 40.88-41.20) and the M6 PG pair (y 381.98-382.66), between M2-M3-M4-M5 PG via stacks at every row, with a full-width M8 obstruction row at y 380.42. The guide drops M6 to M1 exactly there.
- MEASURED, probe of QC sle_st_b_v2: port pin `x_fw_ctl_p2_i[464]` is an M7 pin at x 181.536, on the track of the M7 VDD stripe (x 181.488-181.776, full height); 26 M8 obstruction rows in a 3-um window; M5 and M6 PG pairs within 1 um.
- MEASURED: PDN is M5 4.32 um, M6 4.32 um, M7 8.64 um pitch (2.75 times denser than the ASAP7 stock grid) and takes 26-32 % of every layer; M8 is two-thirds die reserve (cbn: 10,929 type tracks of 32,076).
- HYPOTHESIS: this is the cause of all 25, not only of the two probed. 60 % of the failing points lie within 80 um of the edge, 6 of 20 nets are landing-ring nets.
- Fundamental fix: make pin assignment and placement PG-aware in the generator. (a) `gen.py phys` never emits an M5/M6/M7 pin on a track inside or within spacing of a same-layer PG stripe (both abutting types move together); (b) placement blockage under every M5 x M6 PG crossing, so no cell and no repair buffer lands there; (c) the M8 grant leaves whole free tracks next to each reserve run.
- Not fixes: rerun with another seed (slw_hc2 failed on the same net on two hosts; DIE-KV-59 10-31 measured the same), the PG-track hook alone (7 of 20 had it), resistance-aware off alone (all 20 had it).

### S3 Real overflow: the plan is wrong for the type
- QC cbn (MEASURED): four hard tiles of 457.92 x 1157.76 um, each with 2,056 M4 pins on one face. t10 and t01 face the 129.6-um centre channel; t00 (R0) and t11 (MY) face the outer margins. 839 nets cross t00 and t11 over the tile's own M6 wiring (capacity 0 for the first 300 um): overflow 30-79 k on M6, 3-11 k on M8. No direct tile-to-tile nets; all go to glue logic.
  Fundamental fix: plan event that turns every tile's pin face to the centre channel (mirror t00 and t11; rotation and mirroring keep the signed core). If the tile's four buses have consumers on both sides, re-export the tile with pins split by side. Proof: a place-only what-if with the two tiles mirrored and a count of nets crossing a tile (30 min). Connectivity per bus is parallel study.
- S81 col_h9 r1/r2 (MEASURED geometry, HYPOTHESIS cause): 81 hard macros in full-width rows (x 17-554 and 864-1401), top layer M7, overflow 26-31 k with 93 % on M6. M6 is the only horizontal layer above M4 and it is blocked over the macro rows.
  Fundamental fix: the type does not fit under an M7 cap. Either the plan grants M8 east-west tracks over the macro rows, or each macro row gets a through street; choose by measurement, parallel study with DIE-S81-92.
- S81 eng t1 (MEASURED): 36,705 overflow, 88 % landing-ring nets, all within 100 um of the edge: this is S1, not a floorplan of its own.
- KV kv3_hgi (MEASURED): wave overflow is only 31-438 at 7 % use. The column re-floor lane should first prove that hgi fails with allow-congestion on; on these numbers it is class B.

### S4 Types that do not fit
- KV kv3_pc: FF hold -385 to -441 ps on 18,021-31,883 endpoints after CTS. Deleting the hold stop does not sign these off; it turns a 0.2-h stop into hours of buffer insertion. Needs the R-CLOCK landing/tap latency fix in the plan.
- S81 col_h9: hold repair inside GRT had inserted 26,384 buffers and was still running at the 6-h cap. Same class.
- KV kv3_pv_v1n 632 k, kv3_pv_v8 468 k, kv3_hg 415-429 k, S81 dsdv_slice_iq_C 622 k movable cells: split in the plan or harden the repeated engine; S1 removes part of it.
- H: hard-core clock pins without an access point (4 builds): the core view is wrong, fix the view once.

## 5. Routed, not signed off (14 builds): the cheapest sign-offs on the table

| build | DRC | TT setup | FF hold | other | action |
|---|---|---|---|---|---|
| HEAD hd_spn_wshim_rx | 0 | n/a | -1.46 ps | | late ECO, one pass |
| QC slw_su_l0 x4 | 3 | +19 to +36 | +0.93 to -11 | one net at 6.4 ns slew | late ECO: 3 DRC, the slew net, hold on tens of endpoints |
| QC sle_su_l0 x3 | 3 | -19 to +5 | -13 to -45 on 40 | one net at 7.6 ns slew | same |
| HEAD hd_st_n4 | 0 | +155 | -107 | | hold repair before GRT (already signed by a lane) |
| KV kv3_io_ft_v1 x2 | 0 | +18 / -134 | -168 on 4,436 / -14 | | structural clock, R-CLOCK |
| KV kv3_sys_SD | 0 | -77 | -179 | | signed by a lane with late ECO |

The su_l0 family has the same three defects on every build (DRC 3, one unbuffered net, small hold): one family ECO form closes seven builds. What the unbuffered net is: parallel study.

## 6. Owner questions answered

- Can the wrapper failures be recovered to sign-off? Recovered to detail route: yes, cheaply; the routed-global database and guides are intact on 2 of 3 checked and the gate verdict was PASS. Sign-off is not assured: their hc0/hc2 siblings died with DRT-0255, and sle_st_b_v1 estimates setup at -199 ps.
- Can DRT-0255 builds be recovered without redoing global route? Not by a rerun (deterministic). Plausibly by an ECO on the saved `5_1_grt.odb`: move the boxed-in cell off the PG crossing, incremental global route for the touched nets only, detail route again. Unproven; each pass costs 1-3 h and shows one net, so scan all PG collisions first and fix them in one ECO.
- Is real overflow the only physical problem? No. In builds: PG collisions 25, landing ring about 25, real overflow 12-20, structural hold about 28, oversize types 10, bad core views 4, routed near-misses 9.

## 7. Class fixes, ranked by builds unblocked per effort

| # | fix | where | builds per 10 h | effort | proof (run with the rollout) |
|---|---|---|---|---|---|
| 1 | Family late-ECO form for routed near-misses | ECO lane, `eco_loop.py` | 8 sign-off candidates now | hours | su_l0 x3 + wshim_rx |
| 2 | Resume at detail route when a clean GRT database exists | `tools/autopilot/kit_wave.py` (failure path) | 4 + about 20 | hours | sle_hc0, slw_hc0 on intel1 |
| 3 | Memory: growth accounting, real stage peaks, swap, Error 241 = INFRA | `/usr/local/bin/ot-heavy`, earlyoom args, kit_wave.py classifier | 56-60 | half a day | epyc9 first: earlyoom SIGTERMs per 10 h, 56 today |
| 4 | Allow-congestion and M9 as die defaults | `kit_wave.json` `die_gen_env` (S81, KV, QC), not item_env | 18-37 reach DRT | 1 h | slice_station t8, t37, t52; hgi v1, v2 |
| 5 | Lift the freeze for flow-only source, regenerate pre-CTS kits, stop the pipeline loop | `kit_wave.json` src per die, gen | 62 + 466 FAIL lines | half a day | QC fw/sc x3: DRT-0206 gone |
| 6 | PG-aware pins and cell sites; PG-collision scan + ECO for existing databases | `tools/die_plan/gen.py phys` (io.tcl), placement blockage hook, M8 grant | 25, and the next wall for #4 | 1-2 days | leaf t69, sle_st_b_v2, slw_hc2, kv3_io_cor, coll_ucie |
| 7 | Hard landing macro family; strip density from the plan meanwhile | landing macro per bus width, plan band 52 um, `landing_placement.tcl` default | about 25, shrinks every kit 12-36 % | 2-3 days | slice_station t24, t49; eng t1; sle_hc0 |
| 8 | Plan events: cbn tile orientation; col_h9 M8 or streets; kv3_pc clock latency; oversize types split | die plans (QC, S81, KV) | 12-20 + 28 + 10 | per event | place-only what-if first |

Order of work: 1-5 in parallel today (none needs a plan change); 6-8 start now as lanes, they decide whether builds that pass GRT ever sign off.

## 8. Lanes pursuing dead ends (plainly)

- Relaunching unchanged kits: attempt numbers reach 17-19 on slice_station types. A deterministic GRT or DRT failure does not change on retry.
- Applying form c one type at a time after each failure. It is a family default (fix 4).
- Lower density alone (form b): passes GRT, dies at DRT-0255.
- PG-track hook or resistance-aware off as the DRT-0255 fix: both already on in failing kits.
- Deleting the hold stop, the repair time cap and the cell budget for kv3_pc, col_h9 and the 420-630 k types: the builds now fail later and cost more. These need S4.
- KV hgi column re-floor: not justified by the wave numbers (31-438 overflow); prove with fix 4 first.
- QC coll_n edge-blockage form: a one-type answer to S2 (buffer in a 13-um strip beside a macro); fold it into fix 6.
- Not dead ends: S81 band event B3x2d and leaf event B4L4 (structural, keep), the no-progress watchdog, gunit FWPIPE.

## 9. Not done, for parallel study

- Whether PG collision explains all 25 DRT-0255 builds (2 probed). Count pins on PG tracks and cells under PG crossings per kit.
- cbn: which of the four tile buses has consumers on which side.
- col_h9 r1: where the 26-31 k M6 overflow sits relative to the macro rows (the congestion report lists only 4-7 gcells).
- su_l0: identity of the 6.4-7.6 ns slew net and of the 3 DRC.
- 19 GRT failures whose kit dir was overwritten.

Evidence kept: epyc10 and epyc7 `/srv/opentallas-scratch2/claude/fable-wave-review/` (probe.tcl, probe logs).
