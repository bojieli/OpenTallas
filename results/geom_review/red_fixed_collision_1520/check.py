import csv,json,math,collections
from pathlib import Path
P=Path(__file__).parent
fixed=list(csv.DictReader((P/'fixed.tsv').open(),delimiter='\t'))
removed=[r for r in fixed if r['type']=='CORE' and r['status']=='FIRM' and r['instance'].startswith('red_ck_')]
keep=[r for r in fixed if r not in removed]
rows=[]
for line in (P/'sites.txt').read_text().splitlines():
 a=line.split()
 if a and a[0]=='ROW': rows.append((float(a[1]),float(a[2]),a[3],int(a[4])))
assert len(removed)==649 and len(keep)==6954
nodes=json.loads((P/'slice.json').read_text())['core_tree']['nodes']
w,h,sw=.648,.270,.054
new=[]
for node in nodes:
 assert node['master']=='BUFx8_ASAP7_75t_R'
 x,y=node['xy_um'];rx,ry,orient,n=min(rows,key=lambda r:abs(r[1]+h/2-y))
 a=(x-w/2-rx)/sw
 k=math.floor(a+.5) if a>=0 else math.ceil(a-.5)
 xx=round(rx+k*sw,6); yy=ry
 new.append(dict(name=node['name'],rect=[xx,yy,round(xx+w,6),round(yy+h,6)],requested=[x,y],orient=orient))
def hits(items,others):
 bins=collections.defaultdict(list);out=[]
 for name,r in others:
  for ix in range(math.floor(r[0]),math.floor(r[2])+1):
   for iy in range(math.floor(r[1]),math.floor(r[3])+1):bins[ix,iy].append((name,r))
 for item in items:
  r=item['rect'];seen=set()
  for ix in range(math.floor(r[0]),math.floor(r[2])+1):
   for iy in range(math.floor(r[1]),math.floor(r[3])+1):
    for name,s in bins[ix,iy]:
     if name in seen or name==item['name']:continue
     seen.add(name)
     if r[0]<s[2]-1e-7 and r[2]>s[0]+1e-7 and r[1]<s[3]-1e-7 and r[3]>s[1]+1e-7:out.append([item['name'],name,r,s])
 return out
locked=hits(new,[(r['instance'],[float(r[k]) for k in ('x0','y0','x1','y1')]) for r in keep])
selfhits=hits(new,[(r['name'],r['rect']) for r in new]);selfhits=[r for r in selfhits if r[0]<r[1]]
bounds=[r for r in new if r['rect'][0]<4.32-1e-7 or r['rect'][1]<4.32-1e-7 or r['rect'][2]>272.16+1e-7 or r['rect'][3]>272.16+1e-7]
result=dict(scope='SNAPPED_CLOCK_BUFFER_BODY_VS_ACTUAL_FIXED_AND_SELF_ONLY',nodes=len(new),removed_old_seed=len(removed),retained_fixed=len(keep),locked_tap_collisions=len(locked),self_collisions=len(selfhits),outside_core=len(bounds),locked_collisions=locked,self_pairs=selfhits,bounds=bounds,source_or_clock_qualification='NOT_ASSERTED',movable_body_legality='REQUIRES_NEW_PLACEMENT')
(P/'collision_review.json').write_text(json.dumps(result,indent=2)+'\n');(P/'snapped_nodes.json').write_text(json.dumps(new)+'\n')
print({k:v for k,v in result.items() if k not in ('locked_collisions','self_pairs','bounds')});print('first collisions',locked[:3],selfhits[:3])
