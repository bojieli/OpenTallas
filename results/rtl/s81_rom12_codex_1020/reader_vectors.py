"""Drive actual immutable calendar ROMs/reader from compiler-emitted issuer words."""
import json,sys
from pathlib import Path
D=Path(sys.argv[1]);O=Path(sys.argv[2]);O.mkdir(parents=True,exist_ok=False)
def decode(path):
 a=[int(x,16) for x in path.read_text().split()]
 return [sum(((a[n//8]>>(b*8+n%8))&1)<<b for b in range(72)) for n in range(4096)]
a=decode(D/'pq_calendar_action.viamap.hex');b=decode(D/'pq_calendar_time.viamap.hex');rows=[lo|(hi<<72) for lo,hi in zip(a,b)]
iss={int(t):int(v,16) for t,v in (l.split() for l in (D/'is_d.txt').read_text().splitlines())}
expected={};segments=[]
for t,v in sorted(iss.items()):
 if not (v>>94)&1:continue
 base=(v>>95)&4095;n=(v>>107)&8191
 assert n and base+n<=4096
 seg=rows[base:base+n]
 assert seg[-1]&(1<<72)
 for w in seg:
  T=t+(w>>75)+2
  assert T not in expected
  expected[T]=w&((1<<75)-1)
 segments.append(dict(start=t,base=base,rows=n,end=max(expected)))
end=max(expected)+30;assert end<50000
(O/'issuer.hex').write_text(''.join(f'{iss.get(i,0):040x}\n' for i in range(end+1)))
(O/'expected.hex').write_text(''.join(f'{expected.get(i,0):019x}\n' for i in range(end+1)))
(O/'summary.json').write_text(json.dumps(dict(end=end,segments=segments,events=len(expected)),indent=1)+'\n')
print('READER_VECTORS',D,'segments',len(segments),'events',len(expected),'end',end)
