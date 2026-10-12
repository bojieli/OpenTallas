# el1011-hbm-attn-phys: kq[1] is the FORWARDED clock (ot_fwd_clk_inv of the tile clock; the svc group captures kq[0]
# on ~kq[1]) -- a clock, not a data output (v12 lo timed it as data through the 2.5 ns spine: ck[0] -> kq[1] -2,828 ps).
set_false_path -to [get_ports {kq[1]}]
