# HBM-EP-ROUTE-1 hfd_ep_static: 12.8c entry trunk + routed build (2026-10-27 04:05 PDT), COORD RULING HBM-EP-CAL-1 39a75475cb
Outcome: the trunk works (post-CTS in band); the ROUTE FAILS AT GRT. No DRT, RCX, sign-off or routed LEC exists; nothing is signed off.

## 1. Entry trunk (12.8c; structural, not a residual tool -> no CLOCK-RESIDUAL row)
- ONE fixed chain at the core entry, ahead of the plan root: 4 x BUFx16f_ASAP7_75t_R (`set ot_h_entry_n 4` in kit/mscts_spec.tcl.gz).
  It is common to every branch, so every root->sink path gets the same +4 stages (8 -> 12). No wire padding, no per-tap trims, no balance.
- Size from the plan: entry_trunk.py reads the NLDM liberty tables (RVT TT/FF, ideal clock port, load = next Cin + 0.25 fF) and adds them
  to the cal-1 built 185.81/142.56. N=4 -> +65.7 TT / +50.1 FF -> predicted 251.5 / 192.7 (entry_trunk.out).
- Tool fix: kit/mscts_h.tcl placed entry cells at (0,0). They now sit at the plan root (x - 1.2 um per stage), as mscts_core.tcl does.
  The diff against results/hbm_core_lat_r4_hcroot/cf/mscts_h.tcl is that line plus one comment.
- MEASURED post-CTS, PLACEMENT RC (UNCHECKED): TT mean 253.55 (244.40-257.12, spread 12.72) / FF mean 194.08 (186.69-196.92, spread 10.23).
  Both are in the 250+-20 / 202.5+-20 band, and within +2.0 / +1.4 ps of the liberty prediction. FF hold gate PASS (reg2reg wns -71.75, 435 ep;
  port paths 1152 ep wns -164.28, not gated pre-GRT). 4_cts.odb sha 40d70cf7 (on 3_place fa4f9844 = R4 A / cal-1 placement).

## 2. Route: GRT FAIL (CHECKED, 5_1_grt.log GRT-0096/0116)
Kit recipe: do-5_1_grt, CORNER=BC, FF hold repair, M2-M5, 30 congestion iterations. Run: intel2 ot-run unit oth-ubuntu-1400610-1793096572, 37 min.
- Total overflow 64,245: M2 26,395 / M3 31,007 / M4 5,339 / M5 1,504. Usage 34.8 %.
  The overflow did not converge (reports at iterations 5-30 stay at ~23-27k summed congestion in the 20k-item sample).
- Where (ep_route1_grt_congestion.png, viewed; first 20,000 items of congestion.rpt): all of the sampled overflow is in the LOWER half.
  Most of it lies over the lower SRAM pair (x 34.6-205.8, y 17.3-173.1), where M2-M4 have zero capacity (SRAM OBS M1-M4, so only M5 is left).
  The rest is in the 13-um S std-cell strip (y < 17) at both ends (x 35-45 and 170-206) and in the W column near y 85-110.
  The upper half, over SRAM2/3, has none.
- Cause (geometry): the S face carries 1477 M5 pins along its full width (sd_rx 512 + sd_tx 512 + rx_pin_flit 426 + ...), and the E face carries 798 M4 pins.
  Under the SRAM column the only std-cell area is the ~13 um S strip. Every S-face net under x 35-206 must leave that strip around or over a 156-um-tall SRAM pair.
  With M5 as the ceiling and the SRAM blocking M1-M4, that wall has no horizontal track (M4 is blocked; M5 is vertical-only).
  This is the R5 ASK (B) geometry (S-face SerDes pins at the S corner below the SRAM column), now shown by measurement in routing rather than in clock latency.
- Also seen (warnings, pin-access): DRT-0421 "Term clk has no pins on routing grid" (the plan centre clock pin at 125.28,187.92 M5 is off the M5 track grid),
  and >=1000 DRT-0419 on the SRAM macro terms (no track through the pin centre). They are not the overflow cause, but DRT would hit them.
- Not run: DRT, RCX, S-island trunk routed length/slew (x~69 / x~181), sign-off, routed LEC, routed render. The failed GRT ODB and the iteration reports were deleted.
  The final congestion.rpt is kept as logs/congestion.rpt.gz.

## 3. Next (structural; not a clock problem)
The core needs a plan change before any route: (a) a HBM-MU-QUAD-4 plan delta that moves the S-face sd_tx/sd_rx/rx_pin_flit pins off the SRAM shadow,
toward the W/E columns or the centre band (y 173-203); or (b) a SRAM re-pack that leaves a real S std-cell band or a horizontal channel between
SRAM0 and SRAM1 (now 0.25 um apart); or (c) a COORD ruling on an M6 ceiling for this core (M5 is the core default).
A fresh GRT probe on the changed plan should run before the next full route. With the same tree and placement-RC calibration, the trunk (4 x BUFx16f) carries over.
Kit (kept, CTS successful): intel2:/srv/opentallas-scratch2/claude/hbm-ep-route-1/hfd_ep_static_916cfe0a1db9-_route1.
