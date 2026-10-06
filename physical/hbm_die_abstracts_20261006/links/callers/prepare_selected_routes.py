#!/usr/bin/env python3
"""Exact selected source recipe only, no guard/admission or physical launch."""
import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[4]
rel='physical/hbm_die_abstracts_20261006/links/callers'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=root,text=True).strip():raise SystemExit('Commit selected source before preparation')
rows=[]
for kind,top,sources,params,sdc in [
 ('HBM_single_W2063','ot_fwd_link_stage',['rtl/common/ot_fwd_link_stage.sv'],['W=2063','ENABLE=1'],'single_station.sdc'),
 ('S81_column_W564','dsfd_cfifo',[f'{rel}/selected_dsfd_cfifo_r8.sv','rtl/common/ot_meso_fifo.sv'],[],'column_W564.sdc')]:
 for orient,util in [('H',55),('V',60)]:
  tag=f'{kind}_{orient}_u{util}';run=Path('/srv/opentallas-scratch2/codex/hbm-links-abstracts-20261006')/tag
  cmd=['python3','tools/run_abi3_physical_persistent.py','--persistent-workdir',str(run/'work'),'--launch-receipt',str(run/'launch.json'),'--view','asap7','--top',top]
  for s in sources:cmd+=['--source',s]
  for p in params:cmd+=['--param',p]
  left,right=('left','right') if orient=='H' else ('bottom','top')
  cmd+=['--core-utilization',str(util),'--place-density',str((util+5)/100),'--clock-port','fclk_i' if kind.startswith('HBM') else 'ck','--clock-period-ns','0.833333333','--clock-uncertainty-ns','0.06','--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC','--io-delay-fraction','0.2','--stages','synth,pnr','--hold-margin-ns','0.01','--orfs-var','NUM_CORES=16','--orfs-var','ADDER_MAP_FILE=','--orfs-var',f'CORE_ASPECT_RATIO={.25 if orient=="H" else 4}','--orfs-var',f'SDC_FILE=/src/{rel}/{sdc}']
  if kind.startswith('HBM'):
   cmd+=['--pin-region',f'^(fclk_i|rst_n|i_v|i_d.*)$={left}','--pin-region',f'^(fclk_o|o_v|o_d.*)$={right}','--step-tcl','PRE_CTS=physical/rom_clock/fwd_forwarded_subtree.tcl']
   parent_open=['one native capture and inverter, not historical four-stage waypoint spacing','protection of incoming valid/control and reset/next-hop reservation bound by actual owner','next-hop clock root insertion, capacitance and data receiver load/delay','source-bound floorplan allocation/span<=430.56um']
  else:
   cmd+=['--pin-region',f'^(xf.*|xd.*)$={left}','--pin-region',f'^(co.*|rs.*|xa.*|xb.*|cc.*)$={right}','--pin-region',f'^(ck.*|rst.*|ri.*|st.*)$={left}','--pin-region',f'^(rf.*|rd.*)$={right}']
   parent_open=['unchanged actual source W564 (no W512 credit)','actual128-copy column root load/insertion','writer admission/overrun-fault observation and accepted-debt reset protocol','return70 includes status2+root66+valid/reset; actual receiver clocks/load']
  cmd+=['--nickname-tag',tag,'--purpose','signoff_target','--output',str(run/'physical.json')]
  files=sources+[f'{rel}/{sdc}',f'{rel}/parent_contract.tcl','tools/run_abi3_physical.py','tools/run_abi3_physical_persistent.py']
  rows.append(dict(tag=tag,top=top,source_commit=commit,source_hashes={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in files},argv=cmd,utilization=util,orientation=orient,pin_orientation='explicit variant mapping; corrected die owner must accept, not known placement',launched=False,launch_allowed=False,required_parent_contract_file=f'/src/{rel}/actual_parent_{"single_W2063" if kind.startswith("HBM") else "column_W564"}.tcl: commit actual per-pin delays/corner loads and clock/reset source authority before re-preparing',parent_open=parent_open,source_attributes='Preserve original keep/keep_hierarchy/async_reg and intermediate attributes; missing actual forwarding root fails SDC',corners='SS setup60ps / FF hold25ps with actual per-corner SPEF; include port, clock-to-Q, slew/cap/DRC and receiver context',admission='Kant fresh CPU16 fit before/after unchanged EPYC2 admit.sh; honest inventoried RAM/disk required, no RAM-only waiter',RAM_need_GiB=None,disk_need_GiB=None,new_heavy_job=False))
out=root/'results/physical/hbm_die_abstracts_20261006/links/callers/selected_route_recipes.json'
out.write_text(json.dumps(dict(status='EXACT_SOURCE_RECIPES_PREPARED_PARENT_AND_CPU_HOLD',rows=rows,native_station_implementation_count=1,selected_source_tops=2,independent_208_masters=False,unchanged_component_PASS_reused=True),indent=2)+'\n')
print('Prepared4 exact-source recipes; no synthesis/P&R or admission invoked')
