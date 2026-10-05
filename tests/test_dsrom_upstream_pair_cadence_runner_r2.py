"""Mocked runner/control logs only. Never launches HDL, systemd or physical jobs."""
import importlib.util,io,itertools,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cadence_run',ROOT/'tools/run_dsrom_upstream_pair_cadence_r2.py');RUN=importlib.util.module_from_spec(spec);spec.loader.exec_module(RUN)
def plan():return RUN.reviewed_plan()
def go():
 p=plan()
 return dict(GO=RUN.GO_KIND,prepared_commit='a'*40,approval_id='mock_approval_1234',source_prepare_commit=RUN.PREPARED_SOURCE_COMMIT,sourceplan_sha256=RUN.sha((ROOT/RUN.PREP/'sourceplan.json').read_bytes()),model_sha256=RUN.sha((ROOT/RUN.PREP/'model.json').read_bytes()),bench_sha256=RUN.sha((ROOT/'rtl/test/tb_dsrom_upstream_pair_cadence.sv').read_bytes()),runner_sha256=RUN.sha((ROOT/RUN.RUNNER_PATH).read_bytes()),runner_plan_sha256=RUN.sha((ROOT/RUN.PLAN_PATH).read_bytes()),runner_sourceplan_sha256=RUN.sha((ROOT/RUN.BASE/'sourceplan.json').read_bytes()),generated_package_sha256=p['generated_package_sha256'],expected_contract_sha256=RUN.sha((ROOT/RUN.BASE/'expected_contract.json').read_bytes()),limits=p['caps'],cases=['production5','existing_fast8'],continue_control_after_negative_failure=True,claims=p['claim_limits'])
def fake_git(g):
 def read(*a):
  commit,path=a[1].split(':',1)
  return json.dumps(g).encode() if path==RUN.GO_PATH else (ROOT/path).read_bytes()
 return read

def fixture(case):
 """Synthetic parser-test trace, NOT actual controller/RTL measurement."""
 p=plan();offset=8
 step=5 if case=='production5' else 8
 pushes=[6+offset+step*i for i in range(16)];pops=[7+offset+8*i for i in range(16)]
 emitted=[t-2 for t in pushes];lines=[];q=0;npush=n_pop=n_issue=0;end=1032
 for t in range(3,end):
  push=int(t in pushes);pop=int(t in pops and q>0);issue=pop;xs=int(t in emitted)
  index=emitted.index(t) if xs else min(15,sum(v<t for v in emitted));pos=index//8
  e=[t,5,3,pos,max(0,t-offset),512,512,1,1,0,0,xs,0,index%8,pos,3,q,push,pop,issue,1-issue,1]
  lines.append('EDGE '+' '.join(k+'='+str(v) for k,v in zip(RUN.EDGE_KEYS,e)))
  if xs:lines.append('EMITTED cycle=%d p=0 b=%d pos=%d q0=%s e0=3f8 q1=%s e1=3f8'%(t,index%8,pos,p['expected_contract']['activation_qword'],p['expected_contract']['activation_qword']))
  npush+=push;n_pop+=pop;n_issue+=issue
  if q+push-pop>4:
   lines+=['FIRST_FAULT cycle=%d pos=%d cnt=%d npush=%d pop=%d issue=%d hazard=%d overflow=1 gate=1 emitted=%d pushes=%d pops=%d issues=%d pairfault=1 spinefault=0'%(t,pos,q,push,pop,issue,1-issue,sum(v<=t for v in emitted),npush,n_pop,n_issue),
   'FIRST_FAULT_SOURCE wpos=0 npos=1 slot=0 ca=24 cd=000000000000 row0=0100 row1=8080',
   'REPRODUCED_FIRST_XFIFO_OVERFLOW profile=5 cycle=%d'%t]
   break
  q+=push-pop
  if case=='existing_fast8' and t in (200,201):lines.append('PUBLIC row=256 seg=0 nseg=1 pos=%d value=44000000 err=0'%(t-200))
 if case=='existing_fast8':lines.append('PASS_EXISTING_FAST_PROFILE rows=2 emitted=16 pushes=16 pops=16 issues=16')
 return '\n'.join(lines)+'\n'

def scenario(folder,statuses,override=None,cpus=None):
 root=Path(folder);cg=root/'cg'/'case';cg.mkdir(parents=True);proc=root/'proc';proc.write_text('0::/case\n')
 for k,v in {'memory.max':'4294967296','memory.swap.max':'0','memory.peak':'123456','memory.events':'oom 0\noom_kill 0','memory.oom.group':'1','cpu.max':'200000 100000','cgroup.procs':'123','cgroup.kill':'0',**(override or {})}.items():(cg/k).write_text(v)
 def paths(value):return proc if value=='/proc/self/cgroup' else root/'cg' if value=='/sys/fs/cgroup' else Path(value)
 calls=[];timers=[]
 class Timer:
  def __init__(self,seconds,callback):self.seconds=seconds;self.callback=callback;timers.append(self)
  def start(self):pass
  def cancel(self):pass
 class Child:
  def __init__(self,argv,**kw):
   rc,text=statuses[len(calls)];calls.append(argv);self.rc=rc;self.stdout=io.BytesIO(text.encode())
  def wait(self):return self.rc
 def prepare(work):
  work.mkdir();return dict(files_sha256=json.loads((ROOT/RUN.PREP/'sourceplan.json').read_text())['generated_files_sha256'])
 a=SimpleNamespace(output=root/'out',work=root/'work',go_commit='b'*40);counter=itertools.count();p=plan();raw=json.dumps(go()).encode()
 with patch.object(RUN,'Path',paths),patch.object(RUN,'verify',return_value=({},p,raw)),patch.object(RUN,'prep_module',return_value=SimpleNamespace(prepare=prepare)),patch.object(RUN,'tool_preflight',return_value={'compiled':False}),patch.object(RUN.os,'sched_getaffinity',return_value={0,1} if cpus is None else cpus),patch.object(RUN.os,'chdir'),patch.object(RUN.signal,'signal'),patch.object(RUN.threading,'Timer',Timer),patch.object(RUN.threading,'Thread'),patch.object(RUN.time,'monotonic',side_effect=lambda:float(next(counter))),patch.object(RUN.resource,'setrlimit'),patch.object(RUN.subprocess,'Popen',Child),patch.object(RUN,'git',return_value=b'a'*40):
  rc=RUN.capped_run(a)
 return rc,json.loads((a.output/'record.json').read_text()),calls,timers,cg,a
class RunnerTests(unittest.TestCase):
 def test_source_and_package_pins(self):
  s,p=RUN.source_preflight();self.assertEqual(39,len(s['generated_files_sha256']));self.assertEqual(p['expected_contract']['public_oracle']['FP32'],'44000000')
 def test_GO_all_source_tool_runner_caps_and_case_bindings(self):
  g=go();source,reviewed=RUN.source_preflight()
  with patch.object(RUN,'source_preflight',return_value=(source,reviewed)),patch.object(RUN,'git',side_effect=fake_git(g)):RUN.verify('b'*40)
  for k in g:
   for bad in (None,'wrong'):
    with self.subTest(key=k,value=bad),patch.object(RUN,'source_preflight',return_value=(source,reviewed)),patch.object(RUN,'git',side_effect=fake_git({**g,k:bad})):
     with self.assertRaises(ValueError):RUN.verify('b'*40)
 def test_prepared_file_change_refused(self):
  delegate=fake_git(go())
  def mutate(*a):return delegate(*a)+(b'changed' if a[1].endswith(':'+RUN.RUNNER_PATH) else b'')
  with patch.object(RUN,'git',side_effect=mutate):
   with self.assertRaisesRegex(ValueError,'reviewed prepared file'):RUN.verify('b'*40)
 def test_exact_service_properties_and_environment(self):
  a=SimpleNamespace(go_commit='b'*40,output=Path('/tmp/out'),work=Path('/tmp/work'));argv=RUN.service_argv(a,'mock-unit',plan())
  for v in ['MemoryMax=4294967296','MemorySwapMax=0','CPUQuota=200%','CPUAffinity=0 1','TasksMax=64','OOMPolicy=kill','RuntimeMaxSec=660s','KillMode=control-group','KillSignal=SIGKILL']:self.assertIn(v,argv)
  self.assertNotIn('--collect',argv)
 def test_cap_refusal_before_child_preserved(self):
  for override,cpus in [({'memory.max':'max'},None),({'memory.swap.max':'1'},None),({'memory.oom.group':'0'},None),({'cpu.max':'max 100000'},None),({'cpu.max':'100000 100000'},None),({}, {0,1,2})]:
   with tempfile.TemporaryDirectory() as td:
    rc,r,calls,timers,cg,a=scenario(td,[],override,cpus);self.assertEqual(1,rc);self.assertFalse(calls);self.assertIn('caps',r['exception'])
 def test_one_compile_two_planned_processes_and_shared_budget(self):
  with tempfile.TemporaryDirectory() as td:
   rc,r,calls,timers,cg,a=scenario(td,[(0,'built'),(0,fixture('production5')),(0,fixture('existing_fast8'))])
   self.assertEqual(0,rc);self.assertEqual(3,len(calls));self.assertEqual(['build','simulate','simulate'],[e['phase'] for e in r['runs']])
   self.assertEqual('PASS_BOUNDED_CADENCE_DIAGNOSTIC_ONLY',r['status']);self.assertEqual(600,timers[1].seconds);self.assertEqual(60,timers[2].seconds);self.assertEqual(59,timers[3].seconds)
 def test_compile_failure_no_sim_no_retry(self):
  with tempfile.TemporaryDirectory() as td:
   rc,r,calls,_,_,a=scenario(td,[(1,'compiler failure')]);self.assertEqual(1,len(calls));self.assertEqual(1,rc);self.assertEqual('FAIL_BUILD_UNQUALIFIED',r['status']);self.assertTrue((a.output/'first_failure.json').exists())
 def test_absent_overflow_failure_preserved_control_runs_only_planned(self):
  with tempfile.TemporaryDirectory() as td:
   rc,r,calls,_,_,a=scenario(td,[(0,'built'),(1,'STATIC_WITNESS_NOT_REPRODUCED'),(0,fixture('existing_fast8'))]);self.assertEqual(1,rc);self.assertEqual(3,len(calls));self.assertEqual('production5',r['first_failure']['case']);self.assertTrue(r['runs'][2]['completion']['valid'])
 def test_first_different_cause_no_reclassification(self):
  with tempfile.TemporaryDirectory() as td:
   rc,r,calls,_,_,a=scenario(td,[(0,'built'),(1,'FIRST_FAULT_DIFFERENT_CAUSE'),(1,'PUBLIC_ORACLE_DIFFERENCE')]);self.assertEqual(1,rc);self.assertEqual('production5',r['first_failure']['case']);self.assertFalse(r['runs'][1]['completion']['valid'])
 def test_semantic_expected_fault_and_control(self):
  for case in ('production5','existing_fast8'):self.assertTrue(RUN.completion(fixture(case),case,plan(),0)['valid'])
 def test_all_markers_missing_duplicate_malformed_rejected(self):
  for case in ('production5','existing_fast8'):
   lines=fixture(case).splitlines()
   for i,line in enumerate(lines):
    if line.startswith(('FIRST_FAULT','REPRODUCED','PASS_','PUBLIC','EMITTED')):
     for altered in [lines[:i]+lines[i+1:],lines[:i]+[line,line]+lines[i+1:],lines[:i]+[line+' malformed']+lines[i+1:]]:
      with self.subTest(case=case,line=i):self.assertFalse(RUN.completion('\n'.join(altered),case,plan(),0)['valid'])
 def test_fault_ownership_counters_source_and_wrong_mode_controls(self):
  text=fixture('production5');variants=[text.replace('cnt=4 npush=1 pop=0 issue=0 hazard=1 overflow=1','cnt=3 npush=1 pop=0 issue=0 hazard=1 overflow=1'),text.replace('overflow=1','overflow=0'),text.replace('pairfault=1','pairfault=0'),text.replace('spinefault=0','spinefault=1'),text.replace('row1=8080','row1=0101'),text.replace('profile=5','profile=8'),text+'PASS foreign\n',text+'FIRST_FAULT malformed\n',text+'%Error: ignored\n']
  for v in variants:self.assertFalse(RUN.completion(v,'production5',plan(),0)['valid'])
  self.assertFalse(RUN.completion(text,'existing_fast8',plan(),0)['valid'])
 def test_numerical_flag_tag_word_counter_and_order_controls(self):
  text=fixture('existing_fast8')
  for v in [text.replace('err=0','err=1',1),text.replace('value=44000000','value=44000001',1),text.replace('row=256','row=257',1),text.replace('nseg=1','nseg=2',1),text.replace('pos=0 value','pos=1 value',1),text.replace('rows=2 emitted=16','rows=1 emitted=16'),text.replace('e0=3f8','e0=3f7',1),text.replace('q0=7878','q0=7978',1),text+'DIFF foreign\n',text.replace('EDGE cycle=3','EDGE cycle=4',1)]:self.assertFalse(RUN.completion(v,'existing_fast8',plan(),0)['valid'])
  self.assertFalse(RUN.completion(text,'production5',plan(),0)['valid']);self.assertFalse(RUN.completion(text,'existing_fast8',plan(),1)['valid'])
 def test_timeout_kills_whole_even_evidence_write_fails(self):
  with tempfile.TemporaryDirectory() as td:
   rc,r,calls,timers,cg,a=scenario(td,[(1,'compiler fail')])
   for timer in timers:
    (cg/'cgroup.kill').write_text('0')
    with patch.object(RUN,'write',side_effect=OSError('receipt blocked')):
     with self.assertRaises(OSError):timer.callback()
    self.assertEqual('1',(cg/'cgroup.kill').read_text())
 def test_output_hard_bound_and_callback(self):
  with tempfile.TemporaryDirectory() as td:
   proc=SimpleNamespace(stdout=io.BytesIO(b'x'*17),wait=lambda:0);killed=[]
   def kill(*a):killed.append(a);raise RuntimeError('mock killed')
   path=Path(td)/'log'
   with self.assertRaises(RuntimeError):RUN.bounded_output(proc,path,16,kill)
   self.assertEqual(16,path.stat().st_size);self.assertEqual('LOG_BYTES',killed[0][0])
 def test_GO_single_claim_and_fresh_paths(self):
  with tempfile.TemporaryDirectory() as td,patch.object(RUN,'CLAIMS_DIR',Path(td)/'claims'):
   RUN.claim_GO(json.dumps(go()).encode(),'mock_unit')
   with self.assertRaises(FileExistsError):RUN.claim_GO(json.dumps(go()).encode(),'mock_again')
   out=Path(td)/'out';work=Path(td)/'work';RUN.fresh_paths(out,work)
   for a,b in [(out,out),(out,out/'sub'),(ROOT/'forbidden',work)]:
    with self.assertRaises(ValueError):RUN.fresh_paths(a,b)
 def test_real_main_capped_child_accepts_parent_receipts_byte_identical(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'out';work=Path(td)/'work'
   paths=[Path(str(out)+suffix) for suffix in ('_launcher.log','_launcher.json','_host_admission.json')]
   for path in paths:path.write_bytes(b'legitimate immutable parent receipt\n')
   before={str(p):p.read_bytes() for p in paths}
   argv=[RUN.RUNNER_PATH,'--execute','--capped-child','--go-commit','b'*40,'--output',str(out),'--work',str(work)]
   with patch.object(RUN.sys,'argv',argv),patch.object(RUN,'capped_run',return_value=37) as child,patch.object(RUN,'verify') as verify,patch.object(RUN.subprocess,'Popen') as spawn:
    self.assertEqual(37,RUN.main());child.assert_called_once();verify.assert_not_called();spawn.assert_not_called()
    a=child.call_args.args[0];self.assertEqual(out,a.output);self.assertEqual(work,a.work)
   self.assertEqual(before,{str(p):p.read_bytes() for p in paths});self.assertFalse(out.exists());self.assertFalse(work.exists())
 def test_real_main_parent_rejects_each_existing_launcher_receipt(self):
  for suffix in ('_launcher.log','_launcher.json','_host_admission.json'):
   with tempfile.TemporaryDirectory() as td:
    out=Path(td)/'out';work=Path(td)/'work';receipt=Path(str(out)+suffix);receipt.write_bytes(b'preserved')
    argv=[RUN.RUNNER_PATH,'--execute','--go-commit','b'*40,'--output',str(out),'--work',str(work)]
    with patch.object(RUN.sys,'argv',argv),patch.object(RUN,'capped_run') as child,patch.object(RUN,'verify') as verify,patch.object(RUN.subprocess,'Popen') as spawn:
     with self.assertRaisesRegex(ValueError,'launcher receipt already exists'):RUN.main()
     child.assert_not_called();verify.assert_not_called();spawn.assert_not_called()
    self.assertEqual(b'preserved',receipt.read_bytes())
 def test_real_main_capped_child_still_rejects_existing_or_overlapping_work_output(self):
  for case in ('existing_work','existing_output','overlap'):
   with tempfile.TemporaryDirectory() as td:
    out=Path(td)/'out';work=Path(td)/'work'
    if case=='existing_work':work.mkdir()
    elif case=='existing_output':out.mkdir()
    else:work=out/'child'
    argv=[RUN.RUNNER_PATH,'--execute','--capped-child','--go-commit','b'*40,'--output',str(out),'--work',str(work)]
    with patch.object(RUN.sys,'argv',argv),patch.object(RUN,'capped_run') as child,patch.object(RUN.subprocess,'Popen') as spawn:
     with self.assertRaises(ValueError):RUN.main()
     child.assert_not_called();spawn.assert_not_called()
 def test_r2_exact_diff_and_original_runner_preserved(self):
  old=(ROOT/'tools/run_dsrom_upstream_pair_cadence.py').read_text()
  expected=old.replace("BASE='results/rtl/dsrom_upstream_pair_cadence_runner_prepare_20261002'","BASE='results/rtl/dsrom_upstream_pair_cadence_runner_prepare_r2_20261002'").replace("RUNNER_PATH='tools/run_dsrom_upstream_pair_cadence.py'","RUNNER_PATH='tools/run_dsrom_upstream_pair_cadence_r2.py'")
  expected=expected.replace(" if output==work or output in work.parents or work in output.parents:raise ValueError('output/work overlap')\n for path", " if output==work or output in work.parents or work in output.parents:raise ValueError('output/work overlap')\n\ndef fresh_launcher_paths(output):\n # Only the parent owns launcher receipts; the capped child must accept them.\n for path")
  expected=expected.replace(" if a.capped_child:return capped_run(a)\n source,p,raw=verify", " if a.capped_child:return capped_run(a)\n fresh_launcher_paths(a.output)\n source,p,raw=verify")
  self.assertEqual(expected,(ROOT/RUN.RUNNER_PATH).read_text())
  self.assertEqual((ROOT/'tools/run_dsrom_upstream_pair_cadence.py').read_bytes(),RUN.git('show','190ccbf504441fec37acef5bcc3babfe57e6719e:tools/run_dsrom_upstream_pair_cadence.py'))
 def test_default_preflight_does_not_spawn_build(self):
  with patch.object(RUN.sys,'argv',[RUN.RUNNER_PATH]),patch.object(RUN,'source_preflight',return_value=({},plan())),patch.object(RUN,'tool_preflight',return_value={'compiled':False}),patch.object(RUN,'host_preflight',return_value={'service_launched':False}),patch.object(RUN.subprocess,'Popen') as spawn,patch('sys.stdout',io.StringIO()):self.assertEqual(0,RUN.main());spawn.assert_not_called()
 def test_environment_and_tools_rejected(self):
  p=plan();key=next(iter(p['tools']['environment']))
  with patch.dict(RUN.os.environ,{key:'changed'}):
   with self.assertRaisesRegex(ValueError,'environment'):RUN.tool_preflight(p)
if __name__=='__main__':unittest.main()
