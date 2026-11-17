"""C4 analytical producer floorplan candidate; no source activation or physical qualification."""
import argparse, json, math, hashlib
from pathlib import Path

def overlap(a,b):
 return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def candidates(w,h,obstacles):
 for ix in range(2,116):
  for iy in range(2,154):
   x,y=ix*10.8,iy*10.8;r=(x,y,x+w,y+h)
   if r[2]<=1257.12 and r[3]<=1654.56 and not any(overlap(r,o) for o in obstacles):yield r

def worst(a,b):
 return max(abs(x-u)+abs(y-v) for x in [a[0],a[2]] for y in [a[1],a[3]] for u in [b[0],b[2]] for v in [b[1],b[3]])
def run(plan_path,toolroot,inventory_path,out,macro_lef):
 import sys,itertools,re
 sys.path.insert(0,str(toolroot));import schema as S,gen_phys as G
 raw=json.loads(plan_path.read_text());t=raw['partition_types']['kv3_hub_Wi'];P=S.Plan(raw,path=str(plan_path))
 assert t['outline_um']==[1278.72,1676.16]
 obstacles=[]
 for c in t['hard_cores']:
  x,y=c['origin_um'];w,h=c['outline_um'];obstacles.append((x-10.8,y-10.8,x+w+10.8,y+h+10.8,'core:'+c['inst']))
 for c in t['clock']['reserved_sites_um']:
  a,b,c,d=c['rect_um'];obstacles.append((a-2.16,b-2.16,c+2.16,d+2.16,'clock'))
 for f in t['ft_slots']:
  for i,st in enumerate(f.get('bit_sites_um',[])):
   xs=[p[0] for p in st];ys=[p[1] for p in st]
   obstacles.append((min(xs)-2.16,min(ys)-2.16,max(xs)+2.16,max(ys)+2.16,f['name']+':'+str(i)))
 lef=macro_lef.read_text();size=re.search(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',lef);assert size
 mw,mh=map(float,size.groups());assert [mw,mh]==[171.288,77.784]
 symmetry=re.search(r'\bSYMMETRY\s+([^;]+);',lef).group(1).split();shapes=[(mw+21.6,mh+21.6,'R0')]
 if 'R90' in symmetry:shapes.append((mh+21.6,mw+21.6,'R90'))
 macro=[(r,o) for w,h,o in shapes for r in candidates(w,h,obstacles)]
 logic=list(candidates(86.4,86.4,obstacles));best=None
 for (a,ao),(b,bo) in itertools.combinations(macro,2):
  if overlap(a,b):continue
  aa=(a[0]+10.8,a[1]+10.8,a[2]-10.8,a[3]-10.8);bb=(b[0]+10.8,b[1]+10.8,b[2]-10.8,b[3]-10.8)
  for l in logic:
   if overlap(a,l) or overlap(b,l):continue
   w=max(worst(aa,l),worst(bb,l));cost=w+.05*(abs((l[0]+l[2])/2-1278)+abs((l[1]+l[3])/2-921))
   row=(cost,w,a,ao,b,bo,l)
   if best is None or row<best:best=row
 assert best is not None
 _,reach,a,ao,b,bo,l=best;inv=json.loads(inventory_path.read_text())
 pins=G.type_pins(P,'kv3_hub_Wi');groups={}
 for bus,bit,layer,x,y,face in pins:
  if bus not in ['i_kvs_ctl_o_emb','i_kvs_hroot_EN_o_emb','i_kvs_hroot_ES_o_emb','i_kvs_hroot_WN_o_emb','i_kvs_hroot_WS_o_emb','o_kvs_emb_rowtx__emb_tx_payload','o_kvs_emb_rowtx__emb_tx_v','o_kvs_emb_px_tok','o_kvs_emb_px_tep','L2416_o']:continue
  d=max(abs(x-u)+abs(y-v) for u in [l[0],l[2]] for v in [l[1],l[3]])
  g=groups.setdefault(bus,dict(bits=0,worst_direct_um=0,face=face));g['bits']+=1;g['worst_direct_um']=max(g['worst_direct_um'],d)
 for g in groups.values():
  g['required_segments_at_380um']=math.ceil(g['worst_direct_um']/380)
  g['existing_usable_register_edges']=None
  g['new_relay_cycles']=None
 ff=inv['rows']['context']['FF'];cellarea=inv['rows']['context']['mapped_cell_area_um2'];branches=[]
 for i in range(6):
  branches.append(dict(name='ctx_clk_'+str(i),xy_um=[l[0]+14.4+28.8*(i%3),l[1]+21.6+43.2*(i//3)],FF_sinks=ff//6+(i<ff%6),estimated_uniform_TT_CLK_load_fF=inv['rows']['context']['FF_CLK_cap_fF']/6,qualified=False))
 result=dict(schema='opentallas.qwen-kv-context-placement-candidate.v1',status='GEOMETRY_FIT_ONLY_NOT_BUILD_READY',selected=False,
 source_plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),partition='hub_Wi',partition_type='kv3_hub_Wi',frame='local type um',
 macro_LEF_sha256=hashlib.sha256(macro_lef.read_bytes()).hexdigest(),macro_LEF_symmetry=symmetry,macro_orientation_verified=True,PDN_continuity_qualified=False,global_PG_layer_qualified=False,exact_macro_master='ot_sram_1r1w_64x512_m1_r2c2',macro_LEF_outline_um=[171.288,77.784],macro_halo_um=10.8,
 macros=[dict(inst=n,orientation=o,halo_rect_um=r,body_rect_um=[r[0]+10.8,r[1]+10.8,r[2]-10.8,r[3]-10.8]) for n,r,o in [('u_context.g_rope.u_rowtx.u_row',a,ao),('u_context.g_rope.u_rowtx.u_rope',b,bo)]],
 logic_region_um=l,mapped_logic_area_um2=cellarea,logic_util=cellarea/(86.4**2),mapped_FF=ff,
 tested_obstacles=dict(hard_cores=len(t['hard_cores']),clock_rects=len(t['clock']['reserved_sites_um']),ft_station_envelopes=len(obstacles)-len(t['hard_cores'])-len(t['clock']['reserved_sites_um'])),
 macro_to_logic_all_corners_Manhattan_max_um=reach,internal_geometry_required_additional_cycles=0 if reach<=405 else None,
 internal_route_required_additional_cycles=None,external_endpoint_relay_budget=groups,proposed_clock_branches=branches,
 macro_clock_load_fF_each=9.3458,
 fixed_boundary_lane='L2416',fixed_boundary_cycles=2,
 timing_claim=False,route_claim=False,exactness_claim=False,
 open_requirements=['Trace each actual mapped D/Q net through existing input-delay/join registers before assigning added cycles; boundary distance alone must not become an added-cycle claim.',
 'Place named register banks and route around clock/tree/FT obstacles; direct Manhattan fit is not a routed reach proof.',
 'Real context99 HOST source path originates inside hard-host hierarchy and needs exact source-pin tracing, not a partition-edge assumption.',
 'Proposed six clock branches and two macro clock sinks must be composed into the exact selected tree and recut rows.',
 'Qualify full component with adjusted dates if any new relay edge is introduced; no old-calendar reuse.'])
 out.mkdir(parents=True,exist_ok=False);(out/'placement.json').write_text(json.dumps(result,indent=1)+'\n')
 # Standalone review SVG: source data and all planned objects, no hidden geometry.
 shapes=[]
 for x,y,z,w,label in obstacles:shapes.append(f'<rect x="{x}" y="{1676.16-w}" width="{z-x}" height="{w-y}" fill="'+('#ddd' if label.startswith('core:') else '#aaa' if label=='clock' else '#e5a')+'" opacity="0.65"/>')
 for r,col in [(a,'#35a'),(b,'#35a'),(l,'#0a6')]:shapes.append(f'<rect x="{r[0]}" y="{1676.16-r[3]}" width="{r[2]-r[0]}" height="{r[3]-r[1]}" fill="{col}" opacity="0.7"/>')
 (out/'placement.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1278.72 1676.16"><rect width="1278.72" height="1676.16" fill="white"/>'+''.join(shapes)+'</svg>')
 print(json.dumps(dict(status=result['status'],internal_max=reach,logic_util=result['logic_util'],macros=result['macros'],output=str(out))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--toolroot',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--macro-lef',type=Path,required=True);a=p.parse_args();run(a.plan,a.toolroot,a.inventory,a.out,a.macro_lef)
