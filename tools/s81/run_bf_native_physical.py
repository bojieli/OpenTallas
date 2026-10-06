#!/usr/bin/env python3
"""Route the full native BF pair, under an explicit standalone 20% IO contract."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import run_abi3_physical as flow

SOURCES=['rtl/s81/ot_s81_bf_native.sv','rtl/common/ot_prefix.sv',
 'rtl/hdc/ot_hdc_cg.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
 'rtl/hdc/ot_hdc_fpu.sv','rtl/proto/ot_fp32_add_rne_pipe.sv']
SOURCES += ['rtl/v41rom/'+n+'.sv' for n in (
 'ot_v41_bf16_lanes','ot_v41_bf16_lanes2_rne_prepare','ot_v41_bmul2',
 'ot_v41_bterm','ot_v41_bterm2_w10','ot_v41_chain','ot_v41_chain2','ot_v41_fadd',
 'ot_v41_rom_elem_w10_rne_wake_prepare','ot_v41_segtree','ot_v41_segtree2',
 'ot_v41_bmul2_rne_prepare','ot_v41_bmul_subnormal_rne_prepare')]
MACRO='ot_rom_4096x274_m8'
VIEW='physical/asap7_memory_macros_v2/'+MACRO
SOURCES += [VIEW+'/'+MACRO+'_bb.v',
 'physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v']

def command(a):
 cmd=['--view','asap7','--top','ot_s81_bf_native']
 for s in SOURCES: cmd+=['--source',s]
 if a.margin:
  # margin-first (owner rule 2026-10-06): PINREG=1 register-to-register pins, routed at 770 ps with the die IO
  # budget (insertion +/- 150 ps, 100 ps wire/station on the max side), slot-width die, signed off at 833.333 ps
  cmd+=['--param','PINREG=1','--clock-period-ns','.770','--core-input-delay-min-ns','0.0','--core-input-delay-max-ns','0.40',
   '--output-delay-min-ns','-0.30','--output-delay-max-ns','0.10','--false-path-from','rst_n',
   '--die-area','0','0',str(a.die_w),str(a.die_h),'--core-area','2.16','2.16',str(round(a.die_w-2.16,3)),str(round(a.die_h-2.16,3)),
   '--slew-margin-percent','20','--hold-margin-ns','0.040','--orfs-var','PLACE_DENSITY_LB_ADDON=',
   '--step-tcl','PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl','--step-tcl','PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl']
 else:
  cmd+=['--clock-period-ns','.833','--io-delay-fraction','.2']
 cmd+=['--clock-uncertainty-ns','.060',
 '--clock-uncertainty-hold-ns','.025','--orfs-corner','WC','--hold-corners','WC,BC',
 '--stages','pnr','--synth-timeout-seconds','unlimited',
 '--flow-timeout-seconds','unlimited','--core-utilization',str(a.util),
 '--place-density','.60','--max-transition-ns','.25',
 '--orfs-var','NUM_CORES=16','--orfs-var','ADDER_MAP_FILE=',
 '--orfs-var','SYNTH_SCRIPT=/src/physical/s81_native_bf/synth.tcl',
 '--macro-view',MACRO+'='+VIEW,'--macro-place-halo','5.4','5.4',
 '--step-tcl','POST_MACRO_PLACE=physical/s81_native_bf/place.tcl',
 '--orfs-var','PDN_TCL=/src/physical/abi3/w10_wake_pdn.tcl',
 '--keep-heavy-artifacts','--nickname-tag',a.tag,
 '--keep-workdir',str(a.work),'--output',str(a.output)]
 return cmd

def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--util',type=int,default=55)
 p.add_argument('--tag',default='s81_bf_native_u55')
 p.add_argument('--margin',action='store_true');p.add_argument('--die-w',type=float,default=1002.888);p.add_argument('--die-h',type=float,default=190.08);p.add_argument('--print',action='store_true')
 a=p.parse_args()
 cmd=command(a)
 if a.print:
  import shlex
  print(shlex.join(['python3','tools/s81/run_bf_native_physical.py','--work',str(a.work),'--output',str(a.output),'--util',str(a.util),'--tag',a.tag]));return 0
 original=flow.sdc_lines
 def sdc(view,block,clock_period_ns,constraints=None):
  lines=original(view,block,clock_period_ns,constraints)
  lines += ['# Physical PP ROM read/capture: alternate banks, capture two edges after read.',
   'set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]',
   'set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]']
  return lines
 flow.sdc_lines=sdc
 return flow.main(cmd,synth_timeout=None,flow_timeout=None)
if __name__=='__main__':raise SystemExit(main())
