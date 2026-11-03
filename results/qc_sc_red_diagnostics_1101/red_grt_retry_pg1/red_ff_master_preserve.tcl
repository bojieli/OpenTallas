# Same native family exclusion used by shared post_route_drv/prd_hook.tcl.
# Existing sink FFs remain touchable for D-pin buffer repair, placement LOCKED.
set red_ff_families {DFFHQNx*_ASAP7_75t_R DFFASRHQNx*_ASAP7_75t_R}
set red_du 0
foreach red_f $red_ff_families {
 set red_lc [get_lib_cells -quiet */$red_f]
 if {![llength $red_lc]} {error "RED_FF_MASTER_FAMILY_MISSING $red_f"}
 set_dont_use $red_lc
 incr red_du [llength $red_lc]
}
puts "RED_EXISTING_FF_MASTER_PRESERVE new_master_exclusions=$red_ff_families lib_cells=$red_du existing_instances_touchable"
