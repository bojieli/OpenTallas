"""EPYC2-S3 11-15, widened 11-17 (COORD): every build host that has scratch3 authorizes it as a second scratch root by default; unknown hosts do not."""
import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_ot_run_scratch_disk import load  # noqa: E402

S3 = '/srv/opentallas-scratch3'
_env = {k: v for k, v in os.environ.items() if not k.startswith('OT_RUN_ROOT_SCRATCH')}
_env['OT_RUN_SCRATCH_SECOND_MARGIN_GB'] = '1000000'   # below-floor semantics here; the margin rule is in test_ot_run_job_dir_placement.py
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
        self.assertEqual(m.second_roots('epyc7'), (S3,))
        self.assertEqual(m.second_roots('nohost'), ())

    def test_epyc2_full_scratch2_admits_on_scratch3(self):
        row = m.scratch_disk({'disk_gb': 7}, self.D, probe(7, 2000), host='epyc2')
        self.assertEqual(row['scratch_disk'], S3)
        self.assertTrue(row['scratch_second'])
        self.assertEqual(m.host_refusal(row), '')

    def test_other_host_not_authorized(self):
        row = m.scratch_disk({'disk_gb': 7}, self.D, probe(7, 2000), host='nohost')
        self.assertNotEqual(row.get('scratch_disk'), S3)
        self.assertIn('scratch disk', m.host_refusal(row))

    def test_epyc2_scratch2_ok_stays(self):
        row = m.scratch_disk({'disk_gb': 400}, self.D, probe(400, 2000), host='epyc2')
        self.assertEqual(row['scratch_disk'], '/srv/opentallas-scratch2')

    def test_root_backed_exception_is_not_recommended_as_a_dedicated_disk(self):
        root_probe = probe(89, 743).replace("OT_DIR_ONROOT 0", "OT_DIR_ONROOT 1")
        permitted = m.scratch_disk({"disk_gb": 743}, S3 + "/claude/lane", root_probe, host="epyc2")
        self.assertTrue(permitted["scratch_second"])
        self.assertEqual(permitted["disk_gb"], 743 - m.root_floor("epyc2"))
        self.assertEqual(m.host_refusal(permitted), "")
        note = m.root_dir_guidance(permitted)
        self.assertIn(f"{S3} is an authorized root-backed scratch path", note)
        self.assertIn(f"keeping {m.root_floor('epyc2')} GB free", note)
        self.assertNotIn(f"filesystem {S3}/claude", note)

        unauthorized = m.scratch_disk({"disk_gb": 743}, "/home/ubuntu/lane", root_probe, host="epyc2")
        self.assertIn("without an explicit root scratch exception", m.host_refusal(unauthorized))
        note = m.root_dir_guidance(unauthorized)
        self.assertNotIn(S3, note)
        self.assertIn("/srv/opentallas-scratch2", note)
        low = dict(unauthorized, dedicated_scratch_gb=1)
        self.assertIn("below its", m.root_dir_guidance(low))

    def test_env_script_lists_scratch3_for_epyc2_only(self):
        self.assertIn(' ' + S3 + ' ', m.scratch_env('epyc2').split('case')[1].split('esac')[0])
        self.assertNotIn(' ' + S3 + ' ', m.scratch_env('nohost').split('case')[1].split('esac')[0])


if __name__ == '__main__':
    unittest.main()
