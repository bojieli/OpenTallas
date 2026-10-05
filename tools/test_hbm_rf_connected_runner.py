#!/usr/bin/env python3
"""Read-only/mocked cap tests. Never elaborate, compile, launch service or run RTL."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run_hbm_rf_connected_gate as R
import prepare_hbm_rf_connected_gate as P
class Caps(unittest.TestCase):
    def check(self,**changes):
        args=dict(unit='test.service',cg='/user.slice/user@1000.service/test.service',mem=str(32*1024**3),swap='0',affinity={24,25,26,27},info={'RuntimeMaxUSec':'37min','LimitFSIZE':str(1024**3),'OOMPolicy':'stop'})
        args.update(changes);return R.validate_limits(**args)
    def test_memory_pids_delegation_does_not_require_cpu_max(self):
        self.assertFalse(self.check()['cpu_quota_enforced'])
    def test_wrong_wide_or_narrow_affinity_rejected(self):
        for a in ({24,25},{24,25,26,27,28},set()):
            with self.assertRaises(ValueError):self.check(affinity=a)
    def test_memory_swap_runtime_fsize_oom_rejected(self):
        for x in [dict(mem='max'),dict(mem=str(33*1024**3)),dict(swap='1'),dict(swap='max'),dict(info={'RuntimeMaxUSec':'1h'}),dict(cg='/other.service')]:
            with self.assertRaises(ValueError):self.check(**x)
    def test_fresh_go_and_source_pins_required(self):
        p=P.OUT/P.PROPOSAL;commit='reviewedsha';go=dict(schema=R.GO_SCHEMA,admitted=True,source_commit=commit,proposal_sha256=R.G.sha(p),runner_caps=R.CAPS,unit='test.service',admission_record_path='results/GO.json')
        R.validate_go(go,p,commit)
        for field,value in [('admitted',False),('source_commit','different'),('proposal_sha256','wrong'),('runner_caps',{}),('admission_record_path','../bad.json')]:
            bad={**go,field:value}
            with self.assertRaises(ValueError):R.validate_go(bad,p,commit)
    def test_exact_sequential_phase_budgets(self):
        proposal=json.loads((P.OUT/P.PROPOSAL).read_text());cmd=list(R.commands(proposal,Path('/tmp/test-only-no-launch')))
        self.assertEqual([(t,n,s)for t,n,s,a in cmd],[(t,n,s)for t in ['DS','Qwen']for n,s in [('frontend',300),('CXX',600),('simulation',180),('trace',30)]])
        self.assertEqual(sum(s for t,n,s,a in cmd),2220)
        self.assertTrue(all('<fresh-output>' not in ' '.join(a) for t,n,s,a in cmd))
    def test_runtime_source_no_cpu_controller_dependency(self):
        s=(P.ROOT/'tools/run_hbm_rf_connected_gate.py').read_text()
        self.assertNotIn("/'cpu.max'",s);self.assertNotIn('sched_setaffinity',s)
        self.assertNotIn('systemd-run',s)
    def test_process_affinity_outside_cap_rejected_read_only(self):
        with patch.object(os,'sched_getaffinity',return_value={0,1,2,3}):
            with self.assertRaises(RuntimeError):R.check_process_affinity(os.getpid())
    def test_process_affinity_within_cap_accepted_read_only(self):
        with patch.object(os,'sched_getaffinity',return_value={24,25,26,27}):self.assertGreater(R.check_process_affinity(os.getpid()),0)
    def fake_run_failure(self,reason):
        import contextlib
        class Proc:
            pid=99999999
            returncode=1 if reason=='EXIT' else None
            def poll(self):return self.returncode
        proc=Proc()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'run';gopath=Path(tmp)/'GO.json';proposalpath=P.OUT/P.PROPOSAL
            go=dict(schema=R.GO_SCHEMA,admitted=True,source_commit='source',proposal_sha256=R.G.sha(proposalpath),runner_caps=R.CAPS,unit='test.service',admission_record_path='results/GO.json')
            gopath.write_text(json.dumps(go));proposal=json.loads(proposalpath.read_text())
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(R.G,'git',side_effect=['source','admitted','']))
                stack.enter_context(patch.object(R.subprocess,'check_output',return_value=gopath.read_bytes()))
                stack.enter_context(patch.object(R.P,'prepare',return_value=proposal))
                stack.enter_context(patch.object(R,'validate_cgroup',return_value={'mocked':True}))
                stack.enter_context(patch.object(R.resource,'setrlimit'))
                stack.enter_context(patch.object(R,'commands',return_value=[('DS','frontend',300,['not-executed'])]))
                stack.enter_context(patch.object(R.subprocess,'Popen',return_value=proc))
                stack.enter_context(patch.object(R,'check_process_affinity',return_value=1))
                stack.enter_context(patch.object(R.time,'sleep'))
                stack.enter_context(patch.object(R.time,'monotonic',side_effect=[0,0,301 if reason=='PHASE_TIMEOUT' else 1,302,303]))
                stack.enter_context(patch.object(R.G,'terminate_group',side_effect=lambda p:setattr(p,'returncode',-15)))
                if reason=='OUTPUT_CAP':stack.enter_context(patch.object(R.G,'directory_bytes',return_value=9*1024**3))
                with self.assertRaises(RuntimeError):R.execute(proposalpath,gopath,'go',out)
            verdict=json.loads((out/'verdict.json').read_text())
            self.assertEqual(verdict['verdict'],'FAIL_INCOMPLETE');self.assertFalse(verdict['connected_measurement'])
            self.assertEqual(len(verdict['phases']),1);self.assertTrue((out/'DS/frontend.log').exists())
            self.assertEqual(verdict['phases'][0]['termination_reason'],None if reason=='EXIT' else reason)
            self.assertEqual((out/'GO.json').read_bytes(),gopath.read_bytes())
    def test_mocked_phase_timeout_archived_without_retry(self):self.fake_run_failure('PHASE_TIMEOUT')
    def test_mocked_output_cap_archived_without_retry(self):self.fake_run_failure('OUTPUT_CAP')
    def test_mocked_nonzero_exit_archived_without_retry(self):self.fake_run_failure('EXIT')
    def test_mocked_success_all_eight_phase_receipts(self):
        import contextlib
        class Proc:
            pid=99999999
            returncode=0
            def poll(self):return 0
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'run';gopath=Path(tmp)/'GO.json';proposalpath=P.OUT/P.PROPOSAL
            go=dict(schema=R.GO_SCHEMA,admitted=True,source_commit='source',proposal_sha256=R.G.sha(proposalpath),runner_caps=R.CAPS,unit='test.service',admission_record_path='results/GO.json')
            gopath.write_text(json.dumps(go));proposal=json.loads(proposalpath.read_text())
            def mock_process(cmd,**kwargs):
                if cmd[0].endswith('/Vconnected'):
                    kwargs['stdout'].write(b'CONNECTED_RF_FENCE_PASS\nRESET_RF_FENCE_PASS\n')
                if '--out' in cmd:
                    dst=Path(cmd[cmd.index('--out')+1]);q=0 if dst.parent.name=='DS' else 1
                    dst.write_text(json.dumps({'verdict':'PASS_DIRECTED_CONNECTED_TRACE_ONLY','cases':[{'qwen':q}for _ in range(4)]}))
                return Proc()
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(R.G,'git',side_effect=['source','admitted','']))
                stack.enter_context(patch.object(R.subprocess,'check_output',return_value=gopath.read_bytes()))
                stack.enter_context(patch.object(R.P,'prepare',return_value=proposal))
                stack.enter_context(patch.object(R,'validate_cgroup',return_value={'mocked':True}))
                stack.enter_context(patch.object(R.resource,'setrlimit'))
                popen=stack.enter_context(patch.object(R.subprocess,'Popen',side_effect=mock_process))
                R.execute(proposalpath,gopath,'go',out)
                self.assertEqual(popen.call_count,8)
            verdict=json.loads((out/'verdict.json').read_text());self.assertEqual(verdict['verdict'],'PASS_DIRECTED_NATIVE_DS_QWEN_CONNECTED_ONLY')
            self.assertEqual(len(verdict['phases']),8)
            for target in ('DS','Qwen'):
                for phase in ('frontend','CXX','simulation','trace'):
                    for path in (f'{target}-{phase}-start.json',f'{target}-{phase}-end.json',f'progress-{target}-{phase}.json'):
                        self.assertTrue((out/path).exists(),path)
    def test_original_verified_runner_unchanged(self):
        self.assertEqual((P.ROOT/'tools/full_sm_rf_verilator_gate.py').read_bytes(),P.blob('b764cc45e57a632a8ea32284dad8ca30ebf8091a','tools/full_sm_rf_verilator_gate.py'))
if __name__=='__main__':unittest.main(verbosity=2)
