# Reset is asynchronous, exactly as in the existing SRAM-return lane.
# All data/address/bank-identity and real macro clock paths remain timed.
set_false_path -from [get_ports rst_n]
