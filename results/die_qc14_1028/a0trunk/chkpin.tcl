read_db $::env(ODB)
set db [ord::get_db]; set m [$db findMaster ot_qwen_tile_romleaf]; set mt [$m findMTerm clk]
foreach mp [$mt getMPins] { foreach b [$mp getGeometry] { puts "geom [$b xMin] [$b yMin] [$b xMax] [$b yMax]" } ; set bb [$mp getBBox]; puts "mpinbb [$bb xMin] [$bb yMin]"}
set bb [$mt getBBox]; puts "mtbb [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]"
foreach i [[ord::get_db_block] getInsts] { if {[[$i getMaster] getName] eq "ot_qwen_tile_romleaf"} { set b [$i getBBox]; set it [$i findITerm clk]; set ib [$it getBBox]; puts "INST [$i getOrient] box [$b xMin] [$b yMin] [$b xMax] it [$ib xMin] [$ib yMin] [lindex [$it getAvgXY] 1] [lindex [$it getAvgXY] 2]"; break } }
