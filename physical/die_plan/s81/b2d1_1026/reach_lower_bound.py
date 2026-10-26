import json,sys
p=json.load(open(sys.argv[1])); cc=json.load(open(sys.argv[2]))
for tn in sys.argv[3:]:
  t=p['partition_types'][tn]; W,H=t['outline_um']
  bus={b['name']:b for b in t['buses']}
  box={h['inst']:(h['origin_um'][0],h['origin_um'][1],h['origin_um'][0]+h['outline_um'][0],h['origin_um'][1]+h['outline_um'][1]) for h in t['hard_cores']}
  def fpt(b):
    a,c=b['window_um']; m=(a+c)/2
    return {'N':(m,H),'S':(m,0),'E':(W,m),'W':(0,m)}[b['face']]
  def d(pt,bx):
    dx=max(bx[0]-pt[0],0,pt[0]-bx[2]); dy=max(bx[1]-pt[1],0,pt[1]-bx[3]); return dx+dy
  def dbb(a,b):
    return max(b[0]-a[2],a[0]-b[2],0)+max(b[1]-a[3],a[1]-b[3],0)
  rows=set()
  for ci,ports in cc.get(tn,{}).items():
    for port,tg in ports.items():
      for x in tg:
        k,_,n=x.partition(':')
        if k=='bus' and n in bus: rows.add((round(d(fpt(bus[n]),box[ci]),1),f"bus {n} -> {ci}.{port}"))
        elif k=='core' and n in box: rows.add((round(dbb(box[ci],box[n]),1),f"{ci}.{port} <-> {n}"))
  print("==",tn); 
  for r in sorted(rows,reverse=True)[:14]: print("  ",r)
