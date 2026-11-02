#!/usr/bin/env python3
"""Read-only observer: gate POST window from actual firstcal/boot, never change traffic."""
import argparse,json,re,time
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('run',type=Path);ap.add_argument('--watch',action='store_true');a=ap.parse_args();run=a.run;state={'status':'AWAIT_DATES','post_cycles':290867,'core_minus_far_cycles':282,'observation_cycles':290307,'token_period_cycles':293376,'host_job_completion':'OPEN_ROOT0_ABSENT'};offset=0
while True:
 p=run/'sim.log'
 if p.exists():
  with p.open() as f:
   f.seek(offset)
   for line in iter(f.readline,''):
    if 'HOSTTOK_WAIT ready_wait 1' in line:state['readywait']=True
    m=re.search(r'DIE_SVC_READY cyc (\d+)',line)
    if m:state['status_ready_core']=int(m[1])
    m=re.search(r'HOSTTOK_SENT cyc (\d+)',line)
    if m:state['hosttok_sent_core']=int(m[1])
    m=re.search(r'FAR_CAL cyc (\d+) cal_start seg \d+ layer 0\b',line)
    if m:state.setdefault('firstcal_far',int(m[1]))
    if line.startswith('KVSLICE_BOOT '):
     m=re.search(r' cyc (\d+)\s*$',line)
     if m:state['endboot_core']=int(m[1]);state['boot_pass']=line.startswith('KVSLICE_BOOT PASS')
    m=re.search(r'HOST_CLASS_CREDITS returned_frames (\d+) disabled (\d+)',line)
    if m:state['returned_class_frames']=int(m[1]);state['class_credit_disabled']=int(m[2])
   offset=f.tell()
 if 'firstcal_far' in state and 'endboot_core' in state:
  end=state['endboot_core']+state['post_cycles']-state['core_minus_far_cycles'];first=state['firstcal_far'];low=first+state['observation_cycles'];second=first+state['token_period_cycles']
  state.update(end_far=end,required_end_far=low,second_auto_far=second,window_valid=low<=end<second,status='VALID_WINDOW' if low<=end<second else 'INVALID_WINDOW')
 run.mkdir(parents=True,exist_ok=True);(run/'observation_window.json').write_text(json.dumps(state,indent=2)+'\n')
 if (run/'exit').exists():break
 if not a.watch:break
 time.sleep(10)
print(json.dumps(state))
