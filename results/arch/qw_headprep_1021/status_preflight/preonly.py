import sys,json,hashlib
from pathlib import Path
ROOT=Path.cwd();B=Path('/srv/opentallas-scratch/claude/codex-q-status-pre2-1021')
sys.path[:0]=['tools','results/arch/qwen_tp8_1012']
import qwen_rom_fulldie_b3r2 as G
import die_top_lint as D
assert Path(D.qwen_src()['root']).resolve()==ROOT.resolve()
class PreComplete(Exception):pass
def stop(v,m,*a,**kw):
 by={i.name:i for i in m['insts']};M=v.masters(m,1)
 assert by['native59'].master=='qfd_native59_dv_headprep_obs1'
 assert by['d2d_rom'].master=='qfd_d2d_static_ovl_sf7_obs1'
 callbacks={}
 for si,p,n in [('mu_ctxrx','obs_ctx',62),('mu_dhobs','obs_res',47),('native59','obs_native',60)]:
  rows=[(bid,nn,es)for bid,c,nn,es in m['buses']if(si,p)in es]
  assert len(rows)==1 and rows[0][1]==n and rows[0][2]==[(si,p),('d2d_rom',p)],(p,rows)
  assert M[by[si].master].ports[p][1]==n and M[by['d2d_rom'].master].ports[p][1]==n
  callbacks[p]=dict(source_master=by[si].master,bus=rows[0])
 assert m['sys_face_bind']['deferred_inputs']==[]
 out=dict(scope='STATUS callback source PRE only; stopped before both relay planners; no GEN/age/physical claim',source=str(ROOT),callbacks=callbacks,masters={i:by[i].master for i in ['native59','d2d_rom','mu_ctxrx','mu_dhobs']},buses=len(m['buses']),descriptor_bound=m['sys_face_bind']['head_descriptor_bound'],flags={k:v for k,v in __import__('os').environ.items()if k.startswith(('OT_QWEN_','OT_SPLIT_'))})
 (B/'ACTUAL_PRE.json').write_text(json.dumps(out,indent=2)+'\n')
 print('STATUS_CALLBACK_ACTUAL_PRE_PASS STOP BEFORE RELAYS',flush=True)
 raise PreComplete()
G._relays_fanout=stop;G._relays=stop
assert G._relays_fanout is stop and G._relays is stop
r=dict(D.QWEN_RECIPES['tp8b']);cdc=r.pop('cdc')
try:G.selected(True,cdc=G._cdc_arg(cdc),**r)
except PreComplete:sys.exit(0)
raise SystemExit('PRE interception not reached')
