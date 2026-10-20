from pathlib import Path
import sys,json,subprocess,os
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019')
C=Path('/srv/opentallas-scratch/claude/hbm-record23-consumer-trace-1019')
sys.path[:0]=[str(D/'tools'),str(D)]
from hbm_layer_vehicle.layer_images import column_image
from native_su_calendar import compile_calendar
O=Path.cwd()
base=[int(x,16)for x in (C/'hold_and_local/quarter.mem').read_text().split()]
mask=((1<<78)-1)<<128
for shift in [0,1]:
 w=[x&~mask for x in base]+[base[-1]&~mask]*shift
 for i,x in enumerate(base):
  bits=x&mask
  if bits: w[i+shift]|=bits
 out=O/f'drain{shift}';column_image(w,out)
 cw=[(x&~(((1<<180)-1)<<500))&~(((1<<234)-1)<<206) for x in w]
 c,m=compile_calendar(cw,first_serial=2675,bridge_serial=2675,bridge_stream=3567,host_launch=3500,rows=160,request_lane_edges_by_bank=[4,5,0,0,0,0,0,0],write_lane_edges_by_bank=[3,3,0,0,0,0,0,0])
 (O/'calendar.mem').write_text(''.join(f'{x:064x}\n'for x in c));(out/'calendar_model.json').write_text(json.dumps(m,indent=2))
 W=len((out/'cols/config.mem').read_text().split())
 with (out/'replay.log').open('w')as f:
  r=subprocess.run([str(C/'observe'),f'+CFG={out}/cols/config.mem',f'+GOLD={out}/quarter.mem',f'+N={len(w)}',f'+W={W}'],stdout=f,stderr=subprocess.STDOUT)
 (out/'exit.txt').write_text(str(r.returncode))
 print('REPLAY',shift,r.returncode,flush=True)
