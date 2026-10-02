"""Mocked runner/cgroup/file-bound tests only. No HDL or service execution."""
import importlib.util
import io
import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('primitive_runner',ROOT/'tools/run_dsrom_bmul_rne_primitive_r2.py');R=importlib.util.module_from_spec(s);s.loader.exec_module(R)
MODEL=R.prepare_module().verify();PLAN=R.reviewed_plan()
def go():
    return dict(GO=R.GO_LITERAL,prepared_commit='a'*40,caps=PLAN['caps'],expected_completion=PLAN['expected_completion'],prepared_model_sha256=R.sha((ROOT/R.MODEL_PATH).read_bytes()),bench_sha256=MODEL['new_artifact_pins'][MODEL['bench']],generated_package_sha256=PLAN['generated_package_sha256'],runner_sha256=R.sha((ROOT/R.RUNNER_PATH).read_bytes()),runner_plan_sha256=R.sha((ROOT/R.PLAN_PATH).read_bytes()),sourceplan_sha256=R.sha((ROOT/R.SOURCEPLAN_PATH).read_bytes()),semantic_contract_sha256=R.sha((ROOT/R.BASE/'expected_contract.json').read_bytes()))
def fake_git(g):
    def call(*args):
        if args[0]=='show':
            _,p=args[1].split(':',1)
            return json.dumps(g).encode() if p==R.GO_PATH else (ROOT/p).read_bytes()
        return b'a'*40
    return call

def passing(mode):
    diff=f'DIFF primitive mutant={mode} product_vector=0 expected=000008000 actual=00000000/0\n' if mode else ''
    return diff+f'PASS primitive RNE mode={mode} product_assertions=1416 encoder_assertions=840 baseline_witnesses=2\n'

def scenario(root,statuses):
    root=Path(root);proc=root/'proc';proc.write_text('0::/case\n');cg=root/'cg'/'case';cg.mkdir(parents=True)
    for n,v in {'memory.max':'536870912','memory.swap.max':'0','memory.swap.current':'0','memory.peak':'123','memory.events':'oom 0','cpu.max':'max 100000','cgroup.procs':'1','cgroup.kill':'0'}.items():(cg/n).write_text(v)
    real=Path
    def paths(x):return proc if x=='/proc/self/cgroup' else root/'cg' if x=='/sys/fs/cgroup' else real(x)
    calls=[];timers=[];preparer=R.prepare_module()
    class Timer:
        def __init__(self,n,callback):self.seconds=n;self.callback=callback;self.cancelled=False;timers.append(self)
        def start(self):pass
        def cancel(self):self.cancelled=True
    class Thread:
        def __init__(self,**kwargs):pass
        def start(self):pass
    def prepare(out):out.mkdir();return dict(files_sha256=MODEL['generated_files_sha256'],mocked=True)
    def popen(argv,**kwargs):
        idx=len(calls);calls.append(argv);rc,text=statuses[idx]
        return SimpleNamespace(stdout=io.BytesIO(text.encode()),wait=lambda:rc)
    a=SimpleNamespace(work=root/'work',output=root/'out',go_commit='b'*40);clock=itertools.count()
    with patch.object(R,'Path',paths),patch.object(R,'preflight',return_value=(MODEL,PLAN,json.dumps(go()).encode())),patch.object(R,'prepare_module',return_value=SimpleNamespace(prepare=prepare, inputs=preparer.inputs, encoder_inputs=preparer.encoder_inputs, expected=preparer.expected, O=preparer.O)),patch.object(R,'git',return_value=b'a'*40),patch.object(R.os,'chdir'),patch.object(R.os,'sched_getaffinity',return_value={0}),patch.object(R.resource,'setrlimit'),patch.object(R.signal,'signal'),patch.object(R.threading,'Timer',Timer),patch.object(R.threading,'Thread',Thread),patch.object(R.time,'monotonic',side_effect=lambda:float(next(clock))),patch.object(R.subprocess,'check_output',return_value='MOCK_VERSION_NO_EXECUTION'),patch.object(R.subprocess,'Popen',side_effect=popen),patch.object(R,'tool_preflight',return_value={'compiled':False,'mocked':True}):rc=R.capped_run(a)
    return rc,json.loads((a.output/'record.json').read_text()),calls,timers,cg
class PrimitiveRunnerTests(unittest.TestCase):
    def test_new_GO_every_pin_caps_coverage_fullcommit(self):
        good=go()
        with patch.object(R,'git',side_effect=fake_git(good)):self.assertEqual(MODEL,R.preflight('b'*40)[0])
        for key in good:
            changed={**good,key:'WRONG'}
            with self.subTest(key=key),patch.object(R,'git',side_effect=fake_git(changed)):
                with self.assertRaises(ValueError):R.preflight('b'*40)
    def test_prepared_file_change_rejected(self):
        delegate=fake_git(go())
        def changed(*args):return delegate(*args)+b'changed' if args[0]=='show' and args[1].endswith(':'+R.RUNNER_PATH) else delegate(*args)
        with patch.object(R,'git',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'reviewed commit file changed'):R.preflight('b'*40)
    def test_default_preflight_requires_noGO_and_no_compile(self):
        _,p,raw=R.preflight();self.assertIsNone(raw);self.assertEqual(26,len(p['generated_files_sha256']))
        self.assertIn('if not a.execute:',(ROOT/R.RUNNER_PATH).read_text())
    def test_positive_and_all_mutant_modes_exact_counts(self):
        for mode in range(9):self.assertTrue(R.completion(passing(mode),mode,PLAN,0)['valid'])
        for text in [passing(0).replace('1416','1415'),passing(0)*2,passing(1),passing(0)+'DIFF unrelated\n',passing(0)+'DIFFmalformed\n']:
            self.assertFalse(R.completion(text,0,PLAN,0)['valid'])
    def test_mutant_requires_actual_DIFFERENCE_and_no_crash(self):
        for text,rc in [(passing(1),1),(passing(1)+'%Fatal: bad\n',0),(passing(1).replace('actual=00000000/0','actual=00008000/0'),0),(passing(1).replace('mutant=1','mutant=2'),0),(passing(1).replace('product_vector=0','product_vector=9999'),0),(passing(1).split('\n',1)[1],0)]:self.assertFalse(R.completion(text,1,PLAN,rc)['valid'])
    def test_hostile_markers_and_expected_binding(self):
        terminal=passing(1).split('\n',1)[1]
        bad=[passing(1).replace('000008000','000008001'),
             passing(1).replace('actual=00000000/0','actual=0/0'),
             passing(1).replace('actual=00000000/0','actual=00000000/2'),
             passing(1).replace('actual=00000000/0','actual=00000000'),
             passing(1).replace('product_vector=0','product_vector=708'),
             passing(1).replace('product_vector=0','product_vector=-1'),
             'DIFF malformed early\n'+passing(1), passing(1)+terminal,
             passing(1)+'PASS foreign\n', passing(1)+passing(1),
             passing(1).replace('mode=1','mode=2')]
        for text in bad:
            with self.subTest(text=text):self.assertFalse(R.completion(text,1,PLAN,0)['valid'])
        self.assertTrue(R.completion('diagnostic encoder_vector=irrelevant\n'+passing(1),1,PLAN,0)['valid'])
    def test_encoder_kind_oracle_and_format(self):
        m=R.prepare_module();sign,be,sig=m.encoder_inputs()[0]
        bits=m.O.round32((-1 if sign else 1)*sig*m.O.pow2(be-150))
        terminal=passing(1).split('\n',1)[1]
        line=f'DIFF primitive mutant=1 encoder_vector=0 expected={bits:08x} actual={bits^1:08x}\n'
        self.assertTrue(R.completion(line+terminal,1,PLAN,0)['valid'])
        for text in [line.replace(f'expected={bits:08x}',f'expected={bits^2:08x}'),line.replace('encoder_vector=0','encoder_vector=420'),line.replace(f'actual={bits^1:08x}',f'actual={bits:08x}'),line.replace(f'actual={bits^1:08x}',f'actual={bits^1:08x}/0')]:
            self.assertFalse(R.completion(text+terminal,1,PLAN,0)['valid'])
    def test_PCH_off_supported_make_path_only_plan_change(self):
        old=json.loads((ROOT/'results/rtl/dsrom_bmul_rne_primitive_runner_prepare_20261002/runner_plan.json').read_text())
        argv=PLAN['compile_plan_proposed_only']['shared'];i=argv.index('-MAKEFLAGS')
        self.assertEqual('VM_PARALLEL_BUILDS=0',argv[i+1])
        self.assertEqual(old['compile_plan_proposed_only']['shared'],argv[:i]+argv[i+2:])
        for key in ('caps','expected_completion','generated_files_sha256','generated_package_sha256','simulate_plan_proposed_only'):
            self.assertEqual(old[key],PLAN[key])
        source=json.loads((ROOT/R.SOURCEPLAN_PATH).read_text())
        self.assertEqual(source['compile_plan_proposed_only'],PLAN['compile_plan_proposed_only'])
        self.assertEqual(source['expected_completion'],PLAN['expected_completion'])
        mk=Path(source['PCH_disable_source']['installed_make_rules']).read_text()
        self.assertIn('ifneq ($(VM_PARALLEL_BUILDS),1)',mk)
        self.assertIn('VK_OBJS += $(VM_PREFIX)__ALL.o',mk)
        self.assertIn('%.o: %.cpp',mk)
        self.assertIn('$(VK_OBJS_FAST): %.o: %.cpp $(VK_PCH_H).fast.gch',mk)
        self.assertIn('-MAKEFLAGS <flags>',Path(R.VERILATOR).read_text())
        self.assertIn('-MAKEFLAGS <flags>',PLAN['verilator']['help_option_tokens'])
    def test_supported_make_override_actual_rule_selection_no_compile(self):
        # Read installed rules with a synthetic classes list; explicit inspect target has no recipes.
        # This checks GNU make precedence and selected object dependency without generating HDL or compiling.
        import subprocess
        mk=PLAN['build_plan_revision']['installed_make_rules']
        fixture='VM_PARALLEL_BUILDS = 1\nVM_PREFIX = inspect_fixture\nVM_CLASSES_FAST = sample_fast\nVM_CLASSES_SLOW = sample_slow\ninclude '+mk+'\n$(info parallel=$(VM_PARALLEL_BUILDS);origin=$(origin VM_PARALLEL_BUILDS);objects=$(VK_OBJS))\n.PHONY: inspect\ninspect:\n'
        result=subprocess.run(['make','--no-print-directory','-f','-','VM_PARALLEL_BUILDS=0','inspect'],input=fixture,text=True,capture_output=True,check=True)
        self.assertIn('parallel=0;origin=command line;objects=inspect_fixture__ALL.o',result.stdout)
        self.assertNotIn('.gch',result.stdout)
        self.assertNotIn('g++',result.stdout)
    def test_help_hash_change_rejected(self):
        with patch.object(R.subprocess,'run',side_effect=[SimpleNamespace(stdout=PLAN['verilator']['version'],stderr=''),SimpleNamespace(stdout='\n'.join(PLAN['verilator']['help_option_tokens']),stderr='')]):
            with self.assertRaisesRegex(ValueError,'help changed'):R.tool_preflight(PLAN)
    def test_original_runner_and_primitives_preserved(self):
        for path,pin in PLAN['previous_runner_preservation_sha256'].items():
            self.assertEqual(pin,R.sha((ROOT/path).read_bytes()))
            self.assertEqual((ROOT/path).read_bytes(),R.git('show',PLAN['previous_runner_commit']+':'+path))
    def test_singlecompile_ninemodes_summed_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc,d,calls,timers,cg=scenario(tmp,[(0,'build')]+[(0,passing(n)) for n in range(9)])
            self.assertEqual(0,rc);self.assertEqual(10,len(calls));self.assertEqual({'build':1,'simulate':9},d['used_seconds'])
            self.assertEqual(list(range(9)),[e['mode'] for e in d['runs'][1:]])
            self.assertEqual(list(range(10,1,-1)),[e['remaining_seconds_at_start'] for e in d['runs'][1:]])
            self.assertTrue(all(t.cancelled for t in timers));self.assertFalse(any(d['claims'].values()))
    def test_build_positive_or_mutant_failure_stops_no_retry(self):
        scenarios=[[(1,'compile FAIL')],[(0,'build'),(1,'fixture FAIL')],[(0,'build'),(0,passing(0)),(1,passing(1))]]
        for statuses in scenarios:
            with tempfile.TemporaryDirectory() as tmp:
                rc,d,calls,_,_=scenario(tmp,statuses);self.assertEqual(1,rc);self.assertEqual(len(statuses),len(calls));self.assertEqual('FAIL_UNQUALIFIED',d['status'])
    def test_caps_refuse_wrongmemory_swap_cpu(self):
        with tempfile.TemporaryDirectory() as tmp:
            cg=Path(tmp)
            for n,v in {'memory.max':'536870912','memory.swap.max':'0','cgroup.kill':'0'}.items():(cg/n).write_text(v)
            R.cap_receipt(cg,{0})
            for n,v in [('memory.max','max'),('memory.swap.max','1')]:
                old=(cg/n).read_text();(cg/n).write_text(v)
                with self.assertRaises(RuntimeError):R.cap_receipt(cg,{0})
                (cg/n).write_text(old)
            with self.assertRaises(RuntimeError):R.cap_receipt(cg,{0,1})
    def test_timeout_kills_even_receipt_write_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,_,_,timers,cg=scenario(tmp,[(0,'build')]+[(0,passing(n)) for n in range(9)])
            for t in (timers[0],timers[1]):
                (cg/'cgroup.kill').write_text('0')
                with patch.object(R,'write',side_effect=OSError('intentional receipt failure')),patch.object(R,'cap_receipt',return_value={}):
                    with self.assertRaises(OSError):t.callback()
                self.assertEqual('1',(cg/'cgroup.kill').read_text())
    def test_log_storedbytes_hardbound(self):
        with tempfile.TemporaryDirectory() as tmp:
            log=Path(tmp)/'log';kills=[]
            def kill(kind,detail):kills.append((kind,detail));raise RuntimeError('MOCK_KILL_NO_EXECUTION')
            proc=SimpleNamespace(stdout=io.BytesIO(b'x'*8192),wait=lambda:0)
            with self.assertRaisesRegex(RuntimeError,'MOCK_KILL'):R.bounded_output(proc,log,4097,kill)
            self.assertEqual(4097,log.stat().st_size);self.assertEqual('LOG_BYTES',kills[0][0])
    def test_artifact_and_receipt_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'a').write_bytes(b'123')
            with self.assertRaises(RuntimeError):R.inventory(p,limit_bytes=2)
            with self.assertRaises(RuntimeError):R.inventory(p,limit_files=0)
            with self.assertRaises(RuntimeError):R.write(p/'oversize',{'value':'x'*(4*1024*1024)})
            self.assertFalse((p/'oversize').exists())
    def test_serviceproperties_exact_and_wholekill(self):
        a=SimpleNamespace(go_commit='b'*40,output=Path('/tmp/mock'),work=Path('/tmp/mockwork'))
        argv=R.service_argv(a,'mock');text=' '.join(argv)
        for literal in ('MemoryMax=536870912','MemorySwapMax=0','CPUQuota=100%','CPUAffinity=0','RuntimeMaxSec=70s','KillMode=control-group','TasksMax=32','OOMPolicy=kill'):self.assertIn(literal,text)
    def test_tool_path_version_options_rejected(self):
        with patch.object(R.subprocess,'run',return_value=SimpleNamespace(stdout='WRONG',stderr='')):
            with self.assertRaisesRegex(ValueError,'version mismatch'):R.tool_preflight(PLAN)
        with patch.object(R.subprocess,'run',side_effect=[SimpleNamespace(stdout=PLAN['verilator']['version'],stderr=''),SimpleNamespace(stdout='',stderr='')]):
            with self.assertRaisesRegex(ValueError,'option unavailable'):R.tool_preflight(PLAN)
if __name__=='__main__':unittest.main()
