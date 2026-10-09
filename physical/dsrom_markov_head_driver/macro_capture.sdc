# Actual pingpong preserves each macro q until its2-edge read/capture.
set_multicycle_path -setup 2 -from [get_cells -hierarchical *weights.m?]
set_multicycle_path -hold 1 -from [get_cells -hierarchical *weights.m?]
