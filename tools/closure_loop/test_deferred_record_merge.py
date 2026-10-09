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
