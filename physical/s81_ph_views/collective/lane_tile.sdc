# CLAUDE S81-PH coll v2 lane tile (dsfd_coll_lane_w / _e): appended after the calibrated margin IO SDC (core_clk = ck).
# tf = forwarded clock (kept buffer of ck), not a data output; rs = asynchronous stream reset (synchronised in the tile);
# chb = static configuration pin (registered in the endpoint).
set_false_path -to [get_ports {tf*}]
set_false_path -from [get_ports {rs* chb*}]
