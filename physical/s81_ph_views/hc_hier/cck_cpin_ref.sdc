# s81-suhc-hier-1011: controller clock (cck) of the HC centre pin tile ot_s81_hc_cpin for the REFERENCE TILE FLOW
# (sdc_extra; core_clk = sk is created by ref_tile's clock.sdc).  cck = 3/4 of the slab clock (dsfd_sp_ctrl domain).
# cck flops: command pins c_cmd_* -> n_cmd_* (pin flop in, registered out) and done n_done_* -> c_done_*; nothing
# crosses to sk inside the tile (the adapter's async FIFOs are in cseq): asynchronous groups.  Boundary 0.2 T of c_clk
# on both sides, same as the ref_tile core_clk boundary (replaces cck_cpin.sdc, which re-referenced the old vclk flow).
create_clock -name c_clk -period [expr {[get_property [get_clocks core_clk] period] * 4.0 / 3.0}] [get_ports {cck}]
set_clock_uncertainty -setup 60 [get_clocks c_clk]
set_clock_uncertainty -hold 25 [get_clocks c_clk]
catch {unset_input_delay -clock core_clk [get_ports {cck}]}
set ot_ci [get_ports {c_cmd_v c_cmd_d[*] n_done_v n_done_tag[*] crs}]
catch {unset_input_delay -clock core_clk $ot_ci}
set_input_delay [expr {[get_property [get_clocks c_clk] period] * 0.2}] -clock c_clk $ot_ci
set ot_co [get_ports {c_done_v c_done_tag[*] n_cmd_v n_cmd_d[*]}]
catch {unset_output_delay -clock core_clk $ot_co}
set_output_delay [expr {[get_property [get_clocks c_clk] period] * 0.2}] -clock c_clk $ot_co
set_clock_groups -asynchronous -group [get_clocks c_clk] -group [get_clocks core_clk]
