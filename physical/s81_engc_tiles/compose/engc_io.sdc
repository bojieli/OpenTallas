# dsfd_engram_c composition SDC (el1013-s81-engram 2026-10-13), appended to io_vclk_m_<V>.sdc.
# Leaf reset release (the view flow's rst_mcp2 intent, physical/s81_ph_views/common/make_io_vclk.sh): T_WIN's
# synchronised leaf resets rn_lk / rn_sk (rsl_q[1] / rss_q[1], 2-flop synchronisers kept for exactly this) cross
# 340+ um to the lookup / sink leaves' asynchronous reset pins; release may take 2 cycles (the die holds rst >= 3
# cycles and sends no input valid within 2 cycles of release; a leaf idles until its first input).
set_multicycle_path -setup 2 -through [get_pins {u_win/rn_lk u_win/rn_sk}]
set_multicycle_path -hold 1 -through [get_pins {u_win/rn_lk u_win/rn_sk}]
# Die reset: rst is the asynchronous die reset, synchronised separately in every tile (dsfd_engram_c.sv port comment);
# one pin fans out to 8 tiles across 1.19 mm.  Its release gets the same 2 cycles (CTS-stop run c10: rst -> u_pb2
# was the worst setup path of the cluster, -50.5 ps, a recovery check on a 2-flop synchroniser).
set_multicycle_path -setup 2 -from [get_ports {rst[0]}]
set_multicycle_path -hold 1 -from [get_ports {rst[0]}]
