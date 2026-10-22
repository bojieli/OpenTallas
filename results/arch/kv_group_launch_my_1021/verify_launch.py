import os,sys,json,types,hashlib
from pathlib import Path
W=Path('/home/ubuntu/ot-scratch/claude/qwen-kvsys/wt-kvs14r-052ce32dc-dsg5viewpins')
B=Path('/home/ubuntu/ot-scratch/claude/codex-k-die-1021/dsg-launch-verify')
sys.path[:0]=[str(W/'tools/qwen_kv_die'),str(W/'tools'),str(W/'tools/qwen_split')]
for n in ('kv_group_view_pins','kv_die'):
 mod=types.ModuleType(n);mod.__file__=str(W/'tools/qwen_kv_die'/f'{n}.py');sys.modules[n]=mod
 exec(compile((B/f'{n}.py').read_text(),mod.__file__,'exec'),mod.__dict__)
import kv_die as K
orig=K._relays
last={}
def wrap(m):
 last['m']=m
 return orig(m)
K._relays=wrap
try:
 m=K.build(kv_wq_mirror=True,split=True,reserve_native_astk=True,host_v14=os.environ.get('OT_KV_HOST_V14')=='1',host_north=os.environ.get('OT_KV_HOST_NORTH')=='1',host_trees=os.environ.get('OT_KV_TREES')=='1',v143=os.environ.get('OT_KV_V143')=='1')
 verdict='PASS'
except ValueError as e:
 m=last['m'];verdict='FAIL: '+str(e)
rec=dict(verdict=verdict,source_base='052ce32dc',source_sha256={n:hashlib.sha256((B/f'{n}.py').read_bytes()).hexdigest()for n in ('kv_die','kv_group_view_pins')},die=m['die'],insts=[dict(n=i.name,m=i.master,x=i.x,y=i.y,w=i.w,h=i.h,o=i.orient)for i in m['insts']],group_launch_orientations=m.get('group_launch_orientations',[]),stages=m.get('relay_stages',{}))
if verdict=='PASS':rec['pin_reach']=K.pin_reach(m,K.masters(m,1))
(B/'geometry.json').write_text(json.dumps(rec,default=str));print('LAUNCH_VERIFY',verdict,len(rec['insts']),rec['group_launch_orientations'][:5],flush=True)
if verdict!='PASS':raise SystemExit(1)
