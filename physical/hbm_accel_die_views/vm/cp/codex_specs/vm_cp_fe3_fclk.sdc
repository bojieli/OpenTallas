# vm_cp_fe3: qNE[580] qNE[581] are FORWARDED clocks (ot_fwd_clk_inv of ck, kept inverter at the face), not data
# outputs. The cx1 routes (eca45f5dc) timed ck -> qNE[580|581] as data under the all_outputs budget: the only stalled
# hold class (ot_hold_stall: I2O=2, "ck -> qNE[*]"); a clock cannot take a pin register. Same modelling as the closed
# fe0/fe1/fe2/fw1/fw2 cx2 kits and hattn_ks_entry. Period, uncertainty and every data boundary are unchanged. OPEN at
# die level: fclk-to-data offset = this tile's routed clock insertion; the receiver source-synchronous budget must use it.
set_false_path -to [get_ports {qNE[580]}]
set_false_path -to [get_ports {qNE[581]}]
