#!/usr/bin/env python3
"""Admitted single-element measurement -> route -> real export. No job timeout."""
import argparse,os,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--resume-orfs',type=Path);p.add_argument('--NO',type=int,required=True);p.add_argument('--orientation',choices=['H','V'],required=True);p.add_argument('--util',type=int,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--run',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[4];rel='physical/hbm_die_abstracts_20261006/links/station_physical_20261006'
run=a.run.resolve();run.mkdir(parents=True,exist_ok=True)
name=f'ot_hbm_station_NO{a.NO}_{a.orientation}{a.util}'
ev=json.loads((a.cache.parent/'physical.json').read_text());assert ev['flow_completed'] and ev['design']['parameters']['NO']==a.NO
load_dir=a.cache.parent/'measured_receiver_sta_r3'
if not load_dir.exists():
 subprocess.run(['python3',f'{rel}/measure_receiver.py','--mapped',str(a.cache/'mapped.v'),'--out',str(load_dir),'--src',str(root)],cwd=root,check=True)
assert (load_dir/'receiver.json').is_file(), 'incomplete measurement retained; use a fresh correction run'
sdc=run/'source_local.sdc'
subprocess.run(['python3',f'{rel}/make_component_sdc.py','--loads',str(load_dir),'--NO',str(a.NO),'--out',str(sdc)],cwd=root,check=True)
# This config names an actual source-local envelope. It deliberately does not
# set receiver_bound=true or invoke the absent actual-die authority template.
cmd=['python3',f'{rel}/run_owned.py','--reuse-synthesis-dir',str(a.cache),'--persistent-workdir',str(run/'work'),'--launch-receipt',str(run/'launch.json'),'--view','asap7','--top',name]
for entry in ev['design']['sources']:cmd+=['--source',entry['path']]
cmd+=['--source',f'{rel}/{name}.sv','--param','ENABLE=1','--param',f'NO={a.NO}','--clock-port','clk_sm','--clock-period-ns','0.833333333','--clock-uncertainty-ns','0.06','--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC','--hold-margin-ns','0.01','--core-utilization',str(a.util),'--place-density',str((a.util+5)/100),'--stages','synth,pnr','--keep-heavy-artifacts','--orfs-var','NUM_CORES=16','--orfs-var','ADDER_MAP_FILE=','--orfs-var','PLACE_PINS_ARGS=-min_distance 1 -min_distance_in_tracks','--orfs-var','IO_PLACER_H=M4 M6','--orfs-var','IO_PLACER_V=M5 M7','--orfs-var',f'CORE_ASPECT_RATIO={0.25 if a.orientation=="H" else 4}','--orfs-var','SDC_FILE=/work/source_local.sdc','--step-tcl','PRE_CTS=physical/rom_clock/fwd_forwarded_subtree.tcl','--purpose','signoff_target','--nickname-tag',f'Gauss_NO{a.NO}_{a.orientation}{a.util}','--output',str(run/'physical.json')]
left,right=('left','right') if a.orientation=='H' else ('bottom','top')
cmd+=['--pin-region',f'^(clk_sm|por_n|in_.*|release_.*)$={left}','--pin-region',f'^(fclk_o|out_.*|ACK_.*)$={right}']
# Exact mapped hook creates /work/source_local.sdc before ORFS reads config.
env=os.environ.copy();env['GAUSS_SOURCE_LOCAL_SDC']=str(sdc);env['OT_ORFS_NUM_CORES']='16';env['OPENTALLAS_ORFS_IMAGE']='openroad/orfs:asap7lock'
if a.resume_orfs:env['GAUSS_RESUME_ORFS']=str(a.resume_orfs.resolve())
with (run/'argv.json').open('w') as f:json.dump(dict(argv=cmd,NO=a.NO,orientation=a.orientation,util=a.util,source_local=True,parent_closed=False),f,indent=2)
r=subprocess.run(cmd,cwd=root,env=env)
(run/'route_exit.json').write_text(json.dumps(dict(returncode=r.returncode))+'\n')
phy=json.loads((run/'physical.json').read_text()) if (run/'physical.json').exists() else {}
if not phy.get('flow_completed'):raise SystemExit('real route failed before terminal geometry; source/logs retained')
bases=list((run/'work/orfs/results/asap7').glob('*/base'))
assert len(bases)==1
subprocess.run(['python3',f'{rel}/export_station.py','--base',str(bases[0]),'--out',str(run/'views'),'--name',name,'--NO',str(a.NO),'--physical',str(run/'physical.json')],cwd=root,env=env,check=True)
print('ACTUAL_STATION_ROUTE_AND_EXPORT_TERMINAL',name)
