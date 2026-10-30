Unsigned measured candidate; no route released. Original result remains NOT SIGNED.

Source: epyc2:/srv/opentallas-scratch2/claude/codex-hbm-cores-1030/ring_slew50.
Actual current binder confirms two ring cuts, params{}, strap_qid2 NE=3/NW=2.
Terminal signoff: TT setup69.55, FF hold1.63, pair41.2/37.9, DRC0/antenna0,
only seven TT slew endpoints (worst335.43 vs320) on five BUFx3 nets.
Driver-to-sink distances156–200um; two/three sinks per net, not zero load.
Exact routed-SPEF read-only replacement probe uses the actual TT/FF selected
libraries and the full FF pin-mean clock calibration/overlay. All seven TT
slew failures disappear; calibrated FF slew/cap0, hold1.63 remains unchanged.
TT setup69.55 remains unchanged. The five-buffer map is guarded by expected
master and signal-net identity; it does not resize any sequential or clock cell.
Physical legalization, fresh route/RCX, exact native LEC and full signoff are
still required. Parent review pending before the physical candidate proceeds.

Physical follow-up receipts (10-30):
- DPL-only exact five-buffer candidate passes placement; max displacement0.5um,
  only two neighboring combinational cells move. All1359clock wires and26394
  clock-net instances remain unchanged under the blocking geometry comparison.
- ring_data5_route2 stops before DRT with RSZ-0074 on net11082: old global
  guides reach22of23pins (_182202_/B missing). Reusing the final routed seed
  retained stale SIGNAL wires/guides, including shifted five-driver pin shapes.
- strip_data_routes.py clears145028nonclock SIGNAL wires and1212688data guides,
  keeping the exact reviewed placement and all1359clock wires. Full clock diff
  versus the original routed baseline passes with0changes.
- Initial gated wrapper used make grt and unexpectedly rebuilt synthesis due
  missing prerequisite artifacts. Its exact own container was stopped before
  placement/CTS/GRT/DRT; route3 records rc137, no orphan remains.
- Corrected grt_then_route.sh uses the canonical do-grt target, ordinary actual
  TT/FF insertion gates plus TTsetup>=0/FFhold>=0, then the exact remaining
  do-route steps. Parent approved this one scoped GRT-first cohort; route4 live.
