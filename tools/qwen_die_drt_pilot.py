#!/usr/bin/env python3
"""Qwen ROM die: die-top DETAILED-route pilot (owner request 2026-10-06: size hardware for full-die place and route).

Input: a die case that has run `real` (macro placement + legality + pin access, real k=1 pins) and `pdn` (r5 PDN) ->
floorplan_pdn.odb.  The pilot runs, in ONE OpenROAD process with per-step wall time and VmRSS / VmHWM:
  load -> GRT (k = 1, every die net, 50 congestion iterations) -> repair_design (die-top repeaters/buffers in the free
  sites of corridors / channels; max wire length = the measured 430.56 um stage) -> detailed_placement -> GRT again
  -> DRT -> RCX (asap7 rcx_patterns) -> write SPEF / ODB / DEF
with a checkpoint (write_db) after GRT1, DPL and GRT2 and the routed ODB after DRT; the pilot runs in a container with
a hard memory guard (run_case.sh <mem_gb>, owner: 450 GB on EPYC1) so an overrun cannot OOM other owners' jobs;
then OpenSTA in separate processes at SS (60 ps setup uncertainty) and FF (25 ps hold) at 833.333 ps on the routed
top-level parasitics with the element interface LIBs (tools/qwen_die_element_lib.py) and the real HBM3E PHY lib.
There is no global placement of standard cells (GPL) or detailed placement of macros: every element is a fixed macro;
the only standard cells are the repeaters repair_design adds.  DRC = the detailed router's final violation count
(DRT report); a separate KLayout DRC is not part of this pilot.

    python3 tools/qwen_die_drt_pilot.py --case DIR --libs LIBDIR [--threads 64]
"""
import argparse
from pathlib import Path

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
NLDM = PLAT + '/lib/NLDM'
SS_LIBS = [f'{NLDM}/asap7sc7p5t_{f}_RVT_SS_nldm_{d}.lib{z}' for f, d, z in
           (('AO', '211120', '.gz'), ('INVBUF', '220122', '.gz'), ('OA', '211120', '.gz'), ('SEQ', '220123', ''),
            ('SIMPLE', '211120', '.gz'))]
FF_LIBS = [x.replace('_SS_', '_FF_').replace('SEQ_RVT_FF_nldm_220123.lib', 'SEQ_RVT_FF_nldm_220123.lib')
           for x in SS_LIBS]
PERIOD_PS = 833.333

HEAD = """proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\\s+(\\d+)} $s -> r; regexp {VmHWM:\\s+(\\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err" }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name }
"""


def pilot_tcl(threads, libs):
    reads = '\n'.join(f'read_liberty {x}' for x in SS_LIBS + [f'/work/libs/{libs}_ss.lib', '/work/libs/ot_hbm3e_phy_ss.lib'])
    return HEAD + f"""
set_thread_count {threads}
step load {{ read_db /work/floorplan_pdn.odb }}
step libs {{
{reads}
}}
source {PLAT}/setRC.tcl
set_routing_layers -signal M2-M9 -clock M2-M9
step grt1 {{ global_route -congestion_iterations 50 -allow_congestion -verbose -congestion_report_file /work/grt1_congestion.rpt }}
step ckpt_grt1 {{ write_db /work/ckpt_grt1.odb }}
step est1 {{ estimate_parasitics -global_routing }}
step repair_design {{ repair_design -max_wire_length 430 -verbose }}
step dpl {{ detailed_placement; check_placement -verbose }}
step ckpt_dpl {{ write_db /work/ckpt_dpl.odb }}
step grt2 {{ global_route -congestion_iterations 50 -allow_congestion -verbose -congestion_report_file /work/grt2_congestion.rpt }}
step ckpt_grt2 {{ write_db /work/ckpt_grt2.odb; write_guides /work/route.guide }}
step drt {{ detailed_route -output_drc /work/drt_drc.rpt -output_maze /work/drt_maze.log -verbose 1 -droute_end_iter 64 }}
step write_odb {{ write_db /work/routed.odb }}
step rcx {{ define_process_corner -ext_model_index 0 X; extract_parasitics -ext_model_file {PLAT}/rcx_patterns.rules }}
step write_spef {{ write_spef /work/routed.spef }}
step write_verilog {{ write_verilog /work/routed.v }}
puts OT_PILOT_DONE
"""


def sta_tcl(corner, libs):
    lib = SS_LIBS if corner == 'ss' else FF_LIBS
    reads = '\n'.join(f'read_liberty {x}' for x in lib + [f'/work/libs/{libs}_{corner}.lib',
                                                          f'/work/libs/ot_hbm3e_phy_{corner}.lib'])
    unc = '-setup 60' if corner == 'ss' else '-hold 25'
    rep = 'max' if corner == 'ss' else 'min'
    return HEAD + f"""
step libs {{
{reads}
}}
step lef {{ read_lef {PLAT}/lef/asap7_tech_1x_201209.lef; read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
  read_lef /work/phy_ew.lef; read_lef /work/elements.lef }}
step netlist {{ read_verilog /work/routed.v; link_design qfd_die }}
step spef {{ read_spef /work/routed.spef }}
# clocks: the stream clock leaves the hub's region PLL pins and the IO collective's stream PLL; serial / UCIe / SerDes
# / HBM controller clocks are separate (asynchronous groups, crossings are CDC FIFOs)
create_clock -name stream -period {PERIOD_PS} [get_pins -quiet {{hub_el/pll_r* io_collective/pll_stream}}]
create_clock -name serial -period [expr {{{PERIOD_PS}*4.0/3.0}}] [get_pins -quiet io_collective/pll_serial]
foreach c {{ucie serdes}} {{ create_clock -name $c -period {PERIOD_PS} [get_pins -quiet io_collective/pll_$c] }}
foreach s {{WS WN ES EN}} {{ create_clock -name hclk_$s -period 1024 [get_pins -quiet ctrl_$s/pll_hbm] }}
set_clock_groups -asynchronous -group stream -group serial -group ucie -group serdes -group hclk_WS -group hclk_WN \\
  -group hclk_ES -group hclk_EN
set_clock_uncertainty {unc} [all_clocks]
step sta {{
  report_checks -path_delay {rep} -group_path_count 20 -format end > /work/sta_{corner}_ends.rpt
  report_checks -path_delay {rep} -group_path_count 5 -fields {{slew cap input_pins nets}} -digits 1 > /work/sta_{corner}_paths.rpt
  report_tns; report_wns; report_worst_slack -{rep}
  report_check_types -max_slew -max_capacitance -violators > /work/sta_{corner}_drv.rpt
}}
puts OT_STA_DONE
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--libs', default='qfd_elements')
    ap.add_argument('--threads', type=int, default=64)
    a = ap.parse_args(argv)
    (a.case / 'pilot.tcl').write_text(pilot_tcl(a.threads, a.libs))
    for c in ('ss', 'ff'):
        (a.case / f'sta_{c}.tcl').write_text(sta_tcl(c, a.libs))
    print(a.case)


if __name__ == '__main__':
    main()
