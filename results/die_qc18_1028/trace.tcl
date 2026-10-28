source /w/common.tcl
read_db /p/run/results/asap7/a0_nk_1ck/base/3_place.odb
read_sdc /p/constraint.sdc
set blk [ord::get_db_block]
set N u_g.u_tile.u_tile.u_logic.g_ndh.u_node
proc loc {c} { set o [sta::sta_to_db_inst $c]; if {$o eq "NULL" || $o eq ""} {return "?"}; lassign [$o getLocation] x y; return "[expr {$x/1000.0}],[expr {$y/1000.0}]" }
set fh [open /w/trace.txt w]
foreach bus {a b} { for {set i 0} {$i < 512} {incr i 4} {
  set p [get_pins $N/${bus}\[$i\]]
  set s {}; foreach q [get_fanin -to $p -startpoints_only -flat] { set c [get_cells -quiet -of_objects $q]; if {$c ne ""} { lappend s "[get_property $c ref_name]@[loc $c]" } else { lappend s "PORT:[get_full_name $q]" } }
  puts $fh "$bus $i [join [lrange $s 0 2] { }]"
}}
for {set i 0} {$i < 512} {incr i 4} {
  set p [get_pins $N/y\[$i\]]
  set s {}; foreach q [get_fanout -from $p -endpoints_only -flat] { set c [get_cells -quiet -of_objects $q]; if {$c ne ""} { lappend s "[get_property $c ref_name]@[loc $c]" } else { lappend s "PORT:[get_full_name $q]" } }
  puts $fh "y $i [join [lrange $s 0 2] { }]"
}
close $fh
