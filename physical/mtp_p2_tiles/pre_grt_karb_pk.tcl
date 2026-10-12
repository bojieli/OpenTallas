# PRE_GLOBAL_ROUTE (el1011-ds-mtp 2026-10-12): route_view.sh's fixed karb repair-buffer cap + the above-only face-pin
# keepout (child_lint (f): xport 46b090196 a/b closed timing but 4/1990 face pins had internal M5/M4 OBS above them).
# Env vars set in the job shell do not reach the ORFS container, so the mode is set here.
set ::env(OT_PK_ABOVE_ONLY) 1
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
