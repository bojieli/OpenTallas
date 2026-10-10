# hgi-takeover 2026-10-10 (coordinator: port SECDED clock plan, option 1 as hbm-forks did for the svc face taps):
# ckf is the face clock tap of ot_hcoll_port (FACE_CK = 1) -- a die clock leaf at the PHY face that clocks the RX pin
# flops (rxf_p / rxv_p).  It is the same clock as clk (one core_clk with two source ports); its SOURCE latency is the
# block's interior insertion (route e21dc1395 routed reference TT 692 ps less the ~50 ps face tree), so the face flops
# are timed aligned with the interior registers; the die clock plan delivers the ckf leaf that much later (die CTS
# per-leaf delay, as the svc ckw / cke rows of the die clock_leaf_offsets).
create_clock -name core_clk -period [get_property [get_clocks core_clk] period] [get_ports {clk ckf}]
set_clock_latency -source 0.640 [get_ports ckf]
