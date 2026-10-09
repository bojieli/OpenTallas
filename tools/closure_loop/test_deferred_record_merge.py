import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import closure_loop as cl

class DeferredMergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)
        self.patch = patch.object(cl, 'STATE', self.state)
        self.patch.start()
        self.j = dict(name='fixture', spec=dict(block='fixture', source=dict(branch='candidate'), merge_target='main'))
        self.out = dict(branch_commit='abc123', files=2)
    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()
    def test_hold_keeps_pinned_record_without_any_git(self):
        (self.state/'main_integration_hold.json').write_text('{}')
        with patch.object(cl,'gfetch',side_effect=AssertionError('git during hold')):
            result=cl.merge_record(self.j,self.out,['/results/fixture'])
        self.assertTrue(result['merge'].startswith('DEFERRED'))
        record=json.loads((self.state/'deferred_record_merges/fixture.json').read_text())
        self.assertEqual(record['out']['branch_commit'],'abc123')
    def test_retry_stays_queued_during_hold(self):
        (self.state/'main_integration_hold.json').write_text('{}')
        cl.defer_record_merge(self.j,self.out,[])
        with patch.object(cl,'merge_record',side_effect=AssertionError('retry during hold')):
            cl.retry_deferred_record_merges()
        self.assertTrue((self.state/'deferred_record_merges/fixture.json').exists())
    def test_retry_after_release_updates_existing_job_and_removes_queue(self):
        (self.state/'main_integration_hold.json').write_text('{}')
        cl.defer_record_merge(self.j,self.out,[])
        (self.state/'main_integration_hold.json').unlink()
        existing=dict(self.j,status='CLOSED')
        result=dict(branch_commit='abc123',merge='merged into main def456')
        with patch.object(cl,'merge_record',return_value=result), patch.object(cl,'load_job',return_value=existing), patch.object(cl,'save_job') as save, patch.object(cl,'event'):
            cl.retry_deferred_record_merges()
        self.assertEqual(existing['status'],'CLOSED')
        self.assertEqual(existing['publish'],result)
        save.assert_called_once()
        self.assertFalse((self.state/'deferred_record_merges/fixture.json').exists())
    def test_hold_appearing_before_push_defers_and_removes_merge_worktree(self):
        def shell(args,**kwargs):
            self.assertNotIn('push',args)
            (self.state/'main_integration_hold.json').write_text('{}')
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch.object(cl,'gfetch'),patch.object(cl,'wt_add'),patch.object(cl,'sh',side_effect=shell),patch.object(cl,'git',return_value=SimpleNamespace(stdout='def456\n')),patch.object(cl,'wt_rm') as rm:
            result=cl.merge_record(self.j,self.out,[])
        self.assertTrue(result['merge'].startswith('DEFERRED'))
        rm.assert_called_once()

if __name__=='__main__': unittest.main()

class ClaudeOwnershipTests(unittest.TestCase):
    def test_claude_ownership_defers_without_temporary_hold_or_git(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cl,'STATE',Path(d)), patch.object(cl,'notify_claude_record') as note:
            (Path(d)/'main_publish_owner.json').write_text('{"automatic_main_publish":false}')
            j=dict(name='fixture',spec=dict(block='fixture',source=dict(branch='candidate'),merge_target='main'))
            with patch.object(cl,'gfetch',side_effect=AssertionError('main fetch forbidden')):
                result=cl.merge_record(j,dict(branch_commit='abc123'),[])
                cl.retry_deferred_record_merges()
            self.assertIn('Claude owns',result['merge'])
            note.assert_called_once_with('fixture','candidate','abc123')
    def test_measurements_remain_dirty_under_claude_ownership(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cl,'STATE',Path(d)), patch.object(cl,'gfetch',side_effect=AssertionError('main push forbidden')):
            (Path(d)/'main_publish_owner.json').write_text('{"automatic_main_publish":false}')
            (Path(d)/'measured.dirty').write_text('pending')
            cl.publish_measured()
            self.assertTrue((Path(d)/'measured.dirty').exists())

class MainSourceRecordTests(unittest.TestCase):
    def test_main_source_record_pushes_only_codex_branch_under_claude_policy(self):
        for source_branch in ['main','active-owner-rtl']:
            with tempfile.TemporaryDirectory() as d, patch.object(cl,'STATE',Path(d)):
                (Path(d)/'main_publish_owner.json').write_text('{"automatic_main_publish":false}')
                j=dict(name='fixture',host='test',run='/work',commit_full='123abc',spec=dict(block='fixture',owner='test',source=dict(branch=source_branch)))
                metrics=dict(ss_ps=1,ff_ps=1,drc=0,setup_corner='TT')
                pushes=[]
                def shell(args,**kwargs):
                    if 'push' in args:pushes.append(args[-1])
                    return SimpleNamespace(returncode=0,stdout='results/verdict.json\n' if 'diff' in args else '',stderr='')
                def git(*args,**kwargs):
                    return SimpleNamespace(returncode=0,stdout='abc123\n' if args[0]=='rev-parse' else '',stderr='')
                def add(path,*args):path.mkdir(parents=True,exist_ok=True)
                with patch.object(cl,'gfetch'),patch.object(cl,'wt_add',side_effect=add),patch.object(cl,'wt_rm'),patch.object(cl,'sh',side_effect=shell),patch.object(cl,'git',side_effect=git),patch.object(cl,'host_cfg',return_value=dict(label='test')),patch.object(cl,'notify_claude_record'):
                    result=cl.publish(j,metrics)
                self.assertEqual(pushes,['HEAD:refs/heads/codex/closure-record-fixture'])
                self.assertEqual(result['record_branch'],'codex/closure-record-fixture')

class PendingGateAdmissionTests(unittest.TestCase):
    def test_pending_source_gate_never_starts_job(self):
        from contextlib import nullcontext
        j=dict(name="fixture",status="QUEUED",admission_hold=dict(reason="matching SOURCE gate pending"))
        with patch.object(cl,"job_lock",return_value=nullcontext()),patch.object(cl,"load_job",return_value=j),patch.object(cl,"step",side_effect=AssertionError("pending gate launched")):
            cl.advance_job("fixture",object())

class CurrentSubmitHooksTests(unittest.TestCase):
    def test_ingest_preserves_current_main_submit_lint_and_bench_paths(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cl,'STATE',Path(d)):
            spec=dict(name='fixture',block='fixture',source=dict(branch='candidate',commit='123abc'))
            with patch.object(cl,'gfetch'),patch.object(cl,'route_keys',return_value={}),patch.object(cl,'load_sources',return_value=[('drop:fixture',spec)]),patch.object(cl,'validate',return_value=[]),patch.object(cl,'route_key_full',return_value=False),patch.object(cl,'event'),patch.object(cl,'save_job'),patch.object(cl,'lint_at_submit') as lint,patch.object(cl,'bench_paths_at_submit') as paths:
                cl.ingest()
            lint.assert_called_once()
            paths.assert_called_once_with(lint.call_args.args[0])
    def test_retired_prefix_archives_full_spec_without_lint_or_new_job(self):
        with tempfile.TemporaryDirectory() as d, patch.object(cl,'STATE',Path(d)):
            (Path(d)/'main_publish_owner.json').write_text('{"automatic_main_publish":false,"retired_job_prefixes":["qfd_dspark_"]}')
            spec=dict(name='qfd_dspark_fixture',block='fixture',source=dict(branch='candidate',commit='123abc'))
            with patch.object(cl,'gfetch'),patch.object(cl,'route_keys',return_value={}),patch.object(cl,'load_sources',return_value=[('drop:fixture',spec)]),patch.object(cl,'lint_at_submit',side_effect=AssertionError('retired source reached lint')),patch.object(cl,'save_job',side_effect=AssertionError('retired job ingested')):
                cl.ingest()
            records=list((Path(d)/'retired_sources').glob('*.json'))
            self.assertEqual(len(records),1)
            self.assertEqual(json.loads(records[0].read_text())['spec'],spec)
