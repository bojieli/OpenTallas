"""Actual sequential incidence selects the small public FF envelope; PREP, no placement."""
import json,re,sys,collections
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];sys.path.insert(0,str(R/'tools/autopilot'));import geom_rules as G
D=G.Design('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector/geom.tsv',[str(O.parent/'kv_ctl_place_1102/memory_tt.lib')],True)
anchors=collections.defaultdict(list)
for p in D.pins:
 if p['name'] in ('rst_n','por_n') or p['sig'] in ('POWER','GROUND','CLOCK') or G.CLOCK_PIN_RE.search(p['name']) or re.search(G.STRAP_RE_DEFAULT,p['name']):continue
 n=D.pin_net.get(p['k']);todo=[n] if n is not None else [];seen=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  if p['io']=='OUTPUT':
   dr=D.nets[n][1]
   if not dr or dr[0]!='i':continue
   cid=dr[1];kind=D.kind(cid)
   if kind=='S':anchors[D.cells[cid][6]].append(p['name'])
   elif kind=='B':todo.extend(nn for nn,clk in D.cell_in.get(cid,[]) if not clk)
  else:
   for s in D.nets[n][2]:
    if s[0]!='i' or s[2]:continue
    kind=D.kind(s[1])
    if kind=='S':anchors[D.cells[s[1]][6]].append(p['name'])
    elif kind=='B':todo.extend(D.drives.get(s[1],[]))
public=set(anchors);macros={c[6] for c in D.cells.values() if c[0]=='M'};names={c[6]:i for i,c in D.cells.items()};seq={i for i,c in D.cells.items() if c[0] in 'SM'};selected=set();pp=0;pm=0;public_edges=0
def captures(cid):
 todo=list(D.drives.get(cid,[]));seen=set();out=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  for sink in D.nets[n][2]:
   if sink[0]!='i' or sink[2]:continue
   if sink[1] in seq:out.add(D.cells[sink[1]][6])
   else:todo.extend(D.drives.get(sink[1],[]))
 return out
for a in public:
 out=captures(names[a]);public_edges+=len(out)
 hits=out&public
 if hits:pp+=len(hits);selected.add(a)
 hits=out&macros
 if hits:pm+=len(hits);selected.add(a)
for a in macros:
 hits=captures(names[a])&public;pm+=len(hits);selected.update(hits)
selected_pins=sorted({p for n in selected for p in anchors[n]})
candidate={p['name']:p for p in json.load(open(O/'candidate_parent_pins_PREP.json'))['pins']};radius=130.;cx=116.64;cy=151.2
sites=json.load(open(O/'candidate_macro_sites_PREP.json'))
def clip(poly,a,b,c):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  ep=a*p[0]+b*p[1]-c;eq=a*q[0]+b*q[1]-c
  if ep<=1e-8:out.append(p)
  if (ep<0 and eq>0) or (ep>0 and eq<0):
   t=ep/(ep-eq);out.append([p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])])
 return out
def area(poly):return abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(poly,poly[1:]+poly[:1])))/2 if poly else 0
regions=[]
for name in sorted(selected):
 c=D.cells[names[name]];cw,ch=c[4]-c[2],c[5]-c[3];x0,x1=4.32+cw/2,233.28-4.32-cw/2;y0,y1=4.32+ch/2,302.4-4.32-ch/2;poly=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
 for x,y,r in [(cx,cy,radius)]+[(candidate[n]['x'],candidate[n]['y'],150.) for n in anchors[name]]:
  for a,b in [(1,1),(1,-1),(-1,1),(-1,-1)]:
   if poly:poly=clip(poly,a,b,r+a*x+b*y)
 assert poly,name
 remaining=area(poly)
 for m in sites:
  cut=poly
  for a,b,k in [(1,0,m['x']+m['width']+4.32+cw/2),(-1,0,-m['x']+4.32+cw/2),(0,1,m['y']+m['height']+4.32+ch/2),(0,-1,-m['y']+4.32+ch/2)]:
   if cut:cut=clip(cut,a,b,k)
  remaining-=area(cut)
 assert remaining>0,(name,remaining)
 regions.append(dict(FF=name,pins=anchors[name],feasible_polygon=poly,macrofree_model_area_um2=remaining))
(O/'centered_public_regions_PREP.json').write_text(json.dumps(regions,indent=1)+'\n')
report=dict(status='SOURCE_ENVELOPE_PREP_NOT_LEGALIZED',source_public_launch_incidence_edges=public_edges,public_capture_FFs=len(public),public_capture_pin_edges=sum(map(len,anchors.values())),public_to_public_edges=pp,public_macro_edges=pm,centered_public_FFs=len(selected),centered_public_pins=len(selected_pins),public_p90_far_budget=684,center_radius_um=radius,all_actual_sequential_edges_bound_um=radius+267.84,selected_regions_nonempty=len(regions),minimum_macrofree_model_region_area_um2=min(r['macrofree_model_area_um2'] for r in regions),within_far_pin_count_budget=len(selected_pins)<=684,centered_public=[dict(FF=n,pins=anchors[n]) for n in sorted(selected)],selected_pins=selected_pins,proposal='All nonpublic FFs and selected public FFs in local center L1radius130; all other public FFs within30um of candidate pin. Any FF in the233.28x302.4 rectangle has radius<=267.84, so mixed bound397.84; public-public edges each have their launch selected; all public-macro incident FFs selected. Macro corners radius<=199.176, so mixed core/macro bound329.176. Native-site density/PG feasibility not yet solved.')
(O/'FF_envelope_PREP.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['centered_public','selected_pins']},indent=2))
