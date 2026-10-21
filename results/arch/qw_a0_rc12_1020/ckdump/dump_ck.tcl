read_db $::env(ODB)
set blk [ord::get_db_block]
set out [open $::env(OUT) w]
foreach nn {ck_dw ck_de ck_rs ck_rsw} {
  set net [$blk findNet $nn]
  if {$net == "NULL"} { puts "no net $nn"; continue }
  foreach it [$net getITerms] {
    set inst [$it getInst]
    set bb [$inst getBBox]
    puts $out "$nn [$inst getName] [[$inst getMaster] getName] [expr {[$bb xMin]/1000.0}] [expr {[$bb yMin]/1000.0}]"
  }
}
close $out
exit
