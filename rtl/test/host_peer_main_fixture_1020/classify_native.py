"""Diagnostic source-family census; never changes native PASS/FAIL."""
import sys,json,re,collections
from pathlib import Path
report,netlist,out=map(Path,sys.argv[1:]);d=json.loads(report.read_text());s=netlist.read_text();drivers={};cells={}
for m in re.finditer(r'^  (\S+) (\\[^\n]+?|\S+)\s*\(\n(.*?)^  \);',s,re.M|re.S):
 typ,name,body=m.groups();pins=dict(re.findall(r'\.(\w+)\((.*?)\)',body));name=name.lstrip('\\').strip();cells[name]=(typ,pins)
 for q in ['Y','Q','QN']:
  if q in pins:drivers[pins[q].strip()]=(name,typ,pins)
def family(name):
 n=name.lower()
 if 'root__u_coordinator' in n:return 'coordinator'
 if 'root__u_peer_codec' in n:return 'rank_codec'
 if 'root__u_root_mux' in n:return 'root_mux'
 if 'u_rank__u_control__u_packet__u_ctrl' in n:return 'token_control'
 if 'u_rank__u_peer' in n:return 'peer_link'
 if '__ot_' in n:return 'pin_wrapper'
 if n.startswith('_')or n.startswith('\\_'):return 'anonymous'
 return 'top_alias_or_other'
def roots(net):
 stack=[net];seen=set();leaves=set()
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  if n not in drivers:leaves.add(n);continue
  name,typ,pins=drivers[n]
  if typ.startswith('DFF'):leaves.add(name);continue
  for k,v in pins.items():
   if k not in ['Y','Q','QN']:stack.append(v.strip())
 return sorted(leaves)
rows=[];groups={}
for v in d['violations']:
 name=v['driver'].rsplit('/',1)[0];group=family(name);support=[]
 if group=='anonymous':
  typ,pins=cells.get(name,('',{}));n=next((pins[k].strip()for k in ['Y','Q','QN']if k in pins),v['net']);support=roots(n)
  fs=sorted(set(family(x)for x in support)-{'anonymous'})
  group=fs[0]if len(fs)==1 else 'mixed:'+','.join(fs)
 row={k:v[k]for k in ['driver','driver_role','net','loads']};row.update(family=group,support_roots=support);rows.append(row)
 g=groups.setdefault(group,{'offenders':0,'max_loads':0});g['offenders']+=1;g['max_loads']=max(g['max_loads'],v['loads'])
peer=[x for x in d['driver_counts']if '.u_rank__u_peer.'in x['driver']]
constants=collections.Counter(x['port_bit'].split('[')[0]for x in d['constant_output_bits'])
z={'status':d['status'],'roots':d['roots_examined'],'max_loads':d['max_dynamic_loads'],'offenders':len(rows),'families':groups,'peer_link_named_drivers':len(peer),'peer_link_max_loads':max(x['loads']for x in peer),'constant_output_bits':len(d['constant_output_bits']),'constant_output_ports':dict(constants),'role_errors':d['role_errors'],'violations':rows,'scope':'Source support grouping is diagnostic only. Complete native census remains authoritative FAIL; no waivers.'}
out.write_text(json.dumps(z,indent=2)+'\n');print(json.dumps({k:v for k,v in z.items()if k!='violations'},indent=2))
