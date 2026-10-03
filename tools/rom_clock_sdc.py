#!/usr/bin/env python3
"""Generate explicit candidate clock constraints in ASAP7 library ps.
No async clock groups, false paths or phase-safe claims. Cross-domain paths are
bounded with OpenSTA's -ignore_clock_latency (its datapath constraint spelling).
Hold is checked at zero-delay bounds for CDC paths; protocol holds payload until
consumer credit returns through 3FF. All local FF1->FF2->FF3 arcs remain timed.
"""
from pathlib import Path
import argparse
MESO='''# Independent phase. Both local periods constrained; no phase alignment claim.
create_clock -name write -period 833.333 [get_ports wclk]
create_clock -name read -period 833.333 [get_ports rclk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Every cross-clock arc is bounded, including all payload/mux arcs.
# The 773.333ps upper bound also bounds Gray-bit skew below one source period.
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks write] -to [get_clocks read]
set_max_delay -ignore_clock_latency 773.333 -from [get_clocks read] -to [get_clocks write]
set_min_delay -ignore_clock_latency 0 -from [get_clocks write] -to [get_clocks read]
set_min_delay -ignore_clock_latency 0 -from [get_clocks read] -to [get_clocks write]
set_input_delay 166.666 -clock write [get_ports {wrst_n w_v w_d*}]
set_input_delay 166.666 -clock read [get_ports {rrst_n r_rdy}]
set_output_delay 166.666 -clock write [get_ports {w_rdy w_live w_fault}]
set_output_delay 166.666 -clock read [get_ports {r_v r_d* r_live r_fault}]
set_max_fanout 32 [current_design]
'''
FWD='''# Falling-edge register and real inverted forwarded output waveform.
create_clock -name incoming -period 833.333 [get_ports fclk_i]
create_generated_clock -name forwarded -source [get_ports fclk_i] -edges {2 3 4} [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.666 -clock incoming [get_ports {rst_n i_v i_d*}]
# Output is consumed at the next falling edge of the inverted clock (source rising).
set_output_delay 166.666 -clock forwarded -clock_fall [get_ports {o_v o_d*}]
set_max_fanout 32 [current_design]
'''
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out-dir',type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
    (a.out_dir/'meso_w512_d4.sdc').write_text(MESO);(a.out_dir/'fwd_w512.sdc').write_text(FWD)
if __name__=='__main__':main()
