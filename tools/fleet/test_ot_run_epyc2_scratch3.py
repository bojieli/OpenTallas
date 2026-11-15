"""EPYC2-S3 11-15: epyc2 authorizes scratch3 (root disk) as second scratch root by default, no other host does."""
import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ot_run_scratch_disk import load  # noqa: E402

S3 = '/srv/opentallas-scratch3'
_env = {k: v for k, v in os.environ.items() if not k.startswith('OT_RUN_ROOT_SCRATCH')}
with mock.patch.dict(os.environ, _env, clear=True):
    m = load()


def probe(s2, root_free):
    return ('OT_SCRATCH_FREE /srv/opentallas-scratch2 %d 0\nOT_SCRATCH_FREE %s %d 1\nOT_ROOTFS 42 %d\nOT_DIR_ONROOT 0\n'
            % (s2, S3, root_free, root_free))


class Epyc2S3(unittest.TestCase):
    D = '/srv/opentallas-scratch2/claude/lane/run'

    def test_second_roots(self):
        self.assertEqual(m.ROOT_SCRATCH_ROOTS, ())
        self.assertEqual(m.second_roots('epyc2'), (S3,))
        self.assertEqual(m.second_roots('epyc7'), ())

    def test_epyc2_full_scratch2_admits_on_scratch3(self):
        row = m.scratch_disk({'disk_gb': 7}, self.D, probe(7, 2000), host='epyc2')
        self.assertEqual(row['scratch_disk'], S3)
        self.assertTrue(row['scratch_second'])
        self.assertEqual(m.host_refusal(row), '')

    def test_other_host_not_authorized(self):
        row = m.scratch_disk({'disk_gb': 7}, self.D, probe(7, 2000), host='epyc7')
        self.assertNotEqual(row.get('scratch_disk'), S3)
        self.assertIn('scratch disk', m.host_refusal(row))

    def test_epyc2_scratch2_ok_stays(self):
        row = m.scratch_disk({'disk_gb': 400}, self.D, probe(400, 2000), host='epyc2')
        self.assertEqual(row['scratch_disk'], '/srv/opentallas-scratch2')

    def test_env_script_lists_scratch3_for_epyc2_only(self):
        self.assertIn(' ' + S3 + ' ', m.scratch_env('epyc2').split('case')[1].split('esac')[0])
        self.assertNotIn(' ' + S3 + ' ', m.scratch_env('epyc7').split('case')[1].split('esac')[0])


if __name__ == '__main__':
    unittest.main()
