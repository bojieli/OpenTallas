from pathlib import Path
import re,json
for t in ['io_cor','hroot']:
 root=Path('/srv/opentallas-scratch2/claude/kv5-i2'); kit=root/'gen2'/('kv3_'+t)
 places=(root/'probe'/t/'place.tsv').read_text().splitlines(); groups={}
 for l in places:
  a=l.split()
  if len(a)<5 or a[0]!='I' or not a[1].startswith('DFF'):continue
  m=re.search(r'u_ft_(ft\d+)_o_(\d+)/q(?:\\?\[(\d+)\\?\])?\$',a[4])
  if m:groups.setdefault((m[1],int(m[3] or 0)),{})[int(m[2])]=(float(a[2]),float(a[3]))
 pins={(p['bus'],int(p['bit'])):(p['x'],p['y']) for p in json.loads((kit/'pins.json').read_text())}
 hops=[];missing=[]
 for (ft,b),stages in groups.items():
  si=sorted(stages)
  ps=[pins.get((ft+'_i',b))]+[stages[s] for s in si]+[pins.get((ft+'_o',b))]
  if None in ps:missing.append((ft,b));continue
  for i,(a,bp) in enumerate(zip(ps,ps[1:])):
   hops.append((abs(a[0]-bp[0])+abs(a[1]-bp[1]),ft,b,i))
 print(t,'bit_chains',len(groups),'hops',len(hops),'missing',len(missing),'max',max(hops),'above405',sum(h[0]>405 for h in hops),'above400',sum(h[0]>400 for h in hops))
