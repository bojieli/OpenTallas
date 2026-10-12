# POST_DETAIL_ROUTE with the face-pin keepout (route_master.sh OT_RM_PK=1): remove exactly the obstructions
# pre_ref_skew_pk.tcl added (the routed odb and the exported abstract carry only real metal), then post_plain.tcl.
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/qwen_die_masters/post_plain.tcl
