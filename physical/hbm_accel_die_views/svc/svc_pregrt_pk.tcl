# svc segment PRE_GLOBAL_ROUTE (el1012-svc-rob5, 2026-10-12): the karb buffer-cap repair route_view.sh runs here by
# default, then the face-pin keepout (stn_pin_keepout.tcl; OT_PK_ABOVE_ONLY=1 / OT_PK_FRAC=0.5 as tools/ref_tile) so the
# exported abstract passes child_lint (f) (rr1012: every used hfd_svc_* view failed (f)).  POST_DETAIL_ROUTE sources
# stn_pin_keepout.tcl again, which removes exactly these obstructions; hold_eco.sh re-applies it (*_pk.tcl, a804fc09b).
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
