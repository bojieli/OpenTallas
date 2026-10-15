from pathlib import Path
import argparse
import random
from gearbox_calendar import calendar
p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--frame',type=int,default=612);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
c=calendar(frame=a.frame);rng=random.Random(20261015)
tx=[];rx=[];frames=[]
for r in c['rows']*3:
 if r['tx_frame_due']:
  v=rng.getrandbits(a.frame);frames.append(v);tx.append((1<<a.frame)|v)
 else:tx.append(0)
for r in c['rows']*3:
 if r['rx_frame_due']:rx.append((1<<a.frame)|frames.pop(0))
 else:rx.append(0)
assert not frames
for name,data in [('tx',tx),('rx',rx)]:
 (a.out/(name+'.hex')).write_text(''.join(f'{v:0154x}\n' for v in data))
