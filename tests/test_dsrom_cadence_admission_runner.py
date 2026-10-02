import importlib.util
import inspect
import itertools
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
RUN=module('admission_runner','tools/run_dsrom_cadence_admission.py')
OLD=module('reviewed_mock_caps','tests/test_dsrom_upstream_pair_cadence_runner_r3.py')
P=RUN.prep_module()
FIX=module('loader_fixture','tests/test_dsrom_cadence_admission_prepare.py')

# Reuse the reviewed test's fake cgroup/process implementation, pointing at
# the new runner. Child prepare/parser are mocks; no service/HDL is launched.
ns=dict(vars(OLD),RUN=RUN,P=P)
code=inspect.getsource(OLD.scenario).replace('SimpleNamespace(prepare=prepare)',
                                         'SimpleNamespace(prepare=prepare,completion=P.completion)')
exec(compile(code,'<reviewed-mocked-cap-scenario>','exec'),ns)
scenario=ns['scenario']


def go():
    p=RUN.reviewed_plan()
    return dict(GO=RUN.GO_KIND,prepared_commit='a'*40,approval_id='admission_mock_01',
        source_prepare_commit=RUN.PREPARED_SOURCE_COMMIT,
        sourceplan_sha256=RUN.sha((ROOT/RUN.PREP/'sourceplan.json').read_bytes()),
        model_sha256=RUN.sha((ROOT/RUN.PREP/'model.json').read_bytes()),
        bench_sha256=RUN.sha((ROOT/P.BENCH).read_bytes()),
        runner_sha256=RUN.sha((ROOT/RUN.RUNNER_PATH).read_bytes()),
        runner_plan_sha256=RUN.sha((ROOT/RUN.PLAN_PATH).read_bytes()),
        runner_sourceplan_sha256=RUN.sha((ROOT/RUN.BASE/'sourceplan.json').read_bytes()),
        generated_package_sha256=p['generated_package_sha256'],
        expected_contract_sha256=RUN.sha((ROOT/RUN.BASE/'expected_contract.json').read_bytes()),
        limits=p['caps'],cases=['existing_fast8'],continue_control_after_negative_failure=False,
        claims=p['claim_limits'])


def fake_git(g):
    def read(*args):
        commit,path=args[1].split(':',1)
        return json.dumps(g).encode() if path==RUN.GO_PATH else (ROOT/path).read_bytes()
    return read

ns['plan']=RUN.reviewed_plan
ns['go']=go


class AdmissionRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FIX.AdmissionPreparation.setUpClass()
        cls.trace=FIX.AdmissionPreparation.fixture

    def test_full_prepared_sources_and_package(self):
        source,p=RUN.source_preflight()
        self.assertEqual(len(source['generated_files_sha256']),34)
        self.assertEqual(p['admitted_cases'],['existing_fast8'])

    def test_all_GO_bindings(self):
        p=RUN.reviewed_plan();g=go()
        with patch.object(RUN,'source_preflight',return_value=({'input_source_sha256':{}},p)),patch.object(RUN,'git',side_effect=fake_git(g)):
            RUN.verify('b'*40)
        for key in g:
            with self.subTest(key=key),patch.object(RUN,'source_preflight',return_value=({},p)),patch.object(RUN,'git',side_effect=fake_git({**g,key:None})):
                with self.assertRaises(ValueError):RUN.verify('b'*40)

    def test_old_GO_and_short_SHA_refused(self):
        with self.assertRaisesRegex(ValueError,'full GO'):RUN.verify('8bbdc0683')
        p=RUN.reviewed_plan();g={**go(),'GO':'BOUNDED_ACTUAL_UPSTREAM_PAIR_CADENCE_AFFINITY_ONLY'}
        with patch.object(RUN,'source_preflight',return_value=({},p)),patch.object(RUN,'git',side_effect=fake_git(g)):
            with self.assertRaisesRegex(ValueError,'GO'):RUN.verify('b'*40)

    def test_stale_case_plan_refused_before_package(self):
        p=RUN.reviewed_plan()
        for change in ({'admitted_cases':['production5']},{'compiled_LAT':5}):
            with patch.object(RUN,'reviewed_plan',return_value={**p,**change}),patch.object(RUN,'prep_module') as provider:
                with self.assertRaisesRegex(ValueError,'STALE_IMAGE_ADMISSION'):RUN.source_preflight()
                provider.assert_not_called()

    def test_strict_loader_and_public_parser(self):
        p=RUN.reviewed_plan()
        self.assertTrue(RUN.completion(self.trace,'existing_fast8',p,0)['valid'])
        for text in (self.trace.replace('valid=0 addr=25','valid=1 addr=25',1),self.trace+'\nPASS_FOREIGN',self.trace.replace('value=44000000','value=44000001',1)):
            self.assertFalse(RUN.completion(text,'existing_fast8',p,0)['valid'])
        self.assertFalse(RUN.completion(self.trace,'production5',p,0)['valid'])

    def test_single_build_single_sim_no_retry(self):
        with tempfile.TemporaryDirectory() as td:
            rc,r,calls,timers,cg,a=scenario(td,[(0,'built'),(0,self.trace)])
            self.assertEqual(rc,0,r)
            self.assertEqual(len(calls),2)
            self.assertEqual(r['status'],'PASS_BOUNDED_LAT8_ADMISSION_SELECTED_PAIR_ONLY')
            # One mocked second elapsed between entry and whole timer setup;
            # the runner charges it rather than restarting a fresh660s budget.
            self.assertEqual([t.seconds for t in timers[:3]],[659,600,60])

    def test_compile_failure_retained_no_sim(self):
        with tempfile.TemporaryDirectory() as td:
            rc,r,calls,_,_,a=scenario(td,[(1,'compile failed')])
            self.assertEqual(rc,1);self.assertEqual(len(calls),1)
            self.assertEqual(r['status'],'FAIL_BUILD_UNQUALIFIED')
            self.assertTrue((a.output/'first_failure.json').exists())

    def test_sim_failure_retained_no_retry(self):
        with tempfile.TemporaryDirectory() as td:
            rc,r,calls,_,_,a=scenario(td,[(0,'built'),(1,'%Fatal public mismatch')])
            self.assertEqual(rc,1);self.assertEqual(len(calls),2)
            self.assertEqual(r['status'],'FAIL_UNQUALIFIED')
            self.assertEqual(r['first_failure']['case'],'existing_fast8')

    def test_exact_memory_swap_affinity_refusal(self):
        for override,cpus in [({'memory.max':'max'},None),({'memory.swap.max':'1'},None),({'memory.oom.group':'0'},None),({}, {0,1,2})]:
            with tempfile.TemporaryDirectory() as td:
                rc,r,calls,_,_,_=scenario(td,[],override,cpus)
                self.assertEqual(rc,1);self.assertFalse(calls)

    def test_missing_cpu_interface_not_quota_proof(self):
        with tempfile.TemporaryDirectory() as td:
            m=RUN.metrics(Path(td))
            self.assertIsNone(m['cpu.max']);self.assertFalse(m['cpu_quota_proof_accepted'])
        caps=RUN.reviewed_plan()['caps']
        self.assertFalse(caps['cpu_quota_enforced']);self.assertEqual(caps['cpu_affinity'],[0,1])

    def test_whole_kill_timer_and_service_properties(self):
        p=RUN.reviewed_plan()
        argv=RUN.service_argv(SimpleNamespace(go_commit='a'*40,output=Path('/tmp/out'),work=Path('/tmp/work')),'mock-unit',p)
        for prop in ('MemoryMax=4294967296','MemorySwapMax=0','CPUAffinity=0 1','OOMPolicy=kill','RuntimeMaxSec=660s','KillMode=control-group','KillSignal=SIGKILL'):
            self.assertIn(prop,argv)

    def test_original_exception_survives_final_metrics_error(self):
        real=RUN.metrics;calls=itertools.count()
        def final_error(cg):
            if next(calls)==0:return real(cg)
            raise FileNotFoundError('FINAL_METRICS')
        with tempfile.TemporaryDirectory() as td,patch.object(RUN,'cap_receipt',side_effect=RuntimeError('ORIGINAL_CAP_REFUSAL')),patch.object(RUN,'metrics',side_effect=final_error):
            rc,r,calls,_,_,a=scenario(td,[])
            self.assertEqual(rc,1);self.assertFalse(calls)
            self.assertIn('ORIGINAL_CAP_REFUSAL',r['exception'])
            self.assertIn('FINAL_METRICS',r['final_metrics_error'])
            self.assertTrue((a.output/'record.json').exists())


if __name__=='__main__':unittest.main()
