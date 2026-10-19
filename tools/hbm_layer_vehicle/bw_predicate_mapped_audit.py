#!/usr/bin/env python3
"""Transparent native kept-predicate truth, area, state, and all-load audit."""
import hashlib,json,re,sys
from pathlib import Path
base=Path(sys.argv[1]);sys.path.insert(0,str(base/'src/tools'));import textbook_lint as T
p=next((base/'routes/gate/work/orfs/results/asap7').glob('*/base/1_2_yosys.v'))
g,top=T.flatten(T.parse_verilog(p.read_text()),'ot_hbm_svc_pc_ctrl_leaf_cfg_safe_legacy');a=T.build(g,None);clks,_=T.clock_nets(g,a)
errors=[]
def net(name):
 if name not in g.net_id:raise ValueError('missing named source net '+name)
 return g.find(g.net_id[name])
def root(n):
 seen=set();inv=0
 while n not in seen:
  seen.add(n);d=a['driver'].get(n)
  if not d:return n,None,inv
  ci,pin=d
  if ci<0 or a['kind'][ci]!='buf':return n,ci,inv
  typ=g.cells[ci][0];inv^=int(typ.startswith('INV'))
  ins=list(T._in_nets(g,a,ci));assert len(ins)==1;n=ins[0]
 raise ValueError('buffer cycle')
def evaluate(n,env,seen=None):
 if n in env:return env[n]
 if n<=3:
  s=g.net_name[n]
  if s.endswith('0'):return False
  if s.endswith('1'):return True
  raise ValueError('unknown constant '+s)
 seen=set()if seen is None else set(seen)
 if n in seen:raise ValueError('combin cycle')
 seen.add(n);d=a['driver'].get(n)
 if not d or d[0]<0:raise ValueError('unexpected free input '+g.net_name[n])
 ci=d[0];typ,name,pins=g.cells[ci]
 if a['kind'][ci]=='ff':raise ValueError('unexpected state '+name)
 v={k:evaluate(ns[0],env,seen)for k,ns in pins.items()if a['pin_dir'][ci].get(k)=='input'}
 vals=list(v.values());key=typ.split('_')[0]
 if key.startswith('INV'):return not vals[0]
 if key.startswith(('BUF','HB')):return vals[0]
 if key.startswith('NAND'):return not all(vals)
 if key.startswith('NOR'):return not any(vals)
 if key.startswith('AND'):return all(vals)
 if key.startswith('OR'):return any(vals)
 if key.startswith('XNOR'):return sum(vals)%2==0
 if key.startswith('XOR'):return sum(vals)%2==1
 if key.startswith(('AO','OA')):
  inv=key.startswith(('AOI','OAI'));stem=key.replace('AOI','AO').replace('OAI','OA')
  groups=re.findall(r'([A-Z])\d',','.join(v))
  grouped=[];used=set()
  for letter in sorted(set(groups)):
   ns=[k for k in v if re.fullmatch(letter+r'\d',k)];used.update(ns)
   grouped.append(all(v[k]for k in ns)if stem.startswith('AO')else any(v[k]for k in ns))
  grouped += [x for k,x in v.items()if k not in used]
  val=any(grouped)if stem.startswith('AO')else all(grouped)
  return not val if inv else val
 if key.startswith('MAJ'):return sum(vals)>=2
 raise ValueError('unsupported actual cell '+typ+' '+name)
stat=next((base/'routes/gate/work/orfs/reports/asap7').glob('*/base/synth_stat.txt'));areas={}
for l in stat.read_text().splitlines():
 z=l.split()
 if len(z)==5 and z[0].isdigit():
  try:areas[z[4]]=float(z[1])/int(z[0])
  except ValueError:pass
rows=[]
def predicate(name,operands,fn):
 try:
  n=net(name);ops=[net(x)for x in operands];rn,ci,pol=root(n)
  if ci is None or a['kind'][ci]!='comb':raise ValueError('predicate is not a real combinational gate')
  typ,cn,pins=g.cells[ci]
  if typ.startswith(('BUF','INV')):raise ValueError('identity-only predicate')
  truth=[]
  for i in range(1<<len(ops)):
   bits=[bool((i>>j)&1)for j in range(len(ops))];got=evaluate(n,dict(zip(ops,bits)));want=fn(bits)
   truth.append(dict(inputs=[int(v)for v in bits],actual=int(got),expected=int(want)))
   if got!=want:raise ValueError('actual mapped truth mismatch '+str(bits))
  loads=T.bufinv_fanout(g,a,rn,clks)[0]
  if loads>32:raise ValueError('predicate actual loads '+str(loads))
  rows.append(dict(source_net=name,actual_driver=cn,library=typ,pins={k:[g.net_name[q]for q in ns]for k,ns in pins.items()},output_inversions=pol,actual_nonbuffer_loads=loads,library_area_um2_rounded=areas.get(typ),operands=operands,truth=truth))
 except Exception as e:errors.append(name+': '+str(e))
for r in range(18):predicate(f'u_kr_bridge.pop_regions[{r}]',[f'u_kr_bridge.valid_regions[{r}]','kr_rdy'],lambda v:v[0]and v[1])
predicate('u_native.controller.row_grant',['u_native.controller.slot_next','u_native.controller.r_v'],lambda v:v[0]and v[1])
for r in range(4):predicate(f'u_native.controller.REFRESH_BYTE[{r}].clear_byte',[f'u_native.controller.refresh_update_regions[{r}]','u_native.controller.refresh_round_complete'],lambda v:v[0]and v[1])
for b,k in enumerate([3,2,1]):predicate(f'u_native.length_prefix[{b}]',[f'u_native.length[{i}]'for i in range(4)],lambda v,k=k:sum(int(x)<<i for i,x in enumerate(v))<=k if k!=1 else sum(int(x)<<i for i,x in enumerate(v))==1)
# Source wire aliases resolve through buffers/inverters to actual distinct FFs.
families={'u_native.sticky_regions':3,'u_native.unposted_aq':7,'u_native.controller.fault_regions_q':3,'u_native.controller.open':32,'u_native.controller.open_column':32,'u_native.controller.refresh_update_regions':4}
state=[];seen_ff={}
for fam,n in families.items():
 for b in range(n):
  name=f'{fam}[{b}]'
  try:
   rn,ci,pol=root(net(name))
   if ci is None or a['kind'][ci]!='ff':raise ValueError('not a retained FF')
   typ,cn,pins=g.cells[ci]
   if cn in seen_ff:raise ValueError('state aliases another FF '+seen_ff[cn])
   seen_ff[cn]=name;loads=T.bufinv_fanout(g,a,rn,clks)[0]
   if loads>32:raise ValueError('state actual loads '+str(loads))
   state.append(dict(source_net=name,cell=cn,library=typ,pins={k:[g.net_name[q]for q in ns]for k,ns in pins.items()},output_inversions=pol,actual_nonbuffer_loads=loads))
  except Exception as e:errors.append(name+': '+str(e))
for name in ['kr_rdy']:
 rn,ci,pol=root(net(name));loads=T.bufinv_fanout(g,a,rn,clks)[0]
 if loads>32:errors.append(name+' actual port loads '+str(loads))
fan=json.loads((base/'fanout_gt32.json').read_text());sha=hashlib.sha256(p.read_bytes()).hexdigest()
if fan['source_sha256']!=sha:errors.append('global census/netlist SHA mismatch')
critical=[r for r in fan['roots']if not r['reset']]
if critical:errors.append('global nonreset >32 roots '+str(len(critical)))
unique={r['actual_driver']:r for r in rows}
x=dict(schema='opentallas.bw_native_predicate_audit.v1',source_netlist_sha256=sha,pass_gate=not errors,errors=errors,predicates=rows,unique_predicate_gates=len(unique),unique_gate_library_area_um2_rounded=sum(r['library_area_um2_rounded']or 0 for r in unique.values()),area_basis='actual mapped library cells, synth_stat area/count rounded to report precision; not placement area or timing',retained_state=state,global_nonreset_over32=critical)
(base/'predicate_mapped_audit.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k]for k in ['pass_gate','errors','unique_predicate_gates','unique_gate_library_area_um2_rounded']}));raise SystemExit(bool(errors))
