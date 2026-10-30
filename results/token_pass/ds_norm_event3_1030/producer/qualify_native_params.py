import json,re,sys,hashlib
from pathlib import Path
p='/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030';t='/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029';sys.path[:0]=[p+'/code',p+'/code/layer_prog',t+'/tools/s81_dv',t+'/tools/die_plan',t+'/tools']
from layer_prog.emitted_leaf_routes import Wiring,_params
from layer_prog.bound_control import BoundControl
inv=json.load(open('/srv/opentallas-scratch2/claude/codex-s81-inventory-1030/inventory.json'));top=Path(inv['source_top']);text=top.read_text();out=[]
for row in inv['slices']:
 for k in range(5):
  part=row['part'][:-2]+'_L'+str(k)
  hit=re.search(r'^\s*(\w+)(?:\s+#\((.*?)\))?\s+'+re.escape(part)+r'\s*\(',text,re.M)
  if not hit:raise ValueError('actual native leaf part absent '+part)
  file=top.parent/(hit[1]+'.sv');s=file.read_text();w=Wiring(s);atoms={}
  for half in ('a','b'):
   h=re.search(r'^\s*(ot_s81sl_vn_'+half+r')\s+#\((.*?)\)\s+(\w+)\s*\((.*?)^\s*\);',s,re.M|re.S)
   params={key:BoundControl._integer(value)for key,value in _params(h[2]).items()};expect={'LA':6,'LM':5}
   if half=='b':expect['HW_STAGE']=0
   if params!=expect:raise ValueError('actual current VN parameter mismatch '+part+str(params))
   ports=_params(h[4]);atoms[half]=dict(master=h[1],instance=h[3],params=params,ports=ports)
  terminals=set();fields={}
  for port in ('c_v','c_s'):
   source=w.bits(atoms['a']['ports'][port]);target=w.bits(atoms['b']['ports'][port]);terminals={n for n,_ in source}
   if len(source)!=len(target)or any(w.trace(b,terminals)!=(a[0],a[1],0)for a,b in zip(source,target)):
    raise ValueError('actual VN chain boundary differs '+part)
  # The n_go/n_pre, HW and WL inputs must reach both halves identically.
  for port in ('n_go','n_pre','hw_v','hw_j','hw_hf','hw_d','wl_v','wl_i'):
   a=w.bits(atoms['a']['ports'][port]);b=w.bits(atoms['b']['ports'][port])
   if a!=b:raise ValueError('actual VN broadcast wiring differs '+part+'.'+port)
  ng_sources={n for n in w.widths if n.endswith('_driver_n_go_Q')and '_vp_'in n}
  if len(ng_sources)!=1:raise ValueError('one actual VP n_go output register required '+part)
  ng=next(iter(ng_sources))
  if w.trace(w.bits(atoms['a']['ports']['n_go'])[0],ng_sources)!=(ng,0,0):
   raise ValueError('actual extra VP-to-VN n_go stages differ '+part)
  out.append(dict(slice=row['logical_slice'],leaf=k,part=part,native_master=hit[1],native_file=str(file),native_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),a=atoms['a'],b=atoms['b'],vn_chain_extra_edges=0,vp_n_go_to_vn_edges=0,actual_vp_n_go_output=ng))
Path(p+'/producer_params.json').write_text(json.dumps(dict(status='PASS_ACTUAL_NATIVE_80_VN_PARAMS_AND_CHAIN',leaves=out),indent=1)+'\n');print('actual80 VN params/chain PASS')
