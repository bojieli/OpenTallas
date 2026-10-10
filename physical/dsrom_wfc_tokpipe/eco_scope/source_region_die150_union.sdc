# Exact union of retained WFC incontext/reg2reg/region/die150 obligations.
# Clock target and IO/uncertainty inherited byte-for-byte from original signoff.
read_sdc /src/physical/dsrom_wfc_tokpipe/eco_scope/source_signoff_9f7a7f35e.sdc
set_propagated_clock [all_clocks]
set lmin 1e9
set lmax 0
foreach p [all_registers -clock_pins] {
 set a [get_property $p arrival_max_rise]; if {$a != "INF" && $a > $lmax} {set lmax $a}
 set a [get_property $p arrival_min_rise]; if {$a != "INF" && $a < $lmin} {set lmin $a}
}
set per [get_property [get_clocks core_clk] period]
set io [expr 0.2 * $per]
set ins [lsearch -all -inline -not [all_inputs] [get_ports clk]]
catch {unset_input_delay -clock [get_clocks io_clk] $ins}
catch {unset_output_delay -clock [get_clocks io_clk] [all_outputs]}
unset_input_delay $ins
unset_output_delay [all_outputs]
# die150 remains an independent virtual clock on every boundary.
create_clock -name wfc_die150 -period $per
set_clock_latency -min [expr $lmin - 150] [get_clocks wfc_die150]
set_clock_latency -max [expr $lmax + 150] [get_clocks wfc_die150]
set_clock_uncertainty -setup 60 [get_clocks wfc_die150]
set_clock_uncertainty -hold 25 [get_clocks wfc_die150]
set_input_delay $io -clock wfc_die150 $ins
set_output_delay $io -clock wfc_die150 [all_outputs]
# Region: independent 90ps neighbours, 150ps stage link, existing 50ps IO hold.
foreach {name skew} {wfc_region90 90 wfc_region150 150} {
 create_clock -name $name -period $per
 set_clock_latency -min [expr $lmin - $skew] [get_clocks $name]
 set_clock_latency -max [expr $lmax + $skew] [get_clocks $name]
 set_clock_uncertainty -setup 60 [get_clocks $name]
 set_clock_uncertainty -hold 50 [get_clocks $name]
}
set link_in [get_ports {in_*}]
set link_out [get_ports {out_*}]
set other_in [lsearch -all -inline -not $ins $link_in]
# OpenSTA collections are Tcl lists; remove each link port explicitly.
set other_in {}
foreach p $ins {if {[lsearch -exact $link_in $p] < 0} {lappend other_in $p}}
set other_out {}
foreach p [all_outputs] {if {[lsearch -exact $link_out $p] < 0} {lappend other_out $p}}
if {[llength $other_in]} {set_input_delay -add_delay $io -clock wfc_region90 $other_in}
if {[llength $other_out]} {set_output_delay -add_delay $io -clock wfc_region90 $other_out}
set_input_delay -add_delay $io -clock wfc_region150 $link_in
set_output_delay -add_delay $io -clock wfc_region150 $link_out
