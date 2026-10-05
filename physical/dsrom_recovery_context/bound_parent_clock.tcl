# Source-owned reg-to-reg context query. No virtual clocks, IO-delay overrides,
# false paths, multicycle exceptions, or inherited FIFO insertion assumptions.
# Invoke AFTER real linked/mapped context and CTS/parasitics are loaded:
# ot_s81_bound_reg_context $launch_q_pins $capture_d_pins core_clk $out_prefix
# Call separately for SS and FF using their actual libraries.
proc ot_s81_bound_reg_context {launch_q_names capture_d_names reference_clock out_prefix} {
  set ref [get_clocks -quiet $reference_clock]
  if {[llength $ref] != 1} {error "S81 reference clock missing/ambiguous: $reference_clock"}
  set qpins {}; set dpins {}
  foreach n $launch_q_names {
    set p [get_pins -quiet $n]
    if {[llength $p] != 1} {error "S81 real launch pin missing/ambiguous: $n"}
    if {![regexp {/(Q|QN)$} [get_full_name $p]]} {error "S81 launch must be actual flop Q/QN: $n"}
    if {[llength [get_cells -of_objects $p]] != 1} {error "S81 launch is not a linked cell: $n"}
    lappend qpins $p
  }
  foreach n $capture_d_names {
    set p [get_pins -quiet $n]
    if {[llength $p] != 1} {error "S81 real capture pin missing/ambiguous: $n"}
    if {![regexp {/D$} [get_full_name $p]]} {error "S81 capture must be actual flop D: $n"}
    lappend dpins $p
  }
  if {![llength $qpins] || ![llength $dpins]} {error "S81 empty physical boundary"}
  # Propagate the existing physical tree; do not create an ideal replacement.
  set_propagated_clock $ref
  set min_paths [find_timing_paths -from $qpins -to $dpins -path_delay min -group_path_count 1]
  set max_paths [find_timing_paths -from $qpins -to $dpins -path_delay max -group_path_count 1]
  if {![llength $min_paths] || ![llength $max_paths]} {error "S81 launch/capture pair has no timed physical path"}
  # Expanded clock reports expose BOTH launch and capture insertion/reference
  # and actual earliest/latest path delay, rather than declared port arrival.
  report_checks -from $qpins -to $dpins -path_delay min -group_path_count 10 \
    -format full_clock_expanded -fields {slew cap input_pin net fanout} > ${out_prefix}.min.rpt
  report_checks -from $qpins -to $dpins -path_delay max -group_path_count 10 \
    -format full_clock_expanded -fields {slew cap input_pin net fanout} > ${out_prefix}.max.rpt
  set f [open ${out_prefix}.endpoints.txt w]
  puts $f "reference_clock=$reference_clock"
  puts $f "launch_q_names=$launch_q_names"
  puts $f "capture_d_names=$capture_d_names"
  puts $f "basis=actual loaded linked reg-to-reg paths and propagated clock; no production IO arrival inferred"
  close $f
}
