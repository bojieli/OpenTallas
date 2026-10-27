import json
from pathlib import Path
p=Path(__file__).parent;d=json.load(open(p/'prog_NE2_local110.json'));a=json.load(open(p/'prog_static_proposal.json'));w=json.load(open(p/'prog_Ewrite_cohort.json'))
old={c['name']:c for c in d['cells']};new={c['name']:c for c in a['placements']}
def ctr(b):return((b[0]+b[2])/2,(b[1]+b[3])/2)
def trans(name,pin):
 c=old[name];n=new[name];px,py=ctr(next(z['box'] for z in c['pins'] if z['pin']==pin));x,y,X,Y=c['box'];px-=x;py-=y
 if c['orient'] in ('MY','R180'):px=X-x-px
 if c['orient'] in ('MX','R180'):py=Y-y-py
 if n['orient'] in ('MY','R180'):px=X-x-px
 if n['orient'] in ('MX','R180'):py=Y-y-py
 return(n['box'][0]+px,n['box'][1]+py)
def mhd(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
out=[]
for b in w['cohort']:
 inv,ff=b['chain'];wp=ctr(b['pinbox']);iy=trans(inv['name'],'Y');ia=trans(inv['name'],'A');q=trans(ff['name'],'QN');ck=trans(ff['name'],'CLK')
 out.append(dict(bit=b['bit'],macro_pin=wp,inv_Y=iy,inv_A=ia,ff_QN=q,ff_CLK=ck,write_escape_mhd=mhd(wp,iy),pair_mhd=mhd(ia,q)))
s=dict(transformed_pairs=len(out),max_macro_write_escape_mhd=max(z['write_escape_mhd'] for z in out),max_ff_inv_mhd=max(z['pair_mhd'] for z in out),route_capacity_not_measured=True)
json.dump(dict(summary=s,pairs=out),open(p/'prog_proposed_pin_geometry.json','w'),indent=2);print(s)
