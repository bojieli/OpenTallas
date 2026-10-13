"""A same-name historical closure must not destroy a newer candidate's diagnosis."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import closure_loop as cl

A = 'a' * 40
B = 'b' * 40


def job(name, status='EARLY_FAIL_HOLD', revision=B):
    return dict(name=name, status=status, host='ot-epyc1tb', run='/srv/x/' + name,
                commit_full=revision, spec=dict(block='blk', source=dict(commit=revision)),
                metrics={}, events=[])


class SourceRetentionTests(unittest.TestCase):
    def test_revision_and_revocation(self):
        candidate = job('new')
        old = job('old', 'CLOSED', A)
        with patch.object(cl, 'revoked_closures', return_value=(set(), set())):
            index = cl.release_source_index([candidate, old])
            self.assertTrue(cl.source_mismatch_retained(candidate, index))
            self.assertFalse(cl.source_mismatch_retained(old, index))
            self.assertFalse(cl.source_mismatch_retained(candidate, cl.release_source_index([candidate])))
            matching = job('matching', 'CLOSED')
            self.assertFalse(cl.source_mismatch_retained(candidate, cl.release_source_index([candidate, old, matching])))
            self.assertTrue(cl.source_mismatch_retained(candidate, {'blk': {'bbbbbbb'}}))
            self.assertTrue(cl.source_mismatch_retained(job('unknown', revision=''), index))
        with patch.object(cl, 'revoked_closures', return_value=({'old'}, set())):
            self.assertEqual(cl.release_source_index([old]), {})

    def test_bulk_and_sweeper_manifest_keep_new_revision_without_metrics(self):
        jobs = [job('new'), job('old', 'CLOSED', A)]
        with tempfile.TemporaryDirectory() as t, \
             patch.object(cl, 'NEAR_MISS_JSON', Path(t) / 'retain.json'), \
             patch.object(cl, 'revoked_closures', return_value=(set(), set())), \
             patch.object(cl, 'hosts_table', return_value=[dict(name='ot-epyc1tb')]), \
             patch.object(cl, 'ssh') as ssh:
            cl.release_bulk(jobs)
            ssh.assert_not_called()
            rows = json.loads(cl.NEAR_MISS_JSON.read_text())['jobs']
            self.assertEqual([r['job'] for r in rows], ['new'])
            self.assertEqual(rows[0]['reason'], 'source-mismatched closure')

    def test_deep_release_cannot_delete_new_revision(self):
        jobs = [job('new'), job('old', 'CLOSED', A)]
        with patch.object(cl, 'revoked_closures', return_value=(set(), set())), \
             patch.object(cl, 'hosts_table', return_value=[dict(name='ot-epyc1tb')]), \
             patch.object(cl, '_terminal_age_h', return_value=10), \
             patch.object(cl, '_main_evidence', return_value=dict(refs=[])), \
             patch.object(cl, 'deep_release_mode', side_effect=lambda j, *a: 'fail' if j['name'] == 'new' else None), \
             patch.object(cl, 'ssh') as ssh:
            self.assertEqual(cl.release_deep(jobs), 0)
            ssh.assert_not_called()

    def test_owner_keep_survives_bulk_release_override(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            odb = root / 'routes/x/orfs/4_cts.odb'
            odb.parent.mkdir(parents=True)
            odb.write_text('unique diagnosis')
            (root / '.keep').write_text('Codex active diagnosis')
            result = subprocess.run(['bash', '-c', 'NEAR_MISS_RELEASE=1\n' + cl.BULK_RELEASE_SH % dict(run=str(root))], capture_output=True, text=True)
            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertEqual(odb.read_text(), 'unique diagnosis')


if __name__ == '__main__':
    unittest.main()
