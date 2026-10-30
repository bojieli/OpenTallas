import sys,json,gzip,collections,functools
from pathlib import Path
B=Path(__file__).parent;sys.path.insert(0,str(B));import geom_rules as G
mode=sys.argv[1]if len(sys.argv)>1 else 'base';D=G.Design(B/'geom.tsv');rows=json.loads((B/'clock_sinks.json').read_text());byid={a['id']:a for a in rows};plans=json.load(gzip.open(B/({'base':'tree_screen_plans.json.gz','balanced':'tree_balanced_proposal.json.gz','packed':'tree_packed_actual_pins.json.gz'}[mode]),'rt'));models=json.load(gzip.open(B/({'base':'tree_screen_full_models.json.gz','balanced':'balanced_full_models.json.gz','packed':'packed_full_models.json.gz'}[mode]),'rt'))
lat={c:{}for c in ('TT','FF')};owner={}
for root,sl in plans.items():
 for c in lat:
  leaves={a['node']:a for a in models[root]['corners'][c]['leaf_means']}
  for l in sl['core_tree']['leaves']:
   v=leaves[l['node']]
   for name in l['sinks']:lat[c][name]=(v['min_ps'],v['max_ps']);owner[name]=root
@functools.lru_cache(None)
def sources(cid):
 c=D.cells[cid]
 if c[0]=='S':return frozenset((cid,))
 if c[0]not in'BLK':return frozenset()
 s=set()
 for n,isclk in D.cell_in.get(cid,[]):
  if isclk:continue
  d=D.nets[n][1]
  if d and d[0]=='i':s.update(sources(d[1]))
 return frozenset(s)
pairs=set()
for dst in byid:
 for n,isclk in D.cell_in.get(dst,[]):
  if isclk:continue
  d=D.nets[n][1]
  if d and d[0]=='i':pairs.update((src,dst)for src in sources(d[1])if src in byid)
classes=collections.Counter();worst={};records={}
for src,dst in pairs:
 a,b=byid[src],byid[dst];oa,ob=owner[a['name']],owner[b['name']]
 if a['root']=='clk'and b['root']=='clk':kind='RCLK_same_entry'if oa==ob else'RCLK_cross_entry'
 elif a['root']==b['root']:kind='same_FCLK'
 else:kind='different_clock_family'
 classes[kind]+=1
 if kind=='different_clock_family':continue
 for c in lat:
  x,y=lat[c][a['name']],lat[c][b['name']];v=max(abs(x[0]-y[1]),abs(x[1]-y[0]));key=kind+'/'+c
  if v>worst.get(key,-1):worst[key]=v;records[key]=dict(src=a['name'],dst=b['name'],src_entry=oa,dst_entry=ob,source_span_ps=x,capture_span_ps=y)
report=dict(scope='Conservative leaf-span related-clock screen from actual data/reset graph; equal-zero input phase assumption; no actual die/forwarded-source timing price',geometry_mode=mode,pairs=len(pairs),classes=classes,worst_ps=worst,worst_pairs=records,excluded='Different FCLK/RCLK owners need actual forwarded source phase, LCA/CPPR and latency receipts; not priced with equal-source fiction',build_qualified=False)
(B/({'base':'related_clock_screen.json','balanced':'balanced_related_clock_screen.json','packed':'packed_related_clock_screen.json'}[mode])).write_text(json.dumps(report,indent=1));print(json.dumps({k:v for k,v in report.items()if k!='worst_pairs'},indent=1))
