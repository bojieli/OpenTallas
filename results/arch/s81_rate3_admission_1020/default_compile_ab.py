"""Same default fixture/frame/op on c347 and012; preserve failures, do not infer a regression from new assertion alone."""
import hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import xs_place as X
import dv_layer_compile as C
out=dict(source_root=str(R),frame='u_f_0R00',op='ffn.shared_gu',scope='default exact-input A/B',
 xs_place_sha256=hashlib.sha256(Path(X.__file__).read_bytes()).hexdigest())
die=C.Die(C.die_tree(None,'/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'))
try:
 rec,field=X.compile_frame(die,out['frame'],'/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0',[out['op']],only=set())
 out.update(success=True,nphases=rec['nphases'])
except Exception as e:
 traceback.print_exc();out.update(success=False,type=type(e).__name__,error=str(e))
print('DEFAULT_COMPILE',json.dumps(out),flush=True)
