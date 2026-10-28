source /w/common.tcl
read_db /p/run/results/asap7/a0_nk_1ck/base/3_place.odb
read_sdc /p/constraint.sdc
set N u_g.u_tile.u_tile.u_logic.g_ndh.u_node
proc loc {c} { set o [sta::sta_to_db_inst $c]; if {$o eq "NULL" || $o eq ""} {return "?"}; lassign [$o getLocation] x y; return "[expr {$x/1000.0}],[expr {$y/1000.0}]" }
proc cellof {q} { return [get_cells -quiet -of_objects $q] }
set fh [open /w/trace2.txt w]
foreach bus {a b} { for {set i 0} {$i < 512} {incr i 4} {
  foreach q [get_fanin -to [get_pins $N/${bus}\[$i\]] -startpoints_only -flat] {
    set c [cellof $q]; if {$c eq ""} continue
    set dp [get_pins -quiet -of_objects $c -filter "direction==input"]
    set ups {}
    foreach d $dp { if {[get_property $d is_clock]} continue
      foreach u [get_fanin -to $d -startpoints_only -flat] { set uc [cellof $u]; if {$uc ne ""} { lappend ups "[get_full_name $uc]@[loc $uc]" } else { lappend ups "PORT:[get_full_name $u]" } } }
    puts $fh "$bus $i [get_full_name $c]@[loc $c] UP [llength $ups] [join [lrange $ups 0 3] { }]"
    break
  }
}}
for {set i 0} {$i < 512} {incr i 4} {
  foreach q [get_fanout -from [get_pins $N/y\[$i\]] -endpoints_only -flat] {
    set c [cellof $q]; if {$c eq ""} continue
    set op [get_pins -quiet -of_objects $c -filter "direction==output"]
    set dns {}
    foreach o $op { foreach u [get_fanout -from $o -endpoints_only -flat] { set uc [cellof $u]; if {$uc ne ""} { lappend dns "[get_full_name $uc]@[loc $uc]" } else { lappend dns "PORT:[get_full_name $u]" } } }
    puts $fh "y $i [get_full_name $c]@[loc $c] DN [llength $dns] [join [lrange $dns 0 3] { }]"
    break
  }
}
close $fh
