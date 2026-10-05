# su_norm minimum-component routes: the block's data ports face registered neighbours on the same clock tree (the hub
# wire stages), so their hold is a property of the parent's clock-tree balance (checked at assembly), not of this
# block; an ideal port with no clock insertion would demand ~300 ps of hold buffers on every input bit (the aq12 r1
# route hit the repair cap).  Hold from inputs is therefore not repaired here; every register-to-register path is
# (signoff: tools/w18/corner_sta.py worst_reg_to_reg_slack, SS setup 60 ps / FF hold 25 ps).
set_false_path -hold -from [all_inputs -no_clocks]
