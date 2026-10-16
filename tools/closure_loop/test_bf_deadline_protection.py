"""Pinned deployment must retain BF routes and prevent redundancy cancellation."""
import datetime as dt
import unittest
from unittest.mock import patch
import closure_loop as cl
import stuckscan


class BFProtection(unittest.TestCase):
    def job(self, name='bfa_full', status='CANCELLED'):
        return dict(name=name, host='remote', run='/scratch/bf', status=status,
                    spec=dict(block='ot_s81_bf_native', source=dict(commit='a')), created='2026-10-08T00:00:00-07:00')

    def test_deadline_and_non_bf(self):
        before = dt.datetime.fromisoformat('2026-10-10T21:29:59-07:00')
        end = dt.datetime.fromisoformat('2026-10-10T21:30:00-07:00')
        self.assertTrue(cl.bf_exempt(self.job(), before))
        self.assertFalse(cl.bf_exempt(self.job(), end))
        self.assertFalse(cl.bf_exempt(dict(name='qfd_other', spec=dict(block='other')), before))

    def test_live_protection_blocks_all_retirement_paths(self):
        job = self.job()
        with patch.object(cl, 'bf_exempt', return_value=True), patch.object(cl, 'closed_blocks', return_value={'ot_s81_bf_native'}), \
             patch.object(cl, 'write_near_miss_retain'), patch.object(cl, 'ssh') as ssh, patch.object(cl, 'load_job') as load:
            cl.release_bulk([job])
            self.assertIsNone(cl.deep_release_mode(job, {'ot_s81_bf_native'}, {}))
            self.assertEqual(stuckscan.redundant(job, [job], {'ot_s81_bf_native'}), (None, False))
            ssh.assert_not_called()
            load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
