#!/usr/bin/env python3
"""Analytical cone replication only. Does not emit/patch RTL or native cells."""
import csv,json,hashlib,collections,math,gzip,io
from pathlib import Path
P=Path(__file__).resolve().parent
def raw(name):
 f=P/name
 return f.read_bytes() if f.exists() else gzip.decompress((P/(name+'.gz')).read_bytes())
cells={x['instance']:x for x in csv.DictReader(io.StringIO(raw('cells.tsv').decode()),delimiter='\t')}
roots=list(csv.DictReader(io.StringIO(raw('all_roots_full.tsv').decode()),delimiter='\t'))
for r in roots:
 r['sinks']=r['examples'].split(',') if r['examples'] else []
 assert len(r['sinks'])==int(r['loads']),r
 r['source']=None if r['kind']=='input' else r['root'].rsplit('/',1)[0]
 if r['source'] is not None: assert r['source'] in cells,r
 for s in r['sinks']:
  if not s.startswith('port:'): assert s.rsplit('/',1)[0] in cells,s
# Existing native unique sink pins are the indivisible units, incl D/RESETN/macro roles.
# Replicating a destination increases all of its input demands, not just its target Q.
n={k:1 for k in cells}
trace=[]
def demand(r,counts):
 return sum(1 if s.startswith('port:') else counts[s.rsplit('/',1)[0]] for s in r['sinks'])
while True:
 nxt=n.copy()
 for r in roots:
  k=r['source']
  if k is not None and cells[k]['kind'] not in ('macro','transparent'):
   nxt[k]=max(nxt[k],math.ceil(demand(r,n)/32))
 trace.append({'iteration':len(trace)+1,'added_cells':sum(v-1 for v in nxt.values()),'changed_cells':sum(nxt[k]!=n[k] for k in n)})
 if nxt==n: break
 n=nxt
 # A structural model that explodes is rejected rather than truncating any roots.
 if sum(n.values())>100*len(n): raise RuntimeError('copy recurrence diverges; decomposition required')
rows=[]; fixed=[]
for r in roots:
 total=demand(r,n);copies=1 if r['source'] is None else n[r['source']]
 rec={k:r[k] for k in ('root','kind','loads','reset_loads','macro_loads')}
 rec.update(total_new_sink_pins=total,copy_count=copies,maximum_balanced_pins=math.ceil(total/copies))
 if rec['maximum_balanced_pins']>32: fixed.append(rec)
 if copies>1: rows.append(rec)
added=collections.Counter();area=collections.Counter();detail=[]
for k,v in n.items():
 if v==1:continue
 c=cells[k];added[c['kind']]+=v-1;area[c['kind']]+=(v-1)*float(c['area_um2'])
 detail.append(dict(c,copies=v,added_cells=v-1,added_area_um2=(v-1)*float(c['area_um2'])))
report={'status':'ANALYTICAL_GRAPH_MODEL_ONLY_NOT_IMPLEMENTATION_OR_BUILD_AUTHORITY','source_commit':'cec6a7abc','native_stage':'original SF6U source1_synth.odb','bound':32,'root_count':len(roots),'cell_count':len(cells),'baseline_unsafe_roots':sum(int(r['loads'])>32 for r in roots),'iterations':trace,'added_cells_by_kind':dict(added),'reference_master_area_delta_by_kind_um2':dict(area),'reference_master_area_delta_total_um2':sum(area.values()),'fixed_input_or_macro_excess':fixed,'model_replica_roots':rows,'cell_copies':detail,'source_proof_status':'HOLD: per-source state/enable/reset/first-use and kept genuine-logic realization must be proved before source build','functional_first_use_and_phase_claim':False,'area_scope':'reference native master cloning cost; excludes polarity distribution, clock/PG/pin/placement changes; not a final upper bound','latency_added_edges_target':0,'source_latency_measured':False,'indexed_storage_cloned':False,'macro_count_unchanged':4,'files_sha256':{f:hashlib.sha256(raw(f)).hexdigest() for f in ('all_roots_full.tsv','cells.tsv','dump_graph.tcl')}}
(P/'fixed_point.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('model_replica_roots','cell_copies','fixed_input_or_macro_excess','files_sha256')},indent=2))
print('FIXED ROLE HOLD',json.dumps(fixed))

# Trace all duplicated Boolean roots through genuine logic to native state/port operands.
byroot={r['root']:r for r in roots}
incoming=collections.defaultdict(set)
for r in roots:
 for sink in r['sinks']:
  if not sink.startswith('port:'): incoming[sink.rsplit('/',1)[0]].add(r['root'])
def leaves(root,seen):
 if root in seen: return {"COMB_CYCLE:"+root}
 r=byroot[root]
 if r['kind']!='comb':return {root}
 out=set()
 for parent in incoming[r['source']]:out.update(leaves(parent,seen|{root}))
 return out
cones=[]
for r in roots:
 if r['kind']=='comb' and n[r['source']]>1:
  cones.append({'root':r['root'],'copies':n[r['source']], 'actual_native_master':cells[r['source']]['master'],'immediate_native_operands':sorted(incoming[r['source']]),'state_port_macro_tie_leaves':sorted(leaves(r['root'],set())),'source_realization_status':'HOLD: identify equation and every live operand, keep genuine logic, verify truth coverage and new native mapped pins'})
(P/'boolean_operands.json').write_text(json.dumps(cones,indent=2)+'\n')
