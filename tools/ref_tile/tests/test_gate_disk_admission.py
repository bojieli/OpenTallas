"""Admission regressions: real tar payloads, no synthesis or remote mutation."""
import contextlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as PG


def archive(size=8193):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        item = tarfile.TarInfo('rtl/top.v')
        item.size = size
        tf.addfile(item, io.BytesIO(b'0' * size))
    return buf.getvalue()


class DiskBudget(unittest.TestCase):
    def test_default_retains_twenty_gib_work_reserve_and_prices_staging(self):
        data = archive()
        budget = PG.gate_disk_budget({}, data)
        self.assertEqual(budget, dict(reserve_gb=20, archive_bytes=len(data),
                                     unpacked_bytes=16384, pick_gb=22, runtime_gb=22))

    def test_positive_fraction_rounds_up_and_cli_overrides_spec(self):
        self.assertEqual(PG.gate_disk_budget({'gate_disk_gb': 40.1}, archive())['reserve_gb'], 41)
        self.assertEqual(PG.gate_disk_budget({'gate_disk_gb': 40}, archive(), 0.25)['reserve_gb'], 1)

    def test_bad_reserve_refused(self):
        for bad in (True, False, 0, -1, float('inf'), float('-inf'), float('nan'), '20', None):
            with self.subTest(bad=bad), self.assertRaises(PG.RT.SpecError):
                PG.gate_disk_budget({'gate_disk_gb': bad}, archive())

    def test_large_compressible_source_is_charged_for_extraction(self):
        # Only a tar header is needed to represent a large file for budget calculation.
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as tf:
            item = tarfile.TarInfo('large-source')
            item.size = 3 * 1024**3
            # tar writer would materialize it; a sparse test member uses mocked iteration instead.
        with patch.object(tarfile, 'open') as opened:
            opened.return_value.__enter__.return_value.__iter__.return_value = iter([item])
            budget = PG.gate_disk_budget({}, buf.getvalue())
        self.assertEqual(budget['runtime_gb'], 25)
        self.assertGreaterEqual(budget['pick_gb'], budget['runtime_gb'])


class RemoteAdmission(unittest.TestCase):
    def exercise(self, host='auto', disk=None, reject=False):
        with tempfile.TemporaryDirectory() as td, contextlib.ExitStack() as stack:
            root = Path(td)
            kd = root / 'physical/kit'
            kd.mkdir(parents=True)
            (kd / 'floorplan.json').write_text(json.dumps({'referenced': []}))
            stack.enter_context(patch.object(PG, 'ROOT', root))
            stack.enter_context(patch.dict(PG.os.environ, {'TMPDIR': td}))
            stack.enter_context(patch.object(PG, 'absent_working_inputs', return_value=[]))
            stack.enter_context(patch.object(PG, 'referenced_closure', return_value=(set(), {}, set())))
            stack.enter_context(patch.object(PG.SB, 'git_head', return_value='abc'))
            stack.enter_context(patch.object(PG.HO, 'capture_plan', return_value=({'files': []}, {})))
            stack.enter_context(patch.object(PG, 'ship_tar', return_value=archive()))
            stack.enter_context(patch.object(PG.SB, 'snapshot', return_value={
                'commit': 'abc', 'archive_sha256': 'sha', 'files': []} ))
            stack.enter_context(patch.object(PG, 'gate_consumed', return_value={}))
            analyse = stack.enter_context(patch.object(PG, 'analyse_remote'))
            calls = []
            def run(cmd, **kwargs):
                calls.append(cmd)
                if '--pick' in cmd:
                    return subprocess.CompletedProcess(cmd, 1 if reject else 0,
                                                       '' if reject else 'ot-test\n', 'disk too small' if reject else '')
                return subprocess.CompletedProcess(cmd, 0, b'', b'')
            stack.enter_context(patch.object(PG.subprocess, 'run', side_effect=run))
            gate = PG.Gate()
            PG.remote(gate, kd, {'name': 'test', 'top': 'top', 'clock_port': 'ck', 'gate_disk_gb': 30},
                      host, 60, 16, True, disk)
            if reject:
                self.assertEqual(gate.verdict, 'FAIL')
                self.assertEqual(len(calls), 1)  # no upload, no started job
                analyse.assert_not_called()
            else:
                self.assertEqual(gate.source_binding['disk_admission']['reserve_gb'], 30 if disk is None else 7)
                analyse.assert_called_once()
            return calls

    def test_auto_checks_staging_before_upload_and_extraction_at_runtime(self):
        calls = self.exercise()
        pick, runtime = calls[0], calls[-1]
        self.assertEqual(pick, ['ot-run', '--mem', '16', '--disk', '32',
                                '--dir', '/srv/opentallas-scratch', '--pick'])
        self.assertIn('--disk', runtime)
        self.assertEqual(runtime[runtime.index('--disk') + 1], '32')
        self.assertEqual(runtime[runtime.index('--hosts') + 1], 'ot-test')
        self.assertNotIn('ot-heavy', runtime)

    def test_explicit_host_uses_same_disk_checks_and_cli_override(self):
        calls = self.exercise(host='ot-test', disk=6.5)
        self.assertEqual(calls[0][-2:], ['--hosts', 'ot-test'])
        self.assertEqual(calls[0][calls[0].index('--disk') + 1], '9')
        self.assertEqual(calls[-1][calls[-1].index('--disk') + 1], '9')

    def test_no_disk_qualifying_host_does_not_ship_or_run(self):
        self.exercise(reject=True)


if __name__ == '__main__':
    unittest.main()
