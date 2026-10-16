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

    def test_complete_remote_path_parses_digit_bearing_archive_key_and_clock(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root, daemon = Path(td) / 'repo', Path(td) / 'daemon'
            self.init(root)
            daemon.mkdir()
            (root / 'kit/floorplan.json').write_text(json.dumps({'referenced': ['kit/input.v'], 'die': [0, 0, 80, 80], 'blocks': []}))
            staged = {}
            real_run = subprocess.run
            def run(cmd, **kw):
                if cmd[0] == 'git':
                    return real_run(cmd, **kw)
                if cmd[0] == 'ssh' and '.tgz' in cmd[-1]:
                    staged['archive'] = kw['input']
                if cmd[0] == 'ot-run' and '--pick' in cmd:
                    # Disk/memory admission (ea71c5c16) picks the host before upload (text mode).
                    return subprocess.CompletedProcess(cmd, 0, 'test-host\n', '')
                if (cmd[0] == 'ssh' and 'ot-heavy' in cmd[-1]) or (cmd[0] == 'ot-run' and '--' in cmd):
                    out = ('GATE_SOURCE_ARCHIVE_SHA256=' + hashlib.sha256(staged['archive']).hexdigest() + '\n'
                           'GATE_FLOW_RC=0 GATE_FLOW_S=1\nGATE_IOP_RC=0\nGATE_CTS_RC=0\n'
                           'GATE_CK_RC=0\nGATE_DONE\n'
                           'GATE_TB textbook_lint: INFO clock_roots max_root_sinks=48000 root=port:clk\n'
                           'GATE_CK tt insertion all 210.0..280.0 ps\n')
                    return subprocess.CompletedProcess(cmd, 0, out.encode(), b'')
                return subprocess.CompletedProcess(cmd, 0, b'', b'')
            spec = {'name': 'probe', 'top': 'probe', 'kind': 'tile', 'clock_port': 'clk', 'route': {'pd': .5}}
            with patch.object(PG, 'ROOT', root), patch.object(PG, 'DAEMON_TREE', daemon), patch.object(PG, 'SHIP_HELPERS', ()), \
                    patch.object(PG, 'referenced_closure', return_value=({'kit/input.v'}, set(), set())), \
                    patch.object(PG.subprocess, 'run', side_effect=run), patch.object(PG.HO, 'HELPERS', ()):
                g = PG.Gate()
                PG.remote(g, root / 'kit', spec, 'test-host', 10, 1, True)
                self.assertTrue(g.source_binding['remote_archive_verified'])
                self.assertEqual(g.clock['tt_insertion_ps'], 280.)
                self.assertEqual(g.clock['tt_spread_ps'], 70.)
                # the mocked remote returns no layout dump (owner rule 20:45 WARN); everything else must be INFO
                self.assertEqual([i['check'] for i in g.items if i['severity'] != 'INFO'], ['layout_images'])

    def test_recovery_requires_full_manifest_log_script_and_staged_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as td:
            root, daemon = Path(td) / 'repo', Path(td) / 'daemon'
            start = self.init(root)
            daemon.mkdir()
            with patch.object(PG, 'ROOT', root), patch.object(PG, 'DAEMON_TREE', daemon), patch.object(PG, 'SHIP_HELPERS', ()):
                data = PG.ship_tar({'kit'})
            binding = SB.snapshot(data, root, start, daemon, None, ())
            script = b'exact executed script'
            binding['remote_script_sha256'] = hashlib.sha256(script).hexdigest()
            (root / 'SOURCE_COMMIT').write_text(start)
            log = ('GATE_SOURCE_ARCHIVE_SHA256=' + binding['archive_sha256'] + '\n').encode()
            recovered = SB.recover_verified_snapshot(binding, root, log, script)
            self.assertTrue(recovered['remote_archive_verified'])
            self.assertEqual(recovered['commit'], start)
            with self.assertRaises(ValueError):
                SB.recover_verified_snapshot(binding, root, b'wrong archive log', script)
            with self.assertRaises(ValueError):
                SB.recover_verified_snapshot(binding, root, log, b'changed script')
            (root / 'kit/input.v').write_text('changed source')
            with self.assertRaises(ValueError):
                SB.recover_verified_snapshot(binding, root, log, script)

    def test_recovery_parser_never_clears_a_source_mismatch_failure(self):
        with tempfile.TemporaryDirectory() as td:
            kd = Path(td)
            (kd / 'floorplan.json').write_text(json.dumps({'die': [0, 0, 80, 80], 'blocks': []}))
            binding = {'commit': None, 'start_commit': 'original-commit', 'archive_sha256': 'a' * 64}
            out = ('GATE_SOURCE_ARCHIVE_SHA256=' + 'a' * 64 + '\nGATE_FLOW_RC=0 GATE_FLOW_S=1\n'
                   'GATE_IOP_RC=0\nGATE_CTS_RC=0\n'
                   'GATE_TB textbook_lint: INFO clock_roots max_root_sinks=48000 root=port:clk\n'
                   'GATE_CK tt insertion all 210.0..280.0 ps\n')
            spec = {'kind': 'tile', 'clock_port': 'clk', 'route': {'pd': .5}}
            g = PG.Gate()
            g.source_binding = binding
            g.add('FAIL', 'source_binding', 'candidate route source has changed')
            PG.analyse_remote(g, kd, spec, out, True, binding, 10, 'original-host')
            self.assertEqual(g.verdict, 'FAIL')
            self.assertEqual(g.clock['tt_insertion_ps'], 280.)
            self.assertEqual(binding['start_commit'], 'original-commit')
            self.assertIsNone(binding['commit'])

    def test_remote_script_verifies_archive_before_extracting(self):
        script = PG.REMOTE_SH.format(R='/tmp/test', ARCHIVE_SHA256='a' * 64, COMMIT='snapshot-sha256:abc', CAP=1,
                                    KIT='kit', IMG='unused', RC='', TOP='test', CTS=0, PGM=1, CLK='clk',
                                    TRIAL=0, CLKS='clk', STEP_CAP=1)
        self.assertLess(script.index('sha256sum'), script.index('tar -xzf'))
        self.assertIn('GATE_SOURCE_ARCHIVE_SHA256=$ACTUAL', script)


if __name__ == '__main__':
    unittest.main()
