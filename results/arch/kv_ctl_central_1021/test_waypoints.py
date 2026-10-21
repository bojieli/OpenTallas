import ast,json,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
B=Path(__file__).parent
D=json.load(open(B/'pre_relays_central.json'))
m=dict(insts=[SimpleNamespace(name=i['n'],**{k:v for k,v in i.items() if k!='n'}) for i in D['insts']],geo=D['geo'])
def load(p):
 tree=ast.parse(Path(p).read_text());node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_hroot_waypoints')
 ns={'os':os};exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns);return ns['_hroot_waypoints']
f=load(B/'kv_static_die.py')
g=load('/home/ubuntu/ot-scratch/claude/qwen-kvsys/wt-kvs14r-283f5922a-dsg3c432/tools/qwen_kv_die/kv_static_die.py')
for st in ('WS','ES'):
 h='kvs_hroot_'+st
 with patch.dict(os.environ,{'OT_KV_CTL_CENTRAL':'0'}):assert f(m,'kvs_ctl','o_hroot_'+st,h,'i_ctl')==g(m,'kvs_ctl','o_hroot_'+st,h,'i_ctl')
 with patch.dict(os.environ,{'OT_KV_CTL_CENTRAL':'1'}):
  pts=f(m,'kvs_ctl','o_hroot_'+st,h,'i_ctl')
  assert pts[1][1]==D['geo']['ctl_central']['waypoint_y']
  assert max(y for x,y in pts)<14000
  assert f(m,h,'i_ctl','kvs_ctl','o_hroot_'+st)==list(reversed(pts))
  assert f(m,'kvs_emb','o_hroot_'+st,h,'i_ctl')==g(m,'kvs_emb','o_hroot_'+st,h,'i_ctl')
  print(st,'CENTRAL_PATH',pts)
print('WAYPOINT_PASS legacyOFF identical; centralSrootdirect; reverse exact; EMB path unchanged')
