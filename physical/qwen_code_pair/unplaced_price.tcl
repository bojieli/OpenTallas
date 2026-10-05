# Pre-route logic price from the retained mapped source, not SS/FF closure.
# No placement, clock tree, wire parasitics, timing repair or RTL changes.
# Kant's positive wire/skew reserves must be composed outside this report.
set job $::env(CODE_JOB)
set src $::env(CODE_SOURCE)
set corner $::env(CODE_CORNER)
foreach family {AO INVBUF OA SEQ SIMPLE} {
  set libs [lsort [glob $job/libs/asap7sc7p5t_${family}_RVT_${corner}_nldm*.lib]]
  read_liberty [lindex $libs 0]
}
foreach master {ot_sram_1r1w_1024x256_m2_r2c2 ot_sram_1r1w_128x256_m1_r2c2} {
  read_liberty $src/physical/asap7_memory_macros/$master/${master}_[string tolower $corner].lib
}
read_verilog $job/mapped/mapped.v
link_design ot_qwen_hbm_code_pair_context
# OpenSTA's set_units checks consistency; it does not rescale Liberty units.
# Exact physical translation of Kant's ns/pF boundary contract to ps/fF.
set_units -time ps -capacitance fF
create_clock -name core -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
set code_inputs {}
foreach port [all_inputs] {
  if {[get_full_name $port] ni {clk por_n}} {lappend code_inputs $port}
}
set_input_delay -clock core -max 120 $code_inputs
set_input_delay -clock core -min 0 $code_inputs
set_driving_cell -lib_cell BUFx2_ASAP7_75t_R -pin Y $code_inputs
set_output_delay -clock core -max 120 [all_outputs]
set_output_delay -clock core -min 0 [all_outputs]
set_load 0.558822 [all_outputs]
set_false_path -from [get_ports por_n]
set_clock_transition 20 [get_clocks core]
puts "SCOPE: unplaced cell/pin-load price; 20ps clock slew ESTIMATE; no physical clock or wire credit"
puts "KANT positive wire/coupling/skew budgets remain additional; not signoff"
set captures {}
foreach cell [get_cells *] {
  if {[get_property $cell ref_name] == "DFFHQNx1_ASAP7_75t_R"} {
    lappend captures $cell
  }
}
if {[llength $captures] != 2880} {error "bank-local capture census is not 2880"}
puts "CAPTURE_COUNT [llength $captures]"
set data [get_cells *data_store]
set check [get_cells *check_store]
if {[llength $data] != 10 || [llength $check] != 10} {error "macro census differs"}
proc price {label args} {
  puts "BEGIN_PRICE $label"
  report_checks {*}$args -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 6 -group_path_count 3 -slack_max 100000
  puts "END_PRICE $label"
}
price data_to_capture -from $data -to $captures -path_delay max
price check_to_capture -from $check -to $captures -path_delay max
price capture_to_boundary -from $captures -to [all_outputs] -path_delay max
price all_setup -path_delay max
price all_hold -path_delay min
price macro_inputs_setup -to [concat $data $check] -path_delay max
price macro_inputs_hold -to [concat $data $check] -path_delay min
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 6
puts "UNPLACED_PRICE_COMPLETE $corner"
exit
