import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import pre_route_gate as PG
import source_binding as SB


class SourceBindingTest(unittest.TestCase):
    def test_remote_sha256_receipt_is_parsed_with_other_statuses(self):
        digest = "083f8575af36b60465bef1514c455caaecca55fffb011014deae06541eb6275e"
        values = PG.parse_remote_values("GATE_SOURCE_ARCHIVE_SHA256=" + digest +
                                        "\nGATE_FLOW_RC=0 GATE_FLOW_S=47\nGATE_CTS_RC=0\n")
        self.assertEqual(values["GATE_SOURCE_ARCHIVE_SHA256"], digest)
        self.assertEqual(values["GATE_FLOW_RC"], "0")
        self.assertEqual(values["GATE_FLOW_S"], "47")
        self.assertEqual(values["GATE_CTS_RC"], "0")

    def test_remote_wrong_digest_remains_distinct_from_expected_digest(self):
        expected = "a" * 64
        values = PG.parse_remote_values("GATE_SOURCE_ARCHIVE_SHA256=" + "b" * 64)
        self.assertNotEqual(values["GATE_SOURCE_ARCHIVE_SHA256"], expected)

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def init(self, root):
        root.mkdir()
        self.git(root, 'init')
        self.git(root, 'config', 'user.email', 'test@example.com')
        self.git(root, 'config', 'user.name', 'Test')
        (root / 'kit').mkdir()
        (root / 'kit/input.v').write_text('before\n')
        self.git(root, 'add', 'kit/input.v')
        self.git(root, 'commit', '-m', 'before')
        return SB.git_head(root)

    def test_gate_completion_after_head_advances_remains_bound_to_staged_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root, daemon = Path(td) / 'repo', Path(td) / 'daemon'
            start = self.init(root)
            daemon.mkdir()
            with patch.object(PG, 'ROOT', root), patch.object(PG, 'DAEMON_TREE', daemon), patch.object(PG, 'SHIP_HELPERS', ()):
                data = PG.ship_tar({'kit'})
                binding = SB.snapshot(data, root, start, daemon, None, ())
                binding['remote_archive_verified'] = True
                # A run is in flight while another worker changes and commits its source.
                (root / 'kit/input.v').write_text('after\n')
                self.git(root, 'add', 'kit/input.v')
                self.git(root, 'commit', '-m', 'advance HEAD during gate')
                gate = PG.Gate()
                gate.source_binding = binding
                gate.clock = {'max_root_sinks': 9000}
                completed = PG.write_gate_result(gate, root / 'kit', False, 'test-host')
                self.assertEqual(completed['commit'], start)
                self.assertNotEqual(SB.git_head(root), start)
                self.assertEqual(binding['commit'], start)
                self.assertIsNone(PG.kit_clock_evidence(root / 'kit'))
                self.assertEqual(PG.kit_clock_evidence(root / 'kit', start)['max_root_sinks'], 9000)
                with tarfile.open(fileobj=io.BytesIO(data)) as tf:
                    self.assertEqual(tf.extractfile('kit/input.v').read(), b'before\n')

    def test_dirty_generated_kit_and_daemon_overlay_are_exact_hashes_not_commit_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root, daemon = Path(td) / 'repo', Path(td) / 'daemon'
            start = self.init(root)
            daemon.mkdir()
            (daemon / 'kit').mkdir()
            (daemon / 'kit/input.v').write_text('actual daemon version\n')
            (root / 'kit/generated.tcl').write_text('generated untracked\n')
            (root / 'kit/gate_result.json').write_text('old irrelevant receipt')
            with patch.object(PG, 'ROOT', root), patch.object(PG, 'DAEMON_TREE', daemon), patch.object(PG, 'SHIP_HELPERS', ('kit/input.v',)):
                data = PG.ship_tar({'kit', 'kit/input.v'})
                binding = SB.snapshot(data, root, start, daemon, None, ('kit/input.v',))
                self.assertIsNone(binding['commit'])
                self.assertEqual(binding['identity'], 'exact_content_snapshot')
                self.assertNotIn('kit/gate_result.json', [f['path'] for f in binding['files']])
                self.assertTrue(SB.validate(binding, root, daemon)[0])
                (daemon / 'kit/input.v').write_text('changed daemon\n')
                self.assertFalse(SB.validate(binding, root, daemon)[0])

    def test_legacy_result_cannot_qualify_new_source(self):
        with tempfile.TemporaryDirectory() as td:
            kd = Path(td)
            (kd / 'gate_result.json').write_text(json.dumps({'commit': 'later-head', 'clock': {'max_root_sinks': 9000}}))
            gate = PG.Gate()
            PG.check_clock_evidence(gate, kd)
            self.assertEqual(gate.verdict, 'FAIL')
            self.assertIsNone(PG.kit_clock_evidence(kd))

    def test_remote_script_verifies_archive_before_extracting(self):
        script = PG.REMOTE_SH.format(R='/tmp/test', ARCHIVE_SHA256='a' * 64, COMMIT='snapshot-sha256:abc', CAP=1,
                                    KIT='kit', IMG='unused', RC='', TOP='test', CTS=0, PGM=1, CLK='clk')
        self.assertLess(script.index('sha256sum'), script.index('tar -xzf'))
        self.assertIn('GATE_SOURCE_ARCHIVE_SHA256=$ACTUAL', script)


if __name__ == '__main__':
    unittest.main()
