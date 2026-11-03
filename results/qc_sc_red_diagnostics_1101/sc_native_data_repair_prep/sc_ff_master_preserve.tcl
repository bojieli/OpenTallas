# Same native family exclusion used by shared post_route_drv/prd_hook.tcl.
# Existing sink FFs remain touchable for D-pin buffer repair, placement LOCKED.
set sc_ff_families {DFFHQNx*_ASAP7_75t_R DFFASRHQNx*_ASAP7_75t_R}
set sc_du 0
foreach sc_f $sc_ff_families {
 set sc_lc [get_lib_cells -quiet */$sc_f]
 if {![llength $sc_lc]} {error "SC_FF_MASTER_FAMILY_MISSING $sc_f"}
 set_dont_use $sc_lc
 incr sc_du [llength $sc_lc]
}
puts "SC_EXISTING_FF_MASTER_PRESERVE new_master_exclusions=$sc_ff_families lib_cells=$sc_du existing_instances_touchable"
