read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz
read_db /inputs/6_final.odb
read_sdc /inputs/6_final.sdc
read_spef /inputs/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /inputs/post.sdc
if {[llength [all_clocks]] != 1 || [get_full_name [lindex [all_clocks] 0]] ne "core_clk"} {error "clock mismatch"}
set n 0
set live 0
foreach inst [[ord::get_db_block] getInsts] {
 if {![string match clkload* [$inst getName]]} {continue}
 foreach it [$inst getITerms] {
  if {[$it getIoType] ne "OUTPUT"} {continue}
  incr n
  set net [$it getNet]
  if {$net ne "NULL"} {
   foreach sink [$net getITerms] {if {[$sink getIoType] ne "OUTPUT"} {incr live}}
   foreach sink [$net getBTerms] {if {[$sink getIoType] ne "INPUT"} {incr live}}
  }
 }
}
puts "OT_CLKLOAD_OUTPUTS $n LIVE_SINKS $live"
if {$n != 743 || $live != 0} {error "unannotated clock load output coverage not resolved"}
read_liberty /view/ot_dsrom_head_bundle_glue_ss.lib
read_liberty /view/ot_dsrom_head_bundle_glue_ff.lib
puts "OT_LIBERTY_RELOAD_DONE"
exit
