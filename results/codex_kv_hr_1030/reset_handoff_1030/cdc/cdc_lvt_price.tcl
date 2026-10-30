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
if {![grt::have_routes]} {error "no actual native routes"}
estimate_parasitics -global_routing
ot_clk_restore_parasitics {tc /work/eco2_grt/original_clock_only.spef bc /work/eco2_grt/original_clock_only.spef}
set_propagated_clock [get_clocks clk]
file mkdir /work/model_lvt/results
proc model_report {phase} {
 foreach {tag c kind lat} {TT tc max 250 FF bc min 202.5} {
  set_clock_latency -source $lat [get_clocks vclk]
  set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
  set inputs {};foreach ip [all_inputs] {if {![string match ck* [get_full_name $ip]]} {lappend inputs $ip}}
  set_input_delay -min -40 -clock [get_clocks vclk] $inputs
  set paths [find_timing_paths -corner $c -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
  set worst Inf;foreach p $paths {set worst [expr {min($worst,[get_property $p slack])}]}
  puts "CDC_LVT_PRICE $phase $tag worst_ps $worst"
  report_checks -corner $c -path_delay $kind -format full_clock_expanded -fields {slew cap fanout} -digits 3
  if {$tag eq "FF"} {
   set count [expr {[llength [all_registers -data_pins]]+[llength [all_registers -async_pins]]+[llength [all_outputs]]}]
   set ps [find_timing_paths -corner $c -path_delay min -group_path_count $count -endpoint_path_count 1]
   set f [open /work/model_lvt/results/all_ff_${phase}.tsv w];set neg 0;set min Inf
   foreach p $ps {set s [get_property $p slack];if {$s<0} {incr neg};set min [expr {min($min,$s)}];puts $f "[get_full_name [get_property $p startpoint]]\t[get_full_name [get_property $p endpoint]]\t$s"};close $f
   puts "CDC_LVT_PRICE $phase ALL_FF endpoints [llength $ps] negative $neg worst $min"
  }
 }
}
model_report before
set b [ord::get_db_block];set f [open /work/model_lvt/results/actual_caps_slews.tsv w]
foreach {name master} {wire4506 BUFx16f place3260 BUFx10 place3259 BUFx10} {
 set i [$b findInst $name]
 if {[[$i getMaster] getName] ne "${master}_ASAP7_75t_R"} {error "allowlist master mismatch $name"}
 foreach port {A Y} {
  set p [get_pins $name/$port];set n [[[$i findITerm $port] getNet] getName];set nn [sta::find_net $n]
  foreach c {tc bc} {
   set sc [sta::find_scene $c]
   puts $f "$name\t$port\t$c\tCAPfF[expr {[$nn capacitance $sc max]*1e15}]\tWIREfF[expr {[$nn wire_capacitance $sc max]*1e15}]\tSLEWmax[get_property $p slew_max]"
  }
 }
}
close $f
foreach {name master} {wire4506 BUFx16f place3260 BUFx10 place3259 BUFx10} {replace_cell $name ${master}_ASAP7_75t_L}
model_report after3lvt
# Actualunmodified shortbranch recovery/removal andload foroneBUF analyticprice.
foreach {tag c kind lat} {TT tc max 250 FF bc min 202.5} {
 set_clock_latency -source $lat [get_clocks vclk]
 set to {};foreach p [all_registers -async_pins] {if {[get_full_name $p] eq {u_done.ocr_q$_DFF_PN0_/RESETN}} {set to $p;break}}
 if {$to eq ""} {error "short removal target absent"}
 puts "CDC_ONEBUF_PRICE $tag EXISTING_RECOVERY_REMOVAL"
 report_checks -corner $c -path_delay $kind -to $to -format full_clock_expanded -fields {slew cap fanout} -digits 3
}
puts CDC_LVT_PRICE_READONLY_DONE_NO_DB_SAVED_NO_PHYSICAL_ECO
