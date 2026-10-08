foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_SS*] { read_liberty $l }
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_db /work/cts.odb
read_sdc /work/clocks.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_wire_rc -clock -layers {M8 M9}
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set f [open /work/tree_SS.txt w]
proc drv_of {pin} {
  set net [get_nets -quiet -of_objects [get_pins $pin]]
  if {$net eq ""} { return "-" }
  foreach p [get_pins -quiet -of_objects $net -filter "direction==output"] { return [regsub {/[^/]+$} [get_full_name $p] {}] }
  return "-"
}
foreach c [get_cells *] {
  set ref [get_property $c ref_name]
  set n [get_name $c]
  if {[string match BUF* $ref] || [string match CKINV* $ref] || [string match INV* $ref]} {
    set y [lindex [get_pins -of_objects $c -filter "direction==output"] 0]
    set ai [lindex [get_pins -of_objects $c -filter "direction==input"] 0]
    puts $f "B $n [drv_of [get_full_name $ai]] [get_property $y arrival_max_rise] [get_property $y arrival_min_rise] $ref"
  } elseif {[string match DFF* $ref]} {
    set cp [get_pins $n/CLK]
    puts $f "S $n [drv_of $n/CLK] [get_property $cp arrival_max_rise] [get_property $cp arrival_min_rise]"
  }
}
close $f
exit
