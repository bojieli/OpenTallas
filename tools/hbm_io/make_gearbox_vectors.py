from pathlib import Path
import argparse
import random
from gearbox_calendar import calendar
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
c=calendar();rng=random.Random(20261015)
tx=[];rx=[];frames=[]
for r in c['rows']*3:
 if r['tx_frame_due']:
  v=rng.getrandbits(612);frames.append(v);tx.append((1<<612)|v)
 else:tx.append(0)
for r in c['rows']*3:
 if r['rx_frame_due']:rx.append((1<<612)|frames.pop(0))
 else:rx.append(0)
assert not frames
for name,data in [('tx',tx),('rx',rx)]:
 (a.out/(name+'.hex')).write_text(''.join(f'{v:0154x}\n' for v in data))
