set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f {asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty $L/$f }
read_db $::env(ODB)

set block [ord::get_db_block]
proc ctr {inst} { set bb [$inst getBBox]; return [list [expr {([$bb xMin]+[$bb xMax])/2000.0}] [expr {([$bb yMin]+[$bb yMax])/2000.0}]] }
set fh [open /out/hops.tsv w]
foreach d [all_registers -data_pins] {
  set di [sta::sta_to_db_inst [lindex [get_cells -of_objects $d] 0]]
  lassign [ctr $di] dx dy
  set best 0; set bs ""
  foreach s [get_fanin -to $d -flat -startpoints_only -trace_arcs all] {
    set sc [get_cells -quiet -of_objects $s]
    if {[llength $sc]} {
      set si [sta::sta_to_db_inst [lindex $sc 0]]
      lassign [ctr $si] sx sy
    } else {
      set bt [$block findBTerm [get_full_name $s]]
      if {$bt eq "NULL"} continue
      set bb [$bt getBBox]; set sx [expr {[$bb xMin]/1000.0}]; set sy [expr {[$bb yMin]/1000.0}]
    }
    set L [expr {abs($sx-$dx)+abs($sy-$dy)}]
    if {$L > $best} { set best $L; set bs "[get_full_name $s]\t$sx\t$sy" }
  }
  puts $fh "[get_full_name $d]\t$dx\t$dy\t$best\t$bs"
}
# outputs: last reg -> port
foreach o [all_outputs] {
  set bt [$block findBTerm [get_full_name $o]]
  if {$bt eq "NULL"} continue
  set bb [$bt getBBox]; set ox [expr {[$bb xMin]/1000.0}]; set oy [expr {[$bb yMin]/1000.0}]
  set best 0; set bs ""
  foreach s [get_fanin -to $o -flat -startpoints_only -trace_arcs all] {
    set sc [get_cells -quiet -of_objects $s]
    if {![llength $sc]} continue
    lassign [ctr [sta::sta_to_db_inst [lindex $sc 0]]] sx sy
    set L [expr {abs($sx-$ox)+abs($sy-$oy)}]
    if {$L > $best} { set best $L; set bs "[get_full_name $s]\t$sx\t$sy" }
  }
  puts $fh "OUT:[get_full_name $o]\t$ox\t$oy\t$best\t$bs"
}
close $fh
