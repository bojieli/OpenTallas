# ref_tile POST_DETAIL_ROUTE: remove the pin-access keepout, restore the plain boundary SDC
if {[file exists /src/physical/ref_tile/qfd_dv_slice2_stnrgc_bt2/stn_pin_keepout.tcl]} { source /src/physical/ref_tile/qfd_dv_slice2_stnrgc_bt2/stn_pin_keepout.tcl } else { puts "REF_TILE WARNING: /src/physical/ref_tile/qfd_dv_slice2_stnrgc_bt2/stn_pin_keepout.tcl is not in the kit: the face-pin keepout toggle is skipped" }
source /src/physical/qwen_die_masters/post_plain.tcl
source /src/physical/qwen_die_masters/sram_edge_guard.tcl
