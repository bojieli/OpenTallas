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
# RECUT (BF re-cut A): the q-element and its re-cut modules (harmless to the original build: not elaborated)
SOURCES += ['rtl/v41rom/'+n+'.sv' for n in (
 'ot_v41_rom_elem_qx_w10','ot_v41_chain2u2','ot_v41_kreg','ot_v41_chain3','ot_v41_chain4','ot_v41_fadd2','ot_v41_bterm3_w10',
 'ot_v41_bterm4_w10','ot_v41_bterm5_w10','ot_v41_segtree3','ot_v41_segtree4','ot_v41_segtree5','ot_v41_segtree6',
 'ot_v41_fadd3','ot_v41_chain5','ot_v41_bmul3_rne','ot_v41_bf16_lanes3')]   # + RECUT 4 / 5 deep full-rate BF (s81-bf)
MACRO='ot_rom_4096x274_m8'
VIEW='physical/asap7_memory_macros_v2/'+MACRO
SOURCES += [VIEW+'/'+MACRO+'_bb.v',
 'physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v']

def command(a):
 cmd=['--view','asap7','--top','ot_s81_bf_native']
 for s in SOURCES: cmd+=['--source',s]
 if a.margin:
  # margin-first (owner rule 2026-10-06): PINREG=1 register-to-register pins, routed at 770 ps with the die IO
  # budget on setup (insertion +/- 150 ps, 100 ps wire/station on the max side), owner hold model (FF insertion ~175,
  # 50 ps hold IO: in min 125 / out min -225, hold repaired at the FF corner), slot-width die, signed off at 833.333 ps
  # --ins-ss/--ins-ff: MEASURED mid core_clk insertion (ps, CTS-only calibration), the IO constraints follow it
  # (owner 2026-10-06): in max = ss+150+100, in min = ff-50, out max = 100-(ss-150), out min = -(ff+50)
  ss=a.ins_ss if a.ins_ss else 150.0; ff=a.ins_ff if a.ins_ff else 175.0
  io=lambda v: str(round(v/1000.0,4))
  # --wc-only (BF rowfix closure 2026-10-07): ORFS repairs at the WC (SS) corner only, the route's hold IO follows the
  # SS insertion (pass --ins-ff = --ins-ss); --hold-corners BC made ORFS CORNERS=BC, i.e. setup repaired at FF (bf_m2)
  hc=a.corner if a.wc_only else 'BC'
  if a.hitfix: cmd+=['--param','HITFIX=1']
  if a.half: cmd+=['--param','HALF=1']
  if a.half_phl: cmd+=['--param','HALF_PHL=1']
  if a.recut: cmd+=['--param','RECUT='+str(a.recut_level),'--orfs-var','OT_BF_RECUT=1']   # synth.tcl: no W10 wake leaves
  cmd+=['--param','PINREG=1','--clock-period-ns',a.period,'--core-input-delay-min-ns',io(ff-50),'--core-input-delay-max-ns',io(ss+250),
   '--output-delay-min-ns',io(-(ff+50)),'--output-delay-max-ns',io(100-(ss-150)),'--false-path-from','rst_n',
   '--die-area','0','0',str(a.die_w),str(a.die_h),'--core-area','2.16','2.16',str(round(a.die_w-2.16,3)),str(round(a.die_h-2.16,3)),
   '--hold-corners',hc,'--slew-margin-percent','20','--hold-margin-ns','0.020','--orfs-var','PLACE_DENSITY_LB_ADDON=',
   '--step-tcl','PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl','--step-tcl','PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl']
 else:
  cmd+=['--clock-period-ns','.833','--io-delay-fraction','.2','--hold-corners','WC,BC']
 cmd+=['--clock-uncertainty-ns','.060',
 '--clock-uncertainty-hold-ns','.025','--orfs-corner',a.corner,
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
 if a.half_phl:   # s81-bf HALF_PHL: phase FF onto the ICG clock net (PRE_CTS hook also carries the karb buffer cap)
  karb='PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl'
  assert karb in cmd and a.half and a.margin
  cmd[cmd.index(karb)]='PRE_CTS=physical/s81_native_bf/margin/ph_local.tcl'
  cmd+=['--step-tcl','POST_CTS=physical/s81_native_bf/margin/ph_local_post.tcl']
 if a.recut_cgl:   # s81-bf: element clock-gate enable FF onto an ancestor clock net (cg_local.tcl; carries the karb cap)
  karb='PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl'
  assert karb in cmd and a.recut and a.margin
  cmd[cmd.index(karb)]='PRE_CTS=physical/s81_native_bf/margin/cg_local.tcl'
  cmd+=['--step-tcl','POST_CTS=physical/s81_native_bf/margin/cg_local_post.tcl']
 if a.extra: cmd+=a.extra.split()
 return cmd

def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--util',type=int,default=55)
 p.add_argument('--tag',default='s81_bf_native_u55')
 p.add_argument('--margin',action='store_true');p.add_argument('--ins-ss',type=float,default=0.0);p.add_argument('--ins-ff',type=float,default=0.0);p.add_argument('--die-w',type=float,default=1002.888);p.add_argument('--die-h',type=float,default=190.08);p.add_argument('--print',action='store_true')
 p.add_argument('--wc-only',action='store_true');p.add_argument('--hitfix',action='store_true');p.add_argument('--half',action='store_true');p.add_argument('--half-phl',action='store_true');p.add_argument('--recut-cgl',action='store_true');p.add_argument('--corner',default='WC',choices=('WC','TC'));p.add_argument('--period',default='.770');p.add_argument('--recut',action='store_true');p.add_argument('--recut-level',type=int,default=2);p.add_argument('--extra',default='')
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
  if a.half:   # BF SAFE variant B: element + pin regs on the half-rate gated clock (multicycle 2 / 1 among them)
   lines += [l for l in (ROOT/'physical/s81_native_bf/margin/half_mc.sdc').read_text().splitlines() if l.strip()]
  if a.recut and a.recut_level == 3:   # BF unroll-by-2: the lane chains' hs_* registers multicycle 2/1
   lines += [l for l in (ROOT/'physical/s81_native_bf/margin/u2_mc.sdc').read_text().splitlines() if l.strip()]
  return lines
 flow.sdc_lines=sdc
 return flow.main(cmd,synth_timeout=None,flow_timeout=None)
if __name__=='__main__':raise SystemExit(main())
