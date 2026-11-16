# FABLE-PD-S81CORES-1915: dsdv_bksel_q, dsdv_gunit_l1f_bf, t51 native_w (2026-11-15 19:45 PST)

Read-only diagnosis for S81-CORES-1115 (r203). Nothing launched, stopped or edited in any kit.
MEASURED = read by me from the kit files or from my own STA read. INFERENCE is marked.
My only writes: epyc8 `/srv/opentallas-scratch2/claude/fable-pd-s81cores-1915/` (2 TT STA reads of the two 6_final databases, 5 MB, may be deleted).

## 0. Verdicts

| core | cause | fix | build needed |
|---|---|---|---|
| dsdv_bksel_q | Setup is lost in unrepaired max-slew nets, not in logic depth, macro arcs or the floorplan. The kit runs with `SKIP_INCREMENTAL_REPAIR = 1`, so no `repair_design` ever ran after placement. | Repair slew, then setup, then hold. Fastest: post-route ECO on the routed DB. In parallel: `repair_design` on 4_cts before GRT. | ECO about 3 h, or GRT + route about 6 h |
| bksel lib binding | Not a wrong binding. The FF run loaded `ot_s81ph_hq_pk2_BC.lib`. `macro_libs: FAIL` is a false report from `signoff.py macro_libs()`. | Checker fix in `tools/die_plan/signoff.py` line 237; re-run sign-off only. | none |
| dsdv_gunit_l1f_bf | The -42.0 is input-port hold (1,629 of 1,644 endpoints), judged at the parent. The real miss is -4.82 ps on 15 register paths. The ECO repaired them, then the kit's `core_final_repair.tcl` ran a second repair outside the clock freeze. | Same ECO with `core_final_repair.tcl` out of the post-GRT chain. | one ECO, about 1.5 h |
| t51 native_w | Signed, counted and archived. Only the published view pack for the wave is missing. | Publish the view from the signed kit on epyc7. | none |

## 1. dsdv_bksel_q (epyc8 `/srv/opentallas-scratch2/claude/core-bksel-1115/{b1o,b1g}/bksel_vC9*`)

### 1.1 What the 215 / 243 endpoints are made of (MEASURED)

My STA read of each `6_final.odb` + `6_final.spef` + `constraint.sdc`, TT libs from the sign-off receipt, reproduces sign-off: b1o WNS -256.81, TNS -16,178.3, 215 endpoints; b1g -219.49, 243 endpoints. All are clk to clk, none on vclk or ports.

| measure over the violating paths | b1o (215) | b1g (243) |
|---|---|---|
| paths with a pin above the 320 ps slew limit on the data path | 183 | 204 |
| largest slew on the path, median / max | 431 / 1,943 ps | 435 / 1,674 ps |
| data delay, median | 867 ps | 840 ps |
| data delay spent in stages whose input slew is above 320 ps, median / p75 / max | 362 / 520 / 875 ps | 230 / 419 / 766 ps |
| logic stages, median / max | 9 / 13 | 8 / 13 |
| capture minus launch clock, mean | -88.7 ps | -108.4 ps |
| paths with skew below -50 ps | 84 | 119 |

Worst path (b1o -256.81): `u_q.u_mem.g_oh[30].oh1` -> `u_q.u_s.g_r1[17].q[24]`, 5 cells. `DFFHQNx1` QN drives 16 loads at slew 174 ps; `_42019_` (`OAI22x1`) drives 2 loads and 91.3 fF, output slew 645 ps; the next cell `_44413_` (`AO22x1`) sees 2,064 ps at B1 and costs 875 ps. Skew on this path is +64 ps, so the clock is not the cause.

Sign-off counts 1,905 (b1o) / 1,763 (b1g) max-slew pins at TT. Worst-stage drivers on the violating paths are small cells on long nets: `INVx1` 42, `NAND2x1` 42, `DFFHQNx1` 23, `HB4xp67` 11 (b1o).

Estimate, arithmetic only, not an STA result: if each slew-sick stage cost 60 ps instead of what it costs now, 212 of 215 (b1o) and 235 of 243 (b1g) paths would be at or above -42 ps. With zero skew and the slews left as they are, 125 of 215 and 173 of 243 would be.

### 1.2 Why the slews are there (MEASURED)

- `config.mk`: `SKIP_INCREMENTAL_REPAIR = 1` ("route-first form: no in-GRT repair_design/repair_timing; timing closes by post-route ECO") and `SKIP_CTS_REPAIR_TIMING = 1`. `5_1_grt.log` has no `repair_design`. The post-route ECO that this form relies on was never run.
- Slew violators by stage: 638 after detailed placement, 440 after CTS, 1,905 at finish.
- The post-GRT repair (`core_final_repair.tcl`) ran `repair_timing` only. It found 1 setup endpoint at -11.53 ps and ended at 0.00, with `_44413_/B1` already at 1,393 ps slew in the same log. Routed RC then raised that pin to 2,064 ps. A path that meets timing on a 1.4 ns slew has no margin against the GRT to route RC change; that is the whole 0.00 -> -256.81 step.
- The same repair inserted 5,765 `HB4xp67` hold buffers in 12,377 s. These are weak drivers and appear as the worst stage on 11 violating paths.

### 1.3 Candidates ruled out

| candidate | finding |
|---|---|
| path structure | No. Median 9 stages; the worst path has 5 cells. |
| macro lib / arc | No. Paths into pk2 (`g_remc` -> `u_pk`, 42 in b1o, worst -168.1) carry a 789 ps slew on the way in. Paths out of pk2 are 14, worst -74.3. |
| high-fanout net | No. Max fanout 32, 0 fanout violators. The cause is wire length per driver strength: 91 fF on a 2-load net. |
| clock | Second factor, not the first. Mean skew -89 / -108 ps. The -500 class (`r1_d_l` latch -> `c1_p`, 20-25 paths) is the latch stage. Do not rebuild CTS. |
| floorplan | No re-floorplan. Standard-cell utilisation is 6 %; the long channels make the nets long, and buffering closes them. |

### 1.4 Lib binding (MEASURED)

- `signoff/ff/libraries.json` lists `/work/macros/ot_s81ph_hq_pk2_BC.lib` (sha256 d9c41fe9...), loaded through `BC_LIB_FILES`. The TT run loaded `ot_s81ph_hq_pk2_tc.lib`. The two files differ (clock tree path 232.1 vs 183.2 ps). The FF corner is correctly bound.
- The FAIL comes from `tools/die_plan/signoff.py`, `macro_libs()` (line 210 on main, the kit copy line 246). The unscoped line `ADDITIONAL_LIBS = ... /work/macros/ot_s81ph_hq_pk2_tc.lib` is checked for every corner. The suffix pattern on line 237 knows only `_(ss|tt|ff|typ)`, so `_tc` falls to `elif p.is_file() and (corner == "tt" or scoped)`, which is false for FF, and the file is reported as `ot_s81ph_hq_pk2_tc.lib (ff)`.
- It is a flow bug in the checker, and it blocks: `macro_libs` is in the blocking list when present.
- Fix: accept the ORFS abstract suffixes in that pattern (`tc` -> tt, `BC` -> ff, `WC` -> ss), and do not report an `ADDITIONAL_LIBS` entry as missing when the corner-scoped field supplies a lib for the same master. Do not rename the libs in the kit: `config.mk` is a make prerequisite.

### 1.5 Ranked fix

1. **Checker fix (1.4)**, then sign-off re-run on any routed result. 6 min per corner.
2. **Post-route ECO on the routed DB** (`eco_loop.py` / `post_route_drv`, route-keep form): `repair_design -slew_margin 20 -cap_margin 20` on routed SPEF, `repair_timing -setup`, hold scope reg2reg margin 5. Base: b1o (FF hold -4.73 on 2 endpoints; b1g has 47). Run b1g as the second form in parallel. bksel's `grt_post_core.tcl` ends with `core_final_repair.tcl`, so `post_grt_chain.py` skips it; check `PRD_POST_GRT_CHAIN.json` shows `skipped_final_repair: true` before the route (see section 2). INFERENCE: this ECO touches several hundred nets and its incremental GRT is the place where GRT-0183/0232 occurred on this core before.
3. **Pre-route form, in parallel**: resume from `4_cts.odb`, run `repair_design` on placement RC in `grt_pre_core.tcl` before `global_route` with clock nets dont_touch and a max wire length near 150 um (the kit's `OT_MAXWIRE_UM = 450` is too long for x1 drivers at a 320 ps limit), legalize, then the existing GRT, hold repair and route. No incremental GRT is open at that point, so it is not the GRT-0183 class. About 6 h (hold repair alone was 3.4 h).
4. After either form, read the remaining setup endpoints. Only if a pk2 or latch family stays below -42 ps is the clock landing (`OT_ETM_EARLY_PS = 160`) the next lever.

## 2. dsdv_gunit_l1f_bf (epyc7 `/srv/opentallas-scratch2/claude/type-gunit-l1f/g3f/dsdv_gunit_l1f_bf_gf5g3f`)

### 2.1 What -42.0 is (MEASURED, `signoff/ff/sta.log`)

- `SO STD_MIN_START port 1629 other 15`. 1,629 of the 1,644 hold endpoints start at an input port. Worst: `s0b[55]` -> `l0b[55]` at -42.00.
- They come from the hold overlay `set_input_delay -min -40` against vclk at the declared FF bound 202.5 ps. The measured FF pin-flop insertion is 339.3 ps (316.8 to 372.2). This is the port-hold class that the parent judges (`io_hold_parent: NEEDS_PARENT`), not a kit miss.
- Non-port: 15 endpoints, WNS -4.82, TNS -34.9. This is the blocking number.
- TT setup -16.46 on 4 endpoints is inside the -42 gate. TT slew 15 is advisory.

### 2.2 Why -4.82 (MEASURED)

- The three worst are `rdb_q[431/427/428]` -> `svreg_data[...]`: 2 cells, 21.8 ps of data delay. Launch leaf `clkbuf_leaf_223` lands at 314.6 ps, capture leaf `clkbuf_leaf_235` at 346.8 ps: 32 ps between neighbouring leaves, plus 25 ps uncertainty and 13.4 ps library hold, minus 8.9 ps CRPR.
- The clock is healthy: pair skew 68.5 ps FF, insertion spread 55 ps. No CTS change is needed.
- The base GRT hold repair ran at margin 0 (`OT_HOLD_FF_MARGIN = 0`; `OT_HOLD_GUARD ... margin 0`, 5,074 buffers, 7,341 s) and ended at +0.01 ps; the final repair left -0.75 ps on GRT RC. Routing moved these short paths by 4 ps. Zero margin before route is the structural cause.

### 2.3 Why the ECO fails (MEASURED, `eco_cg1115/i1`)

The ECO itself worked. Order in `5_1_grt.log`:

1. PRD hook: `repair_design` 72 buffers, hold scope reg2reg margin 5: 56 hold buffers, hold +5.05 ps, 0 violators.
2. Route-keep incremental GRT. `OT_CLK_FREEZE post_grt OK: all 847 clock nets carry their pre-ECO FIXED wire (restored 13 destroyed by GRT updateDirtyNets)`.
3. `eco_post.tcl` then sources `prd_post_grt_chain.tcl` = `grt_post.tcl`, **`core_final_repair.tcl`**, `gf5_grt_measure.tcl`. `core_final_repair.tcl` line 56 tests `ot_mm_ws min BC`, the full FF hold including ports (-47.17), so it never sees "already met". It opens a second incremental GRT, inserts 221 more hold buffers at margin 15 and closes with `global_route -end_incremental`. Nothing restores clock wires after this second pass.
4. DRT converges to 0 violations in 27 min and reroutes the clock nets that lost their wire: `CLK_GEOM_DIFF FAIL ... changed 16 (wire 16, pins 0)`, 831 of 847 still FIXED. `prd_run.sh` line 107 turns that into route_rc 5.

Why the known skip did not apply: `post_grt_chain.py` (lines 98-100 on main, the DIE-KV-67 case of 11-04) removes the final repair only when `core_final_repair.tcl` is the last line of `grt_post_core.tcl`. This kit has a private line after it, `source /work/gf5_grt_measure.tcl`, so the tail test fails and `PRD_POST_GRT_CHAIN.json` says `skipped_generated_repair: false`. The margin 1 and margin 2 attempts fail the same way, because step 3 does not depend on the ECO margin.

### 2.4 The ECO form that cannot touch clock nets

1. Same ECO (from `5_2_route.odb`, scope reg2reg, margin 5), with the post-GRT chain reduced to `source /work/grt_post.tcl` and `source /work/gf5_grt_measure.tcl`. Either write those two lines to `i1/prd_post_grt_chain.tcl` after `prd_mk.sh` and before `prd_run.sh`, or apply the tool fix first.
2. Tool fix, `tools/die_plan/post_route_drv/post_grt_chain.py` `stage()`: drop `source /work/core_final_repair.tcl` wherever it stands after `grt_post.tcl`, not only as the last line, and refuse to stage when the chain still sources it.
3. Guard, `prd_hook.tcl`: run the `post_grt` clock freeze restore and assert as the last step of `eco_post.tcl`, after the chain, so a later incremental GRT cannot leave an unwired clock net for DRT.
4. `core_final_repair.tcl` line 56: use the scoped non-port hold, not the full FF hold, when a hold scope is set.

Expected from the first pass of the failed run: non-port FF hold +5.05, 0 violators, TT 18.39 on the stage SDC, DRT 0. INFERENCE: the 4 TT endpoints at -16.46 stay inside the gate; not re-measured after the ECO.

Pre-route fallback, only if the ECO fails for a new reason: rerun GRT of g3f with `OT_HOLD_FF_MARGIN = 10` and route once. About 4.5 h. TT has 122 ps of slack at GRT, so the margin costs no setup.

## 3. s81p_slice_station__t51_ot_s81_station_t51_native_w

- MEASURED: it is signed (R-MINIMAL, 11-13 17:52 PST, rc51f ECO i1: DRC 0, TT +9.81, internal FF hold 0 violators, LEC EQ 34,379), re-signed by the autopilot at 23:38 on flow-20261113-ai-s81, counted, and archived on rtx-pro `/home/ubuntu/signed-export-1114/s81/<module>/` and AGIdock.
- The wave lint says so itself: `count: SIGNED IN COUNT BUT NO WAVE VIEW 1`. `autopilot/prov_view_sources_auto.json` lists the module under `missing`: no view pack was ever published to the wave view store (`kw32-views` / `kw43-views`), because the core was built and signed as a lane kit.
- The view files exist on epyc7: `/srv/opentallas-scratch2/claude/die-s81-85/t51pin/eco_wf_scope21b_1113/i1/run/results/asap7/kl_..._rc51f/base/` holds the `.lef`, `_tc.lib`, `_BC.lib`, `6_final.odb` and `.spef`. The archive copy has no LEF or lib.
- Recipe, no build: (1) compare the signed LEF pins and outline with the B6gE plan pins for this core; (2) if equal, publish the view pack from that directory with the export step the other cores used (`signoff.py` export_view, the KW-FIX-32 form) and replicate it to every wave host; (3) add the LEF and both libs to the two archives; (4) the lint then stops and slice_station__t51 launches on the signed view. INFERENCE: I did not run the pin comparison. If the pins differ, the core needs a re-cut on the current plan, and that is a build.
