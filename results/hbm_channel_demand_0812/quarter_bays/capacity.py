import json,math
from pathlib import Path
p=Path(__file__).parent;o=json.load(open(p/'quarter_bay_lower_bound.json'));g=json.load(open(p/'layout.json'));g['tails'][0]['origin_um']=[1581.12,950.4];g['tails'][1]['origin_um']=[1581.12,1209.6]
obs=[]
for obj in g['cores']+g['tails']+g['srams']:
 x,y=obj['origin_um'];w,h=obj['outline_um'];obs.append((x,y,x+w,y+h))
for site in g['clock_sites']:obs.append(tuple(site['island_um']))
for row in o['rows']:
 x,y=row['point_um'];near=[b for b in obs if b[0]<x+50 and b[2]>x-50 and b[1]<y+50 and b[3]>y-50];need=math.ceil(row['distinct_native_ff']/.6);chosen=None
 for ir in range(4,186):
  r=ir*.27;count=0
  for iy in range(math.ceil((y-r-.135)/.27),math.floor((y+r-.135)/.27)+1):
   yy=iy*.27+.135
   for ix in range(math.ceil((x-r-.54)/1.08),math.floor((x+r-.54)/1.08)+1):
    xx=ix*1.08+.54
    if abs(xx-x)+abs(yy-y)+.675>r+1e-8:continue
    b=(xx-.54,yy-.135,xx+.54,yy+.135)
    if b[0]<0 or b[1]<0 or b[2]>1816.992 or b[3]>2347.488:continue
    if any(b[0]<z[2]-1e-8 and b[2]>z[0]+1e-8 and b[1]<z[3]-1e-8 and b[3]>z[1]+1e-8 for z in near):continue
    count+=1
  if count>=need:chosen=dict(radius_um=r,legal_plain_ff_sites=count,required_sites_at60pct=need);break
 row['isolated_row_grid_bay']=chosen
b={tuple(r['point_um']):r for r in o['rows']};m=json.load(open(p/'output_probe_margin.json'));bad={}
for path in m['paths']:
 points=[tuple(path['source_um'])]+[tuple(w['point_um']) for w in path['waypoints']]+[tuple(path['target_um'])]
 for i,(a,z) in enumerate(zip(points,points[1:])):
  if a==z:continue
  ra=b[a]['isolated_row_grid_bay']['radius_um'] if i>0 else 0;rz=b[z]['isolated_row_grid_bay']['radius_um'] if i+1<len(points)-1 else 0;hop=abs(a[0]-z[0])+abs(a[1]-z[1]);short=hop+ra+rz-405
  if short>0:bad[(a,z)]=dict(a=a,b=z,point_hop_um=hop,radius_a_um=ra,radius_b_um=rz,robust_shortfall_um=short)
o['isolated_grid_qualification']='Plain FF 1.08x0.27 rows only; macros and clock islands excluded. Individual bay candidates can overlap other bays and ignore holds/PG/INV/production copies. Capacity is a lower-bound planning diagnostic, no physical acceptance.';o['isolated_grid_robust_shortfalls']=list(bad.values());(p/'quarter_bay_lower_bound.json').write_text(json.dumps(o,indent=1));print('peak',o['rows'][0]['isolated_row_grid_bay'],'bad',len(bad));print(list(bad.values())[:10])
