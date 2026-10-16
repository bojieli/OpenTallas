#!/bin/bash
# mtp-head-1010 2026-10-10 (FLOW-IOREF for generated signoff_*.sdc): print the IO lines of a block's sign-off SDC against
# an insertion-reference VIRTUAL clock instead of numeric delays on the real clock.
#   signoff_io_vclk.sh <period_ps> <ISS_ps> <IFF_ps> [in_hold_skew_ps]
# The legacy lines (dsrom_fh_safe/cl_route.sh family) bake the calibrate run's CTS-only insertion into
#   set_input_delay -max ISS+250 / -min IFF-skew / set_output_delay -max 250-ISS / -min -(IFF+50)   on core_clk,
# so the loop's routed re-STA (physical/common_flow/io_ref_routed.sdc, which moves only vclk* / ot_lb_v_* / nbr_clk)
# cannot re-reference them: mtp-head340-mkdrv-rg1a2 signed off FF -89.74 against the CTS-only FF 607 while its routed FF
# insertion was 512 (-8.26 at the routed reference).  Here vclk_io carries the corner's insertion as latency (FF libraries
# loaded -> IFF, else ISS) and every delay is relative to it, so at the calibrate insertion the checks are IDENTICAL
# (input arrival ISS+250 / IFF-skew; output setup required T+ISS-250, hold IFF+25+50) and io_ref_routed.sdc moves
# vclk_io to the ROUTED mean of each corner (same 60/25 ps uncertainties, same 50 ps receiver margin).
P=$1; ISS=$2; IFF=$3; SK=${4:-0}
cat <<S
create_clock -name vclk_io -period $P
if {[llength [get_libs -quiet *_FF_*]]} { set_clock_latency $IFF [get_clocks vclk_io] } else { set_clock_latency $ISS [get_clocks vclk_io] }
set_clock_uncertainty -setup 60 [get_clocks vclk_io]
set_clock_uncertainty -hold 25 [get_clocks vclk_io]
set_input_delay -max 250 -clock vclk_io [all_inputs -no_clocks]
set_input_delay -min $(echo "0-$SK" | bc) -clock vclk_io [all_inputs -no_clocks]
set_output_delay -max 250 -clock vclk_io [all_outputs]
set_output_delay -min -50 -clock vclk_io [all_outputs]
S
