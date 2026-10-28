# DIE-QC-14: rebuild the cluster-CTS parent db with the a0k5 romleaf abstract pin (def round trip, new LEF)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lef
read_lef $L/asap7_tech_1x_201209.lef
read_lef $L/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /p/macros/ot_qwen_tile_lsl_rawfault_m3.lef
read_lef /p/macros/ot_qwen_tile_node.lef
read_lef /w/ot_qwen_tile_romleaf_a0k5pin.lef
read_def /w/cl_nk.def
set u 1000
foreach i [[ord::get_db_block] getInsts] { if {[[$i getMaster] getName] eq "ot_qwen_tile_romleaf"} { set it [$i findITerm clk]; puts "INST [$i getName] [$i getOrient] [expr {[lindex [$it getAvgXY] 1]/1000.0}] [expr {[lindex [$it getAvgXY] 2]/1000.0}]" } }
write_db /w/cl_nkr.odb
