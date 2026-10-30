import json,math
from pathlib import Path
p=Path(__file__).resolve().parent;d=json.load(open(p/'variant_C.json'));L=d['layout'];by={v['inst'].split('u_bound.u_u_')[-1]:v for v in L};raw=json.load(open(p/'native_children.json'));pin={}
for key in ['vn_u_a','vn_u_b']:
 r=next(r for r in raw['core_rows'] if r['source_interface']['physical_inst'].endswith(key));z=json.load(open(Path('/home/ubuntu/OpenTallas/physical/die_plan/s81')/r['known_parent_placement']['pins_file']));pin[key]={q['name']:(q['x']+by[key]['xy'][0],q['y']+by[key]['xy'][1]) for q in z['pins']}
def md(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def inside(bb,r):return min(bb[2],r[2])>max(bb[0],r[0]) and min(bb[3],r[3])>max(bb[1],r[1])
rows=[]
for name in [f'c_s[{i}]' for i in range(31)]+['c_v']:
 s=pin['vn_u_a'][name];t=pin['vn_u_b'][name];pts=[s,(s[0],1075.056),(861.84,1075.056),(861.84,763.344),(t[0],763.344),t];length=sum(md(a,b) for a,b in zip(pts,pts[1:]));half=length/2;remaining=half
 for a,b in zip(pts,pts[1:]):
  n=md(a,b)
  if remaining<=n:
   frac=remaining/n;st=(a[0]+frac*(b[0]-a[0]),a[1]+frac*(b[1]-a[1]));break
  remaining-=n
 x=round((st[0]-.54)/.054)*.054;y=round((st[1]-.135)/.27)*.27;bb=(x,y,x+1.08,y+.27);hits=[]
 for v in L:
  xx,yy=v['xy'];w,h=v['wh']
  if inside(bb,(xx,yy,xx+w,yy+h)):hits.append(v['inst'])
 rows.append(dict(signal=name,source=s,target=t,path=pts,path_um=length,station_cell_bbox=bb,leg1_est_um=half+md(st,(x+.54,y+.135)),leg2_est_um=half+md(st,(x+.54,y+.135)),body_hits=hits))
coll=[(a['signal'],b['signal']) for i,a in enumerate(rows) for b in rows[i+1:] if inside(a['station_cell_bbox'],b['station_cell_bbox'])]
r=dict(status='ANALYTIC_ONLY_NOT_RTL_OR_ADOPTED',cell='DFFHQNx1_ASAP7_75t_R',cell_wh=[1.08,.27],site_pitch=[.054,.27],rows=rows,station_overlaps=coll,max_path_um=max(r['path_um'] for r in rows),max_leg_est_um=max(r['leg1_est_um'] for r in rows),notes='All32bits require same extra pipeline stage plus modeled alignment/reset. Point route and cell bboxes only; tapcell/PDN, clock, pin access, actual logic timing and DPL not proven.')
(p/'variant_C_relay32.json').write_text(json.dumps(r,indent=2)+'\n');print(r['max_path_um'],r['max_leg_est_um'],coll,[(v['signal'],v['body_hits']) for v in rows if v['body_hits']])
