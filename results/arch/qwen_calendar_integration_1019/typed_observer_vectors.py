import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--composition',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
events=[int(e['cmd'],16) for e in json.loads(a.composition.read_bytes())['events'] if (int(e['cmd'],16)>>1)&7==1]
assert len(events)==114
with a.out.open('w') as f:
 for stage in range(1,37):
  for user in range(4):
   for c in events:
    pc=((c>>4)&511)+128*user;assert pc<512
    rc=(c&~(511<<4))|(pc<<4)
    f.write(f'{user} {rc:029x}\n')
print('TYPED_SOURCE_VECTORS',len(events)*144)
