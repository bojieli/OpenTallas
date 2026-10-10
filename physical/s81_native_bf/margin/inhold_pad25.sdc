# BF-PINCLK 2026-10-09 variant (b): ROUTE-TIME input hold padding for the pin-register residue.  Read in the route's FF hold
# scene AFTER signoff_ref.sdc (OT_MM_FF_SDC list); NOT a sign-off constraint (the verdict and corner_sta read
# signoff_ref.sdc only).  Same measured reference L as signoff_ref.sdc (mean clock arrival at the g_pin.r_* registers),
# input min = L - 25 ps, so route/CTS hold repair pads every input path 25 ps beyond the sign-off requirement
# (IN_HOLD_SKEW = 25, as physical/dsrom_fh_safe/cl_route.sh).  Setup and outputs untouched.
set bfp_w [sta::worst_slack_cmd max]
set bfp_n 0; set bfp_amin 0.0
foreach bfp_c [get_cells -quiet -hierarchical {g_pin.r_*}] {
  set bfp_p [get_pins -quiet "[get_full_name $bfp_c]/CLK"]
  if {[llength $bfp_p] == 0} continue
  set bfp_y [get_property $bfp_p arrival_min_rise]
  if {$bfp_y eq "INF"} continue
  incr bfp_n; set bfp_amin [expr {$bfp_amin + $bfp_y}]
}
if {$bfp_n == 0} { error "BF_INHOLD_PAD: no g_pin.r_* register" }
set bfp_lmin [expr {$bfp_amin / $bfp_n}]
set_input_delay -min [expr {$bfp_lmin - 25}] -clock core_clk [all_inputs -no_clocks]
puts "BF_INHOLD_PAD route input min = L $bfp_lmin - 25 over $bfp_n pin registers"
