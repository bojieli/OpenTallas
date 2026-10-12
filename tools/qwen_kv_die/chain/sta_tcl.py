#!/usr/bin/env python3
"""kv-die: the die STA script (GRT parasitics) for die_chain.sh.
usage: sta_tcl.py <kv|r22k> <tt|ff> <out.tcl> [clock plan.json]

qwendie-1011 (textbook audit class 1): with a clock plan (tools/budgets/clock_plan.py record of the die's clock-only
CTS, htop + hreg) every CTS sink pin gets its MEASURED clock arrival as a per-pin clock latency (FF run: the FF
insertion; TT run: mean of the SS and FF insertions -- interpolated, the plan measures SS / FF only), written to
clock_lat_<c>.tcl next to the script and sourced after the clocks.  Without it the die clock is ideal (pathfinding)."""
import json
import sys
from pathlib import Path
die, c, out = sys.argv[1:4]
plan = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
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
lat = ''
if plan:
    si = json.loads(Path(plan).read_text())['sink_insertion']
    rows = [f'set p [get_pins -quiet {{{k}}}]; if {{[llength $p]}} {{ set_clock_latency {(v[1] if c == "ff" else (v[0] + v[1]) / 2):.1f} $p; incr ot_lat_n }} else {{ incr ot_lat_miss }}'
            for k, v in sorted(si.items())]
    Path(out).with_name(f'clock_lat_{c}.tcl').write_text('set ot_lat_n 0; set ot_lat_miss 0\n' + '\n'.join(rows) +
        f'\nputs "OT_CLOCK_PLAN corner={c} sinks={len(rows)} bound=$ot_lat_n missing=$ot_lat_miss"\n')
    lat = f'source /work/clock_lat_{c}.tcl\n'
mm, unc = ('max', 'set_clock_uncertainty -setup 60 [all_clocks]') if c == 'tt' else ('min', 'set_clock_uncertainty -hold 25 [all_clocks]')
rd = '\n'.join(f'read_liberty {x}' for x in libs)
# die-evidence-2 2026-10-09: ETM-bound element views (tools/qwen_die_etm_map.py: routed sign-off ETMs of slab_m8 /
# cst / chead) are read FIRST when the run's libs carry them; qfd_elements_<c>.lib then holds only the ASSUMED rest
rd = f'if {{[file exists /work/libs/qfd_etm_{c}.lib]}} {{ read_liberty /work/libs/qfd_etm_{c}.lib }}\n' + rd
# kv-die lead 2026-10-12 (die_iter_1012): per-view ETMs bound by tools/qwen_kv_die/bind_views.py (one lib per master)
rd = f'foreach f [lsort [glob -nocomplain /work/libs/qfd_etm_*_{c}.lib]] {{ read_liberty $f }}\n' + rd
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
# die-evidence-2 2026-10-09: GRT parasitics from the SPEF the GRT session wrote (grt.tcl step spef).  The old
# read_guides + estimate_parasitics -global_routing path gave no wire RC (GRT-0008): the run now fails without the SPEF.
if {{![file exists /work/die_grt.spef]}} {{ puts "OT_STEP_FAIL spef missing: /work/die_grt.spef (GRT-0008: guides carry no RC)"; exit 1 }}
# ds-1010 10-10: a failed read_spef must stop the run (the step proc only logs): KV11's first STA timed the die with no wire RC
if {{[catch {{read_spef /work/die_grt.spef}} err]}} {{ puts "OT_STEP_FAIL spef $err"; exit 1 }}
{clocks}
{lat}{unc}
step sta {{
  report_checks -path_delay {mm} -group_path_count 3000000 -endpoint_path_count 1 -unique_paths_to_endpoint -format end > /work/grt_{c}_ends.rpt
  report_checks -path_delay {mm} -group_path_count 5 -fields {{slew cap input_pins nets}} -digits 1 > /work/grt_{c}_paths.rpt
  report_tns; report_wns; report_worst_slack -{mm}
  report_check_types -max_slew -max_capacitance -violators > /work/grt_{c}_drv.rpt
}}
puts OT_STA_DONE
"""
open(out, 'w').write(tcl)
