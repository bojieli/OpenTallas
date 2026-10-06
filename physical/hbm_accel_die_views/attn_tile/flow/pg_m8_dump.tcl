# CLAUDE HBM-ABSTRACTS (attn): dump the tile's M8 PG shapes (input of reduce_lef.py --pg-m8) and the quad footprints
read_db /in/4_cts.odb
set blk [ord::get_db_block]
set dbu [$blk getDbUnitsPerMicron]
set f [open /out/pg_m8.txt w]
foreach n {VDD VSS} { foreach sw [[$blk findNet $n] getSWires] { foreach w [$sw getWires] {
  if {[$w isVia]} continue
  if {[[$w getTechLayer] getName] ne "M8"} continue
  puts $f "$n [expr {[$w xMin]/double($dbu)}] [expr {[$w yMin]/double($dbu)}] [expr {[$w xMax]/double($dbu)}] [expr {[$w yMax]/double($dbu)}]" } } }
close $f
foreach i [$blk getInsts] { if {[[$i getMaster] getName] eq "ot_attn_tile_m6h1q"} { set b [$i getBBox]; puts "OT_QUAD [expr {[$b xMin]/double($dbu)}],[expr {[$b yMin]/double($dbu)}],[expr {[$b xMax]/double($dbu)}],[expr {[$b yMax]/double($dbu)}]" } }
exit
