import os,sys,types,json,pickle,hashlib
from pathlib import Path
W=Path('/home/ubuntu/ot-scratch/claude/qwen-kvsys/wt-kvs14r-966018b48-dsg4central')
B=Path('/home/ubuntu/ot-scratch/claude/codex-k-die-1021/ctl-height')
sys.path[:0]=[str(B),str(W/'tools/qwen_kv_die'),str(W/'tools'),str(W/'tools/qwen_split')]
for name in ('kv_group_view_pins','kv_static_die','kv_die'):
 mod=types.ModuleType(name);mod.__file__=str(W/'tools/qwen_kv_die'/f'{name}.py');sys.modules[name]=mod
 exec(compile((B/f'{name}.py').read_text(),mod.__file__,'exec'),mod.__dict__)
import kv_group_view_pins as GP,kv_die as K
rec={}
for n in GP.KITS:
 r=GP.load(n);rec[n]={k:v for k,v in r.items() if k!='ports'}
 rec[n]['ports']={p:dict(n=len(ps),x=[min(x for x,y in ps),max(x for x,y in ps)],y=[min(y for x,y in ps),max(y for x,y in ps)]) for p,ps in r['ports'].items()}
m=pickle.load(open('/home/ubuntu/ot-scratch/claude/codex-kv-closure-0037/fail_dsg4central.json.pkl','rb'))
rec['old_plan_actual_reach']=K.pin_reach(m,K.masters(m,1))
(B/'group_pin_proof.json').write_text(json.dumps(rec,indent=2));print('GROUP_PIN_PROOF',len(rec)-1,rec['old_plan_actual_reach']['violations'],rec['old_plan_actual_reach']['worst'][:4])
from types import SimpleNamespace
for master in GP.KITS:
 r=GP.load(master)
 for orient in ('R0','MY','MX','R180'):
  i=SimpleNamespace(name='test_'+master,master=master,x=10,y=20,w=r['w']-.024,h=r['h']-.024,orient=orient)
  ps=GP.points(i,'krsp'); assert len(ps)==1062
  anchor=GP.xy(i,'krsp'); far=GP.far(i.name,'krsp',(0,0))
  assert far==max(abs(x)+abs(y) for x,y in ps)
  assert far>sum(anchor)
  if orient in ('MY','R180'): assert max(x for x,y in ps)<11
  else: assert min(x for x,y in ps)>10+r['w']-1
 i.w-=1
 try:GP.xy(i,'krsp')
 except ValueError:pass
 else:raise AssertionError('wrong actual view frame accepted')
assert GP.load('qkd_kvs_grp_s6c_alias') is None
print('ACTUAL_BIT_ORIENTATION_AND_NEGATIVE_FRAME_PROOF PASS')
