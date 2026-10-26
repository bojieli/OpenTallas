# Explicit HBM TKM prototype guard; sourcing alone does not activate it.
# Call setup AFTER planned root wiring. This does not insert or move anything.
namespace eval ::ot_hbmentry { variable block; variable port; variable max_um; variable root_net; variable first }
proc ::ot_hbmentry::check {} {
  variable block; variable port; variable max_um; variable root_net; variable first
  set bt [$block findBTerm $port]
  if {$bt eq "NULL" || [$bt getNet] ne $root_net} { error "OT_HBM_ENTRY missing/changed actual root $port" }
  set loads {}
  foreach it [$root_net getITerms] { if {[$it isInputSignal]} { lappend loads $it } }
  if {[llength $loads] != 1} { error "OT_HBM_ENTRY root must drive one planned first buffer, got [llength $loads]" }
  set pin [lindex $loads 0]; set inst [$pin getInst]
  if {![regexp {^BUF} [[$inst getMaster] getName]] || [[$inst getMaster] isBlock]} { error "OT_HBM_ENTRY first clock load is not an actual buffer" }
  if {[info exists first] && $first ne [$inst getName]} { error "OT_HBM_ENTRY first buffer changed" }
  set first [$inst getName]
  set pb [$bt getBBox]; set ib [$pin getBBox]
  set x [expr {([$pb xMin]+[$pb xMax])/2.0}]; set y [expr {([$pb yMin]+[$pb yMax])/2.0}]
  set ix [expr {([$ib xMin]+[$ib xMax])/2.0}]; set iy [expr {([$ib yMin]+[$ib yMax])/2.0}]
  set distance [expr {(abs($x-$ix)+abs($y-$iy))/[$block getDbUnitsPerMicron]}]
  if {$distance > $max_um} { error "OT_HBM_ENTRY unbuffered root segment $distance um exceeds $max_um um" }
  puts "OT_HBM_ENTRY PASS port=$port first=$first pin=[$pin getMTerm] distance_um=$distance limit_um=$max_um (included in unchanged tile clock insertion contract)"
  return $distance
}
proc ::ot_hbmentry::setup {blk root_port {limit_um 20.0}} {
  variable block; variable port; variable max_um; variable root_net
  if {[llength [info commands ::ot_hbmentry::cts_orig]]} { error "OT_HBM_ENTRY setup twice" }
  set block $blk; set port $root_port; set max_um $limit_um
  if {![string is double -strict $limit_um] || $limit_um <= 0 || $limit_um > 20.0} { error "OT_HBM_ENTRY limit must be positive and <=20um" }
  set bt [$block findBTerm $port]
  if {$bt eq "NULL"} { error "OT_HBM_ENTRY missing actual BTerm $port" }
  set root_net [$bt getNet]
  check
  rename ::clock_tree_synthesis ::ot_hbmentry::cts_orig
  proc ::clock_tree_synthesis {args} {
    set result [::ot_hbmentry::cts_orig {*}$args]
    ::ot_hbmentry::check
    return $result
  }
}
