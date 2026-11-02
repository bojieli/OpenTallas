ot_clk_freeze_assert reload_post_grt
ot_prd_route_keep_restore
source /work/grt_post_core.tcl
# Every connected signal needs actual current routing coverage. Frozen clock
# wires count only when truly FIXED; the independent ORIGINAL wire diff blocks.
set missing {}; set guided 0; set fixed 0
foreach n [[ord::get_db_block] getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  if {[llength [$n getITerms]] + [llength [$n getBTerms]] < 2} continue
  if {[llength [$n getGuides]]} { incr guided; continue }
  if {[$n getWire] ne "NULL" && [ot_clk_wire_types $n] eq {64}} { incr fixed; continue }
  lappend missing [$n getName]
}
puts "PC_RELOAD_COVERAGE current_guided $guided fixed_wire $fixed missing [llength $missing]"
if {[llength $missing]} { error "PC_RELOAD_COVERAGE missing [lrange $missing 0 15]" }
ot_clk_dump /work/reload_post_grt.clock.tsv reload_post_grt
write_guides $::env(RESULTS_DIR)/route.guide
# Reaching this marker proves the entire required original POST succeeded.
set ::pc_fresh_grt_post_complete 1
