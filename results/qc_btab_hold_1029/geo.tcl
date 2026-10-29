read_db /base/6_final.odb
set b [ord::get_db_block]
foreach n {mp_ck_Tpqpy mp_ck_Tpqpz mp_ck_Tpqpa mp_ck_Tpqpw mp_ck_Tpqsx mp_ck_Tpqrv} {
  set i [$b findInst $n]; set net [[$i findITerm Y] getNet]
  set bb [$i getBBox]
  set s "GEO $n drv ([expr {[$bb xMin]/1000.0}],[expr {[$bb yMin]/1000.0}]) net [$net getName]"
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} continue
    set xy [$it getAvgXY]
    append s " | [[$it getInst] getName]/[[$it getMTerm] getName] ([expr {[lindex $xy 1]/1000.0}],[expr {[lindex $xy 2]/1000.0}])"
  }
  puts "$s"
}
