# QC-P5 10-23 A0 v4: the core clock enters at 20 interior tap ports of the SAME die clock (ck + ck_t1..ck_t19,
# OT_A0_CK_TAPS).  Appended after the kit SDC: core_clk is redefined (same name, same period; uncertainty and IO delays
# stay on the clock object, checked in OpenSTA) with every tap port as a source; the taps were IO data inputs when
# all_inputs -no_clocks ran, so their input delay / transition are removed.
set ot_a0_taps [get_ports {ck_t*}]
unset_input_delay $ot_a0_taps
set_input_transition 0 $ot_a0_taps
create_clock -name core_clk -period [get_property [get_clocks core_clk] period] [get_ports {ck ck_t*}]
