from pathlib import Path
import json,re,sys,math,hashlib
root=Path(sys.argv[2]) if len(sys.argv)>2 else Path('/srv/opentallas-scratch2/claude/kv-r/pc_delta_hg6')
root.mkdir(parents=True,exist_ok=True)
pf=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/srv/opentallas-scratch2/claude/kv-clk-r2/rows_e9_hg3b/plan_hg5.json')
sys.path.insert(0,'/srv/opentallas-scratch2/claude/rt/current/tools/die_plan')
import schema,landing_place,ft_spread,ft_bit_sites
raw=json.load(open(pf));P=schema.Plan(raw,str(pf));rows={};report={}
boxes=[[483.,246.,552.,514.],[483.,1006.,552.,1274.]]
def overlap(a,b):
 return min(a[2],b[2])>max(a[0],b[0])+1e-8 and min(a[3],b[3])>max(a[1],b[1])+1e-8
def subtract(a,b):
 if not overlap(a,b):return [a]
 x0,y0,x1,y1=a;bx0,by0,bx1,by1=b
 ix0,iy0,ix1,iy1=max(x0,bx0),max(y0,by0),min(x1,bx1),min(y1,by1)
 return [r for r in [[x0,y0,x1,iy0],[x0,iy1,x1,y1],[x0,iy0,ix0,iy1],[ix1,iy0,x1,iy1]] if r[2]-r[0]>1e-6 and r[3]-r[1]>1e-6]
for tn in ['kv3_pc_v1__cl23f6a148','kv3_pc_v1__cl7f648944','kv3_pc_v1__cl4ea58a5c']:
 t=P.types[tn];lp=landing_place.tcl(P,tn)
 groups=[dict(name=m[0],rect=[float(x) for x in m[1:5]],tag=m[5]) for m in re.findall(r'\{(\S+) \{(-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)\} (\S+)\}',lp)]
 protected=[]
 for g in groups:
  if any(overlap(g['rect'],b) for b in boxes):
   r=g['rect'];x=0.216;y=0.27
   h=[round(math.floor((r[0]-x)/.054)*.054,6),round(math.floor((r[1]-y)/.27)*.27,6),round(math.ceil((r[2]+x)/.054)*.054,6),round(math.ceil((r[3]+y)/.27)*.27,6)]
   protected.append(dict(g,hole=h))
 slots,_=ft_spread.spread_type(P,tn,t)
 fs=ft_bit_sites.table(slots);sizes={m[0]:(float(m[1]),float(m[2])) for m in re.findall(r'dict set ff_bit_site_cells \{(\w+)\} \{([\d.]+) ([\d.]+)\}',fs)}
 for m in re.findall(r'dict set ff_bit_sites \{(\w+),\d+,\d+\} \{(-?[\d.]+) (-?[\d.]+)\}',fs):
  if m[0] not in sizes:continue
  x,y=map(float,m[1:]);w,h=sizes[m[0]];r=[x,y,x+w,y+h]
  if any(overlap(r,b) for b in boxes):protected.append(dict(name=m[0],rect=r,tag='FT_FIRM',hole=[x-.216,y-.27,x+w+.216,y+h+.27]))
 rects=boxes
 for h in protected:rects=[r2 for r in rects for r2 in subtract(r,h['hole'])]
 rects=[[round(x,6) for x in r] for r in rects]
 assert not any(overlap(r,g['rect']) for r in rects for g in protected)
 reserve=[x for x in t['clock'].get('reserved_sites_um',[]) if not (x.get('kind')=='channel_keepout' and x.get('ref')=='PC gap density remedy; carved around all generated fixed landing/station bays')]
 assert not any(x.get('kind')=='channel_keepout' for x in reserve), 'unknown channel keepout requires explicit reconciliation'
 # Keep every measured HG5 clock-tree rectangle byte-identical.
 new=[*reserve,*[dict(rect_um=r,kind='channel_keepout',ref='PC gap density remedy; carved around all generated fixed landing/station bays') for r in rects]]
 rows[tn]={'clock.reserved_sites_um':new}
 area=lambda rs:sum((r[2]-r[0])*(r[3]-r[1]) for r in rs)
 report[tn]=dict(original_keepout_area_um2=area(boxes),carved_keepout_area_um2=area(rects),bay_open_area_um2=area(boxes)-area(rects),rectangles=len(rects),mandatory_bays=protected,old_keepout_bay_collisions=len(protected),new_keepout_bay_collisions=0,added_cycles=0,added_cells=0,die_clock_reserved_rows_preserved=len(reserve),rows=rects)
out=dict(lane='KV-PC-DELTA-1115',source_plan_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),rows=rows)
(root/'HG6_PC_carve_only_rows.json').write_text(json.dumps(out,indent=1)+'\n')
(root/'HG6_PC_carve_only_report.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:{x:v[x] for x in ['carved_keepout_area_um2','bay_open_area_um2','rectangles','old_keepout_bay_collisions','new_keepout_bay_collisions']} for k,v in report.items()},indent=1))
