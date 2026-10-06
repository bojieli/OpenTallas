set c $::env(WFC_CORNER)
set l /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [list asap7sc7p5t_AO_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${c}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_${c}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${c}_nldm_220123.lib] {read_liberty $l/$f}
foreach m {ot_rom_4096x72_m8 ot_sram_1r1w_512x128_m4_r2c2} {read_liberty /src/physical/asap7_memory_macros/$m/${m}_[string tolower $c].lib}
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach m {ot_rom_4096x72_m8 ot_sram_1r1w_512x128_m4_r2c2} {read_lef /src/physical/asap7_memory_macros/$m/$m.lef}
read_verilog /input/results/asap7/copernicus_wfc_producers/base/1_2_yosys.v
link_design ot_dsrom_wfc_producer_context
read_sdc /src/physical/dsrom_wfc_producer_context/constraint.sdc
set_units -time ps -capacitance fF
set block [ord::get_db_block]
proc cap {it} {
 set ref [[[$it getInst] getMaster] getName];set pin [[$it getMTerm] getName]
 set lp [get_lib_pins -quiet */$ref/$pin]
 if {[llength $lp]!=1} {error "actual library pin missing/ambiguous $ref/$pin"}
 return [get_property $lp capacitance]
}
proc sinks {net} {
 set load 0.;set receivers {}
 foreach it [$net getITerms] {
  if {[$it isOutputSignal] || [[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
  set v [cap $it];set load [expr {$load+$v}]
  lappend receivers [list [[$it getInst] getName] [[$it getMTerm] getName] $v]
 }
 return [list $load $receivers]
}
set f [open /out/${c}_boundary.tsv w]
puts $f "direction\tport\tnet\tcap_fF\treceivers\tdrivers"
foreach bt [$block getBTerms] {
 set net [$bt getNet];if {$net eq "NULL"} {error "unbound port [$bt getName]"}
 lassign [sinks $net] load receivers
 set drivers {}
 foreach it [$net getITerms] {if {[$it isOutputSignal]} {lappend drivers [list [[$it getInst] getName] [[$it getMTerm] getName] [[[$it getInst] getMaster] getName]]}}
 puts $f [join [list [$bt getIoType] [$bt getName] [$net getName] $load $receivers $drivers] "\t"]
}
close $f
set f [open /out/${c}_macro.tsv w];puts $f "macro\tmaster\tpin\tnet\tcap_fF\treceivers"
set nr 0;set ns 0
foreach inst [$block getInsts] {
 set m [[$inst getMaster] getName]
 if {$m ni {ot_rom_4096x72_m8 ot_sram_1r1w_512x128_m4_r2c2}} {continue}
 if {$m eq "ot_rom_4096x72_m8"} {incr nr} else {incr ns}
 foreach it [$inst getITerms] {
  if {[[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
  set net [$it getNet];if {$net eq "NULL"} {continue}
  if {[$it isOutputSignal]} {lassign [sinks $net] load receivers} else {set load [cap $it];set receivers {}}
  puts $f [join [list [$inst getName] $m [[$it getMTerm] getName] [$net getName] $load $receivers] "\t"]
 }
}
close $f
if {$nr!=4 || $ns!=14} {error "wrong fullshape macro count ROM=$nr SRAM=$ns"}
report_clock_properties [all_clocks] > /out/${c}_clocks.rpt
write_db /out/${c}_linked.odb
puts "WFC_REAL_PRODUCER_BOUNDARY_PASS $c ROM=$nr SRAM=$ns"
