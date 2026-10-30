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
