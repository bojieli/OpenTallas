# Full ot_su64_full64 candidate: two divider sites, two real ICGs each.
# Source after the master core_clk exists and after signoff recreates core_clk.
# Use library-native units: ASAP7 ps versus ns in another library.
set div64_master [get_clocks core_clk]
if {[llength $div64_master] != 1} { error "DDIV64 requires core_clk" }
set div64_period [get_property $div64_master period]
set div64_n 0
set div64_clocks {}
foreach cell [get_cells -hierarchical *u_icg*] {
    set cname [get_full_name $cell]
    if {![regexp {(^|[./])g([ab])[./]u_icg$} $cname -> sep bank]} { continue }
    set pin [get_pins "$cname/GCLK"]
    if {[llength $pin] != 1} { error "DDIV64 missing gate output $cname" }
    set edges [expr {$bank eq "a" ? {1 2 5} : {3 4 7}}]
    set name div64_[incr div64_n]
    create_generated_clock -name $name -master_clock core_clk -source [get_ports clk] -edges $edges $pin
    lappend div64_clocks $name
}
if {$div64_n != 4} { error "DDIV64 expected four physical ICGs, found $div64_n" }
set_clock_uncertainty -setup [expr {$div64_period > 10 ? 60.0 : 0.060}] [get_clocks $div64_clocks]
set_clock_uncertainty -hold [expr {$div64_period > 10 ? 25.0 : 0.025}] [get_clocks $div64_clocks]
# No blanket MCP or false paths. Fast input/output and clock-gate checks remain.
# CTS and signoff must propagate all five clocks; do not force propagation in
# this fragment, which is also used before CTS.
