# mock OpenROAD/ODB for landed_raw_tap.tcl ot_lrt_tap (L2H-PGVM unit check)
namespace eval ord {}; namespace eval odb {}; namespace eval sta {}
set ::chain [dict create]   ;# iterm -> number of buffers in front
set ::nid 0
proc obj {name body} { proc $name {m args} $body }
proc ord::get_db {} { return DB }
proc ord::get_db_block {} { return BLK }
obj DB { if {$m eq "findMaster"} { return BM } }
obj BM { if {$m eq "getMTerms"} { return {MA MY} } }
obj MA { switch $m { getSigType {return SIGNAL} getIoType {return INPUT} getName {return A} } }
obj MY { switch $m { getSigType {return SIGNAL} getIoType {return OUTPUT} getName {return Y} } }
proc all_clocks {} { return {} }
proc get_property {o p} { if {$p eq "lib_pin_name"} { return [lindex [split $o :] 1] } ; return 0 }
obj BLK { if {$m eq "getInsts"} { return {I0 I1 I2} } }
foreach i {I0 I1 I2} {
  obj $i "switch \$m { getMaster {return MST} getName {return $i} getITerms {return {${i}_ckr ${i}_ck}} findITerm {return ${i}_ck} getBBox {return BB} }"
  foreach p {ckr ck} {
    obj ${i}_$p "switch \$m { getMTerm {return MT_$p} getNet {return NET} getAvgXY {return {1 10 20}} disconnect {} connect {} }"
  }
  dict set ::chain ${i}_ckr 0
}
obj MST { if {$m eq "getName"} { return MST } }
obj MT_ckr { return ckr }
obj MT_ck { return ck }
proc get_cells {args} { return [lindex $args end] }
proc get_pins {args} { set c [lindex $args end]; return [list $c:ckr $c:ck] }
proc odb::dbInst_create {blk bm name} { incr ::nid; set n B$::nid; obj $n {switch $m { findITerm {return TERM} getObjectType {return dbInst} default {} }}; return $n }
obj TERM { }
proc odb::dbNet_create {blk name} { incr ::nid; set n N$::nid; obj $n {switch $m { getObjectType {return dbNet} default {} }}; return $n }
proc odb::dbInst_destroy {b} {}
proc odb::dbNet_destroy {n} {}
proc detailed_placement {} {}
proc estimate_parasitics {args} { incr ::est }
set ::est 0
set ::ot_lrt_targets [dict create MST/ckr {ref ck tt 25 ff 25 ss 25}]
source [lindex $argv 0]
# per-pin mock: the iterm's chain length is counted by connect calls on the buffer output; emulate via made-list size
proc ot_lrt_corner {cell} { return tt }
# raw pin wire = 10 * (buffers in front) + per-instance offset; buffers counted from created inst names in the chain
rename odb::dbInst_create _ic
proc odb::dbInst_create {blk bm name} { regexp {ot_lrt_(I[0-9])_} $name -> i; dict incr ::chain ${i}_ckr; set ::last($i) [_ic $blk $bm $name]; return $::last($i) }
rename odb::dbInst_destroy _id
proc odb::dbInst_destroy {b} { foreach i {I0 I1 I2} { if {[info exists ::last($i)] && $::last($i) eq $b} { dict incr ::chain ${i}_ckr -1 } }; _id $b }
proc ot_lrt_wire {pin} { lassign [split $pin :] c p; if {$p eq "ck"} { return 0.0 }; set off [dict get {I0 -3 I1 4 I2 -20} $c]; return [expr {10.0*[dict get $::chain ${c}_ckr] + $off}] }
ot_lrt_tap
puts "estimates=$::est chains=$::chain"
