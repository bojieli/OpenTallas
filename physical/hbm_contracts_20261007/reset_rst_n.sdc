# Raw asynchronous reset port feeds only the local reset synchroniser rst_s (async assert, release by two
# local flops); its recovery/removal against the asynchronous port is not a timed path.
set_false_path -from [get_ports rst_n]
