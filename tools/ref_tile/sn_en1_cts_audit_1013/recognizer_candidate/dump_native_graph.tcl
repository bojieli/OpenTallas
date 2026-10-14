set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $plat/lib/NLDM/*RVT_TT*] {read_liberty $f}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/4_1_cts.odb
set ot_blk [ord::get_db_block]
set ot_dffe_net /out/actual_native_graph.tsv
set fh [open $ot_dffe_net w]
proc ot_dffe_row {fh args} {
  foreach field $args {if {[regexp {[\t\r\n]} $field]} {error "OT_DFFE_PAIR: unsafe native graph name"}}
  puts $fh [join $args "\t"]
}
foreach bt [$ot_blk getBTerms] {
  set n [$bt getNet];if {$n eq "NULL"} {error "OT_DFFE_PAIR: disconnected port"}
  ot_dffe_row $fh PORT [string tolower [$bt getIoType]] [$bt getName] "@[$n getId]"
}
foreach i [$ot_blk getInsts] {
  ot_dffe_row $fh CELL [$i getName] [[$i getMaster] getName]
  foreach it [$i getITerms] {
    if {![$it isInputSignal] && ![$it isOutputSignal]} continue
    set n [$it getNet]
    if {$n eq "NULL"} {
      # Keep a unique disconnected vertex; it cannot prove any input/clock root.
      set key "@disconnected:[$i getId]:[[$it getMTerm] getName]"
      puts "OT_DFFE_PAIR uncovered disconnected [$i getName]/[[$it getMTerm] getName]"
    } else {set key "@[$n getId]"}
    ot_dffe_row $fh PIN [$i getName] [[$it getMTerm] getName] $key
  }
}
close $fh
puts "SN_ACTUAL_NATIVE_GRAPH_PASS"
exit
