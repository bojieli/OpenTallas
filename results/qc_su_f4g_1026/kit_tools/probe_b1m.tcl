# F4G probe 3 (B1 clock-first): route ONLY clock nets on the post-hold GRT DB; all other regular nets temporarily special
read_db $::env(ODB)
set blk [ord::get_db_block]
proc isclk {n} { set nm [$n getName]; return [expr {[$n getSigType] eq "CLOCK" || [string match ot_ms_* $nm] || [string match clknet* $nm]}] }
read_guides $::env(GUIDE)
set sp {}; set nclk 0
foreach n [$blk getNets] {
  if {[$n isSpecial]} continue
  if {[isclk $n]} { incr nclk; continue }
  $n clearGuides; if {$::env(MODE) eq "special"} {$n setSpecial}; lappend sp $n
}
puts "PROBE3 clk $nclk made_special [llength $sp]"
set_routing_layers -signal M2-M6
detailed_route -output_drc /p/drc_b1.rpt -verbose 1
puts "PROBE3 design_is_routed [design_is_routed]"
if {$::env(MODE) eq "special"} { foreach n $sp { $n clearSpecial } }
write_db /p/b1_$::env(MODE).odb
