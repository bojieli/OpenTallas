# DIE-QC-50/gen47ndr RCX with PG context: the 13,304 full-span PG stripes of the source are OBSTRUCTIONS (OpenRCX does
# not see them), so a clock-only RCX extracts the NDR wire with no shield/plane neighbours (C ~0.06 fF/um vs planned
# 0.108).  Here every full-span obstruction becomes an SBox of a special GROUND net OT_PGCTX on its layer (RCX context
# only; DRT already treated them as blockages), then the same width-aware OpenRCX as rcx.tcl.  Signal nets stay absent.
read_db $::env(DB)
set b [ord::get_db_block]
set da [$b getDieArea]
set pg [odb::dbNet_create $b OT_PGCTX]; $pg setSpecial; $pg setSigType GROUND
set sw [odb::dbSWire_create $pg ROUTED]
set k 0; set lc {}
foreach o [$b getObstructions] {
  set bb [$o getBBox]
  if {([$bb xMin] == [$da xMin] && [$bb xMax] == [$da xMax]) || ([$bb yMin] == [$da yMin] && [$bb yMax] == [$da yMax])} {
    set L [$bb getTechLayer]; if {$L eq "NULL"} continue
    odb::dbSBox_create $sw $L [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] STRIPE; incr k; dict incr lc [$L getName]
  }
}
puts "PGCTX sboxes $k $lc"
set ot_tech [ord::get_db_tech]
[$ot_tech findLayer M1] setResistance 0.563166
[$ot_tech findLayer M2] setResistance 0.534825
[$ot_tech findLayer M3] setResistance 0.563166
[$ot_tech findLayer M4] setResistance 0.432876
[$ot_tech findLayer M5] setResistance 0.455842
[$ot_tech findLayer M6] setResistance 0.380144
[$ot_tech findLayer M7] setResistance 0.400304
[$ot_tech findLayer M8] setResistance 0.337862
[$ot_tech findLayer M9] setResistance 0.355786
extract_parasitics -ext_model_file $::env(RUN)/rcx_ndr008.rules -lef_res
write_spef $::env(OUT)
puts RCX_DONE
