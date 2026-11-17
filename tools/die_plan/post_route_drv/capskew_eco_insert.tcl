# CAPSKEW-ECO 11-17 (FABLE-FIX-HEAD-SD9F ECO2, generalised): insert capture-skew clock delay chains and hold pads on a routed DB.
#   CK <flop> CLK <cells>   delay chain between the clock leaf net and the flop clock pin (the flop captures later)
#   D  <inst> <pin> <cells> hold pad in front of a data pin
# Environment: E_IN (routed odb, no fillers), E_LIST (tsv), E_DIR (output dir), E_OUT (odb), E_PGDIR (kit dir with pg_connect.tcl, optional),
#   E_TAPS (optional file: one clock tap / root net name per line), E_MAXFAN (leaf clock net sink limit, default 100).
# Limits checked BEFORE anything is changed (each prints OT_LIMIT ... and the script exits without writing E_OUT):
#   a CK target pin must sit on a leaf clock net: not a port net, not a net named in E_TAPS, sink count <= E_MAXFAN.
# New cells start on their target cell's site; detailed_placement legalises; every net of a moved or new cell and every rewired net is
# ripped (wire destroyed) for the following detailed_route.  No other netlist, placement or constraint change.
read_db $::env(E_IN)
set blk [ord::get_db_block]; set db [ord::get_db]; set u [$blk getDbUnitsPerMicron]
set pgdir [expr {[info exists ::env(E_PGDIR)] ? $::env(E_PGDIR) : ""}]
set maxfan [expr {[info exists ::env(E_MAXFAN)] ? $::env(E_MAXFAN) : 100}]
set taps {}
if {[info exists ::env(E_TAPS)] && [file exists $::env(E_TAPS)]} {
  set fh [open $::env(E_TAPS) r]; foreach l [split [read $fh] \n] { if {$l ne ""} { lappend taps $l } }; close $fh
}
proc ot_cs_inst {blk name} {
  set inst [$blk findInst $name]
  if {$inst eq "NULL"} { set inst [$blk findInst [string map [list "\[" "\\\[" "\]" "\\\]"] $name]] }   ;# odb keeps Verilog bus brackets escaped
  return $inst
}
set rows {}; set bad 0
set fp [open $::env(E_LIST) r]
foreach line [split [read $fp] \n] {
  if {$line eq "" || [string index $line 0] eq "#"} continue
  lassign [split $line \t] kind iname pin cells
  set inst [ot_cs_inst $blk $iname]
  if {$inst eq "NULL"} { puts "OT_LIMIT no instance $iname"; incr bad; continue }
  set it [$inst findITerm $pin]
  if {$it eq "NULL"} { puts "OT_LIMIT no pin $iname/$pin"; incr bad; continue }
  set net [$it getNet]
  if {$net eq "NULL"} { puts "OT_LIMIT unconnected $iname/$pin"; incr bad; continue }
  if {$kind eq "CK"} {
    set nm [$net getName]
    if {[llength [$net getBTerms]]} { puts "OT_LIMIT clock root/port net $nm on $iname/$pin"; incr bad; continue }
    if {[lsearch -exact $taps $nm] >= 0} { puts "OT_LIMIT clock tap net $nm on $iname/$pin"; incr bad; continue }
    if {[$net getITermCount] - 1 > $maxfan} { puts "OT_LIMIT clock net $nm has [expr {[$net getITermCount]-1}] sinks > $maxfan (not a leaf) on $iname/$pin"; incr bad; continue }
  } else {
    if {[llength [$net getBTerms]] || [$net getSigType] ne "SIGNAL"} { puts "OT_LIMIT data pad on a port/non-signal net $iname/$pin"; incr bad; continue }
  }
  lappend rows [list $kind $inst $it $net $cells]
}
close $fp
if {$bad} { puts "CAPSKEW_REFUSED limits $bad"; exit 0 }
if {$pgdir ne "" && [file exists $pgdir/pg_connect.tcl]} { source $pgdir/pg_connect.tcl }
array set before {}
foreach i [$blk getInsts] { if {[$i getPlacementStatus] eq "PLACED"} { set before([$i getName]) [$i getLocation] } }
set new {}; set rip [dict create]; set k 0; set ncells 0
foreach row $rows {
  lassign $row kind inst it old cells
  dict set rip [$old getName] $old
  if {[[$inst getMaster] isBlock]} {
    set bb [$it getBBox]; set x [$bb xMin]; set y [$bb yMin]; set orient R0
  } else { lassign [$inst getLocation] x y; set orient [$inst getOrient] }
  set prev $old; set j 0
  foreach c [split $cells ,] {
    set m [$db findMaster $c]
    if {$m eq "NULL"} { error "CAPSKEW: no master $c" }
    set ni [odb::dbInst_create $blk $m "ot_cs_${kind}_${k}_$j"]
    $ni setOrient $orient; $ni setLocation $x $y; $ni setPlacementStatus PLACED
    set nn [odb::dbNet_create $blk "ot_cs_n_${kind}_${k}_$j"]
    $nn setSigType [$old getSigType]
    [$ni findITerm A] connect $prev
    [$ni findITerm Y] connect $nn
    dict set rip [$nn getName] $nn
    set prev $nn; lappend new $ni; incr j; incr ncells
  }
  $it disconnect
  $it connect $prev
  incr k
}
puts "CAPSKEW_INSERT targets $k cells $ncells"
if {[llength [info commands ot_pg_connect_all]]} { ot_pg_connect_all capskew_eco; ot_pg_require_bound capskew_eco }
detailed_placement
check_placement -verbose
set moved {}
set fm [open $::env(E_DIR)/moved.txt w]
foreach i [$blk getInsts] {
  set nm [$i getName]
  if {[info exists before($nm)] && $before($nm) ne [$i getLocation]} {
    lappend moved $i
    lassign $before($nm) ox oy; lassign [$i getLocation] nx ny
    puts $fm "$nm\t$ox\t$oy\t$nx\t$ny"
  }
}
foreach i $new { lassign [$i getLocation] nx ny; puts $fm "[$i getName]\t$nx\t$ny\t$nx\t$ny" }
close $fm
set dmax 0
foreach i $moved { lassign $before([$i getName]) ox oy; lassign [$i getLocation] nx ny; set d [expr {abs($nx-$ox)+abs($ny-$oy)}]; if {$d > $dmax} { set dmax $d } }
puts "CAPSKEW_MOVED [llength $moved] max_displacement_um [expr {$dmax/double($u)}] new [llength $new]"
foreach i [concat $moved $new] { foreach t [$i getITerms] { set nn [$t getNet]; if {$nn ne "NULL" && [$nn getSigType] in {SIGNAL CLOCK}} { dict set rip [$nn getName] $nn } } }
set nrip 0
set fr [open $::env(E_DIR)/ripped.txt w]
dict for {nm nn} $rip { puts $fr $nm; set w [$nn getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w; incr nrip } }
close $fr
puts "CAPSKEW_RIP nets [dict size $rip] wires_destroyed $nrip"
write_db $::env(E_OUT)
puts "CAPSKEW_INSERT_DONE"
