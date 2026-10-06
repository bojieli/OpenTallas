set c $::env(CFG_CORNER)
set l /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $l/*_RVT_${c}_*.lib*] {read_liberty $f}
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
set output [open /out/${c}_receiver_loads.tsv w]
puts $output "kind\tinstance\tpin\tnet\tcap_fF\treceivers"
foreach it [$macro getITerms] {
 set mt [$it getMTerm]
 if {[$mt getSigType] in {POWER GROUND}} {continue}
 set net [$it getNet]
 if {$net eq "NULL"} {continue}
 set pin [$mt getName]
 if {![$it isOutputSignal]} {
  puts $output [join [list macro_input [$macro getName] $pin [$net getName] [cap $it] {}] "\t"]
 } else {
  set load 0.;set sinks {}
  foreach sink [$net getITerms] {
   if {[$sink isOutputSignal] || [[$sink getMTerm] getSigType] in {POWER GROUND}} {continue}
   set v [cap $sink];set load [expr {$load+$v}]
   lappend sinks [list [[$sink getInst] getName] [[$sink getMTerm] getName] v=$v]
  }
  puts $output [join [list macro_output [$macro getName] $pin [$net getName] $load $sinks] "\t"]
 }
}
foreach bt [$block getBTerms] {
 if {![string match cfg_rom_a* [$bt getName]]} {continue}
 set net [$bt getNet];set load 0.;set sinks {}
 foreach sink [$net getITerms] {
  if {[$sink isOutputSignal] || [[$sink getMTerm] getSigType] in {POWER GROUND}} {continue}
  set v [cap $sink];set load [expr {$load+$v}]
  lappend sinks [list [[$sink getInst] getName] [[$sink getMTerm] getName] v=$v]
 }
 puts $output [join [list loader_address_port {} [$bt getName] [$net getName] $load $sinks] "\t"]
}
close $output
report_clock_properties [all_clocks] > /out/${c}_clocks.rpt
write_db /out/${c}_linked.odb
puts "CFG_NATIVE_RECEIVER_PASS $c macro=[$macro getName] CLK_net=[[$macro findITerm clk] getNet]"
