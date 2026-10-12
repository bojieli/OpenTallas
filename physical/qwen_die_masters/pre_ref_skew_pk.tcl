# PRE_GLOBAL_ROUTE with the face-pin keepout (route_master.sh OT_RM_PK=1, el1011-ds-misc/lint 2026-10-11): the die-context
# boundary as pre_ref_skew.tcl, then the adjacent-layer obstructions over the face-pin column (removed by post_plain_pk.tcl).
source /src/physical/qwen_die_masters/pre_ref_skew.tcl
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
