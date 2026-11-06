source /OpenROAD-flow-scripts/flow/platforms/asap7/liberty_suppressions.tcl
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
set tt /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
set ff /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty $tt
read_liberty $ff
read_verilog /work/tiny.v
link_design tiny
set_mode ss
set_mode ff
define_scene tc -mode ss -liberty [list $tt]
define_scene BC -mode ff -liberty [list $ff]
read_sdc -mode ss /work/fixture.sdc
read_sdc -mode ff /work/fixture.sdc
set_mode ff
set_clock_latency -source 400 [get_clocks clk]
set_clock_latency -source 202.5 [get_clocks vclk]
set_false_path -setup -from [all_clocks]
set_mode ss
set_false_path -hold -from [all_clocks]
set ::env(OT_HOLD_MM) 0
source /work/flow_scope.tcl
set ::env(OT_HOLD_REPAIR_SCOPE) reg2reg
set ::env(RESULTS_DIR) /work
set ::env(OT_HOLD_SCOPE_KEEP_SDC) 1
set ::ot_mm_stage 4_cts.sdc
set ::ot_mm_synced 1
write_sdc -mode ff -digits 17 -no_timestamp /work/test_ff_before.sdc
write_sdc -mode ss -digits 17 -no_timestamp /work/test_tt_before.sdc
set baseline [ot_hold_stats]
set io_paths [llength [find_timing_paths -path_delay min -scenes BC -from [all_inputs] -group_path_count 100]]
if {$io_paths == 0} {error "bad fixture: no IO paths before scope"}
set rc [catch {ot_hold_repair_scope {
  if {[llength [find_timing_paths -path_delay min -scenes BC -from [all_inputs] -group_path_count 100]] != 0} {error "IO path not masked during repair"}
  set i [find_timing_paths -path_delay min -scenes BC -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 100]
  if {[llength $i] == 0} {error "internal paths were accidentally masked"}
  error deliberate
}} msg]
if {$rc != 1 || $msg ne "deliberate"} {error "repair exception changed: $rc $msg"}
if {[sta::cmd_mode_name] ne "ss"} {error "current mode not restored"}
if {[ot_hold_stats] ne $baseline} {error "original numerical FF slack not restored"}
write_sdc -mode ff -digits 17 -no_timestamp /work/test_ff_after.sdc
write_sdc -mode ss -digits 17 -no_timestamp /work/test_tt_after.sdc
foreach mode {tt ff} {
 if {[ot_hold_scope_read /work/test_${mode}_before.sdc] ne [ot_hold_scope_read /work/test_${mode}_after.sdc]} {error "original $mode SDC differs"}
}
unset ::env(OT_HOLD_REPAIR_SCOPE)
if {[ot_hold_repair_scope {set x default_unchanged}] ne "default_unchanged"} {error "default bypass changed"}
puts "FLOW_SCOPE_PASS exact_TT_FF_SDC original_FF_slack mode exception IO_mask internal_paths default_bypass"
