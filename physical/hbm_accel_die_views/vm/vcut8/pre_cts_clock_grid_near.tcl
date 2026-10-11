# [vm8] clock grid r3 variant: nearest-root re-home (no capacity cap) on the 2 x 10 grid.  r2 a585c1cfc calibrate: the
# 1.25 cap spilled ~25% of the sinks to a non-nearest root and lengthened the tails (FF max see 355 -> 536, nww 228 ->
# 406, new 180 -> 386 ps; cap 1.0: see 613, sew 667); the 2 x 10 regions alone already bound the per-root share.
set ::env(OT_CG_CAP) 1e9
source /src/physical/hbm_accel_die_views/vm/vcut8/pre_cts_clock_grid.tcl
