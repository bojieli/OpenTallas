# hfd_router sign-off post-SDC (Claude:hbm-router 2026-10-06): the four forwarded-clock outputs e{NE,NW,SE,SW}[128]
# carry ~ck (ot_fwd_clk_inv at leaf insertion), not data.  Their relation to vclk is clock-as-data, not a capture:
# the receiving station captures the e*[127:0] bus on this forwarded clock (falling ck edge = half a period after the
# launching ck edge), so they are excluded from the vclk IO check; the fclk/data skew at the face is reported instead.
set_false_path -to [get_ports {eNE[128] eNW[128] eSE[128] eSW[128]}]
