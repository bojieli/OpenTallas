# rr1012 (reference tile flow, sdc_extra) for dsfd_su_t_ctl: second clock cck = the dsfd_sp_ctrl controller clock
# (engine adapter c-side: c_cmd / c_done pins, the c-side pin flops and the adapter's CDC FIFOs).  Same intent as the
# closed route's root_cck.sdc (s81su-tctl-4be685202-tc-pd45): timed at the slab clock's period (the stricter of the
# controller domains), asynchronous to core_clk = sk (the adapter crosses only through async FIFOs); c-side IO at the
# reference flow's 0.2 T budget against the controller clock.
create_clock -name c_clk -period [get_property [get_clocks core_clk] period] [get_ports {cck}]
set_clock_uncertainty -setup 60 [get_clocks c_clk]
set_clock_uncertainty -hold 25 [get_clocks c_clk]
catch {unset_input_delay -clock core_clk [get_ports {cck}]}
set ot_ci [get_ports {c_cmd_v c_cmd_d[*] crs}]
catch {unset_input_delay -clock core_clk $ot_ci}
set_input_delay [expr {[get_property [get_clocks c_clk] period] * 0.2}] -clock c_clk $ot_ci
set ot_co [get_ports {c_done_v c_done_tag[*]}]
catch {unset_output_delay -clock core_clk $ot_co}
set_output_delay [expr {[get_property [get_clocks c_clk] period] * 0.2}] -clock c_clk $ot_co
set_clock_groups -asynchronous -group [get_clocks c_clk] -group [get_clocks core_clk]
