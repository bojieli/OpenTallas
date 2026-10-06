set c $::env(CFG_CORNER)
set l /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${c}_nldm_220123.lib] {read_liberty $l/$f}
read_liberty /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_[string tolower $c].lib
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef
read_verilog /input/results/asap7/copernicus_cfg_provider/base/1_2_yosys.v
link_design ot_v41_pair_cfgrom_context
read_sdc /input/constraint.sdc
set_units -time ps -capacitance fF
set block [ord::get_db_block]
set macro [$block findInst g_hard_cfg.u_cfg]
if {$macro eq "NULL" || [[$macro getMaster] getName] ne "ot_rom_4096x72_m8"} {error "real cfg macro absent"}
proc cap {it} {
 set inst [$it getInst]
 set pin [[$it getMTerm] getName]
 set ref [[$inst getMaster] getName]
 set lp [get_lib_pins -quiet */$ref/$pin]
 if {[llength $lp]!=1} {error "real library pin missing/ambiguous: $ref/$pin"}
 return [get_property $lp capacitance]
}
set output [open /out/${c}_input_receivers.tsv w]
puts $output "port\tinstance\tpin\tref\tcap_fF"
foreach bt [$block getBTerms] {
 if {[$bt getIoType] ne "INPUT"} {continue}
 set net [$bt getNet]
 if {$net eq "NULL"} {continue}
 foreach sink [$net getITerms] {
  if {[$sink isOutputSignal] || [[$sink getMTerm] getSigType] in {POWER GROUND}} {continue}
  puts $output [join [list [$bt getName] [[$sink getInst] getName] [[$sink getMTerm] getName] [[[$sink getInst] getMaster] getName] [cap $sink]] "\t"]
 }
}
close $output
puts "CFG_INPUT_RECEIVERS_PASS $c"
