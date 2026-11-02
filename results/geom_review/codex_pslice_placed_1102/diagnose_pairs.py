from pathlib import Path
import importlib.util,json,subprocess,collections,math,hashlib
r=Path(__file__).resolve().parent;p=r/'out';tool=r/'input/geom_rules.py'
s=importlib.util.spec_from_file_location('canonical_geom',tool);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
D=m.Design(str(p/'geom.tsv'),[str(r/'input/ot_sram_1r1w_128x256_m1_r2c2_tt.lib')],True)
pairs=[];summary=m.r2r_metrics(D,pairs);assert summary['r2r_captures_gt405']==3150
line=next(x for x in (r/'input/macro_reg_guide.tcl').read_text().splitlines() if x.startswith('set ::ot_mrg_spec '))
tcl=line+'\nforeach {name prefixes x0 y0 x1 y1} $::ot_mrg_spec {puts [join [concat [list $name $x0 $y0 $x1 $y1] $prefixes] "\\t"]}\n'
raw=subprocess.check_output(['tclsh'],input=tcl,text=True);guides=[]
for ln in raw.splitlines():
 f=ln.split('\t');assert len(f)>=6;guides.append(dict(name=f[0],box=list(map(float,f[1:5])),prefixes=f[5:]))
assert len(guides)==65
norm=lambda n:n.replace('\\','')
cells={norm(c[6]):c for c in D.cells.values()}
assert len(cells)==len(D.cells),'ambiguous normalized instance name'
def meta(name):
 c=cells[norm(name)];return dict(name=norm(name),kind=c[0],master=c[1],bbox=list(c[2:6]),xy=list(m.ctr(c)))
def guide_for(name):
 n=norm(name);return [g for g in guides if any(n.startswith(x) for x in g['prefixes'])]
def point_in(xy,b):return b[0]<=xy[0]<=b[2] and b[1]<=xy[1]<=b[3]
def box_gap(a,b):return max(a[0]-b[2],b[0]-a[2],0)+max(a[1]-b[3],b[1]-a[3],0)
def min_canonical_macro_bound(g,b):
 cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
 px=max(g[0],min(cx,g[2]));py=max(g[1],min(cy,g[3]))
 return abs(px-cx)+abs(py-cy)+(b[2]-b[0]+b[3]-b[1])/2
def point_bbox_distance(xy,b):return max(b[0]-xy[0],xy[0]-b[2],0)+max(b[1]-xy[1],xy[1]-b[3],0)
def corner_distance(a,b):return max(abs(x-u)+abs(y-v) for x,y in [(a[0],a[1]),(a[0],a[3]),(a[2],a[1]),(a[2],a[3])] for u,v in [(b[0],b[1]),(b[0],b[3]),(b[2],b[1]),(b[2],b[3])])
rows=[]
for q in pairs:
 a,b=meta(q['launch']),meta(q['capture']);gs=[]
 for end in [a,b]:
  if end['kind']=='S':
   for g in guide_for(end['name']):
    other=b if end is a else a
    gs.append(dict(reg=end['name'],guide=g['name'],box=g['box'],final_center_inside=point_in(end['xy'],g['box']),connected_other_kind=other['kind'],connected_other_name=other['name'],guide_to_other_bbox_min_um=box_gap(g['box'],other['bbox']),guide_to_other_bbox_max_um=corner_distance(g['box'],other['bbox']),guide_min_possible_canonical_macro_reach_um=min_canonical_macro_bound(g['box'],other['bbox']) if other['kind']=='M' else None))
 rows.append(dict(distance_um=q['distance_um'],launch=a,capture=b,guide_memberships=gs,endpoint_bbox_min_distance_um=box_gap(a['bbox'],b['bbox']),FF_center_to_macro_bbox_min_um=point_bbox_distance(a['xy'],b['bbox']) if b['kind']=='M' else point_bbox_distance(b['xy'],a['bbox'])))
rows.sort(key=lambda x:x['distance_um'],reverse=True)
ff2m=[x for x in rows if x['launch']['kind']=='S' and x['capture']['kind']=='M'];m2ff=[x for x in rows if x['launch']['kind']=='M' and x['capture']['kind']=='S']
counts=collections.Counter();gstats=collections.defaultdict(lambda:dict(matched_registers=0,final_centers_outside=0))
for n,c in cells.items():
 if c[0]!='S':continue
 for g in guide_for(n):gstats[g['name']]['matched_registers']+=1;gstats[g['name']]['final_centers_outside']+=not point_in(m.ctr(c),g['box'])
for x in rows:
 counts[x['launch']['kind']+'->'+x['capture']['kind']]+=1
 for g in x['guide_memberships']:
  if g['final_center_inside']:counts['long_inside_guide']+=1
  else:counts['long_outside_guide']+=1
  if g['guide_to_other_bbox_min_um']>405:counts['guide_min_reach_itself_gt405']+=1
  if (g.get('guide_min_possible_canonical_macro_reach_um') or 0)>405:counts['guide_best_possible_canonical_reach_still_gt405']+=1
# Actual one-cycle data fanout of the worst write FF, stopping at all sequential endpoints.
worst_name=rows[0]['launch']['name'];sid=next(i for i,c in D.cells.items() if norm(c[6])==worst_name)
seen=set();todo=[sid];connected=set()
while todo:
 cid=todo.pop()
 if cid in seen:continue
 seen.add(cid)
 for ni in D.drives.get(cid,[]):
  for sk in D.nets[ni][2]:
   if sk[0]!='i' or sk[2] or sk[1] not in D.cells:continue
   end=sk[1];kind=D.cells[end][0]
   if kind=='M':connected.add(end)
   elif kind in 'BLK':todo.append(end)
mb=[D.cells[i] for i in connected]
us=[z for c in mb for z in [c[2]+c[3],c[4]+c[5]]];vs=[z for c in mb for z in [c[2]-c[5],c[4]-c[3]]]
fanout=dict(source=worst_name,connected_memory_bodies=[meta(D.cells[i][6]) for i in sorted(connected)],canonical_unrestricted_one_point_minimax_um=max((max(us)-min(us))/2,(max(vs)-min(vs))/2),meaning='whole-body conservative bound, not exact connected port coordinates')
record=dict(scope='EXISTING_EXPORTED_DATA_ONLY_NO_EDA',summary=summary,worst_write_actual_fanout=fanout,guide_count=len(guides),guide_prefix_count=sum(len(x['prefixes']) for x in guides),counts=dict(counts),guide_membership_stats=dict(gstats),top20_memory_to_FF=m2ff[:20],top20_FF_to_memory=ff2m[:20],top20_all=rows[:20],notes=['Distances are canonical typed-memory bbox-bound reach, not routed/SPEF delay.','No native regions persist in savedDPL DB: source explicitly releases temporary GPL guides before detailed placement.','Outside means final position outside intended GPL box, not a claim which resize/DPL operation moved it.','Active macro_reg_guide.tcl is authoritative; companion JSON still has pre-trunk u_c.u_p prefixes.'],input_hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [r/'input/macro_reg_guide.tcl',r/'input/macro_reg_guide_release.tcl',p/'geom.tsv']})
(p/'long_pair_diagnosis.json').write_text(json.dumps(record,indent=2)+'\n');(p/'all_gt405_pairs.json').write_text(json.dumps(rows,indent=1)+'\n');print(json.dumps({'summary':summary,'counts':dict(counts),'guides':len(guides),'top':rows[:1]},indent=2))
