import json,collections,sys
from pathlib import Path
import argparse
ap=argparse.ArgumentParser(description='Audit whole-group native station FF translations through every combinational gate; clock and primary-port reach are separate.')
ap.add_argument('--netlist',type=Path,required=True);ap.add_argument('--instances',type=Path,required=True);ap.add_argument('--pose',type=Path,required=True);ap.add_argument('--module',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--clock-receipt',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
pose=json.loads(args.pose.read_text());j=json.loads(args.netlist.read_text());top=j['modules'][args.module];cells=top['cells'];p={};shifts=pose['group_shifts_um'];sequential=set(json.loads(args.clock_receipt.read_text())['sequential_masters'])
for l in open(args.instances):
 n,m,*v=l.rstrip().split('\t');n=n.replace('\\','');p[n]=list(map(float,v))
ff={n:c for n,c in cells.items() if c['type'] in sequential};origins={};drivers={};targets=[]
for n,c in cells.items():
 ins=[b for pin,bits in c['connections'].items() if c['port_directions'][pin]=='input' and pin not in ('VDD','VSS','VNW','VPW') for b in bits if isinstance(b,int)]
 outs=[b for pin,bits in c['connections'].items() if c['port_directions'][pin]=='output' for b in bits if isinstance(b,int)]
 if n in ff:
  for b in outs:origins[b]=frozenset((n,))
  for pin,bits in c['connections'].items():
   if c['port_directions'][pin]=='input' and pin not in ('CLK','VDD','VSS','VNW','VPW'):
    targets.extend((n,pin,b) for b in bits if isinstance(b,int))
 else:
  for b in outs:
   if b in drivers:raise RuntimeError(('multiple driver',b))
   drivers[b]=ins
visiting=set();cache={}
def cone(bit):
 if bit in origins:return origins[bit]
 if bit in cache:return cache[bit]
 if bit in visiting:raise RuntimeError(('combinational cycle',bit))
 visiting.add(bit);s=set()
 for b in drivers.get(bit,[]):s.update(cone(b))
 visiting.remove(bit);cache[bit]=frozenset(s);return cache[bit]
def bbox(n,moved):
 b=p[n];d=shifts.get(n.split('/')[0],[0,0]) if moved else [0,0]
 return [b[0]+d[0],b[1]+d[1],b[2]+d[0],b[3]+d[1]]
def distance(a,b):return max(abs(x-y)+abs(u-v) for x in (a[0],a[2]) for y in (b[0],b[2]) for u in (a[1],a[3]) for v in (b[1],b[3]))
out={'schema':'opentallas.station_native_pose_cones.v1','basis':'native mapped cells, every combinational gate traversed; sequential input pin/output cell bbox corners; primary-input and clock reach separate','FF_count':len(ff),'limit_um':402.84}
for moved,key in [(False,'baseline'),(True,'candidate')]:
 count=0;bad=0;worst=[];roles=collections.Counter();groupbad=collections.Counter()
 for dst,pin,bit in targets:
  db=bbox(dst,moved)
  for src in cone(bit):
   count+=1;d=distance(bbox(src,moved),db)
   if d>402.84+1e-6:
    bad+=1;roles[pin]+=1;groupbad[(src.split('/')[0],dst.split('/')[0])]+=1;worst.append((round(d,3),src,dst,pin))
  if len(worst)>500:worst=sorted(worst,reverse=True)[:30]
 out[key]={'pairs':count,'overreach':bad,'roles':dict(roles),'worst':sorted(worst,reverse=True)[:30],'group_violations':[[a,b,n] for (a,b),n in groupbad.most_common(30)]}
 print(key,count,bad,flush=True)
(args.out/'native_cones.json').write_text(json.dumps(out,indent=1)+'\n')
agg={}
for dst,pin,bit in targets:
 db=p[dst];gb=dst.split('/')[0] if dst.split('/')[0] in shifts else '@fixed'
 for src in cone(bit):
  ga=src.split('/')[0] if src.split('/')[0] in shifts else '@fixed'
  if ga==gb:continue
  ab=p[src];v=agg.setdefault((ga,gb),[-1e9]*4)
  for i,(sx,sy) in enumerate(((1,1),(1,-1),(-1,1),(-1,-1))):
   d=max(sx*(x-y)+sy*(u-vv) for x in (ab[0],ab[2]) for y in (db[0],db[2]) for u in (ab[1],ab[3]) for vv in (db[1],db[3]));v[i]=max(v[i],d)
(args.out/'group_constraints.json').write_text(json.dumps({'groups':list(shifts),'constraints':[[a,b,v] for (a,b),v in agg.items()]},indent=1)+'\n')
print('group constraints',len(agg),flush=True)
