"""Reserve measured predecessor normal buffer footprint; insert no cells."""
import json,gzip,csv,sys,collections
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];sys.path.insert(0,str(R/'tools/autopilot'));import geom_rules as G
C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector');D=G.Design(str(C/'geom.tsv'));names={c[6]:i for i,c in D.cells.items()};pk={p['name']:p['k'] for p in D.pins};native=[json.loads(x) for x in gzip.open(O/'native_nets.jsonl.gz','rt')];hot=json.loads(gzip.decompress((O/'hotspot_contributors.json.gz').read_bytes()));dims={}
for q in csv.DictReader(open(C/'placed.csv')):
 if q['master'].startswith(('BUF','HB')):dims[q['master']]=(float(q['w']),float(q['h']))
allbuf={i for i,c in D.cells.items() if c[1].startswith(('BUF','HB'))};selected=set();per_net=[];unknown=[]
for ni in sorted({c['index'] for w in hot['windows'] for c in w['contributors'] if c['movable_comb_cells'] and not c['clock_network']}):
 n=native[ni]
 if len(n['drivers'])!=1:unknown.append(dict(index=ni,name=n['name'],reason='not single driver'));continue
 e=n['drivers'][0]
 if e['inst'] is None:
  if e['pin'] not in pk:unknown.append(dict(index=ni,name=n['name'],reason='predecessor BTerm absent'));continue
  initial=[D.pin_net[pk[e['pin']]]]
 elif e['inst'] in names and D.cells[names[e['inst']]][0]!='M':
  initial=D.drives.get(names[e['inst']],[])
  if len(initial)!=1:unknown.append(dict(index=ni,name=n['name'],reason='predecessor output-net binding not unique'));continue
 else:unknown.append(dict(index=ni,name=n['name'],reason='macro output or absent predecessor driver; not aliased'));continue
 todo=list(initial);seen=set();found=set()
 while todo:
  nn=todo.pop()
  if nn in seen:continue
  seen.add(nn)
  for sk in D.nets[nn][2]:
   if sk[0]=='i' and sk[1] in allbuf:found.add(sk[1]);todo.extend(D.drives.get(sk[1],[]))
 selected.update(found);per_net.append(dict(index=ni,name=n['name'],driver_instance=e['inst'],driver_pin=e['pin'],measured_buffers=[D.cells[i][6] for i in sorted(found)]))
counts=collections.Counter(D.cells[i][1] for i in selected);area=sum(dims[k][0]*dims[k][1]*v for k,v in counts.items());total=collections.Counter(D.cells[i][1] for i in allbuf)
r=dict(status='SPACE_RESERVE_ONLY_NO_NEW_BUFFERS_OR_NEW_POSTPLACE_CLAIM',predecessor_native_geometry=str(C/'geom.tsv'),source_net_cohort=len(per_net),unpriced_bindings=unknown,selected_measured_buffers=len(selected),selected_class_counts=dict(counts),selected_cell_area_um2=area,space_at_genuine_GPL_density_point6_um2=area/.6,all_predecessor_buffer_classes={k:dict(count=v,width_um=dims[k][0],height_um=dims[k][1],area_um2=dims[k][0]*dims[k][1]*v) for k,v in total.items()},buffers_inserted=0,FFs_added=0,cycles_added=0,limits=['Selected footprint is measured from genuine prior same-source normal port/repair BUF trees, not invented count','New geometry may require different repair classes/counts; ordinary actual PLACE/repair must measure them','No BUF tree is copied, forced or treated as a new physical result; this only reserves room'],per_source_net=per_net)
(O/'measured_buffer_space.json.gz').write_bytes(gzip.compress(json.dumps(r,separators=(',',':')).encode(),mtime=0));(O/'measured_buffer_space_summary.json').write_text(json.dumps({k:v for k,v in r.items() if k!='per_source_net'},indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['per_source_net','all_predecessor_buffer_classes','unpriced_bindings']},indent=2));print('UNPRICED_BINDINGS',len(unknown))
