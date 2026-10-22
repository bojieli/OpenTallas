"""Exercise the actual exporter function bodies without invoking EDA or die planning."""
import ast, json, os, re, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/qwen_kv_die'))
import kv_grp_private0 as GP
src=(ROOT/'tools/qwen_kv_die/kv_die.py').read_text()
parsed=ast.parse(src)
functions=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in ('write_netlist','_case_ties')]
assert len(functions)==2
inp=Path(sys.argv[1]); report=Path(sys.argv[2])
raw=(inp/'gen7_die_bound.v').read_text()
renamed=re.sub(r'^(  qkd_kvs_grp(?:_h)?) (slg_\w+) \(',lambda m:m[1]+'_private0 '+m[2]+' (',raw,flags=re.M)
records=[]
namespace=dict(os=os,Path=Path,json=json,re=re,static_instance_params=lambda m:{})
state={}
def emit(m,k,path,top):
    state['called']=True
    Path(path).write_text(state['source'])
namespace['F']=SimpleNamespace(write_netlist=emit)
exec(compile(ast.Module(body=functions,type_ignores=[]),str(ROOT/'tools/qwen_kv_die/kv_die.py'),'exec'),namespace)
m=dict(geo=dict(static_die=True,kv_wq_leaves=False))
previous=os.environ.get('OT_KV_GRP_PRIVATE0')
try:
 with tempfile.TemporaryDirectory(prefix='grp-private-export-') as td:
  path=Path(td)/'die.v'
  for enabled,source in [(False,raw),(True,renamed)]:
   os.environ['OT_KV_GRP_PRIVATE0']='1' if enabled else '0'
   state.update(source=source,called=False)
   namespace['write_netlist'](m,1,path)
   expected=GP.parent_connections(source) if enabled else source
   assert path.read_text()==expected
   assert state['called']
   path.write_text(source)
   namespace['_case_ties'](m,path)
   assert path.read_text()==expected
   records.append(dict(case='both actual parent exporters private='+str(enabled),result='PASS'))
  state['called']=False
  try: namespace['write_netlist'](m,32,path)
  except ValueError as error:
   assert 'full-width' in str(error) and not state['called']
   records.append(dict(case='compressed parent nets',result='REFUSED_BEFORE_WRITE',reason=str(error)))
  else:raise AssertionError('compressed private ABI accepted')
finally:
 if previous is None:os.environ.pop('OT_KV_GRP_PRIVATE0',None)
 else:os.environ['OT_KV_GRP_PRIVATE0']=previous
report.write_text(json.dumps(records,indent=2)+'\n')
print('GRP_PRIVATE_EXPORT PASS both actual exporters default/private; scaled ABI refused before write')
