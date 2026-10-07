# Margin-first fused head SIGN-OFF (owner rule 2026-10-06), read by tools/w18/corner_sta.py --post-sdc after the routed
# 6_final.sdc (routed over-constrained at 770 ps): clock back at 833.333 ps with 60 / 25 ps uncertainty. Context scope
# unchanged from the C-series head (physical/dsrom_fh_capture/boundary.sdc): stand-in ports are false-pathed; every
# internal register, SRAM read/capture, protection and clock path is timed.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
