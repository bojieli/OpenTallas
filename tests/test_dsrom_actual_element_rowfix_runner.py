"""Runner gates/control-flow with mocked children only; no systemd/HDL execution."""
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rowfix_runner',ROOT/'tools/run_dsrom_actual_element_rowfix.py')
RUN=importlib.util.module_from_spec(spec);spec.loader.exec_module(RUN)
MODEL=RUN.prepare_module().verify()
PLAN=RUN.reviewed_plan()
def valid_go():
    return dict(GO='BOUNDED_ROWFIX_ACTUAL_ELEMENT_DIFFERENTIAL_VERIFICATION_ONLY',bench_revision='rowfix',prepared_commit='a'*40,prepared_model_sha256=RUN.sha((ROOT/RUN.MODEL_PATH).read_bytes()),bench_sha256=MODEL['new_artifact_pins'][MODEL['bench_path']],generated_package_sha256=RUN.package_sha(MODEL['generated_files_sha256']),runner_sha256=RUN.sha((ROOT/RUN.RUNNER_PATH).read_bytes()),runner_plan_sha256=RUN.sha((ROOT/RUN.PLAN_PATH).read_bytes()),sourceplan_sha256=RUN.sha((ROOT/RUN.SOURCEPLAN_PATH).read_bytes()))
def fake_git(go):
    def git(*args):
        if args[0]=='show':
            commit,path=args[1].split(':',1)
            if path==RUN.GO_PATH:return json.dumps(go).encode()
            return (ROOT/path).read_bytes()
        raise AssertionError('unexpected git call '+str(args))
    return git

def scenario(root,statuses):
    """Local fake cgroup files and mocked subprocesses; never touches real caps."""
    root=Path(root);proc=root/'proc';proc.write_text('0::/case\n');cg=root/'cg'/'case';cg.mkdir(parents=True)
    for name,value in {'memory.max':'4294967296','memory.swap.max':'0','memory.peak':'123','memory.events':'oom 0','cpu.max':'max 100000','cgroup.procs':'123','cgroup.kill':'0'}.items():(cg/name).write_text(value)
    real_path=Path
    def paths(value):
        if value=='/proc/self/cgroup':return proc
        if value=='/sys/fs/cgroup':return root/'cg'
        return real_path(value)
    calls=[];timers=[]
    def prepare_stub(out):
        out.mkdir(parents=True,exist_ok=False)
        return dict(files_sha256=MODEL['generated_files_sha256'],mocked=True)
    class Timer:
        def __init__(self,seconds,callback):self.seconds=seconds;self.callback=callback;self.cancelled=False;timers.append(self)
        def start(self):pass
        def cancel(self):self.cancelled=True
    def child(argv,stdout,stderr):
        idx=len(calls);calls.append(argv);rc,text=statuses[idx];stdout.write(text);return SimpleNamespace(returncode=rc)
    counter=itertools.count()
    a=SimpleNamespace(output=root/'out',work=root/'work',go_commit='b'*40)
    with patch.object(RUN,'prepare_module',return_value=SimpleNamespace(prepare=prepare_stub)),patch.object(RUN,'Path',paths),patch.object(RUN,'verify',return_value=(MODEL,json.dumps(valid_go()).encode())),patch.object(RUN,'git',return_value=b'a'*40),patch.object(RUN.os,'sched_getaffinity',return_value={0,1}),patch.object(RUN.os,'chdir'),patch.object(RUN.signal,'signal'),patch.object(RUN.threading,'Timer',Timer),patch.object(RUN.time,'monotonic',side_effect=lambda:float(next(counter))),patch.object(RUN.subprocess,'check_output',return_value='MOCK_CHILD_VERSION_NO_EXECUTION'),patch.object(RUN.subprocess,'run',side_effect=child),patch.object(RUN,'tool_preflight',return_value={'compiled':False,'mocked':True}):
        rc=RUN.capped_run(a)
    return rc,json.loads((a.output/'record.json').read_text()),calls,timers,cg
PASSQ='PASS actual-element BF=0 cycles=2 partials=1 issues=1 gated=1 opened=1 loads=200\n'
PASSB=PASSQ.replace('BF=0','BF=1')
class RunnerTests(unittest.TestCase):
    def test_new_GO_and_each_authoritative_pin_required(self):
        good=valid_go()
        with patch.object(RUN,'git',side_effect=fake_git(good)):self.assertEqual(MODEL,RUN.verify('b'*40)[0])
        for field in ('GO','bench_revision','prepared_model_sha256','bench_sha256','generated_package_sha256','runner_sha256','runner_plan_sha256','sourceplan_sha256','prepared_commit'):
            for value in (None,'wrong'):
                go={**good,field:value}
                with self.subTest(field=field,value=value),patch.object(RUN,'git',side_effect=fake_git(go)):
                    with self.assertRaises(ValueError):RUN.verify('b'*40)
    def test_full_prepared_commit_files_and_package_bound(self):
        good=valid_go();delegate=fake_git(good)
        def changed(*args):
            data=delegate(*args)
            return data+b'changed' if args[1].endswith(':'+RUN.RUNNER_PATH) else data
        with patch.object(RUN,'git',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'reviewed rowfix file changed'):RUN.verify('b'*40)
        prep=RUN.prepare_module();package=prep.files();package['ref_ot_prefix.sv']+='\n'
        with patch.object(RUN,'git',side_effect=delegate),patch.object(RUN,'prepare_module',return_value=prep),patch.object(prep,'files',return_value=package):
            with self.assertRaisesRegex(ValueError,'package mismatch'):RUN.verify('b'*40)
    def test_tool_preflight_rejects_version_and_options_changes(self):
        def mismatch(*args,**kwargs):return SimpleNamespace(stdout='WRONG VERSION',stderr='',returncode=0)
        with patch.object(RUN.subprocess,'run',side_effect=mismatch):
            with self.assertRaisesRegex(ValueError,'version mismatch'):RUN.tool_preflight(PLAN)
        responses=[SimpleNamespace(stdout=PLAN['verilator']['version'],stderr=''),SimpleNamespace(stdout='help with no options',stderr='')]
        with patch.object(RUN.subprocess,'run',side_effect=responses):
            with self.assertRaisesRegex(ValueError,'option unavailable'):RUN.tool_preflight(PLAN)
    def test_exact_caps_and_unchanged_compile_options(self):
        source=(ROOT/RUN.RUNNER_PATH).read_text();old=(ROOT/'tools/run_dsrom_actual_element_gate_r2.py').read_text()
        properties=('MemoryMax=4294967296','MemorySwapMax=0','CPUQuota=200%','CPUAffinity=0 1','TasksMax=64','OOMPolicy=kill','RuntimeMaxSec=660s','TimeoutStopSec=1s','KillMode=control-group')
        for p in properties:self.assertIn(p,source);self.assertIn(p,old)
        self.assertIn('budget=dict(build=600.0,simulate=60.0)',source)
        self.assertIn('if len(cpus)!=2:',source)
        old_model=json.loads((ROOT/'results/rtl/dsrom_actual_element_prepare_r2_20261001/model.json').read_text())
        for case in ('q','bfcolumn'):
            expected=[x.replace('tb_dsrom_actual_element_gate_r2.sv',Path(MODEL['bench_path']).name) for x in old_model['compile_plan_proposed_only'][case]]
            self.assertEqual(expected,PLAN['compile_plan_proposed_only'][case])
    def test_q_then_BF_no_retry_and_summed_budgets(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,record,calls,timers,cg=scenario(tmp,[(0,'build\n'),(0,PASSQ),(0,'build\n'),(0,PASSB)])
            self.assertEqual(0,rc);self.assertEqual(4,len(calls))
            self.assertEqual([('q','build'),('q','simulate'),('bfcolumn','build'),('bfcolumn','simulate')],[(r['case'],r['phase']) for r in record['runs']])
            self.assertEqual([600,60,599,59],[r['remaining_seconds_at_start'] for r in record['runs']]);self.assertEqual({'build':2,'simulate':2},record['used_seconds'])
            self.assertTrue(all(t.cancelled for t in timers));self.assertLessEqual(timers[0].seconds,660)
            self.assertFalse(record['arithmetic_claim']);self.assertFalse(record['timing_claim'])
    def test_q_sim_failure_preserved_BF_continues_only_planned(self):
        for text,kind in [('tag/walk scoreboard\n','FIXTURE_OR_IMPLEMENTATION'),('DIFF public\n','DIFFERENTIAL')]:
            with self.subTest(text=text),tempfile.TemporaryDirectory() as tmp:
                rc,record,calls,timers,cg=scenario(tmp,[(0,'build\n'),(1,text),(0,'build\n'),(0,PASSB)])
                self.assertEqual(1,rc);self.assertEqual(4,len(calls));self.assertEqual(kind,record['failures'][0]['kind']);self.assertEqual('FAIL_UNQUALIFIED',record['status'])
    def test_build_failure_stops_without_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,record,calls,timers,cg=scenario(tmp,[(1,'compile FAIL\n')]);self.assertEqual(1,rc);self.assertEqual(1,len(calls));self.assertEqual('FAIL_UNQUALIFIED',record['status'])
    def test_missing_PASS_never_qualifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,record,calls,timers,cg=scenario(tmp,[(0,'build\n'),(0,'no PASS marker\n'),(0,'build\n'),(0,PASSB)])
            self.assertEqual(1,rc);self.assertEqual('FAIL_UNQUALIFIED',record['status'])
    def test_whole_and_phase_kill_even_receipt_write_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,record,calls,timers,cg=scenario(tmp,[(0,'build\n'),(0,PASSQ),(0,'build\n'),(0,PASSB)])
            for timer in (timers[0],timers[1]):
                (cg/'cgroup.kill').write_text('0')
                with patch.object(RUN,'write',side_effect=OSError('intentional receipt failure')):
                    with self.assertRaises(OSError):timer.callback()
                self.assertEqual('1',(cg/'cgroup.kill').read_text())
if __name__=='__main__':unittest.main()
