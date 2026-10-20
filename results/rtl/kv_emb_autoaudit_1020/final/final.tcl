source /cl/native_pg_binding.tcl
read_db /work/results/asap7/opentallas_qkd_embedding_row_tx_ctx_native32_asap7_ref_qkd_embedding_row_tx_ctx_n32c_n32c_801bce136/base/6_final.odb

ot_pg_audit_snapshot [ord::get_db_block] /out/pg_final.json
set f [open /out/net_geometry.tsv w]
puts $f "net\txmin\tymin\txmax\tymax\tspan_dbu"
set worst 0;set wn "";set pg 0;set unbound 0;set protected 0;set fixed 0
foreach i [[ord::get_db_block] getInsts] {
 foreach it [$i getITerms] {
  if {[$it getSigType] in {POWER GROUND}} {
   incr pg
   if {[$it getNet] eq "NULL"} {incr unbound;if {[$i isDoNotTouch]} {incr protected};if {[$i isFixed]} {incr fixed}}
  }
 }
}
foreach net [[ord::get_db_block] getNets] {
 if {[$net getSigType] in {POWER GROUND CLOCK}} {continue}
 set xmin 999999999;set ymin 999999999;set xmax -1;set ymax -1;set count 0
 foreach it [$net getITerms] {
  set bb [[$it getInst] getBBox]
  set xmin [expr {min($xmin,[$bb xMin])}];set ymin [expr {min($ymin,[$bb yMin])}]
  set xmax [expr {max($xmax,[$bb xMax])}];set ymax [expr {max($ymax,[$bb yMax])}];incr count
 }
 foreach bt [$net getBTerms] {
  foreach bp [$bt getBPins] {foreach bb [$bp getBoxes] {
   set xmin [expr {min($xmin,[$bb xMin])}];set ymin [expr {min($ymin,[$bb yMin])}]
   set xmax [expr {max($xmax,[$bb xMax])}];set ymax [expr {max($ymax,[$bb yMax])}];incr count
  }}
 }
 if {$count<2} {continue}
 set span [expr {$xmax-$xmin+$ymax-$ymin}]
 puts $f "[$net getName]\t$xmin\t$ymin\t$xmax\t$ymax\t$span"
 if {$span>$worst} {set worst $span;set wn [$net getName]}
}
close $f
set b [ord::get_db_block];set dbu [$b getDbUnitsPerMicron];set rect [$b getDieArea]
puts "OT_FINAL_GEOMETRY max_signal_bbox_manhattan_um=[expr {$worst/double($dbu)}] net=$wn outline_um=[expr {[$rect dx]/double($dbu)}]x[expr {[$rect dy]/double($dbu)}]"
puts "OT_FINAL_PG pg=$pg unbound=$unbound protected_unbound=$protected fixed_unbound=$fixed"
exit
