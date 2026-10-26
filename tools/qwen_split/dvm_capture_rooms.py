#!/usr/bin/env python3
"""Rectangle-only capture room candidates. Never a physical admission receipt."""
import argparse,json,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
c=json.loads(a.candidate.read_text());bodies=c['children']+c['banks']+c['reset_nodes'];W,H=c['outline_um'];w,h,halo=21.6,75.6,5.4
xs={halo,W-w-halo};ys={halo,H-h-halo}
for q in bodies:
 xs.update([q['x']-halo-w,q['x']+q['w']+halo]);ys.update([q['y']-halo-h,q['y']+q['h']+halo])
xs={round(math.ceil(x/.54-1e-8)*.54,6)for x in xs if halo-1e-5<=x<=W-w-halo+1e-5};ys={round(math.ceil(y/.27-1e-8)*.27,6)for y in ys if halo-1e-5<=y<=H-h-halo+1e-5}
legal=[]
for x in sorted(xs):
 for y in sorted(ys):
  if all(x+w+halo<=q['x']+1e-6 or q['x']+q['w']+halo<=x+1e-6 or y+h+halo<=q['y']+1e-6 or q['y']+q['h']+halo<=y+1e-6 for q in bodies):legal.append(dict(x=x,y=y,w=w,h=h,orient='R0',master='qwen_glue_v514',status='RECTANGLE_ONLY_NO_PIN_CLOCK_OR_RESIDUAL_ADMISSION'))
result=dict(schema='opentallas.qwen.dvm-external-capture-room-screen.v1',outline_um=[W,H],existing_explicit_bodies=len(bodies),halo_um=halo,candidate_count=len(legal),candidate_poses=legal,qualification=False,missing=['Logical leaf-to-tile ownership and native full data bit mapping','Actual source-specific pin RC/TT/FF clock phases/hold','Incoming raw1024WD reach and downstream storage/pd reach','Residual2278FF home and its entire incident graph','Complete NK/NL parent source equivalence and actual reset topology','Independent head/station/channel and full die packing'])
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(candidate_count=len(legal),qualified=False)))
