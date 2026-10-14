# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
source /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl
source /src/physical/qwen_die_masters/post_plain.tcl
set ::ot_smpub_corridor_pins {{i_v[0]} {i_v[1]}}
set ::ot_smpub_corridor_half 0.864
set ::ot_smpub_corridor_post 1
source /src/physical/hgi_sm_pub_parent_stations/pin_corridor.tcl
