read_db /out/coupon.odb
set tech [ord::get_db_tech]
[$tech findLayer M1] setResistance 0.563166
[$tech findLayer M2] setResistance 0.534825
[$tech findLayer M3] setResistance 0.563166
[$tech findLayer M4] setResistance 0.432876
[$tech findLayer M5] setResistance 0.4558416
[$tech findLayer M6] setResistance 0.380144
[$tech findLayer M7] setResistance 0.400304
[$tech findLayer M8] setResistance 0.3378624
[$tech findLayer M9] setResistance 0.355786
extract_parasitics -ext_model_file /out/physical_multi.rules -lef_res -max_res 0 -no_merge_via_res -coupling_threshold 0
write_spef -coordinates /out/actual.spef
write_db /out/extracted.odb
