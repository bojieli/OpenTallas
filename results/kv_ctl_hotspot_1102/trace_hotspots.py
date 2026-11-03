"""Trace exact source nets behind fixed source-model cut windows; no route/waiver claim."""
import json,gzip,sys,math,collections,re,csv,inspect,os,hashlib
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent;P=O.parent/'kv_ctl_compact233x302_PREP_1102';R=O.parents[1];sys.path.insert(0,str(R/'tools/autopilot'));import geom_rules as G
D=G.Design('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector/geom.tsv',[str(O.parent/'kv_ctl_place_1102/memory_tt.lib')],True);model={c[6]:c for c in json.loads(gzip.decompress((P/'source_cell_model_PREP.json.gz').read_bytes()))};assert {c[6] for c in D.cells.values()}==set(model)
for i,c in list(D.cells.items()):D.cells[i]=tuple(model[c[6]])
D.die=(0.,0.,233.28,302.4);pinmap={p['name']:p for p in json.load(open(P/'candidate_parent_pins_PREP.json'))['pins']}
for p in D.pins:
 if p['name'] in pinmap:p['x'],p['y']=pinmap[p['name']]['x'],pinmap[p['name']]['y']
news={p['name']:p for p in json.load(open(P/'candidate_macro_sites_PREP.json'))};src=(P/'model_source_cuts_PREP.py').read_text();part=src[src.index('import inspect,collections,re,csv,json,gzip,math'):src.index('src=inspect.getsource')];savedO=O;O=P;exec(compile(part,'phase_capacity_definition','exec'));O=savedO
N=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-netpin-reader-0700');native=[json.loads(x) for x in gzip.open(O/'native_nets.jsonl.gz','rt')];assert len(native)==len(D.nets)
for i,(n,g) in enumerate(zip(native,D.nets)):
 assert n['index']==i and g[0]==n['sig']
 assert g[1]==(G.ref(n['drivers'][0]['ref']) if n['drivers'] else None),(i,'driver')
 assert g[2]==[G.ref(s['ref']) for s in n['sinks']],(i,'sinks')
shapes=json.loads(gzip.decompress((O/'native_master_pin_shapes.json.gz').read_bytes()))['masters'];E=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-netpin-master-extra-0720/master_pin_shapes.json')
if E.exists():shapes.update(json.load(open(E))['masters'])
ff={q['name']:q for q in json.loads(gzip.decompress((P/'FF_sites_PREP.json.gz').read_bytes()))};missing=set()
def access_windows(e):
 r=G.ref(e['ref'])
 if r[0]=='p':
  p=D.pin_by_k[r[1]];return [[p['x'],p['y'],p['x'],p['y'],p['layer']]]
 c=D.cells[r[1]];master=c[1]
 if master not in shapes or e['pin'] not in shapes[master]['pins']:missing.add((master,e['pin']));return [[*G.ctr(c),*G.ctr(c),'UNRESOLVED']]
 m=shapes[master];rects=m['pins'][e['pin']]['rectangles'];orient=[ff[e['inst']]['orient']] if e['inst'] in ff else (['R0'] if c[0]=='M' else ['R0','MX']);out=[]
 for o in orient:
  for q in rects:
   x0,y0,x1,y1=[v/1000 for v in q['rect_dbu']]
   if o in ['MX','FS']:y0,y1=m['height_dbu']/1000-y1,m['height_dbu']/1000-y0
   elif o not in ['R0','N']:raise ValueError(('ORIENT',o))
   out.append([c[2]+x0,c[3]+y0,c[2]+x1,c[3]+y1,q['layer']])
 return out
clock_nets=set();clock_cells=set();todo=[n for cid,ins in D.cell_in.items() for n,ck in ins if ck]
while todo:
 ni=todo.pop()
 if ni in clock_nets:continue
 clock_nets.add(ni);dr=D.nets[ni][1]
 if dr and dr[0]=='i' and D.cells[dr[1]][0] in 'BLK':clock_cells.add(dr[1]);todo.extend(n for n,ck in D.cell_in[dr[1]])
allnets=D.nets;boxmap=[]
for i,n in enumerate(allnets):
 D.nets=[n];bs=G._net_boxes(D)
 if bs:boxmap.append((i,bs[0]))
D.nets=allnets
report=json.load(open(P/'source_cut_model_PREP.json'));rows=[]
for direction in ['H','V']:
 met=report['native_phase_PG_prediction'];a0,a1,cut=met['channel_'+direction.lower()+'_at'];nb=math.ceil(302.4 if direction=='H' else 233.28);cap=source_phase_cap(direction,cut,nb);cs=np.concatenate([[0],np.cumsum(cap)]);j,k=int(a0),int(a1);window_cap=float(cs[k]-cs[j]);contributors=[]
 for ni,box in boxmap:
  x0,y0,x1,y1=box;lo_a,hi_a,lo_b,hi_b=(y0,y1,x0,x1) if direction=='H' else(x0,x1,y0,y1)
  if not lo_b<cut<hi_b:continue
  s0=max(0,min(nb-1,int(lo_a)));s1=max(0,min(nb-1,int(hi_a)));total=float(cs[s1+1]-cs[s0]);over=float(cs[min(k,s1+1)]-cs[max(j,s0)]) if min(k,s1+1)>max(j,s0) else 0
  if total<=0 or over<=0:continue
  n=native[ni];eps=n['drivers']+n['sinks'];macro=[e for e in eps if e['inst'] and D.cells[G.ref(e['ref'])[1]][0]=='M'];movable=[e for e in eps if e['inst'] and D.cells[G.ref(e['ref'])[1]][0] in 'BL' and G.ref(e['ref'])[1] not in clock_cells and ni not in clock_nets];fixed=[e for e in eps if e not in movable];aw=[(e,access_windows(e)) for e in eps];allw=[w for _,ws in aw for w in ws];real=[min(w[0] for w in allw),min(w[1] for w in allw),max(w[2] for w in allw),max(w[3] for w in allw)];axis=0 if direction=='H' else 1;real_forced=any(max(w[axis+2] for w in ws)<cut for _,ws in aw) and any(min(w[axis] for w in ws)>cut for _,ws in aw)
  contributors.append(dict(index=ni,name=n['name'],native_id=n['native_id'],clock_network=ni in clock_nets,crossing_share=over/total,model_bbox_um=box,real_pin_envelope_um=real,real_pin_forced_cross_cut=real_forced,macro_ports=[dict(instance=e['inst'],pin=e['pin'],access=ws) for e,ws in aw if e in macro],movable_comb_cells=sorted({e['inst'] for e in movable}),fixed_endpoints=[dict(instance=e['inst'],pin=e['pin']) for e in fixed],all_comb_endpoints=not fixed,endpoint_pin_windows=[dict(instance=e['inst'],pin=e['pin'],access=ws) for e,ws in aw]))
 contributors.sort(key=lambda q:-q['crossing_share']);share=sum(c['crossing_share'] for c in contributors);rows.append(dict(direction=direction,cut_um=cut,window_um=[a0,a1],derated_window_tracks=window_cap,proxy_ratio=share/window_cap,source_nets=len(contributors),crossing_share=share,macro_net_count=sum(bool(c['macro_ports']) for c in contributors),macro_share=sum(c['crossing_share'] for c in contributors if c['macro_ports']),real_pin_not_forced_count=sum(not c['real_pin_forced_cross_cut'] for c in contributors),real_pin_not_forced_share=sum(c['crossing_share'] for c in contributors if not c['real_pin_forced_cross_cut']),all_comb_count=sum(c['all_comb_endpoints'] for c in contributors),all_comb_share=sum(c['crossing_share'] for c in contributors if c['all_comb_endpoints']),no_movable_count=sum(not c['movable_comb_cells'] for c in contributors),no_movable_share=sum(c['crossing_share'] for c in contributors if not c['movable_comb_cells']),unique_movable_comb_cells=len({n for c in contributors for n in c['movable_comb_cells']}),contributors=contributors))
r=dict(status='EXACT_SOURCE_NET_HOTSPOT_TRACE_PREP_NOT_ROUTE',native_nets_joined=len(native),source_net_pin_reader=str(N),missing_real_pin_shapes=sorted(missing),windows=rows,limits=['Movable combinational centers are analytical estimates','Real macro port rectangles are native master geometry transformedR0 into proposed coordinates','PG path capacities are the source-phase prediction; no new native233floorplan or route','This does not waive the normal checker or qualify a route'])
(O/'hotspot_contributors.json.gz').write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));summary={k:v for k,v in r.items() if k!='windows'};summary['windows']=[{k:v for k,v in q.items() if k!='contributors'} for q in rows];(O/'hotspot_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
