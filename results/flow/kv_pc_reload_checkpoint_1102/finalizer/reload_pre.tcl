# Fresh interpreter, true post-repair checkpoint; no sizing or hold repair here.
source /work/grt_pre_core.tcl
source /work/clk_freeze.tcl
ot_clk_freeze
# Clear mixed access catalog BEFORE DPL and fresh native pin_access.
source /work/eco_drt_pre.tcl
detailed_placement
check_placement -verbose
ot_clk_freeze_assert reload_post_dpl
# This must be the ORIGINAL routed DB, never the repaired 4_cts alias.
source /work/prd_route_keep.tcl
ot_prd_route_keep /work/original_route.odb
