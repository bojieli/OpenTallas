set_io_pin_constraint -group -region left:* -pin_names {next_data*}
set_io_pin_constraint -group -region right:* -pin_names {data*}
set_io_pin_constraint -group -region top:* -pin_names {clk rst_n we}
set_io_pin_constraint -group -region bottom:* -pin_names {good ce due}
