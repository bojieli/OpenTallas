import csv,json,collections,glob,sys,re,hashlib
from pathlib import Path
sys.path.insert(0,'/audit/tools/ref_tile')
import native_census as C
raw=json.loads(Path('/audit/grt_native_raw.json').read_text())
masters=collections.defaultdict(list)
for row in csv.reader(open('/audit/master_pins.tsv'),delimiter='\t'):masters[row[0]].append(row[1:])
physical={m:rows for m,rows in masters.items() if rows and all(r[0] in ('CORE_SPACER','CORE_WELLTAP') and r[2] in ('POWER','GROUND') for r in rows)}
errors=[];removed=collections.Counter()
for err in raw.get('role_errors',[]):
 hit=re.fullmatch(r'missing Liberty cell (\S+) instance (.+)',err)
 if hit and hit[1] in physical:removed[hit[1]]+=1
 else:errors.append(err)
roles,libs=C.liberty_roles(glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*')+glob.glob('/src/physical/asap7_memory_macros_v2/*/*_tt.lib'))
terms={};loads=collections.defaultdict(list);outputs=collections.defaultdict(list)
for row in csv.reader(open('/audit/terms.tsv'),delimiter='\t'):
 name,net,direction,master,block,x,y=row;inst,pin=name.rsplit('/',1)
 d=dict(name=name,net=net,direction=direction,master=master,inst=inst,pin=pin,block=bool(int(block)))
 terms[name]=d
 if master=='PORT':
  if direction=='OUTPUT':loads[net].append(d)
 elif direction=='INPUT':loads[net].append(d)
 elif direction=='OUTPUT':outputs[inst].append(d)
spec=json.loads(Path('/src/physical/ref_tile/dscoll_lane_e_s6c/spec.json').read_text())
clocks=set(spec.get('clock_ports',[]))|{spec['clock_port']}
# Exact generated-clock contract, already in the route's selected signoff SDC.
sdc=Path('/src/physical/ref_tile/dscoll_lane_e_s6c/signoff.sdc').read_text()
clocks.update(re.findall(r'create_clock -name \S+ -period \S+ \[get_ports (\S+)\]',sdc))
unconnected=collections.defaultdict(set)
for inst,master,pin in csv.reader(open('/audit/unconnected_outputs.tsv'),delimiter='\t'):
 unconnected[inst].add(pin)

forwarded={}
pattern=r'create_generated_clock -name (\S+) -master_clock (\S+) -source \[get_ports (\S+)\] -divide_by 1 \[get_ports (\S+)\]'
for _,_,src,out in re.findall(pattern,sdc):
 if src in clocks:forwarded[out]=src
proof=[]
for clock in sorted(clocks):
 start=terms['PORT/'+clock]['net'];todo=[start];seen=set();ends=[];bad=[];dangling=[]
 while todo:
  net=todo.pop()
  if net in seen:continue
  seen.add(net)
  for d in loads[net]:
   if d['master']=='PORT':
    (ends if forwarded.get(d['pin'])==clock else bad).append(dict(endpoint=d['name'],kind='declared_generated_clock_output'))
    continue
   role=roles.get(d['master'],{});p=role.get('pins',{}).get(d['pin'])
   if not p:bad.append(dict(endpoint=d['name'],kind='missing_role'));continue
   if p['clock'] and (role.get('sequential') or d['block']):
    ends.append(dict(endpoint=d['name'],kind='actual_liberty_clock'));continue
   if role.get('sequential'):
    bad.append(dict(endpoint=d['name'],kind='data_or_reset'));continue
   outs=outputs[d['inst']]
   if not outs:
    op={pin:r for pin,r in role['pins'].items() if r['direction']=='output'}
    ip={pin:r for pin,r in role['pins'].items() if r['direction']=='input'}
    f=re.sub(r'[\s()]','',next(iter(op.values())).get('function') or '') if len(op)==1 else ''
    pin=d['pin']
    if len(ip)==1 and f in (pin,'!'+pin,'~'+pin,pin+"'") and set(op)==unconnected[d['inst']]:
     dangling.append(dict(endpoint=d['name'],master=d['master'],function=f,unconnected_outputs=sorted(op),kind='actual_unconnected_unary_clock_load'))
    else:bad.append(dict(endpoint=d['name'],kind='comb_no_output_not_unary_null_clock_load'))
    continue
   for out in outs:
    if not loads[out['net']]:dangling.append(dict(endpoint=out['name'],net=out['net'],kind='actual_unloaded_clock_branch'))
    else:todo.append(out['net'])
 proof.append(dict(clock=clock,nets=len(seen),clock_endpoints=len(ends),endpoints=ends,bad=bad,dangling=dangling))
validclock={p['clock'] for p in proof if not p['bad'] and p['clock_endpoints']}
other=[v for v in raw.get('violations',[]) if not(v['driver_role']=='input_port' and v['driver'] in validclock)]
counts=[r['loads'] for r in raw.get('driver_counts',[]) if not(r['driver_role']=='input_port' and r['driver'] in validclock)]
result=dict(scope='GRT native classification, raw pre-gate CLI failure retained; no helper waiver',status='PASS' if not errors and not other and all(not p['bad'] for p in proof) else 'FAIL',physical_only_excluded_instances=dict(removed),physical_only_master_complete_mterms={m:physical[m] for m in removed},remaining_role_errors=errors,clock_proofs=proof,forwarded_clock_contract=forwarded,signoff_sdc_sha256=hashlib.sha256(sdc.encode()).hexdigest(),remaining_dynamic_violations=other,max_nonclock_dynamic_loads=max(counts,default=0),actual_liberty=libs)
Path('/audit/classification.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:result[k] for k in ('status','physical_only_excluded_instances','max_nonclock_dynamic_loads')});print('remaining roleerrors',len(errors),'violations',len(other));print([(p['clock'],p['clock_endpoints'],len(p['bad']),len(p['dangling'])) for p in proof])
