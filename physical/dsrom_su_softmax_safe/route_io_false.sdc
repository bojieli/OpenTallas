# SAFE tile boundary: every input is captured by a flop and every output is a flop, so IO timing is checked in the die
# context (check_io.sh re-times it against the measured insertion); the route does not repair input hold.
set_false_path -from [all_inputs -no_clocks]
set_false_path -to [all_outputs]
