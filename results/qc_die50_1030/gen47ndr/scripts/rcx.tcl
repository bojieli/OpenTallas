# DIE-QC-50/gen47ndr stage 3: OpenRCX of the DRT-routed clock nets (clk_drt.odb = clock nets only), width-aware rules:
# rcx_ndr008.rules (main tools/die_plan/rcx_width_rules.py write stock.rules rcx/asap7_m8m9_cal.json --widths 0.08:
# second M8/M9 width entry = 0.08 = the NDR width) + -lef_res with RPERSQ = rules r(w0) x w0 (CLOCK-128-R6 recipe,
# clock_routed.rcx_tcl("ndr")).  Signal nets are absent (GRT-only): no signal coupling in this extraction.
read_db $::env(RUN)/drt_$::env(TAG)/clk_drt.odb
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
write_spef $::env(OUT)/clk_rcx.spef
puts RCX_DONE
