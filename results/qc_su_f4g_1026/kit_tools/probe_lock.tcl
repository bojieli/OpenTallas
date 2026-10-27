# F4G probe: does DRT keep pre-existing clock-net routing? MODE=dt (dont_touch) | none | special
read_db $::env(ODB)
set blk [ord::get_db_block]
proc isclk {n} { set nm [$n getName]; return [expr {[$n getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm]}] }
proc fp {blk} {
  set s 0; set k 0
  foreach n [$blk getNets] {
    if {![isclk $n]} continue
    set w [$n getWire]; if {$w eq "NULL" || $w eq ""} continue
    incr k; set s [expr {($s + [$w length]*131 + [$w count]) % 1000000007}]
  }
  return "$k $s"
}
set nclk 0; set nsig 0
foreach n [$blk getNets] {
  if {[$n isSpecial]} continue
  if {[isclk $n]} { incr nclk; if {$::env(MODE) eq "dt"} {$n setDoNotTouch 1}; if {$::env(MODE) eq "special"} {$n setSpecial}; continue }
  set w [$n getWire]; if {$w ne "NULL" && $w ne ""} { odb::dbWire_destroy $w; incr nsig }
}
puts "PROBE mode $::env(MODE) clocknets $nclk sig_wires_removed $nsig before_fp [fp $blk]"
read_guides $::env(GUIDE)
set_routing_layers -signal M2-M6
detailed_route -droute_end_iter 1 -verbose 0
puts "PROBE mode $::env(MODE) after_fp [fp $blk]"
write_db /p/after_$::env(MODE).odb
