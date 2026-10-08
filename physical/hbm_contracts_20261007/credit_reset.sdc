# Raw asynchronous reset ports feed only the local reset synchronisers (async assert, synchronous release
# by two local flops); recovery/removal of those two flops against the asynchronous port is not a timed path.
set_false_path -from [get_ports {rst_in_n phy_rst_in_n}]
