import os,sys,json,types,hashlib
from pathlib import Path
B=Path(__file__).parent
ROOT=Path.cwd()
sys.path[:0]=['tools','results/arch/qwen_tp8_1012']
import qwen_split
for short in ('static_link_bind','dv_case'):
 name='qwen_split.'+short
 source=B/(short+'.py')
 mod=types.ModuleType(name);mod.__file__=str(ROOT/'tools/qwen_split'/(short+'.py'));mod.__package__='qwen_split'
 sys.modules[name]=mod;setattr(qwen_split,short,mod)
 exec(compile(source.read_text(),mod.__file__,'exec'),mod.__dict__)
import qwen_rom_fulldie_b3r2 as G
import die_top_lint as D
class PreComplete(Exception):pass
def stop(v,m,*a,**kw):
 by={i.name:i for i in m['insts']};M=v.masters(m,1)
 assert by['native59'].master=='qfd_native59_dv_headprep'
 for p in ('tx_user','rx_user'):
  matches=[(bid,n,es) for bid,c,n,es in m['buses'] if ('native59',p) in es]
  assert len(matches)==1 and matches[0][1]==2,(p,matches)
  assert ('d2d_rom',p) in matches[0][2],(p,matches)
  assert M[by['native59'].master].ports[p][1]==2
 assert m['sys_face_bind']['deferred_inputs']==[]
 assert len(m['sys_face_bind']['head_descriptor_bound'])==3
 receipt=dict(scope='PRE only, stopped before relay planners; no GEN result or transport ages',source=str(ROOT),native_master=by['native59'].master,die=m['die'],overlay={p:hashlib.sha256((B/p).read_bytes()).hexdigest() for p in ('static_link_bind.py','dv_case.py')},head_descriptor_bound=m['sys_face_bind']['head_descriptor_bound'],buses=m['buses'])
 (B/'ACTUAL_PRE.json').write_text(json.dumps(receipt,indent=2))
 print('HEAD_PREP_ACTUAL_PRE_PASS STOP BEFORE RELAYS',flush=True)
 raise PreComplete()
G._relays_fanout=stop;G._relays=stop
D.QWEN_RECIPE='tp8b';D._QW.clear();D.QSRC=None
r=dict(D.QWEN_TP8B);cdc=r.pop('cdc')
try:G.selected(True,cdc=G._cdc_arg(cdc),**r)
except PreComplete:sys.exit(0)
raise SystemExit('PRE interception not reached')
