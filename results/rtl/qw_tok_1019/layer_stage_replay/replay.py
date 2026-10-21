"""Replay unchanged fixtures on the two existing binaries; fail closed on rebuild."""
import pathlib,sys,os,json,hashlib,traceback,time,concurrent.futures
R=pathlib.Path('/srv/opentallas-scratch/claude/refill-1225/QWLAYER'); W=R/'staging_replay_1019';SRC=W/'src'
os.environ.update(QWEN_O4_TP='8',QWEN_O4_GROUPS='3072',HDC_SU_WIDTH='64',HDC_KV_FMT='fp8',OT_GOLD_ROOT=str(SRC),PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(SRC/'rtl/test/qwen_dv'));sys.path.insert(0,str(SRC/'tools/qwen_layerbench'))
import dv_lower_vec_bench as B
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
exes={x['nu']:x for x in json.loads((W/'executables.json').read_text())}
expected={1:'7ba89595a8c4d2e77ba02e76479b2703237c426caf994cc8f2911ec698b8ce86',4:'2b1db9ca2ff412ea081c66d66d135278960ed3044157e2af8cac96e295d073e1'}
def run(c):
 # Processes isolate the bench globals, redirected stdout, numpy state and run directories.
 nu=c['nu'];exe=pathlib.Path(exes[nu]['path']);assert sha(exe)==expected[nu]
 d=W/f'nu{nu}'/c['name']; d.mkdir(parents=True,exist_ok=False)
 def existing(work):
  assert work==d and exe.is_file() and sha(exe)==expected[nu]
  print('RTL_EXEC_BEGIN',str(exe),'sha256='+sha(exe),flush=True)
  return exe
 B.LB.build=existing
 reads=set()
 def audit(event,args):
  if event=='open' and isinstance(args[0],str):
   p=pathlib.Path(args[0])
   if p.is_file() and (p.is_relative_to(SRC) or p.is_relative_to(R/'fx_qk')):reads.add(str(p))
 sys.addaudithook(audit)
 with (d/'bench.out').open('w') as out:
  sys.stdout=out;sys.stderr=out
  try:rc=B.main_run(d,c['mode'],c['mutant'],1,None,'row',c['fixture'])
  except BaseException:
   traceback.print_exc();rc=99
  print('BENCH_RC',rc,flush=True)
 (d/'runtime_reads.json').write_text(json.dumps({p:sha(pathlib.Path(p)) for p in sorted(reads)},indent=2)+'\n')
 return dict(nu=nu,name=c['name'],rc=rc,expected_rc=1 if c['mutant'] else 0,files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in d.iterdir() if p.is_file()})
if __name__=='__main__':
 assert all(x.get('preflight')=='PASS' for x in json.loads((W/'cases.json').read_text()))
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
  fs=[pool.submit(run,c) for c in json.loads((W/'cases.json').read_text())]
  rows=[]
  for f in concurrent.futures.as_completed(fs):
   r=f.result();rows.append(r);print('RESULT',r['nu'],r['name'],'rc',r['rc'],flush=True)
 (W/'replay_results.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('REPLAY TERMINAL; numerical classification requires bench verdict and actual RTL logs')
