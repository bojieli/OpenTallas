# DIE-HEAD-16 (2026-10-28): hd_tile register clock as a plan-placed spine + local trees (12.13b / 12.16e local form)

Labels: CHECKED = my own tool runs on the named files (not NUMBER-CHECKed). ESTIMATE = model claim. All numbers are
TT/FF placement RC (estimate_parasitics -placement, kit setRC_rcx: clock wire 21.4 ohm/um, 0.113 fF/um) unless marked GRT.
DIAGNOSTIC only: CTS step of the DIE-HEAD-14/15 one-entry hd_tile kit (synth/floorplan/place reused, 3_place.odb of
DIE-HEAD-14), not a run_kit gate run. Data: intel1:/srv/opentallas-scratch2/claude/die-head-16/{p1..p4,kits/hd_tile}.

## Form (kit-local, `kits/hd_tile/h16_spine.tcl` + planner `spine16.py`)
- Root split and core early taps from DIE-HEAD-15 (`h16_coretaps.tcl` = h15_coretaps with 0 core delay stages and the
  root split moved above the die-island row, y 368).
- Register sinks (25,747 on clk) clustered by k-means (seeded from fixed 118 x 115 um bins, radius cap 100 um after
  pass 1, deterministic). One BUFx24 tap driver per cluster at its centroid (moved outside a hard core if inside);
  TritonCTS builds ONLY the tap nets (`-clk_nets {h16_t* fclk_in_i}`), so each local tree is 2-4 levels.
- Trunk: BUFx24 at plan coordinates, hops 115-220 um, every node fed from its parent's output net:
  channel x 354, cross row y 368 (above the island row 349.9-358.6), strip y 717/726, columns beside eB.
  V3 adds EXPRESS chains (X*, no taps) from the entry to region hubs H* in the upper regions.
- Balance (pass 4): per-tap PAD x BUFx4 abutted before the tap driver (driver end, slew by construction), PAD =
  round((T - measured tap mean)/22 ps) from pass 3 (plan data, per tap, not a post-CTS ECO on sinks).

## Results (CHECKED own runs)
| pass | form | taps | reg insertion TT min/p50/p99/max | notes |
|---|---|---|---|---|
| DIE-HEAD-15 | TritonCTS one net | - | 748 / 793 / 1095 / 1119 | depth 19-22, avg sink wire 854 um |
| p1 | V1 trunk, radius 150 | 25 | 229 / 389 / 689 / 704 | FF 178..595 |
| p2 | V2 per-direction root drivers, radius 100 | 34 | 182 / 394 / 600 / 666 | |
| p3 | V3 + express to upper hubs | 34 | 183 / 373 / 564 / 631 | far taps 500-600 |
| p4 | V3 + per-tap balance to 560 (273 BUFx4) | 34 | 522 / 562 / 592 / 625 | FF 421 / 448 / 485 / 528 |

p4 (balanced), register<->register related pairs (pair_skew.tcl unchanged, 1861 core-pin pairs filtered out by
`ps_regonly.tcl`; 55,549 pairs, CPPR): TT setup 89.9 / hold 94.2 ps, FF setup 69.6 / hold 83.8 ps, p99 raw 35-40 ps.
DIE-HEAD-15 worst was -800.5 (incl. the 8 fclk_out_o relay flops; FF hold worst here is u_srl_37 -> u_rrl_38 83.8).
Local trees: depth 2-4, tap driver -> leaf 100-110 ps; in-tap spread 6-87 ps (most 10-30).
Clock-net slews: no clock-net max_slew/max_cap violator (pre-repair data-net violators only); max CK pin slew 302 ps.
Core pins (p4): eA1-3 186-195 TT (eff. 441-451 vs the old 450 target, OK); eA0 389 / eB 407 = the FLOW tap_balance
core pass re-hung them (3 delay cells) -- the plan form must turn that pass off for plan-tapped cores.
With T_reg = 562 the core early taps must be re-targeted: P = T - L = eA 307 / eB 331 TT (worst reg->core pair now -428.6
because cores still sit at the 450 plan).

## ESTIMATE correction (12.14b)
DIE-HEAD-15 estimated T = 430-470 TT with 0.34 ps/um repeated wire + 80-120 ps local tree. Measured (p3 trunk.txt):
- BUFx24 hop delay 35-50 ps (loaded), wire 30-65 ps per 120-220 um at the kit clock RC -> 0.43-0.55 ps/um effective.
- local tree 100-110 ps, tap driver ~30-35 ps, entry 10-40 ps.
- Far upper regions (x 120-200 / 520-640, y 790-970) are 640-760 um Manhattan from the single clk entry at the channel
  cross -> 500-600 ps TT from the spine; balanced floor T ~ 560 TT / 450 FF on placement RC.
So T = 450 TT from ONE entry at the channel cross is NOT reachable with BUFx24 on the kit clock RC; the spine cuts
the register insertion from 793 (p50) to a balanced 562 and the spread from 371 to 103 ps.
GRT probe on p4 (CHECKED own, `make grt` SKIP_INCREMENTAL_REPAIR=1, GLOBAL_ROUTE_ARGS -congestion_iterations 50,
log intel1 die-head-16/kits/hd_tile/grt_h16_p4.log): overflow 0 on M2-M7 (max H/V 0/0) after extra iteration 1/50,
wirelength 1.516 m; diagnostic only, NOT a tile pass (no repair, no hold gate).
Routed-RC arrivals (estimate_parasitics -global_routing, `h16_grtmeas.tcl` POST_GLOBAL_ROUTE, meas16g/):
- registers TT 439 / 524 / 585 / 590 (min/p50/p99/max), tap means 475-579, max CK slew 131 ps, no clock-net slew violator.
- the express trunk is ~20-25 % faster than on placement RC (HL3 Y 372 vs 462; XU2 Y 162 vs 206) because GRT puts
  the long clock nets on M5-M7, so the balance pads computed on placement RC over-pad the near taps on routed RC
  (spread 151 ps routed vs 103 placement).
- core pins TT eA1-3 127-146, eA0 280, eB 283 (flow core pass), all-pair worst reg->core -461.5 (cores still on the 450 plan).
- ESTIMATE from the routed trunk: unpadded far-tap floor ~510-530 TT -> a routed-balanced T ~ 520-530 TT (UNCHECKED;
  needs one pass with pads computed from routed arrivals).

## What this means for the plan (ASK in COORD-REVIEW-QUEUE)
T = 450 TT is not reachable from the one clk entry at the channel cross. Options:
(a) DEFAULT: keep the single entry and the spine form; set the hd_tile register target from the routed spine floor
    (~520-530 TT, FF ~ x0.8), compute the per-tap pads from ROUTED arrivals (pads become plan data), re-target the core
    early taps to P = T - L (eA ~270 / eB ~295 TT: natural ~130-150 + ~6 BUFx4 at the driver end), switch off the flow
    tap_balance core pass for plan-tapped cores, then re-run the HEAD die CA plan + die STA with the new hd_tile
    insertion (the die STA PASS 161.3/182.9 used the old budget; UNCHECKED how the die model binds hd_tile insertion:
    die_plan_root_sp5.json hd_tile clock.insertion_ps = 250 with core taps 255.24, kit OT_VCLK 450).
(b) a second hd_tile clock entry for the upper regions (y > 700) fed from the die tree: keeps 450 but adds a die-level
    unshared-clock crossing inside the tile (12.16b) -- not recommended.
