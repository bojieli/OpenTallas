# F4G probe 2: full DRT (all iterations) of signals with existing clock routing kept + M6 strip; MODE=dt|none
read_db $::env(ODB)
set blk [ord::get_db_block]
proc isclk {n} { set nm [$n getName]; return [expr {[$n getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm]}] }
set nclk 0; set nsig 0
foreach n [$blk getNets] {
  if {[$n isSpecial]} continue
  if {[isclk $n]} { incr nclk; if {$::env(MODE) eq "dt"} {$n setDoNotTouch 1}; if {$::env(MODE) eq "fx"} {$n setWireType FIXED}; continue }
  set w [$n getWire]; if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w; incr nsig }
}
read_guides $::env(GUIDE)
set m6 [[[ord::get_db] getTech] findLayer M6]; set obs {}
set fh [open $::env(STRIP)]; while {[gets $fh l] >= 0} { lassign $l a b c d; lappend obs [odb::dbObstruction_create $blk $m6 $a $b $c $d] }; close $fh
puts "PROBE2 mode $::env(MODE) clk $nclk sigwires_removed $nsig obstructions [llength $obs]"
set_routing_layers -signal M2-M6
detailed_route -output_drc /p/drc_$::env(MODE).rpt -verbose 1
foreach o $obs { odb::dbObstruction_destroy $o }
foreach n [$blk getNets] { if {[isclk $n]} { $n setDoNotTouch 0 } }
write_db /p/full_$::env(MODE).odb
