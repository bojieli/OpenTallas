# el1011-ds-coll 2026-10-11: PRE_GLOBAL_ROUTE hook of the cb/ce hard tiles (children of a wiring-only parent).
# Why: the cbh parent's detail router found no access point for u_q0/ts (DRT-0073): the tile router had run its own
# signals on BOTH layers adjacent to the M5 face pins (cbq0 OBS M6 41.65-45.64 x 0.06-1.86 over ts / t_vm[409..420],
# OBS M4 0.19 um inside the pin end), so the parent can neither via up/down nor reach the 0.024-um stub.  Child LEF
# audit (c2e836720-p2): cbq0 12 / cbq 17 / cbr 51 face pins covered on the layer above.  Fix = a pin-access plan in
# the child: before its global route, the layers adjacent to each face's pin layer are obstructed over the outer
# part of the pin column (stn_pin_keepout.tcl, OT_PK_FRAC of the pin depth + OT_PK_HALO along the face); the SAME
# keepout file is the POST_DETAIL_ROUTE hook and removes exactly those obstructions, so the abstract carries only
# real metal and the outer pin part is clear on the adjacent layers for the parent's via / planar access.
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
