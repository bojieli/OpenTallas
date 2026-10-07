# Isolated boundary contract of the retained CODE-pair routes (BUFx2 drive, one DFF D-pin load).
set_driving_cell -lib_cell BUFx2_ASAP7_75t_R -pin Y [all_inputs -no_clocks]
set_load 0.558822 [all_outputs]
