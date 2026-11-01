# CLOCK-128-R6 width-aware extraction: RPERSQ (ohm/sq) = rules r(w0) x w0 per layer, R = RPERSQ x L / w
# OWNER 12.24 optimistic size-effect credit per layer (credit at width): M1=1:w0 M2=1:w0 M3=1:w0 M4=1:w0 M5=1:w0 M6=1:w0 M7=1:w0 M8=0.711361:0.24 M9=0.711361:0.24
set ot_tech [ord::get_db_tech]
[$ot_tech findLayer M1] setResistance 0.563166
[$ot_tech findLayer M2] setResistance 0.534825
[$ot_tech findLayer M3] setResistance 0.563166
[$ot_tech findLayer M4] setResistance 0.432876
[$ot_tech findLayer M5] setResistance 0.455842
[$ot_tech findLayer M6] setResistance 0.380144
[$ot_tech findLayer M7] setResistance 0.400304
[$ot_tech findLayer M8] setResistance 0.240342
[$ot_tech findLayer M9] setResistance 0.253092
extract_parasitics -ext_model_file $P/rcx_patterns.rules -lef_res