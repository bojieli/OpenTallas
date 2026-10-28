# DIE-QC-14: move the romleaf fixture clk pin from the macro centre to the real a0k5 entry (21.612,15.12) M5 (QC-A0-KITS-5 plan fix)
read_db $::env(ODB)
set db [ord::get_db]; set u [[$db getTech] getDbUnitsPerMicron]
set m [$db findMaster ot_qwen_tile_romleaf]
set mt [$m findMTerm clk]
foreach mp [$mt getMPins] {
  foreach b [$mp getGeometry] { set ly [$b getTechLayer]; puts "old [$ly getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]"; odb::dbBox_destroy $b }
  set nb [odb::dbBox_create $mp $ly [expr {int(21.588*$u)}] [expr {int(14.88*$u)}] [expr {int(21.636*$u)}] [expr {int(15.36*$u)}]]
  puts "new [$nb xMin] [$nb yMin] [$nb xMax] [$nb yMax] u=$u"
}
set blk [ord::get_db_block]
foreach i [$blk getInsts] { if {[[$i getMaster] getName] eq "ot_qwen_tile_romleaf"} { set it [$i findITerm clk]; set bb [$it getBBox]; puts "INST [$i getName] [$i getOrient] [expr {([$bb xMin]+[$bb xMax])/2.0/$u}] [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]" } }
write_db $::env(OUT)
