"""Production-shape throughput on the existing source-checked release frame sequence binary."""
import hashlib,json,os,pickle,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
os.environ['PYTHONPATH']=str(R/'tools/s81_dv/layer_prog')+':'+os.environ.get('PYTHONPATH','')
import xs_place as X
import dv_layer_compile as C
D=Path('/srv/opentallas-scratch/codex/s81-rom12-1020');O=D/'out/fseq12';O.mkdir(parents=True,exist_ok=True)
FX='/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0';DR='/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
Q=D/'fseq_src';B=Path('/srv/opentallas-scratch/claude/toksim-s81c-fseq/v_h9nx_e5');exe=B/'obj/Vtb_toksim_fgu_seq'
die=C.Die(C.die_tree(None,DR));results=[]
for op,period in [('ffn.experts_gu',145),('attn.wq_b',126)]:
 name=op.split('.')[-1];V=O/name;V.mkdir(exist_ok=True)
 cache=O/(name+'.pickle')
 if cache.exists():rec,field=pickle.loads(cache.read_bytes())
 else:
  rec,field=X.compile_frame(die,'u_f_0L00',FX,[op]);cache.write_bytes(pickle.dumps((rec,field)))
 assert all(not p['faults'] for p in rec['phases'])
 report=dict(rec,phases=[{k:v for k,v in p.items() if k!='plan'} for p in rec['phases']])
 (V/'frame.json').write_text(json.dumps(report,indent=1)+'\n')
 for ph in rec['phases']:
  if ph['op']!=op:continue
  out=V/f'p{ph["phase"]}'
  if not (out/'meta.json').exists():X.gen_one(SimpleNamespace(fixtures=FX,frame='u_f_0L00',mutant=None,bf_measure=False),rec,field,ph,out)
 cmd=[sys.executable,str(Q/'toksim_fseq_seqops.py'),'--vec',str(V),'--name',name,'--ops',op]
 r=subprocess.run(cmd,capture_output=True,text=True);(V/'sequence_gen.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stdout+r.stderr
 _,sd,nph,K,rows,ph0=r.stdout.strip().split();sd=Path(sd);nph=int(nph)
 for P in [period,period-1]:
  log=V/f'run_P{P}.log'
  args=[str(exe),f'+OT_ROM_DIR={sd}',f'+T={nph*P+1500}',f'+K={K}',f'+OPS={rows}',f'+PH={ph0}',f'+NPH={nph}',f'+PER={P}','+RETIRE=1']
  if log.exists() and 'END edges=' in log.read_text():
   r=SimpleNamespace(returncode=0)
  else:
   with log.open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
  out=V/f'check_P{P}.json'
  chk=subprocess.run([sys.executable,str(Q/'toksim_fgu_check.py'),'seq','--seq',str(sd),'--vec',str(V),'--log',str(log),'--out',str(out),'--per',str(P),'--ref-go','63'],capture_output=True,text=True)
  (V/f'check_P{P}.log').write_text(chk.stdout+chk.stderr)
  result=dict(op=op,period=P,positive=P==period,run_rc=r.returncode,check_rc=chk.returncode,checker=json.loads(out.read_text()))
  results.append(result);print('FSEQ12',op,P,'run',r.returncode,'check',chk.returncode,chk.stdout.strip(),flush=True)
  if P==period:assert r.returncode==0 and chk.returncode==0,result
(O/'summary.json').write_text(json.dumps(dict(PASS=all(r['check_rc']==0 and r['run_rc']==0 for r in results if r['positive']),results=results,binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest()),indent=1)+'\n')
