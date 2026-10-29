#!/usr/bin/env python3
"""Compare actual clock-buffer bodies/masters, clock-net graph and CLK sink identities.
Uses the canonical compact geom_dump.tsv: only S/M clock-pin inputs seed the walk.
ICG enable/data cones are never traversed. Sink body geometry is reported separately
(data placement may change it); compact dumps do not encode cell orientation.
"""
import argparse,hashlib,importlib.util,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('old',type=Path);ap.add_argument('new',type=Path);ap.add_argument('--rules',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
spec=importlib.util.spec_from_file_location('geom_rules',a.rules);G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
def capture(path):
 D=G.Design(str(path));pending=[];cells={};sinks=[];sink_bodies={};seen=set();edges=[];ambiguous=[]
 for cid,c in D.cells.items():
  if c[0] not in ('S','M'):continue
  for n,clock in D.cell_in.get(cid,[]):
   if clock:pending.append(n);sinks.append(c[-1]);sink_bodies[c[-1]]=list(c[1:-1])
 def name(ref):return D.cells[ref[1]][-1] if ref[0]=='i' else D.pin_by_k[ref[1]]['name']
 while pending:
  n=pending.pop()
  if n in seen:continue
  seen.add(n);sig,driver,loads=D.nets[n]
  if driver is None:continue
  for load in loads:edges.append((name(driver),name(load),load[2] if load[0]=='i' else False))
  if driver[0]=='i' and D.kind(driver[1]) in ('B','K'):
   c=D.cells[driver[1]];cells[c[-1]]=list(c[1:-1]);ins=D.cell_in.get(driver[1],[]);clock_ins=[nn for nn,clock in ins if clock]
   if clock_ins:pending.extend(clock_ins)
   elif len(ins)==1:pending.append(ins[0][0])
   else:ambiguous.append(dict(cell=c[-1],inputs=len(ins),kind=c[0]))
 return dict(cells=cells,edges=sorted(edges),sinks=sorted(sinks),sink_bodies=sink_bodies,ambiguous=ambiguous)
x,y=capture(a.old),capture(a.new)
sha=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
changes=lambda x,y:[dict(name=k,old=x.get(k),new=y.get(k)) for k in sorted(set(x)|set(y)) if x.get(k)!=y.get(k)]
r=dict(old=str(a.old),new=str(a.new),clock_cells_before=len(x['cells']),clock_cells_after=len(y['cells']),clock_cell_geometry_identical=x['cells']==y['cells'],clock_graph_identical=x['edges']==y['edges'],clock_sink_identities_identical=x['sinks']==y['sinks'],changed_clock_cells=changes(x['cells'],y['cells']),clock_geometry_sha_before=sha(x['cells']),clock_geometry_sha_after=sha(y['cells']),clock_graph_sha_before=sha(x['edges']),clock_graph_sha_after=sha(y['edges']),ambiguous_clock_input_roles_old=x['ambiguous'],ambiguous_clock_input_roles_new=y['ambiguous'],sink_body_geometry_identical_info=x['sink_bodies']==y['sink_bodies'],changed_sink_bodies_info=changes(x['sink_bodies'],y['sink_bodies']),scope='No data-enable cones or sequential owners included as clock buffers. Actual compact dump cell master+bbox coordinates; sequential/macro sink identity and body-position information recorded independently.')
a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if not k.startswith('changed_')},indent=2))
