# Optional PRE_GLOBAL_PLACE placement structure for FT QN -> INV pairs.
# Keep the polarity inverter beside the planned launch station; subsequent
# repair_design buffers the long wire after the inverter, rather than the weak QN.
# Placement only: no cells, connections, clocks, or cycles change. The ordinary
# face_flops_release hook releases these cells for legalisation before DPL.
if {![info exists ::env(OT_FT_POLARITY_LOCAL)] || $::env(OT_FT_POLARITY_LOCAL) ne "1"} {return}
set fpl_blk [ord::get_db_block]
set fpl_core [$fpl_blk getCoreArea]
set fpl_n 0
set fpl_seen {}
set fpl_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
foreach fpl_ff [$fpl_blk getInsts] {
  if {![regexp {^u_ft_.+_s[0-9]+/q\[} [$fpl_ff getName]]} {continue}
  if {![string match DFF* [[$fpl_ff getMaster] getName]]} {continue}
  if {[$fpl_ff getPlacementStatus] ni {FIRM PLACED}} {continue}
  foreach fpl_q [$fpl_ff getITerms] {
    if {![$fpl_q isOutputSignal] || [[$fpl_q getMTerm] getName] ne "QN"} {continue}
    set fpl_net [$fpl_q getNet]
    if {$fpl_net eq "NULL" || $fpl_net eq "" || [llength [$fpl_net getBTerms]]} {continue}
    set fpl_loads {}
    foreach fpl_it [$fpl_net getITerms] {
      if {[$fpl_it isInputSignal]} {lappend fpl_loads $fpl_it}
    }
    if {[llength $fpl_loads] != 1} {continue}
    set fpl_it [lindex $fpl_loads 0]
    set fpl_inv [$fpl_it getInst]
    if {[[$fpl_it getMTerm] getName] ne "A" || ![string match INV* [[$fpl_inv getMaster] getName]]} {continue}
    if {[$fpl_inv getPlacementStatus] in {FIRM LOCKED COVER} || [dict exists $fpl_seen [$fpl_inv getName]]} {continue}
    set fpl_bb [$fpl_ff getBBox]
    set fpl_w [[$fpl_inv getMaster] getWidth]
    set fpl_x [$fpl_bb xMax]
    if {$fpl_x + $fpl_w > [$fpl_core xMax]} {set fpl_x [expr {[$fpl_bb xMin]-$fpl_w}]}
    if {$fpl_x < [$fpl_core xMin]} {continue}
    $fpl_inv setOrient [$fpl_ff getOrient]
    $fpl_inv setLocation $fpl_x [$fpl_bb yMin]
    $fpl_inv setPlacementStatus FIRM
    dict set fpl_seen [$fpl_inv getName] 1
    puts $fpl_out "[$fpl_inv getName]\tPOLARITY\t$fpl_x\t[$fpl_bb yMin]\t[$fpl_ff getName]"
    incr fpl_n
  }
}
close $fpl_out
puts "OT_FT_POLARITY_LOCAL launch pairs $fpl_n (placement only, PIN CYCLES 0)"
