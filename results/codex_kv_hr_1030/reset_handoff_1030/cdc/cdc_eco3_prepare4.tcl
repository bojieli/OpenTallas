define_corners tc bc
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner tc /work/model_lvt/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz
read_liberty -corner bc /work/model_lvt/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz
read_db /work/eco2_grt/5_1_grt_pg_bound.odb
read_lef /work/model_lvt/asap7sc7p5t_28_L_1x_220121a.lef
read_sdc /work/eco2_grt/5_1_grt.sdc
source /work/setRC_rcx.tcl
source /work/clk_freeze_supported.tcl
foreach n [ot_clk_dbnets] {$n clearSpecial}
set_propagated_clock [get_clocks clk]
file mkdir /work/eco3b
set ::env(RESULTS_DIR) /work/eco3b
ot_clk_freeze

set b [ord::get_db_block];set before {};set allowed {wire4506 place3260 place3259}
foreach i [$b getInsts] {
 dict set before [$i getName] [list [[$i getMaster] getName] [$i getOrient] [$i getLocation]]
 $i setPlacementStatus LOCKED
}
foreach {name master} {wire4506 BUFx16f place3260 BUFx10 place3259 BUFx10} {
 set i [$b findInst $name]
 if {[[$i getMaster] getName] ne "${master}_ASAP7_75t_R"} {error "allowlist master mismatch"}
 replace_cell $name ${master}_ASAP7_75t_L
}
estimate_parasitics -placement
set target {};foreach p [all_registers -data_pins] {if {[get_full_name $p] eq {u_done.ib[1][50]$_DFFE_PP_/D}} {set target $p;break}}
if {$target eq ""} {error "id50D absent"}
set targetinst [sta::sta_to_db_inst [$target instance]]
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins [list $target] -location {28.566 157.14} -buffer_name cdc_ib50_hold
set newinsts {};foreach i [$b getInsts] {if {![dict exists $before [$i getName]]} {lappend newinsts $i}}
if {[llength $newinsts]!=1} {error "expected one newBUF"}
set ni [lindex $newinsts 0];set newbufname [$ni getName]
if {[[$ni getMaster] getName] ne "BUFx2_ASAP7_75t_R"} {error "wrongnewmaster"}
puts "CDC_ONEBUF_NATIVE_NAME $newbufname"
set ru [$b getDbUnitsPerMicron];set rowor {}
foreach row [$b getRows] {dict set rowor [lindex [$row getOrigin] 1] [$row getOrient]}
set xx [expr {round(28.566*$ru)}];set yy [expr {round(157.14*$ru)}]
if {![dict exists $rowor $yy]} {error "newBUFoffrow"}
$ni setOrient [dict get $rowor $yy];$ni setLocation $xx $yy;$ni setPlacementStatus FIRM
source /work/pg_connect.tcl
ot_pg_connect_all cdc_eco3
ot_pg_require_bound cdc_eco3
write_db /work/eco3b/3_place.odb
write_def /work/eco3b/3_place.def
write_verilog /work/eco3b/3_place.v
check_placement -verbose
ot_clk_freeze_assert post_cdc_eco3b
set changes {};set newcount 0
foreach i [$b getInsts] {
 set name [$i getName]
 if {![dict exists $before $name]} {incr newcount;if {$name ne $newbufname} {error "unexpectednewcell"};continue}
 lassign [dict get $before $name] oldm oldo oldxy
 if {[$i getOrient] ne $oldo || [$i getLocation] ne $oldxy} {error "oldcellmoved $name"}
 if {[[$i getMaster] getName] ne $oldm} {lappend changes $name}
}
if {$newcount!=1 || [lsort $changes] ne [lsort $allowed]} {error "fourcellallowlist changed"}
puts "CDC_ECO3_ACTUAL_FOURCELL_GUARD_PASS oldhomes_allfixed changedmasters$changes newBUF1 site28.566_157.14"
puts CDC_ECO3_PREP_DONE_NO_GRT_NO_DRT_NO_STALE_TIMING_QUALIFICATION
