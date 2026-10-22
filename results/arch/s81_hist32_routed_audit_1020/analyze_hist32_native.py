from pathlib import Path
import sys,json,hashlib,re,collections
sys.path.insert(0,'/audit/tools');sys.path.insert(0,'/audit/tools/ref_tile')
import native_census as NC
import textbook_lint as TL
base=Path('/job');out=Path('/audit');raw=json.loads((out/'native_final.json').read_text());physical=json.loads((out/'native_endpoint_dump.json').read_text())
libs=sorted(Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('*RVT_TT*'))
roles,receipts=NC.liberty_roles([str(x) for x in libs]);v=next(base.glob('routes/*/work/orfs/results/asap7/*/base/6_final.v'));mods=TL.parse_verilog(v.read_text());mods={k:v for k,v in mods.items() if k=='ot_s81ph_native_sel_hist_bank' or k not in roles};g,top=TL.flatten(mods,'ot_s81ph_native_sel_hist_bank')
xy={};bxy={};btags={};native_names={}
def norm(s):return s.replace(chr(92),'')
for n in physical['nets']:
 for t in n['iterms']:
  key=norm(t['inst']);old=native_names.setdefault(key,t['inst']);assert old==t['inst'],('native name normalization collision',old,t['inst']);xy[(key,norm(t['pin']))]=(t['x'],t['y'])
 for t in n['bterms']:bxy[norm(t['pin'])]=(t['x'],t['y']);btags[norm(t['pin'])]=n['sig_type']
loads=collections.defaultdict(list);outs={};errors=[]
def pinrole(master,pn):
 r=roles[master]['pins'].get(pn)
 if r is None:raise ValueError('unknown Liberty pin '+master+'/'+pn)
 return r
for ci,(master,name,pins) in enumerate(g.cells):
 if master not in roles:raise ValueError('unknown master '+master)
 oo=[]
 for pn,nets in pins.items():
  r=pinrole(master,pn)
  for net in nets:
   if r['direction']=='input':loads[net].append((ci,pn,r))
   elif r['direction']=='output':oo.append((net,pn,r))
   else:raise ValueError('unsupported role '+master+'/'+pn)
 outs[ci]=oo
portouts=collections.defaultdict(list)
for name,(direction,net) in g.ports.items():
 if direction=='output':portouts[net].append(name)
clock_roots=[(name,net) for name,(direction,net) in g.ports.items() if direction=='input' and btags.get(name)=='CLOCK']
assert clock_roots,'no native ODB CLOCK input root'
clock_nets=set();clock_sinks=set();dummy=[];todo=[net for name,net in clock_roots]
while todo:
 net=todo.pop()
 if net in clock_nets:continue
 clock_nets.add(net)
 assert not portouts[net],'clock drives data output'
 for ci,pn,r in loads[net]:
  master,name,pins=g.cells[ci];role=roles[master]
  if r['clock']:
   assert role['sequential'],('clock sink is not sequential',name,pn)
   clock_sinks.add((name,pn));continue
  assert not role['sequential'],('clock reaches nonclock sequential pin',name,pn)
  allin=[p for p,rr in role['pins'].items() if rr['direction']=='input'];allout=[(p,rr) for p,rr in role['pins'].items() if rr['direction']=='output']
  assert allin==[pn] and len(allout)==1,('non-unary clock consumer',name,allin)
  fun=re.sub(r'[\s()]','',allout[0][1].get('function') or '')
  assert fun in (pn,'!'+pn,'~'+pn,pn+"'"),('unproved clock function',name,fun)
  if not outs[ci]:
   assert (name,pn) in xy,('dummy load missing native physical pin',name,pn)
   dummy.append(dict(instance=name,master=master,input=pn,liberty_function=fun,connected_output_count=0))
  else:todo.extend(n for n,p,rr in outs[ci])
nonclock=[x for x in raw['driver_counts'] if not any(g.net_name[n]==x['net'] for n in clock_nets)]
nonclockmax=max(x['loads'] for x in nonclock);nonclockbad=[x for x in nonclock if x['loads']>32]
starts=[]
for name,(direction,net) in g.ports.items():
 if direction=='input' and net not in clock_nets:
  assert name in bxy,('missing actual input coordinate',name)
  starts.append((name,net,bxy[name]))
for ci,(master,name,pins) in enumerate(g.cells):
 if roles[master]['sequential']:
  for net,pn,r in outs[ci]:
   assert (name,pn) in xy,('missing actual sequential output coordinate',name,pn)
   starts.append((name+'/'+pn,net,xy[(name,pn)]))
pairs=0;worst=None;bad=[];seen_end=set()
def add_end(src,srcxy,end,endxy):
 global pairs,worst
 pairs+=1;dist=abs(srcxy[0]-endxy[0])+abs(srcxy[1]-endxy[1]);row=dict(source=src,endpoint=end,manhattan_um=dist,source_xy_um=srcxy,endpoint_xy_um=endxy)
 if worst is None or dist>worst['manhattan_um']:worst=row
 if dist>405+1e-6:bad.append(row)
for src,first,srcxy in starts:
 seen=set();todo=[first]
 while todo:
  net=todo.pop()
  if net in seen:continue
  seen.add(net)
  assert net not in clock_nets,('data source reaches native clock cone',src)
  for name in portouts[net]:
   assert name in bxy,('missing output coordinate',name)
   add_end(src,srcxy,name,bxy[name]);seen_end.add(('port',name))
  for ci,pn,pr in loads[net]:
   master,name,pins=g.cells[ci];rr=roles[master]
   assert not pr['clock'],('data reaches clock pin',src,name,pn)
   if rr['sequential']:
    assert (name,pn) in xy,('missing actual capture coordinate',name,pn)
    add_end(src,srcxy,name+'/'+pn,xy[(name,pn)]);seen_end.add((name,pn))
   else:
    for dest,op,role in outs[ci]:
     fun=re.sub(r'[\s()]','',role.get('function') or '')
     if fun not in ('0','1',"1'b0","1'b1"):todo.append(dest)
clock_names={g.net_name[x] for x in clock_nets}
r=dict(schema='opentallas.routed_hist32_role_reach.v1',status='PASS' if not nonclockbad and not bad else 'FAIL',native_netlist_sha256=hashlib.sha256(v.read_bytes()).hexdigest(),liberty=receipts,roots_examined=raw['roots_examined'],raw_native_status=raw['status'],raw_native_max=raw['max_dynamic_loads'],raw_violation_count=len(raw['violations']),role_errors=raw.get('role_errors'),clock_classification=dict(basis='native ODB CLOCK input roots plus actual Liberty unary-function traversal to exclusively sequential clock pins or physically present unary dummy loads with no connected outputs',roots=[name for name,net in clock_roots],clock_net_count=len(clock_nets),sequential_clock_pins=len(clock_sinks),dummy_clock_load_count=len(dummy),dummy_clock_loads=dummy,no_data_reset_or_output_consumers=True),nonclock_max_dynamic_loads=nonclockmax,nonclock_violations=nonclockbad,reach=dict(scope='every top input or sequential output, through all combinational cells to every sequential nonclock input or top output; actual final ODB ITerm/BPin coordinates, constants excluded by actual Liberty function; clock cone proved independently',source_count=len(starts),endpoint_pair_count=pairs,unique_endpoints=len(seen_end),max_manhattan_um=worst['manhattan_um'],worst=worst,limit_um=405,violations=bad))
assert not raw.get('role_errors')
(out/'role_reach.json').write_text(json.dumps(r,indent=2)+'\n');print('FINAL_NATIVE_NONCLOCK',nonclockmax,'viol',len(nonclockbad),'clock_dummy',len(dummy),'clock_seq',len(clock_sinks),'ENDPOINT_REACH',worst['manhattan_um'],'pairs',pairs)
sys.exit(0 if r['status']=='PASS' else 1)
