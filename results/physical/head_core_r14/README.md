# HEAD-CORE-R14: s81_head elemA / elemB (2026-10-27)

Successor of HEAD-CORE-R13 (claude/head-core-r13-1027@148ff6a840). It follows COORD RULING HEAD-CORE-R13 (03:23): ASK1, ASK2 (a) and ASK3.
**Neither core is signed off yet.** All the builds below are LIVE, so collect them as listed at the end.

## 1. R13 routed LECs (6_final.v of R12b vs r11 RTL)
| core | verdict | compare points | kept missing | label |
|---|---|---|---|---|
| elemB | **EQUIVALENT** | 27498/27498 proved, 0 differ | 0 | CHECKED (raw epyc2 `elemB_hold2.lec_final/lec/lec.json`, 03:55) |
| elemA | still running at 04:15 (intel1 unit oth-ubuntu-1585112-1793095018) | -- | -- | collect `intel1:.../head-core-r10/elemA_hold2.lec_final/lec/lec.json` |

These prove the flow path only: both R12b netlists are NOT SIGNED.

## 2. Flow change (ASK3), behind one canary kit
- `tools/s81_head/head_grt_drv_unscaled.tcl` (source it from PRE_GLOBAL_ROUTE_TCL). It wraps the GRT-stage repair_design so that it runs on
  the **unscaled** platform setRC (not on rc_cal 0.8/0.9), with slew/cap margin >= 20 %. The kit RC is then restored for hold repair and the reports.
  Calls made before GRT pass through unchanged.
  - Second root cause found: the R10 GRT repair (`actual_head_grt_repair.sh`) ran `do-5_1_grt CORNER=BC CORNERS=bc`, which is FF only.
    The TT slew cone was therefore never visible to repair_design. The R14 rebuild runs GRT MCMM (`CORNER=TC CORNERS="tc bc"`).
- `tools/s81_head/head_eco_post.tcl` + `head_post_route_eco.sh` (warm post-route ECO). It follows the KV-CORES eco_route.tcl recipe, which signed KV e1/e5/e7:
  1. Read the routed RCX SPEF, then run repair_design (fanout 24, margin 20 %).
  2. Run repair_timing -setup (margin 10).
  3. Run repair_timing -hold (margin 10). HB4xp67 is the only added cell, via the kit wrappers hold_pad_hb4 + r10 pass2 (12.4a a1). The clock is untouched.
  4. Run incremental GRT, then DRT re-routes the changed nets, followed by fill, finish and abstract.
  5. Run signoff.py tt,ff (FF bound 202.5). Its rc is recorded but is not fatal.
  6. The **routed LEC ALWAYS runs** whenever a 6_final.v exists.
- `tools/s81_head/head_core_r14_rebuild.sh`: core rebuild up to a GRT checkpoint with the R14 GRT flow.
  1. The plan tree is computed on this build's 3_place before CTS.
  2. It STOPS before route for render + GEOM review.
  3. `OT_R14_FROM_PLACE=1` gives a warm start from the kit's own 3_place, which holds the 12.2a1 pushdown-patched synth plus the island. Only the clock pin box moves.
- **Canary = elemA R12b routed kit.** It has the measured failures (slew TT 8, FF hold -3.38/6). Run on intel1: `head-core-r14/elemA_eco`, unit oth-ubuntu-2273451-1793098716.
  ECO log from the 5_1_grt step (UNCHECKED, tool-reported):
  - PRE (RCX): setup +122.12/0, hold **-4.06/6**, max-slew **8**, max-cap 0.
  - repair_design: 69 slew violations found, 74 buffers inserted on 70 nets, 2 cells resized.
  - Setup: no violations.
  - Hold: 267 endpoints, 263 HB4 inserted, then R10_HOLD_DONE WNS +10.02 / 0.
  - POST (GRT estimate): setup +118.47/0, hold +4.49/0, slew 0, cap 0.
  - HB4 total 16242.
  - DRT was running at 04:15. The sign-off and routed-LEC verdicts are pending.

## 3. elemA rebuild (ASK1): centre pin + balanced trunk
Finding (CHECKED, from the routed abstract LEF and io.tcl):
- The R12b elemA clock pin ft_mstrap_i was already at **(162.00,163.44)**, 4.2 um from the centre. It was not an edge pin.
- The asymmetry is in the **plan trunk**: root legs were 122/145/107/109 um, with N1 down-sized to BUFx10 (left panel of `elemA_plans.png`).

R14:
- The pin moves to exactly (159.84,159.84). The tree is re-planned with head_tree_plan.py `--l1_mirror 1`, which places the L1 nodes at root +-(69.81,51.13), so every root leg is 121 um by geometry.
- Two variants are built in parallel; the first to close wins:
  - `m2` (`--eq_levels 2`): 196 nodes. Root legs are 121/121/121/121 um, and each L1 node's sibling L2 legs are equalised (16 plan-placed detour nodes).
  - `m12` (`--eq_levels 1,2`): 200 nodes. The L1 legs are also equalised by detour, which breaks the mirror. Prefer m2 unless its GRT STA fails.
- Viewed `elemA_plans.png`:
  - m2 is a symmetric H trunk.
  - m12 equalises the root legs with short detour stubs (35-57 um) in front of the mirrored nodes.
- Both use the same plan options as before otherwise (`--entry 159.84,159.84 --seg 1000 --fanouts 4,4,2,4,4 --balance 1 --fringe 8,1,6`), all BUFx24, with no post-measurement sizing.
- CTS finished 04:14 (rc 0, both). GRT MCMM started at 04:14 (the R10 GRT took 1 h 55 m).
- Runs: intel1 `head-core-r14/elemA_rb_m2`, `elemA_rb_m12`.
- Band prediction: UNCHECKED, no plan-model number. The mirror lengthens the two short north legs, which moves the TT mean (228.5) up toward 250.
- Slew cone: handled structurally by GRT repair_design on unscaled RC, which sizes the driver or buffers the net (121-146 um, well under the 405 um reach).

## 4. elemB (ASK2 a)
- RTL: `rtl/dsrom_sys/s81_head/ot_s81hd_elemB_rb.sv` removes the 50 proven-dead input ports row0[16:0], b_v and b_d[31:0]. Inside the wrapper the element inputs are constant 0, the same value the parent tied before.
  - The repo file stays the SYNTHESIS source (clk port). The kit's 12.2a1 pushdown patch (patch_synth.tcl on 1_synth.odb) adds the ft_* island ports after synthesis.
    The LEC gold wrapper (epyc2 `head-core-r14/elemB_rtl_lec/rtl`) is the kit's ft_* form with the same three edits.
  - The sim model `ot_s81hd_elem_cv.sv`, the black box `ot_s81hd_elem_cv_bb.v` and the bundle `ot_s81hd_bundle.sv` drop the ports and the parent ties too.
- LEC: lec.py with gold = the NEW RTL (r11 CY_COPY element RTL + new wrapper) and gate = the hold2 export `actual_functional.v`.
  - That export is already proven EQUIVALENT 27498/27498 to the r11 RTL (R12).
  - The gate-only row0/b_v/b_d inputs become free inputs, so EQUIVALENT proves new RTL = old netlist = old RTL.
  - Run: epyc2 `head-core-r14/elemB_rtl_lec`, unit oth-ubuntu-3964732-1793099267. Collect `lec/lec.json`.
- Kit `epyc2:head-core-r14/elemB_src` (copy of hold2):
  - new RTL;
  - io.tcl: 341 -> 291 place_pin;
  - pins.json: 343 -> 293;
  - constraint.sdc: `non_clk_in = {go rst_n x}`.
- Rebuild: `head-core-r14/elemB_rb` with the same plan options as the built tree (`--entry 142.56,142.56 --seg 405 --fanouts 2,4,4,4,4 --balance 0 --halo 4.32`). It re-synthesises from rtl (`OT_R14_PATCH_SYNTH=1`: orfs_hold_mm -> synth -> face_guard_core -> patch_synth -> place), relaunched at 04:20. The first try failed PPL-0061 because it had no patch step; that data was deleted.
- The elemB clock pin ft_mstrap_i is at (144.72,146.16) (routed LEF, CHECKED). It is near the centre, not on the W edge. The edge "clk" pin belonged to the old closed view.

## Collect
| what | where | need |
|---|---|---|
| R13 routed LEC elemA | intel1 `head-core-r10/elemA_hold2.lec_final/lec/lec.json` | EQUIVALENT (info) |
| canary ECO | intel1 `head-core-r14/elemA_eco/eco_chain.log` (`grep '^HEAD_ECO_\|^SIGNOFF'`), `signoff_actual/`, `../elemA_eco.lec_final/lec/lec.json` | slew 0, TT/FF >= 0, DRC 0, LEC EQUIVALENT |
| elemA rebuilds | intel1 `head-core-r14/elemA_rb_{m2,m12}/r14_rebuild.log` (R14RB_*, ACTUAL_HEAD_STA, HD_GRT_DRV) | GRT STA TT/FF >= 0; then render + GEOM REQ, then route |
| elemB RTL LEC | epyc2 `head-core-r14/elemB_rtl_lec/lec/lec.json` | EQUIVALENT |
| elemB rebuild | epyc2 `head-core-r14/elemB_rb/r14_rebuild.log` | as elemA |

After GEOM PASS, route a rebuild with `actual_head_route_r12.sh`, then run `head_post_route_eco.sh` on the routed kit (the LEC is included).
Sign-off needs:
- TT/FF >= 0;
- DRC 0 and slew 0;
- face_guard PASS;
- a sign-off log newer than 6_final.v;
- routed LEC EQUIVALENT.
