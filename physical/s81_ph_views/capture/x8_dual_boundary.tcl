# Reapply both clock-domain IO budgets after every standard io_ref switch.
# Every domain keeps IO 0.2 T and the ordinary 90/50 ps setup/hold skew.
# Registered boundaries refer to their own propagated tree. No crossing exception.
source /src/physical/s81_ph_views/capture/x8_dual_clocks.sdc
proc capx_ref {clock} {
    set arrivals {}
    foreach p [all_registers -clock_pins -clock [get_clocks $clock]] {
        set hi [get_property $p arrival_max_rise]
        set lo [get_property $p arrival_min_rise]
        if {[string is double -strict $hi] && [string is double -strict $lo]} {
            lappend arrivals [list $hi $lo]
        }
    }
    if {![llength $arrivals]} {return {0 0}}
    set arrivals [lsort -real -index 0 $arrivals]
    return [lindex $arrivals [expr {[llength $arrivals] / 2}]]
}
lassign [capx_ref core_clk] capx_ch capx_cl
lassign [capx_ref ser_clk] capx_sh capx_sl
set capx_core_in [get_ports {f_w[*] f_sn[*]}]
set capx_core_out [get_ports {t_ho t_ho[*]}]
set capx_ser_out [get_ports {t_vm[*] t_st[*]}]
unset_input_delay [get_ports {ck ck[*] ckv ckv[*]}]
unset_input_delay $capx_core_in
unset_output_delay [concat $capx_core_out $capx_ser_out]
set_input_delay [expr {0.2*$capx_p+$capx_ch+90}] -max -clock core_clk $capx_core_in
set_input_delay $capx_cl -min -clock core_clk $capx_core_in
set_output_delay [expr {0.2*$capx_p-$capx_ch+90}] -max -clock core_clk $capx_core_out
set_output_delay [expr {-$capx_cl-50}] -min -clock core_clk $capx_core_out
set_output_delay [expr {0.2*$capx_p*4.0/3.0-$capx_sh+90}] -max -clock ser_clk $capx_ser_out
set_output_delay [expr {-$capx_sl-50}] -min -clock ser_clk $capx_ser_out
puts "CAPX_BOUNDARY core $capx_ch/$capx_cl serial $capx_sh/$capx_sl"
