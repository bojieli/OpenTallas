# HBM-CORES-REBAL-12 (2026-10-28) -- hnx_lane_x face fix, programme_store_r10 GPL failure, collect state

## 1. hnx_lane_x (C24 child) -- post-synth face_guard FAIL fixed
REBAL-11 kit `hnx_lane_x_c17b412817f2-_c24` passed KIT_PREFLIGHT, but its run stopped at FAIL_PREFLOOR face_guard
(19:10, CHECKED): 1663/1669 ok, shared 4 (r_bdc 3 loads, r_tcc 5, r_g 2, r_x 2) + unregistered 2 (iv_b, sv_f ->
AND2 -> station valid D). Cause: r_* are the lane's sync reset taps (parent relay rr[1..4+4p]) but did not match the
generator's reset regex, so the kit treated them as data pins; under OT_SMH_RP4_SRST the station valid
`xb_v <= r_x ? iv_b : 0` puts the reset AND between pin and flop.
Fix (die-local, no shared tool change):
* `pinreg_cut.py`: in hnx_lane_x only, SRST form: `xb_vr<=iv_b; xf_vr<=sv_f; x_rq<=r_x; xb_v=x_rq&xb_vr; xf_v=x_rq&xf_vr`
  (AND moved behind 3 flops, same cycle behaviour). Async form unchanged inside `else`.
  yosys equiv old cut vs new cut (lanecut_eq/eq.ys, -seq 2 + equiv_induct): 1865/1865 PROVEN; mutant
  (xb_v without x_rq, eqm.ys) CAUGHT (1 unproven). CHECKED.
* `mk_hnx_r12.py`: REBAL-11 mk_hnx.py + RST_RE extended by r_bdc/r_tcc/r_g/r_x (freeze resets 4, reset SDC rule,
  face_guard_core reset exemption as for every core reset) + the r12 cut file.
Kit `hnx_lane_x_c17b412817f2-_c24r12`: KIT_PREFLIGHT PASS 0; post-synth FACE_GUARD PASS 1665/1665 (1670 pins - clk - 4
resets) CHECKED. Hand trial run GOAL cts on intel2 (ot-run, chain_r11.sh -> intel2:/srv/opentallas-scratch2/claude/
hbm-cores-rebal-12/post_hnx/).

## 2. programme_store_r10 C24 -- GPL-0305 divergence, routing-limited
REBAL-11 run `ot_hgi_sfu_programme_store_r10_20117b319f18-_c24` FAILED GPL-0305 (RePlAce diverged) after the
routability loop: 71.5% of GR tiles overflowed (total overflow ~80k). The 10-26 HBM-CORE-LAT r4 kit (RTLMP placement,
epyc2 .../hbm-core-lat-r4-hub) fails the same way (71.4-72.6% tiles, GPL-0305): not caused by the C24 array. CHECKED
from both logs.
Estimate (UNCHECKED, analytic): 44 x ot_sram_1r1w_512x256 (96.55x69.66, 829 pins all M4 on the L/R edges, OBS M1-M4)
= 296k um2 = 72% of the 413k core. Over the macros only M5 (vertical) routes, so all horizontal traffic uses the
8.64-um row gaps; each 15.4-um vertical channel faces ~18 macros x ~415 pins = ~7.5k pins. Std cells 10.7k um2 before
GPL repair. This is a plan/outline/layer problem for DIE-HBM, not a flow knob.
A what-if GPL with MAX_ROUTING_LAYER M7 (docker probe) gave bit-identical overflow numbers, so the config variable is
not what GPL's routability layers read; probe stopped, no conclusion drawn.
