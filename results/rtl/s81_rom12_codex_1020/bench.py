"""Source-pinned contents-only ROM12 proof; one compiler invocation per op, existing release-frame binary."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path.cwd(); sys.path.insert(0,str(ROOT/'tools/s81_dv/layer_prog'))
import xs_place as X
import dv_layer_compile as C
D=Path('/srv/opentallas-scratch/codex/s81-rom12-1020')
FX=Path('/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0')
DR='/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
O=D/'out/bench12'; O.mkdir(parents=True,exist_ok=False)
B=Path('/srv/opentallas-scratch/claude/s81-romcap/out/bench')
# This binary is the already measured release col_h9_l4/LK5 vehicle (5.050).
with (O/'rtl_sources_checked.log').open('w') as f:
 subprocess.run(['sha256sum','-c',str(B/'sources.sha256')],stdout=f,stderr=subprocess.STDOUT,check=True)
(O/'binary.sha256').write_text(hashlib.sha256((B/'obj/Vtb_s81dv_frame').read_bytes()).hexdigest()+'\n')
(O/'verilator.version').write_bytes((B/'verilator.version').read_bytes())
die=C.Die(C.die_tree(None,DR)); results=[]
for op,phases in [('ffn.experts_gu',[1,2,3]),('attn.wq_b',[1,2])]:
 rec,field=X.compile_frame(die,'u_f_0L00',str(FX),[op])
 assert all(not p['faults'] for p in rec['phases'])
 for k,mut in [(k,None) for k in phases]+[(1,'swap'),(1,'shift')]:
  ph=next(p for p in rec['phases'] if p['phase']==k)
  name=op.split('.')[-1]+str(k)+(mut or '')
  out=O/name
  a=SimpleNamespace(fixtures=str(FX),frame='u_f_0L00',mutant=mut,bf_measure=False)
  X.gen_one(a,rec,field,ph,out)
  with (out/'run.log').open('w') as f:
   run=subprocess.run([str(B/'obj/Vtb_s81dv_frame')]+(out/'ARGS').read_text().split(),stdout=f,stderr=subprocess.STDOUT)
  with (out/'check.log').open('w') as f:
   chk=subprocess.run([sys.executable,'tools/s81_dv/layer_prog/xs_place.py','check','--dir',str(out),'--log',str(out/'run.log'),'--fixtures',str(FX)],stdout=f,stderr=subprocess.STDOUT)
  ok=(chk.returncode!=0) if mut else (chk.returncode==0 and run.returncode==0)
  results.append(dict(name=name,mutant=mut,run_rc=run.returncode,check_rc=chk.returncode,PASS=ok))
  print('ROM12_BENCH',results[-1],flush=True)
loaded={str(Path(m.__file__).resolve().relative_to(ROOT)):hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT)}
(O/'compiler_sources.json').write_text(json.dumps(loaded,indent=1)+'\n')
(O/'summary.json').write_text(json.dumps(dict(PASS=all(r['PASS'] for r in results),results=results),indent=1)+'\n')
assert all(r['PASS'] for r in results),results
