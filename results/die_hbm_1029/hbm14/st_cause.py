import json,sys,re,collections
p=json.load(open(sys.argv[1])); H=4.32
for tn in ['q_hub_nw','q_hub_ne']:
  t=p['partition_types'][tn]; R=[]
  for c in t['hard_cores']:
    (x,y),(w,h)=c['origin_um'],c['outline_um']; R.append((c['inst'],x-H,y-H,x+w+H,y+h+H))
  last=collections.Counter(); ends=collections.Counter(); ex=None
  for s in t['internal_stations']:
    hit=[r for r in s.get('regs_um',[]) if any(a<r[0]<c and b<r[1]<d for (_,a,b,c,d) in R)]
    if not hit: continue
    tags=[x.strip().split(' ')[0] for x in s.get('note','').split('|')]
    last[tags[-1][:25]]+=len(hit)
    # is the violated core one of the endpoints?
    a,_,b=s['conn'].partition('|'); ea=a.split('.')[0]; eb=b.split('.')[0]
    own=sum(1 for r in hit if any(nm in (ea,eb) and a1<r[0]<c and b1<r[1]<d for (nm,a1,b1,c,d) in R))
    ends['endpoint core']+=own; ends['third core']+=len(hit)-own
    if ex is None and len(hit)>2: ex=(s['conn'],s.get('note')[:300],hit[:3])
  print(tn,'last tag',last.most_common(6)); print('  ',dict(ends)); print('  ex',ex)
