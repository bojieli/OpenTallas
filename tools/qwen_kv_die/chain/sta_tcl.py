#!/usr/bin/env python3
"""kv-die: the die STA script (GRT parasitics) for die_chain.sh.  usage: sta_tcl.py <kv|r22k> <tt|ff> <out.tcl>"""
import sys
die, c, out = sys.argv[1:4]
L = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_'
C = c.upper()
libs = [f'{L}AO_RVT_{C}_nldm_211120.lib.gz', f'{L}INVBUF_RVT_{C}_nldm_220122.lib.gz', f'{L}OA_RVT_{C}_nldm_211120.lib.gz',
        f'{L}SEQ_RVT_{C}_nldm_220123.lib', f'{L}SIMPLE_RVT_{C}_nldm_211120.lib.gz', f'/work/libs/qfd_elements_{c}.lib']
if die == 'kv':
    libs.append(f'/work/libs/ot_hbm3e_phy_{c}.lib')
    clocks = """create_clock -name stream -period 833.333 [get_pins -quiet {pll/pll_WS pll/pll_WN pll/pll_ES pll/pll_EN pll/pll_c pll/pll_fwd}]
foreach s {WS WN ES EN} { create_clock -name hclk_$s -period 1024 [get_pins -quiet ctrl_$s/pll_hbm] }
set_clock_groups -asynchronous -group stream -group hclk_WS -group hclk_WN -group hclk_ES -group hclk_EN"""
else:
    clocks = """create_clock -name stream -period 833.333 [get_pins -quiet {clk_rx/pll_*}]
create_clock -name serial -period [expr {833.333*4.0/3.0}] [get_pins -quiet io_collective/pll_serial]
foreach k {ucie serdes} { create_clock -name $k -period 833.333 [get_pins -quiet io_collective/pll_$k] }
set_clock_groups -asynchronous -group stream -group serial -group ucie -group serdes"""
mm, unc = ('max', 'set_clock_uncertainty -setup 60 [all_clocks]') if c == 'tt' else ('min', 'set_clock_uncertainty -hold 25 [all_clocks]')
rd = '\n'.join(f'read_liberty {x}' for x in libs)
tcl = f"""proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag rss_mb=[expr {{$r/1024}}] t=[clock seconds]"; flush stdout }}
proc step {{name body}} {{ set t0 [clock milliseconds]
  if {{[catch {{uplevel 1 $body}} err]}} {{ puts "OT_STEP_FAIL $name $err" }}
  puts "OT_TIME step=$name s=[format %.1f [expr {{([clock milliseconds]-$t0)/1000.0}}]]"; mem $name }}
step libs {{
{rd}
}}
step load {{ read_db /work/ckpt_grt.odb }}
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
step guides {{ read_guides /work/route.guide }}
set_routing_layers -signal M4-M9 -clock M4-M9
step est {{ estimate_parasitics -global_routing }}
{clocks}
{unc}
step sta {{
  report_checks -path_delay {mm} -group_path_count 3000000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/grt_{c}_ends.rpt
  report_checks -path_delay {mm} -group_path_count 5 -fields {{slew cap input_pins nets}} -digits 1 > /work/grt_{c}_paths.rpt
  report_tns; report_wns; report_worst_slack -{mm}
  report_check_types -max_slew -max_capacitance -violators > /work/grt_{c}_drv.rpt
}}
puts OT_STA_DONE
"""
open(out, 'w').write(tcl)
