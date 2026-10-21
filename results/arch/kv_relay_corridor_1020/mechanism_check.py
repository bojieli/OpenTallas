import sys,json
from pathlib import Path
sys.path.insert(0,'tools/qwen_kv_die')
import kv_die as K
mode=sys.argv[1]
def event(frame,event,arg):
 d=frame.f_locals;m=d['m'];by=d['by']
 if mode=='pin' and event=='call':
  testm=dict(m,buses=list(m['buses'])+[(f'proof_st_{j}','kv_oneway',31,[('kvs_attn','pvst'),(n,'st')]) for j,n in enumerate(['pvw_0','pvw_1'])]);masters=K.masters(testm,1)
  for name in ['pvw_0','pvw_1']:
   it=by[name]
   for port in ['st']:
    actual=K.pin_xy(it,masters[it.master],port);planned=K._PIN_HINT[name,port]
    assert max(abs(a-b) for a,b in zip(actual,planned))<.1,(name,port,actual,planned)
    print(json.dumps(dict(instance=name,port=port,actual=actual,hint=planned,orientation=it.orient)))
  raise SystemExit(0)
 if mode=='endpoint' and d['bid']=='ks_kvs_attn__attn__tx_payload':
  if event=='exception':raise SystemExit('FAIL '+str(arg[1]))
  if event=='return':
   pt=d['st_']['prev_pt'];far=K.ep_far('d2d_kv','att_tx_payload',pt)
   assert far<=340
   print(json.dumps(dict(actual_endpoint_chain='PASS',stages=d['st_']['k'],last=pt,farthest_view_pin_um=far)))
   raise SystemExit(0)
 return handler
def callback(frame,kind,arg):
 if kind=='call' and frame.f_code.co_name=='chain_' and frame.f_code.co_filename.endswith('kv_die.py'):
  frame.f_trace_lines=False
  return event(frame,kind,arg)
 return None
# Keep handler separate from its event argument.
handler=event
def callback(frame,kind,arg):
 if kind=='call' and frame.f_code.co_name=='chain_' and frame.f_code.co_filename.endswith('kv_die.py'):
  frame.f_trace_lines=False
  handler(frame,kind,arg)
  return handler
 return None
sys.settrace(callback)
K.build(kv_wq_mirror=True,split=True,host_v14=True,host_north=True,host_trees=True,v143=True,reserve_native_astk=True)
raise SystemExit('mechanism not visited')
