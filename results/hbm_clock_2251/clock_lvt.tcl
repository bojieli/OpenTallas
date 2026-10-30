# Explicit near-miss clock-only variant (AGENTS 5.7), no data net/cycle edits.
set db [ord::get_db]
set blk [ord::get_db_block]
set selected {}
set depths {}
set queue {}
foreach bt [$blk getBTerms] {
  if {[$bt getIoType] eq "INPUT" && [regexp {^clk(_ctl)?$} [$bt getName]]} {
    lappend queue [list [$bt getNet] 0]
  }
}
for {set qi 0} {$qi < [llength $queue]} {incr qi} {
  lassign [lindex $queue $qi] net depth
  if {$net eq "NULL" || $net eq ""} continue
  foreach term [$net getITerms] {
    if {[[$term getMTerm] getIoType] ne "INPUT"} continue
    set inst [$term getInst]
    set name [$inst getName]
    if {[dict exists $depths $name]} continue
    if {![regexp {^(BUF|INV).*_ASAP7_75t_R$} [[$inst getMaster] getName]]} continue
    dict set depths $name $depth
    foreach out [$inst getITerms] {
      if {[[$out getMTerm] getIoType] eq "OUTPUT"} {
        lappend queue [list [$out getNet] [expr {$depth+1}]]
      }
    }
  }
}
set maxdepth [expr {[info exists ::env(CLOCK_LVT_MAX_DEPTH)] ? $::env(CLOCK_LVT_MAX_DEPTH) : -1}]
foreach net [$blk getNets] {
  if {[$net getSigType] ne "CLOCK"} continue
  foreach term [$net getITerms] {
    if {[[$term getMTerm] getIoType] ne "OUTPUT"} continue
    set inst [$term getInst]
    # Plan-owned pushdown drivers remain exactly as built.
    if {[$inst isDoNotTouch]} continue
    if {$maxdepth >= 0 && (![dict exists $depths [$inst getName]] || [dict get $depths [$inst getName]] > $maxdepth)} continue
    set old [$inst getMaster]
    set oldname [$old getName]
    if {![regexp {^(BUF|INV).*_ASAP7_75t_R$} $oldname]} continue
    dict set selected [$inst getName] $inst
  }
}
if {![dict size $selected]} {error "CLOCK_LVT no actual clock drivers"}
set total [llength [$blk getInsts]]
if {double([dict size $selected])/$total > .02} {error "CLOCK_LVT exceeds 2 percent"}
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef
set count 0
dict for {name inst} $selected {
  set old [$inst getMaster]
  set newname [regsub {_R$} [$old getName] _L]
  set new [$db findMaster $newname]
  if {$new eq "NULL" || $new eq ""} {error "CLOCK_LVT missing $newname"}
  if {[$old getWidth] != [$new getWidth] || [$old getHeight] != [$new getHeight]} {
    error "CLOCK_LVT size mismatch $name"
  }
  set oldports {}; set newports {}
  foreach mt [$old getMTerms] {lappend oldports [list [$mt getName] [$mt getIoType] [$mt getSigType]]}
  foreach mt [$new getMTerms] {lappend newports [list [$mt getName] [$mt getIoType] [$mt getSigType]]}
  if {[lsort $oldports] ne [lsort $newports]} {error "CLOCK_LVT pin mismatch $name"}
  $inst swapMaster $new
  incr count
}
puts "CLOCK_LVT count=$count total=$total fraction=[expr {double($count)/$total}] maximum_depth=$maxdepth functional_class=BUF_INV_only data_nets_unchanged=1"
