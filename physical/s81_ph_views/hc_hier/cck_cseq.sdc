# s81-suhc-hier-1011 comb v2: controller clock (cck) of ot_s81_hc_cseq (reference tile flow, sdc_extra): the command /
# done seam flops and the engine adapter's controller side; the adapter's async FIFOs are the only crossing to sk
# (core_clk): asynchronous groups.  cck = 3/4 of the slab clock (dsfd_sp_ctrl domain).
create_clock -name c_clk -period [expr {[get_property [get_clocks core_clk] period] * 4.0 / 3.0}] [get_ports {cck}]
set_clock_uncertainty -setup 60 [get_clocks c_clk]
set_clock_uncertainty -hold 25 [get_clocks c_clk]
catch {unset_input_delay -clock core_clk [get_ports {cck}]}
set ot_ci [get_ports {n_cmd_v n_cmd_d[*] crs}]
catch {unset_input_delay -clock core_clk $ot_ci}
set_input_delay [expr {[get_property [get_clocks c_clk] period] * 0.2}] -clock c_clk $ot_ci
set ot_co [get_ports {n_done_v n_done_tag[*]}]
catch {unset_output_delay -clock core_clk $ot_co}
set_output_delay [expr {[get_property [get_clocks c_clk] period] * 0.2}] -clock c_clk $ot_co
set_clock_groups -asynchronous -group [get_clocks c_clk] -group [get_clocks core_clk]
