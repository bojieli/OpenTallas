# CLAUDE S81-PH vm v2 bank-group tile (dsfd_vm_bg): appended after the calibrated margin IO SDC (core_clk = ck, the
# serial 0.9 GHz clock).  rs = asynchronous reset (synchronised in the tile); grp = static tile index (tie cells, registered).
set_false_path -from [get_ports {rs* grp*}]
