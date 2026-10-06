#!/usr/bin/env python3
"""Prepare four source-selected single-element recipes. Never admits/launches."""
import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[4]
rel='physical/hbm_die_abstracts_20261006/links/native_quarter'
sources=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv','rtl/common/ot_fwd_link_stage.sv','physical/hbm_die_abstracts_20261006/links/ot_hbm_native_register_slice.sv','physical/hbm_die_abstracts_20261006/links/parents/ot_hbm_native_station.sv',f'{rel}/ot_hbm_native_frame_station.sv']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True).strip():raise SystemExit('Commit actual selected sources before preparing')
rows=[]
for no in (3,2):
 for orientation,util in [('H',55),('V',60)]:
  tag=f'full73_NO{no}_{orientation}_u{util}'
  run=Path('/srv/opentallas-scratch2/codex/hbm-links-abstracts-20261006')/tag
  cmd=['python3','tools/run_abi3_physical_persistent.py','--persistent-workdir',str(run/'work'),'--launch-receipt',str(run/'launch.json'),'--view','asap7','--top','ot_hbm_native_frame_station']
  for s in sources:cmd+=['--source',s]
  cmd+=['--param','ENABLE=1','--param',f'NO={no}','--core-utilization',str(util),'--place-density',str((util+5)/100),'--clock-port','clk_sm','--clock-period-ns','0.833333333','--clock-uncertainty-ns','0.06','--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC','--stages','synth,pnr','--orfs-var','NUM_CORES=16','--orfs-var','ADDER_MAP_FILE=','--orfs-var',f'CORE_ASPECT_RATIO={0.25 if orientation=="H" else 4}','--orfs-var',f'SDC_FILE=/src/{rel}/frame_station.sdc','--step-tcl','PRE_CTS=physical/rom_clock/fwd_forwarded_subtree.tcl']
  left,right=('left','right') if orientation=='H' else ('bottom','top')
  cmd+=['--pin-region',f'^(clk_sm|por_n|in_.*|release_.*)$={left}','--pin-region',f'^(fclk_o|out_.*|ACK_.*)$={right}','--nickname-tag',tag,'--purpose','signoff_target','--output',str(run/'physical.json')]
  files=sources+[f'{rel}/frame_station.sdc','physical/rom_clock/fwd_forwarded_subtree.tcl','tools/run_abi3_physical_persistent.py','tools/run_abi3_physical.py']
  rows.append(dict(tag=tag,source_commit=commit,source_hashes={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files},argv=cmd,source_selected=True,launched=False,launch_allowed=False,NO=no,orientation=orientation,utilization=util,required_authority=f'{rel}/actual_frame_station_parent.tcl',RAM_need_GiB=None,disk_need_GiB=None,pending=['actual caller receiver min/max delays, per-corner pin/forwarded-root caps and reset/slot authority','fresh CPU16 fit pre/post unchanged admission guard with honest source-specific RAM/disk inventory','actual mapped clock-Q+SSF LIB, real routed LEF/SPEF, port/setup/hold/slew/cap/DRC; cannot borrow prior clock/area'],attributes='retain keep_hierarchy/keep/dont_touch and intermediate attributes during re-synthesis',admission='Kant fresh actual CPU fit; no RAM-only queue, no heavy localhost; EPYC2 NVMe2 unchanged admit.sh'))
out=root/'results/physical/hbm_die_abstracts_20261006/links/native_quarter/selected_frame_route_recipes.json'
out.write_text(json.dumps(dict(status='SOURCE_SELECTED_RECEIVER_AND_CPU_OPEN',rows=rows,station_implementation_count=1,new_hardened_variants=0,waypoint_copies=208),indent=2)+'\n')
print('Four exact single-element recipes; no physical job or admission launched')
