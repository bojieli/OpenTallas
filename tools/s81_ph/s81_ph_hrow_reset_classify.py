#!/usr/bin/env python3
"""Trace actual mapped reset cones, stopping at sequential inputs; no driver inference."""
import argparse,collections,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/arch/s81_hrow_native_placement_1013/reset_classification'
def blocks(s,kind):
 pattern=re.compile(r'\b'+kind+r'\s*\(\s*([^)]*)\)\s*\{')
 for m in pattern.finditer(s):
  depth=1;i=m.end();quoted=False;escaped=False
  while depth and i<len(s):
   c=s[i]
   if c=='"' and not escaped:quoted=not quoted
   if not quoted:depth+=(c=='{')-(c=='}')
   escaped=(c=='\\' and not escaped);i+=1
  yield m.group(1).strip().strip('"'),s[m.end():i-1],s[m.start():i]
def prop(s,n):
 m=re.search(r'\b'+n+r'\s*:\s*([^;]+);',s);return m.group(1).strip().strip('"') if m else None
def uses(expr,pin):return expr is not None and bool(re.search(r'(?<![\w])'+re.escape(pin)+r'(?![\w])',expr))
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
 global OUT
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=OUT);ap.add_argument('--inputs',type=Path);a=ap.parse_args();OUT=a.out.resolve();INPUTS=a.inputs.resolve() if a.inputs else OUT
 def available(name):return OUT/name if (OUT/name).exists() else INPUTS/name
 libraries={};evidence={};raw={};paths={}
 for corner in ['SS','FF']:
  cells={};provenance=[]
  for file in sorted(INPUTS.glob('*_RVT_'+corner+'.lib.gz')):
   text=gzip.open(file,'rt').read();provenance.append(ref(file))
   for name,body,full in blocks(text,'cell'):
    ps={n:{'direction':prop(b,'direction'),'function':prop(b,'function'),'clock':prop(b,'clock'),'arcs':[{'timing_type':prop(a,'timing_type'),'related_pin':prop(a,'related_pin'),'when':prop(a,'when'),'body':a} for _,a,_ in blocks(b,'timing')]} for n,b,_ in list(blocks(body,'pin'))+list(blocks(body,'bus'))}
    ff=list(blocks(body,'ff'))+list(blocks(body,'latch'));seq={p:prop(ff[0][1],p) for p in ['clear','preset','next_state','clocked_on','enable']} if ff else None
    cells[name]={'pins':ps,'sequential':seq};raw[(corner,name)]=(file,full)
  libraries[corner]=cells;evidence[corner]=provenance
 candidate=json.load(open(ROOT/'results/arch/s81_hrow_native_placement_1013/candidate.json'));masters={};used=set()
 netlist_files={p.name.removesuffix('.gz'):p for base in [INPUTS,OUT] for p in list(base.glob('*_6_final.v'))+list(base.glob('*_6_final.v.gz'))}
 for file in sorted(netlist_files.values()):
  master=file.name.removesuffix('.gz').removesuffix('_6_final.v');reset='rst' if master in ['dsfd_die_rstsync','dsfd_mtp_hrow_cbe','dsfd_mtp_hrow_cbw'] else 'rn';text=gzip.open(file,'rt').read() if file.suffix=='.gz' else file.read_text();cells={};fans=collections.defaultdict(list);aliases=collections.defaultdict(list)
  for cm in re.finditer(r'^\s*(\w+)\s+(\\\S+|[\w$]+)\s+\((.*?)\);',text,re.M|re.S):
   typ,name,body=cm.groups()
   if typ=='module':continue
   if not re.search(r'\.\w+\s*\(',body):continue
   if typ not in libraries['SS']:raise ValueError('Missing actual cell Liberty '+typ)
   con={p:n.strip() for p,n in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)};cells[name]={'type':typ,'connections':con}
   for p,n in con.items():
    if libraries['SS'][typ]['pins'][p]['direction']=='input':fans[n].append((name,p))
  for a,b in re.findall(r'\bassign\s+([^=;]+)=\s*([^;]+);',text):
   a=a.strip();b=b.strip();aliases[a].append(b);aliases[b].append(a)
  pending=collections.deque([(reset,[])]);visited=set();endpoints=[];arcs=[]
  while pending:
   net,path=pending.popleft()
   if net in visited:continue
   visited.add(net)
   for other in aliases[net]:pending.append((other,path+[{'assign_alias':[net,other]}]));arcs.append({'assign_alias':[net,other]})
   for instance,pin in fans[net]:
    z=cells[instance];typ=z['type'];cell=libraries['SS'][typ];seq=cell['sequential'];step={'instance':instance,'cell_type':typ,'input_pin':pin,'input_net':net};used.add(typ)
    if seq:
     role='asynchronous_clear_preset' if uses(seq['clear'],pin) or uses(seq['preset'],pin) else 'synchronous_data_control' if uses(seq['next_state'],pin) else 'clock_or_other_sequential_control'
     constraint_types={c:sorted({a['timing_type'] for a in libraries[c][typ]['pins'][pin]['arcs']}) for c in ['SS','FF']}
     endpoints.append(dict(**step,classification=role,sequential_semantics=seq,clock_connections={p:n for p,n in z['connections'].items() if libraries['SS'][typ]['pins'][p]['clock']=='true'},constraint_types=constraint_types,reset_path_witness=path+[step]));arcs.append(dict(**step,sequential_stop=role));continue
    for output,definition in cell['pins'].items():
     if definition['direction']=='output' and uses(definition['function'],pin):
      n=z['connections'].get(output)
      if n is None:continue
      branch=dict(**step,output_pin=output,output_net=n,function=definition['function']);arcs.append(branch);pending.append((n,path+[branch]))
  drivers=collections.defaultdict(list)
  for instance,z in cells.items():
   for pin,net in z['connections'].items():
    if libraries['SS'][z['type']]['pins'][pin]['direction']=='output':drivers[net].append((instance,pin))
  async_pins=[]
  for instance,z in cells.items():
   cell=libraries['SS'][z['type']];seq=cell['sequential']
   if not seq:continue
   for pin,net in z['connections'].items():
    if not (uses(seq['clear'],pin) or uses(seq['preset'],pin)):continue
    queue=collections.deque([net]);seen=set();cone=[];roots=[]
    while queue:
     wire=queue.popleft()
     if wire in seen:continue
     seen.add(wire)
     for alias in aliases[wire]:queue.append(alias);cone.append({'assign_alias':[wire,alias]})
     if not drivers[wire] and not aliases[wire]:roots.append({'input_or_constant_net':wire})
     for launch,output in drivers[wire]:
      l=cells[launch];definition=libraries['SS'][l['type']];used.add(l['type']);function=definition['pins'][output]['function'];step={'driver_instance':launch,'cell_type':l['type'],'output_pin':output,'output_net':wire,'function':function}
      if definition['sequential']:
       roots.append(dict(**step,producer_kind='actual_mapped_sequential_output',clock_connections={p:n for p,n in l['connections'].items() if definition['pins'][p]['clock']=='true'}));continue
      inputs=[p for p,v in definition['pins'].items() if v['direction']=='input' and uses(function,p)]
      if not inputs:roots.append(dict(**step,producer_kind='actual_mapped_constant_or_no_dependency_output'));continue
      for inp in inputs:
       cone.append(dict(**step,input_pin=inp,input_net=l['connections'][inp]));queue.append(l['connections'][inp])
    async_pins.append({'instance':instance,'cell_type':z['type'],'pin':pin,'net':net,'sequential_semantics':seq,'constraint_types':{c:sorted({a['timing_type'] for a in libraries[c][z['type']]['pins'][pin]['arcs']}) for c in ['SS','FF']},'actual_local_producers':roots,'all_backward_cone_arcs':cone})
  instances=[n for n,z in candidate['instances'].items() if z['master']==master]
  masters[master]={'final_netlist':ref(file),'final_netlist_uncompressed_sha256':hashlib.sha256(text.encode()).hexdigest(),'final_netlist_provenance':json.load(open(OUT/'netlist_provenance.json'))[master],'reset_port':reset,'physical_instance_names':instances,'all_reachable_cone_arcs':arcs,'sequential_endpoints':endpoints,'all_actual_async_sequential_pins':async_pins,'endpoint_class_counts':dict(collections.Counter(e['classification'] for e in endpoints)),'coverage':'Complete combinational reset cone to first sequential pin, including aliases; every reached arc retained and one witness per endpoint. No traversal through clocked state inferred.'}
 subset=[]
 for c in ['SS','FF']:
  # Keep source license and exact cells. Full original templates remain available by source hash; this is cell-definition evidence, not a standalone timing library.
  header=gzip.open(INPUTS/('SEQ_RVT_'+c+'.lib.gz'),'rt').read().split('library (')[0];pieces=[]
  for name in sorted(used):
   file,full=raw[(c,name)];pieces.append({'cell_type':name,'source_library':ref(file),'cell_definition_sha256':hashlib.sha256(full.encode()).hexdigest()});subset.append((c,name,full))
  path=OUT/('actual_reset_cells_'+c+'.lib.gz')
  with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as f:f.write((header+'\n\n'.join(full for cc,name,full in subset if cc==c)).encode())
  paths[c]={'cell_definition_evidence':ref(path),'source_libraries':pieces,'scope':'Exact mapped cell definitions, original templates/units by source library hash. Not standalone load interpolation input.'}
 for master,z in masters.items():
  reports={};active=[p for p in z['all_actual_async_sequential_pins'] if p['pin']=='RESETN']
  for c in ['ss','ff']:
   path=available(master+'_reset_'+c+'.rpt');checks=[]
   for part in path.read_text().split('Startpoint:')[1:]:
    endpoint=re.search(r'Endpoint:\s*(.*?)\s*\((recovery|removal) check',part)
    slack=re.search(r'([-\d.]+)\s+slack \((MET|VIOLATED)\)',part)
    if endpoint and slack:checks.append({'startpoint':part.splitlines()[0].strip(),'endpoint':endpoint[1].strip(),'check_type':endpoint[2],'slack_ps':float(slack[1]),'result':slack[2]})
   missing=[{'instance':p['instance'],'pin':p['pin'],'check_type':check} for p in active for check in ['recovery','removal'] if not any(x['endpoint']==p['instance'].lstrip('\\') and x['check_type']==check for x in checks)]
   reports[c]={'report':ref(path),'log':ref(available(master+'_reset_'+c+'.log')),'checks':checks,'missing_active_async_endpoint_checks':missing,'worst_slack_ps':min(x['slack_ps'] for x in checks)}
   assert not missing,(master,c,missing)
  z['routed_recovery_removal']=reports
  z['active_resetn_endpoint_count']=len(active)
  z['tied_setn_count']=sum(p['pin']=='SETN' and all(r.get('function')=='1' for r in p['actual_local_producers']) for p in z['all_actual_async_sequential_pins'])
  z['qualification_scope']='Explicit recovery/removal paths from original CLOSED routed ODB/SPEF and its export constraints, every active RESETN endpoint SS/FF. Leaf interface/local conditioner checks only; no production external source clock/reset delivery inferred.'
 retained={}
 for master in ['dsfd_mtp_hrow_ing','dsfd_mtp_hrow_hub']:
  path=available(master+'_6_finish.rpt');text=path.read_text();checks=[]
  for part in text.split('Startpoint:')[1:]:
   endpoint=re.search(r'Endpoint:\s*(.*?)\s*\((recovery|removal) check',part,re.S)
   if not endpoint:continue
   mapped=re.findall(r'(\S+)/RESETN \(DFFASRHQNx1_ASAP7_75t_R\)',part)
   checks.append({'startpoint':part.splitlines()[0].strip(),'endpoint':endpoint[1].strip(),'check_type':endpoint[2],'explicit_mapped_reset_pins':mapped,'path_group':'asynchronous' if 'Path Group: asynchronous' in part else None,'reported_clock':'core_clk' if 'clock core_clk' in part else None})
  retained[master]={'retained_finish_report':ref(path),'actual_reported_reset_paths':checks,'status':'PARTIAL actual mapped RESETN report evidence. Final netlist/ODB purged; complete rst cone and all-sink coverage OPEN. Reported leaf core_clk does not establish production source identity.'}
 d={'schema':'opentallas.native_hrow_mapped_reset_classification.v1','status':'Partial actual mapped coverage; source clock/reset ABI still OPEN','masters':masters,'actual_cell_liberty_evidence':paths,'missing_closed_final_netlists':['dsfd_mtp_hrow_ing','dsfd_mtp_hrow_hub'],'missing_large_final_netlists':[m for m in ['dsfd_hrow_r1025','dsfd_hrow_r2079'] if m not in masters],'retained_ing_hub_partial_report_evidence':retained,'actual_library_provenance':ref(available('actual_liberty_provenance.json')),'producer_binding':None,'production_clock_delivery':None}
 (OUT/'mapped_reset_classification.json').write_text(json.dumps(d,indent=1)+'\n');print(json.dumps({m:d['endpoint_class_counts'] for m,d in masters.items()}))
if __name__=='__main__':main()
