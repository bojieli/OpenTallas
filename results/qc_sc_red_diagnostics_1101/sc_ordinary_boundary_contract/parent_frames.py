from pathlib import Path
import re,json,hashlib,collections
P=Path(__file__).parent
boundary=json.load(open(P/'boundary_clocks.json'))
plan=json.load(open('/srv/opentallas-scratch/claude/codex-qc62-collect-1101/plan_fleet_complete.json'))
types={k:v for k,v in plan['partition_types'].items()if '_sc' in k and k not in ('slw_sc_v3','sle_sc_v3')}
refs=lambda x:set(re.findall(r'\b[A-Za-z_]\w*\b',re.sub(r"\d+'[bhd][0-9a-fx_z]+",'',x)))
rows=[]
for tn,t in types.items():
 files=list((P/'parent_rtl').glob(tn+'.sv'))or list((P/'parent_rtl').glob('*__'+tn+'.sv'))
 assert len(files)==1,(tn,files)
 f=files[0];s=f.read_text();m=re.search(r'\b(qfd_dv_s5_sc2_leaf)\s+u_core\s*\((.*?)\n\s*\);',s,re.S);assert m,tn
 ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[2]));assert ports['ck']=='clk'
 inst=[]
 for line in s.splitlines():
  mi=re.match(r'\s*(\w+)\s+(?:#\(.*?\)\s+)?(\w+)\s*\((.*)\);',line)
  if mi:
   ps=dict(re.findall(r'\.(\w+)\(([^()]*)\)',mi[3]));inst.append({'module':mi[1],'instance':mi[2],'ports':ps})
 drivers={}
 for i in inst:
  for port in ['q','eq']:
   if port in i['ports']:
    for n in refs(i['ports'][port]):drivers.setdefault(n,[]).append(i)
 aliases=dict(re.findall(r'\bwire\s+(\w+)\s*=\s*(\w+)\s*;',s))
 busrows={}
 for bus,expr in ports.items():
  if bus=='ck':continue
  direction=next(x['io']for x in boundary['rows']if x['pin'].split('[')[0]==bus)
  chosen=[];unresolved=[]
  if direction=='INPUT':
   for n in sorted(refs(expr)):
    nn=aliases.get(n,n)
    if nn not in drivers:unresolved.append(n)
    chosen.extend(drivers.get(nn,[]))
  else:
   for i in inst:
    if 'd'in i['ports']and refs(expr)&refs(i['ports']['d']):chosen.append(i)
  unique={i['instance']:i for i in chosen};endpoints=[]
  for i in unique.values():
   ck=i['ports'].get('clk',i['ports'].get('ck'))
   endpoints.append({'instance':i['instance'],'module':i['module'],'clock':ck,'role':'producer'if direction=='INPUT'else'capture','physical_clock_arrival_TT_ps':None,'physical_clock_arrival_FF_ps':None})
  assert endpoints and not unresolved,(tn,bus,unresolved)
  assert all(e['clock']=='clk'for e in endpoints),(tn,bus,endpoints)
  busrows[bus]={'expression':expr,'io':direction,'parent_endpoints':endpoints,'parent_clock_authority':'LOGICAL_CLOCK_CONNECTIVITY_ONLY_NO_CURRENT_NATIVE_ARRIVAL'}
 perbit=[]
 for b in boundary['rows']:
  bus=b['pin'].split('[')[0];d=busrows[bus]
  perbit.append({'pin':b['pin'],'io':b['io'],'standalone_register_instances':[x['instance']for x in b['boundary_registers']],'standalone_clock_root':'ck','standalone_named_family':'clk','parent_expression':d['expression'],'parent_endpoint_instances':[x['instance']for x in d['parent_endpoints']],'parent_logical_clock':'clk','parent_physical_corner_arrivals':None})
 rows.append({'type':tn,'replicas':sum(x['type']==tn for x in plan['partitions']),'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'core_instance':'u_core','core_module':'qfd_dv_s5_sc2_leaf','core_parameter_override':None,'core_clock_expression':ports['ck'],'bus_contracts':busrows,'boundary_pin_join':{'rows':len(perbit),'register_references':sum(len(x['standalone_register_instances'])for x in perbit),'rule':'Join each boundary_clocks row by scalar pin bus name to this type bus_contracts; all mapped endpoints clocked byclk; no unknown rows.'}})
out={'scope':'Exact frozen913/bd55 bound source logical clock interface inventory, no STA/CAD/count or physical adoption','base_types':len(rows),'replicas':sum(r['replicas']for r in rows),'per_type_signal_pins':571,'per_type_unique_standalone_boundary_FFs':572,'all_ordinary_parent_source_and_capture_logical_clocks':['clk'],'measured_parent_corner_authority':None,'rows':rows}
(P/'parent_frames.json').write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items()if k!='rows'})
for r in rows:print(r['type'],len(r['bus_contracts']),r['boundary_pin_join']['register_references'])
