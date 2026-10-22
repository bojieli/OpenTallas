import os,sys,json
from pathlib import Path
W=Path('/home/ubuntu/ot-scratch/claude/qwen-kvsys/wt-kvs14r-283f5922a-dsg3c432')
B=Path('/home/ubuntu/ot-scratch/claude/codex-k-ctl-geo-1021')
sys.path[:0]=[str(W/'tools/qwen_kv_die'),str(W/'tools'),str(W/'tools/qwen_split')]
central = len(sys.argv)>1 and sys.argv[1]=='central'
if central:
 import types
 os.environ['OT_KV_CTL_CENTRAL']='1'
 os.environ['OT_KV_PVT_HUB_CLEAR']='259.2'
 os.environ['OT_KV_SN_LIFT']='604.8'
 for name in ('kv_static_die','kv_die'):
  mod=types.ModuleType(name);mod.__file__=str(W/'tools/qwen_kv_die'/f'{name}.py')
  sys.modules[name]=mod
  exec(compile((B/f'{name}.py').read_text(),mod.__file__,'exec'),mod.__dict__)
import kv_die as K

def dump(m):
 rec=dict(die=m['die'],insts=[dict(n=i.name,m=i.master,x=i.x,y=i.y,w=i.w,h=i.h,o=getattr(i,'orient',None)) for i in m['insts']],keepouts=m.get('keepouts'),geo=m.get('geo'))
 (B/('pre_relays_central.json' if central else 'pre_relays.json')).write_text(json.dumps(rec,default=str))
 print('GEOMETRY_DUMP',len(rec['insts']),rec['die'],flush=True)
 raise SystemExit(0)
K._relays=dump
sys.argv=['kv_die.py','case','--kv-wq-mirror','--split']
for env,arg in [('OT_KV_HOST_V14','--host-v14'),('OT_KV_HOST_NORTH','--host-north'),('OT_KV_TREES','--host-trees'),('OT_KV_V143','--v143')]:
 if os.environ.get(env)=='1':sys.argv.append(arg)
if os.environ.get('OT_KV_ASTK_EXPAND','1')=='1' and os.environ.get('OT_KV_STATIC_DIE')=='1':sys.argv.append('--reserve-native-astk')
sys.argv+=['--out',str(B/'no_case')]
K.main()
