read_db /work/out/rom_reg/final.odb
set block [ord::get_db_block]
set inst [$block findInst _59683_]
puts "INST_NAME [$inst getName]"
puts "MASTER [[$inst getMaster] getName]"
puts "ORIGIN [$inst getOrigin]"
puts "BBOX [[$inst getBBox] xMin] [[$inst getBBox] yMin] [[$inst getBBox] xMax] [[$inst getBBox] yMax]"
set net [$block findNet _21656_]
puts "NET_NAME [$net getName]"
puts "NET_ITERM_COUNT [llength [$net getITerms]]"
