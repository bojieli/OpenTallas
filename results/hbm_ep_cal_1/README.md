# HBM-EP-CAL-1 hfd_ep_static: ONE CTS-only calibration build (2026-10-27 03:11 PDT) -- COORD RULING HBM-CORE-LAT-R5 ep 048d2ccea2 (A)
Scope: measurement only. do-cts on the R4 variant A placement (3_place.odb sha fa4f9844..., byte-identical to
intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r4-ep/kits/hfd_ep_static_916cfe0a1db9-_r4). No route, no sign-off claim.
Tree: plan-built core_infra_htree R6 --no-pad I3 nb10,6,10,6 smax150 (best slowest-path plan, hbm_core_lat_r5_ep sweep), UNSIZED,
QC mscts_core/mscts_h (same cf/ as the xcal R5 calibration), TritonCTS off, OT_MSCTS_ITERS=0, no pads/trims/balance.
Run: intel2 ot-run unit oth-ubuntu-1130921-1793095651 (--mem 8, docker cap 8g), exit 0. Kit:
intel2:/srv/opentallas-scratch2/claude/hbm-ep-cal-1/hfd_ep_static_916cfe0a1db9-_cal1.
Built: 202 plan nodes, 128 leaves depth 6, 9977 reg sinks + 4 SRAM macro leaves; 335 clock buffers (299 BUFx24 / 36 BUFx16f);
every root->sink path has 8 buffer stages; Steiner path length (dump) mean 330 / max 623 um.
MEASURED post-CTS insertion, clk port -> 9981 clock pins, PLACEMENT RC (estimate_parasitics -placement, setRC_rcx), UNCHECKED:
- TT mean 185.81 (176.65-189.38, spread 12.72)
- FF mean 142.56 (135.16-145.40, spread 10.23)
- FF hold gate PASS reg2reg wns -71.75 (434 ep); port paths (FF vclk) not gated: 1152 ep wns -111.93.
PLAN MODEL (uf_phys3, plan_I3_nb106106_m150.pred.json) vs BUILT:
- TT_rise mean 290.94 / max 345.29 / window 86.5  ->  built 185.81 / 189.38 / 12.7:  error mean -105.1, max -155.9 ps
- FF_early mean 224.08 / max 268.16              ->  built 142.56 / 145.40:          error mean -81.5, max -122.8 ps
- xcal R5 (same tool chain): TT mean 235.0 -> 162.2 = -72.8 ps; FF 178.5 -> 123.5 = -55.0 ps.
  => the model over-predicts on placement RC in both cores, more for the longer tree (ep path ~1.5-2x xcal); the window is not
  reproduced at all (plan 86.5 vs built 12.7): the predicted ring imbalance does not appear on this tree.
Render (viewed): ep_cal1_tree.png (driver->sink straight lines; buffers red rings, entry star, SRAM grey, sinks coloured by TT).
  The S-island trunks cross the SRAM column straight at x=69 / x=181 (~165 um each); SRAM OBS is M1-M4 only, M5 (vertical,
  max layer) is free above it, so the crossing is legal, but its routed length/RC is not in a placement-RC number.
Decision per ruling: TT 185.8 <= ~290 -> NO re-pack (B) needed; READY for the routed build. Built tree is SHALLOW vs 250+-20
(-64 TT): GRT/RCX first, then the 12.8c designed fixed trunk at the entry (same chain per type) if still below 230.
