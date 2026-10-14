# Three RELATED clocks. No asynchronous groups, false paths, multicycle paths,
# or period relaxation. Internal bank/relay paths remain timed at the real period.
set ot_mc_period [get_property [get_clocks core_clk] period]
create_clock -name req_clk -period $ot_mc_period [get_ports ck_req]
create_clock -name ret_clk -period $ot_mc_period [get_ports ck_ret]
create_clock -name ot_bgl_io -period $ot_mc_period
set_input_transition 150 [get_ports {ck ck_req ck_ret}]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# The default single-root hook runs before this scoped hook in signoff.sdc.
# Clear ALL clock and clock-fall data tags, including clock-source ports, before
# reading any arrival. OpenSTA unset_input_delay without -clock clears all tags.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
proc ot_bgl_mc_ports {patterns} {
    set result {}
    foreach pattern $patterns { foreach p [get_ports -quiet $pattern] { lappend result $p } }
    return $result
}
proc ot_bgl_mc_mean {clock patterns} {
    set values {}
    set pins {}
    if {$patterns eq {ALL}} {
        set pins [all_registers -clock_pins -clock [get_clocks $clock]]
    } else {
        foreach pattern $patterns {
            foreach c [get_cells -quiet -hierarchical $pattern] {
                foreach pin [get_pins -quiet "[get_full_name $c]/CLK"] { lappend pins $pin }
            }
        }
    }
    foreach p $pins {
        set a [get_property $p arrival_max_rise]
        if {[string is double -strict $a]} { lappend values $a }
    }
    if {![llength $values]} { error "BGL_MC: no measured reference for $clock ($patterns)" }
    set sum 0.0
    foreach a $values { set sum [expr {$sum+$a}] }
    set mean [expr {$sum/[llength $values]}]
    set sorted [lsort -real $values]
    puts "BGL_MC_RAW root=$clock n=[llength $values] mean=$mean min=[lindex $sorted 0] max=[lindex $sorted end]"
    return $mean
}
# Pin ownership is explicit. Request input/output share rb0; return input/output
# use rt/so in H1. Bank input straps/reset reference bank rst/gidq clocks.
set ot_mc_owners [list [list req_clk {i_v* i_we* i_row* i_mask* i_d*} {f_v* f_we* f_row* f_mask* f_d*} {*rb0*}] \
    [list ret_clk {r_v* r_d* r_f* r_o*} {o_v* o_d* o_f* o_o*} {*rt_v* *rt_d* *so_f* *so_o*}] \
    [list core_clk {rs grp* bi*} {} {ALL}]]
set ot_mc_post [expr {![info exists ::ot_ref_pre_cts] || !$::ot_ref_pre_cts}]
set ot_mc_physical [get_clocks {core_clk req_clk ret_clk}]
# Clear previous compensation before EACH measurement; arrivals below are RAW.
set_clock_latency -source 0 $ot_mc_physical
if {$ot_mc_post} { set_propagated_clock $ot_mc_physical; catch {sta::worst_slack_cmd max} }
set ot_mc_refs [dict create]
foreach owner $ot_mc_owners {
    lassign $owner clock inputs outputs refs
    set R 0.0
    if {$ot_mc_post} { set R [ot_bgl_mc_mean $clock $refs] }
    dict set ot_mc_refs $clock $R
    set ii [ot_bgl_mc_ports $inputs]; set oo [ot_bgl_mc_ports $outputs]
    set sk [expr {$ot_mc_post ? 90.0 : 0.0}]
    set hk [expr {$ot_mc_post ? 50.0 : 0.0}]
    if {[llength $ii]} {
        set_input_delay [expr {166.667+$sk}] -max -clock ot_bgl_io $ii
        set_input_delay 0.0 -min -clock ot_bgl_io $ii
    }
    if {[llength $oo]} {
        set_output_delay [expr {166.667+$sk}] -max -clock ot_bgl_io $oo
        set_output_delay [expr {-$hk}] -min -clock ot_bgl_io $oo
    }
}
# Source-port data tags must be absent after all IO assignments.
unset_input_delay [get_ports {ck ck_req ck_ret}]
# Apply real phi-R delivery once, retaining the measured boundary spread.
# The RAW mean/min/max records above are the root R evidence. Saved SDC / generic
# clock insertion reports include this source compensation; they are NOT raw R.
if {$ot_mc_post} {
    dict for {clock R} $ot_mc_refs {
        set_clock_latency -source [expr {-$R}] [get_clocks $clock]
        puts "BGL_MC_DELIVERY root=$clock period=$ot_mc_period phi=0 R=$R source_latency=[expr {-$R}]"
    }
    dict for {from Rf} $ot_mc_refs {
        dict for {to Rt} $ot_mc_refs {
            if {$from eq $to} { continue }
            set skew [expr {$Rf > 300.0 || $Rt > 300.0 ? 150.0 : 90.0}]
            set_clock_uncertainty -setup [expr {60.0+$skew}] -from [get_clocks $from] -to [get_clocks $to]
            set_clock_uncertainty -hold 100.0 -from [get_clocks $from] -to [get_clocks $to]
        }
    }
}
