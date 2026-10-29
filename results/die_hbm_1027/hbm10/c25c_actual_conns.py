"""Replace stale HBM hub core/leaf links with selected-RTL direct links, retaining plan bus/tap links.
Actual graph is emitted by the bind lane's actual_hub_graph.py. No synthetic S-role providers or glue links.
usage: c25c_actual_conns.py PLAN_DIR ACTUAL_GRAPH.json OUT_DIR
This is PARTIAL connectivity until glue traversal/unmapped providers are resolved; not a completeness claim.
"""
import collections,hashlib,json,sys
from pathlib import Path
D,F,O=map(Path,sys.argv[1:4]);O.mkdir(parents=True,exist_ok=True);P=json.load(open(D/'die_plan.json'));G=json.load(open(F));C=json.load(open(D/'core_conns.json'));part={p['name']:p['type'] for p in P['partitions']}
by=collections.defaultdict(dict)
for c in G['cells']:
 if c.get('partition') in part and c.get('plan_instance'):by[part[c['partition']]][c['plan_instance']]=c
report={'status':'PARTIAL: exact selected-RTL direct pin links; missing glue paths and absent source producers stay OPEN','graph_sha256':hashlib.sha256(F.read_bytes()).hexdigest(),'source_plan_sha256':hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'removed_virtual_base_entries':[],'dropped_unverified_links':0,'direct_edge_groups':0,'missing_actual_providers':[],'unsupported_core_ports':[]}
for tn,cells in by.items():
 t=P['partition_types'][tn];hard={c['inst'] for c in t.get('hard_cores',[])};old=C.get(tn,{})
 # Virtual source-base rows otherwise match every __q0/__q1 in check_core_faces via prefix inheritance.
 for ci in list(old):
  if ci not in cells and ci not in hard and any(h.startswith(ci+'__') for h in hard):
   report['removed_virtual_base_entries'].append({'type':tn,'instance':ci,'ports':len(old[ci])});del old[ci]
 for ci in cells:
  ports=old.setdefault(ci,{})
  for port,lst in ports.items():
   kept=[x for x in lst if not x.startswith(('core:','leaf:'))];report['dropped_unverified_links']+=len(lst)-len(kept);ports[port]=kept
 for ci in sorted(hard-set(cells)):
  if '__q' in ci:report['missing_actual_providers'].append({'type':tn,'core':ci})
 C[tn]=old
for e in G['edges']:
 sp,dp=e.get('src_partition'),e.get('dst_partition');src,dst=e.get('src_plan_instance'),e.get('dst_plan_instance')
 if sp!=dp or sp not in part or not src or not dst or src==dst:continue
 tn=part[sp];hard={c['inst'] for c in P['partition_types'][tn].get('hard_cores',[])};cc=C[tn]
 for ci,port,target in ((src,e['src_port'],dst),(dst,e['dst_port'],src)):
  v=('core:' if target in hard else 'leaf:')+target;ls=cc.setdefault(ci,{}).setdefault(port,[])
  if v not in ls:ls.append(v)
 report['direct_edge_groups']+=1
for tn,cells in by.items():
 for ci in cells:
  for port,ls in C[tn].get(ci,{}).items():
   if not ls:report['unsupported_core_ports'].append({'type':tn,'instance':ci,'port':port})
(O/'core_conns.json').write_text(json.dumps(C,indent=1)+'\n');(O/'actual_core_conns_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in report.items()},indent=1))
