# su_norm unit routes (ot_dsrom_su_norm minimum components).  Data ports face registered neighbours on the same clock
# tree (the hub wire stages): hold from the inputs is the parent's clock-balance check, not this block's (an ideal
# port demands ~300 ps of hold buffers on every input bit); every register-to-register path is repaired and signed
# off (tools/w18/corner_sta.py worst_reg_to_reg_slack, SS setup 60 ps / FF hold 25 ps).
set_false_path -hold -from [all_inputs -no_clocks]
# r / r_v: the rstd observability port of the bench (no consumer in the chain; the rstd's real path is the broadcast
# wire to the lanes, which is register-to-register)
set_false_path -to [get_ports {r[*] r_v}]
