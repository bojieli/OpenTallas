# Selected Qwen die boundary: one 430.56 um hop plus receiver pin.
# This is sourced only by CORE_DIE_IO=1 successor routes. Historical recipes
# and their pinned files retain their original IO loading.
set_load 80 [all_outputs]
set_input_transition 150 [all_inputs -no_clocks]
