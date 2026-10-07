
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(WF_LIB)_*.lib*]] { read_liberty $f }
read_liberty /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_[string tolower $::env(WF_LIB)].lib
read_db $::env(WF_ODB)
read_sdc /work/signoff.sdc
read_spef $::env(WF_SPEF)
set_propagated_clock [all_clocks]
set ck [get_clocks core_clk]
proc fails {} {
  set nv 0; set nh 0
  foreach p [concat [all_registers -data_pins] [all_outputs]] {
    set s [get_property $p slack_max]; if {$s != "INF" && $s < 0} { incr nv }
    set s [get_property $p slack_min]; if {$s != "INF" && $s < 0} { incr nh }
  }
  return "$nv $nh"
}
proc rep {tag} {
  puts "WFSTA $tag setup [sta::worst_slack_cmd max] hold [sta::worst_slack_cmd min] fails [fails]"
  puts "WFPATH $tag max"; report_checks -path_delay max -digits 1
  puts "WFPATH $tag min"; report_checks -path_delay min -digits 1
  puts "WFEND"
}
# insertion delay of the block's own tree (register clock pins)
set lmin 1e9; set lmax 0
foreach p [all_registers -clock_pins] {
  set a [get_property $p arrival_max_rise]; if {$a != "INF" && $a > $lmax} { set lmax $a }
  set a [get_property $p arrival_min_rise]; if {$a != "INF" && $a < $lmin} { set lmin $a }
}
puts "WFLAT $lmin $lmax"
rep block
# in context: the neighbours hang off the same die clock tree -> IO relative to a virtual clock that
# carries the block's own insertion delay (setup: launch late / capture early; hold: the reverse)
set per [get_property $ck period]
set io [expr 0.2 * $per]
set ins [lsearch -all -inline -not [all_inputs] [get_ports $::env(WF_CLK)]]
catch {unset_input_delay -clock [get_clocks io_clk] $ins}
catch {unset_output_delay -clock [get_clocks io_clk] [all_outputs]}
unset_input_delay $ins
unset_output_delay [all_outputs]
create_clock -name vclk -period $per
set_clock_latency -min $lmin [get_clocks vclk]
set_clock_latency -max $lmax [get_clocks vclk]
set_clock_uncertainty -setup $::env(WF_USETUP) [get_clocks vclk]
set_clock_uncertainty -hold $::env(WF_UHOLD) [get_clocks vclk]
set_input_delay $io -clock vclk $ins
set_output_delay $io -clock vclk [all_outputs]
rep incontext
set_clock_latency -min [expr $lmin - 150] [get_clocks vclk]
set_clock_latency -max [expr $lmax + 150] [get_clocks vclk]
rep die150
set lk_in [get_ports {in_*}]
set lk_out [get_ports {out_*}]
create_clock -name vlk -period $per
set_clock_latency -min [expr $lmin - 150] [get_clocks vlk]
set_clock_latency -max [expr $lmax + 150] [get_clocks vlk]
set_clock_latency -min [expr $lmin - 90] [get_clocks vclk]
set_clock_latency -max [expr $lmax + 90] [get_clocks vclk]
set_clock_uncertainty -setup $::env(WF_USETUP) [get_clocks {vclk vlk}]
set_clock_uncertainty -hold 50 [get_clocks {vclk vlk}]
unset_input_delay $lk_in
unset_output_delay $lk_out
set_input_delay $io -clock vlk $lk_in
set_output_delay $io -clock vlk $lk_out
rep region
unset_input_delay $lk_in
unset_output_delay $lk_out
set_input_delay $io -clock vclk $lk_in
set_output_delay $io -clock vclk $lk_out
set_clock_uncertainty -hold $::env(WF_UHOLD) [get_clocks vclk]
set_clock_latency -min $lmin [get_clocks vclk]
set_clock_latency -max $lmax [get_clocks vclk]
set_false_path -from $ins
set_false_path -to [all_outputs]
rep reg2reg
puts "WFDONE"
