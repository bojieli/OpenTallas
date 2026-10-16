# redesign-ds 2026-10-09: dsfd_coll_cb / dsfd_coll_ct (three-tile collective core), appended after the calibrated margin
# IO SDC (core_clk = ck).  rs = asynchronous stream reset (synchronised in each tile).
set_false_path -from [get_ports {rs*}]
