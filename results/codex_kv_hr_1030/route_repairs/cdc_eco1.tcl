define_corners tc
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_db /work/run/results/asap7/hc_qkd_hr_cdc_ch__319_68x319_68/base/6_final.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_cdc_ch__319_68x319_68/base/6_final.sdc
read_spef -corner tc /work/run/results/asap7/hc_qkd_hr_cdc_ch__319_68x319_68/base/6_final.spef
set_propagated_clock [get_clocks clk]
set_clock_latency -source 250 [get_clocks vclk]
set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
set ins {};foreach p [all_inputs] {if {![string match ck* [get_full_name $p]]} {lappend ins $p}}
set_input_delay -min -40 -clock [get_clocks vclk] $ins
set ::env(RESULTS_DIR) /work/eco1
source /work/clk_freeze.tcl
ot_clk_freeze
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set constants {};set tiepins {}
foreach i [$b getInsts] {
 set m [[$i getMaster] getName]
 if {[string match TIE* $m]} {
  foreach t [$i getITerms] {
   set mt [$t getMTerm]
   if {[$mt getIoType] eq "OUTPUT" && [$mt getSigType] eq "SIGNAL" && [$t getNet] ne "NULL"} {
    dict set constants [[$t getNet] getName] 1
    dict set tiepins "$m/[$mt getName]" 1
   }
  }
 }
 if {[regexp {^(FILL|DECAP)} $m]} {odb::dbInst_destroy $i;continue}
 if {[string match DFF* $m]} {$i setPlacementStatus LOCKED}
}
set f [open /work/eco1/old_constant_nets.txt w];puts $f [join [dict keys $constants] "\n"];close $f
puts [exec python3 /work/filter_const_spef.py /work/run/results/asap7/hc_qkd_hr_cdc_ch__319_68x319_68/base/6_final.spef /work/eco1/old_constant_nets.txt /work/eco1/old_nonconstant.spef]
dict for {pin v} $tiepins {
 set lp [get_lib_pins -quiet */$pin]
 if {![llength $lp]} {error "missing tie library pin $pin"}
 repair_tie_fanout -separation 0 $lp
}
set movedties 0
foreach i [$b getInsts] {
 if {![string match TIE* [[$i getMaster] getName]]} continue
 set sinks {}
 foreach t [$i getITerms] {
  if {[[$t getMTerm] getIoType] ne "OUTPUT" || [$t getNet] eq "NULL"} continue
  foreach load [[$t getNet] getITerms] {
   if {[[$load getMTerm] getIoType] eq "INPUT" && [$load getInst] ne $i} {dict set sinks [[$load getInst] getName] [$load getInst]}
  }
 }
 if {[dict size $sinks]==1} {
  set sink [lindex [dict values $sinks] 0];lassign [$sink getLocation] x y
  set xx [expr {max(round(4.32*$u),$x-round(.54*$u))}]
  $i setPlacementStatus PLACED;$i setOrient [$sink getOrient];$i setLocation $xx $y;incr movedties
 }
}
puts "CDC_TIE_LOCALIZATION $movedties"
source /work/setRC_rcx.tcl
estimate_parasitics -placement
read_spef -name tc -corner tc /work/eco1/old_nonconstant.spef
set_dont_use [get_lib_cells *DFF*]
repair_design
repair_timing -setup -setup_margin 0 -skip_last_gasp -skip_gate_cloning -skip_buffer_removal
repair_design
set target {}
foreach p [all_registers -data_pins] {if {[get_full_name $p] eq {u_done.ib[1][46]$_DFFE_PP_/D}} {set target $p;break}}
if {$target eq ""} {error "short hold endpoint not found"}
set inst [sta::sta_to_db_inst [$target instance]];lassign [$inst getLocation] x y
set xy [list [expr {$x/double($u)-.54}] [expr {$y/double($u)}]]
insert_buffer -buffer_cell BUFx2_ASAP7_75t_R -load_pins [list $target] -location $xy -buffer_name cdc_done_hold46
puts CDC_PLANNED_SHORT_HOLD_BUF_ONE
# This is a diagnostic: new/changed data RC requires current GRT and full FF before route.
detailed_placement -max_displacement {20 4}
check_placement -verbose
ot_clk_freeze_assert post_cdc_eco1
write_db /work/eco1/3_place.odb
write_def /work/eco1/3_place.def
write_verilog /work/eco1/3_place.v
report_checks -path_delay max -format full_clock_expanded -group_path_count 1 -fields {slew cap fanout} -digits 3
report_check_types -max_slew -max_capacitance -violators
puts CDC_ECO1_DIAGNOSTIC_DONE_NO_GRT_NO_DRT
