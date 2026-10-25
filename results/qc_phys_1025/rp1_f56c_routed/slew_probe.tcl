foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_liberty /ml0/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib
read_db /base/6_final.odb
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
set blk [ord::get_db_block]
foreach p {_5847_/A _5846_/A _5844_/A place2870/A _5852_/A _5845_/A _5827_/A _5856_/A _5825_/A _5855_/A _5877_/A _5891_/A} {
  set n [get_nets -of_objects [get_pins $p]]
  set d [get_pins -of_objects $n -filter "direction==output"]
  set dn [$blk findNet [get_full_name $n]]
  set bb [$dn getTermBBox]
  puts "SLEWP $p net [get_full_name $n] drv [get_full_name $d] [get_property [get_cells -of_objects $d] ref_name] fanout [llength [get_pins -of_objects $n -filter direction==input]] bbox_um [expr {([$bb xMax]-[$bb xMin])/1000.0}]x[expr {([$bb yMax]-[$bb yMin])/1000.0}] cell [get_property [get_cells -of_objects [get_pins $p]] ref_name]"
}
