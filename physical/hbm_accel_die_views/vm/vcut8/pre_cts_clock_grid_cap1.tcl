# [vm8] clock grid r2 variant: equal sink share per root (OT_CG_CAP 1.0), then the standard hook.  The variant lives in
# a file (PRECTS) because the job's shell environment is not guaranteed to reach OpenROAD inside the ORFS container.
set ::env(OT_CG_CAP) 1.0
source /src/physical/hbm_accel_die_views/vm/vcut8/pre_cts_clock_grid.tcl
