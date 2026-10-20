"""Exact HC terminal-stdout repair, never arbitrary benchmark/source drift."""
import copy
import hashlib
import io
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_binding as SB

FIXTURE = Path(__file__).parent / 'fixtures/hc_tree16_wrapper'
OLD = (FIXTURE / 'old.sh').read_bytes()
NEW = (FIXTURE / 'new.sh').read_bytes()


class WrapperCompatibility(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def setup_snapshot(self, td, old=OLD):
        root, daemon = Path(td) / 'repo', Path(td) / 'daemon'
        root.mkdir(); daemon.mkdir()
        self.git(root, 'init'); self.git(root, 'config', 'user.email', 'test@example.com')
        self.git(root, 'config', 'user.name', 'Test')
        files = {SB.HC_TREE16_WRAPPER: old, 'rtl/design.sv': b'module design; endmodule\n',
                 'physical/ref_tile/hc/spec.json': b'{"top":"design"}\n', 'tools/helper.py': b'# helper\n'}
        for path, data in files.items():
            target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        (daemon / 'tools').mkdir(); (daemon / 'tools/helper.py').write_bytes(files['tools/helper.py'])
        self.git(root, 'add', '.'); self.git(root, 'commit', '-m', 'staged')
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode='w:gz') as tf:
            for path, data in files.items():
                info = tarfile.TarInfo(path); info.size = len(data); tf.addfile(info, io.BytesIO(data))
        binding = SB.snapshot(archive.getvalue(), root, SB.git_head(root), daemon, None, ('tools/helper.py',))
        binding['consumed'] = SB.consumed_record(files, binding['files'], 'test complete consumed set')
        return root, daemon, binding

    def test_literal_reviewed_pair_only(self):
        self.assertTrue(SB.reviewed_bench_wrapper_change(SB.HC_TREE16_WRAPPER, OLD, NEW))
        for path, old, new in [('other.sh', OLD, NEW), (SB.HC_TREE16_WRAPPER, NEW, OLD),
                               (SB.HC_TREE16_WRAPPER, OLD + b'\n', NEW),
                               (SB.HC_TREE16_WRAPPER, OLD, NEW + b'\necho PASS\n')]:
            with self.subTest(path=path, old=hashlib.sha256(old).hexdigest()):
                self.assertFalse(SB.reviewed_bench_wrapper_change(path, old, new))

    def test_exact_repair_preserves_snapshot_and_failed_verdict(self):
        with tempfile.TemporaryDirectory() as td:
            root, daemon, binding = self.setup_snapshot(td)
            (root / SB.HC_TREE16_WRAPPER).write_bytes(NEW)
            gate = {'verdict': 'FAIL', 'items': [{'severity': 'FAIL', 'check': 'physical'}]}
            before_binding, before_gate = copy.deepcopy(binding), copy.deepcopy(gate)
            for commit in (None, 'HEAD'):
                if commit:
                    self.git(root, 'add', '.'); self.git(root, 'commit', '-m', 'reviewed stdout repair')
                ok, why = SB.validate(binding, root, daemon, commit=commit, route_overlay=False, gate=gate)
                self.assertTrue(ok, why)
                self.assertIn('exact reviewed HC terminal-verdict stdout repair compatible', why)
                self.assertEqual(binding, before_binding)
                self.assertEqual(gate, before_gate)

    def test_every_other_consumed_input_remains_exact(self):
        for other in ('rtl/design.sv', 'physical/ref_tile/hc/spec.json', 'tools/helper.py', 'missing'):
            with self.subTest(other=other), tempfile.TemporaryDirectory() as td:
                root, daemon, binding = self.setup_snapshot(td)
                (root / SB.HC_TREE16_WRAPPER).write_bytes(NEW)
                if other == 'missing': (root / 'rtl/design.sv').unlink()
                else: ((daemon if other == 'tools/helper.py' else root) / other).write_bytes(b'changed\n')
                ok, why = SB.validate(binding, root, daemon, route_overlay=False)
                self.assertFalse(ok, why)
                self.assertNotIn('stdout repair compatible', why)

    def test_no_incomplete_consumed_record_or_unreviewed_bytes(self):
        for change in ('no_consumed', 'missing_sha', 'bad_count', 'bool_count', 'extra_wrapper_edit', 'other_old_bytes'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as td:
                root, daemon, binding = self.setup_snapshot(td, OLD + b'\n' if change == 'other_old_bytes' else OLD)
                (root / SB.HC_TREE16_WRAPPER).write_bytes(NEW + (b'\n' if change == 'extra_wrapper_edit' else b''))
                if change == 'no_consumed': binding.pop('consumed')
                elif change == 'missing_sha': binding['consumed']['sha256'].pop('rtl/design.sv')
                elif change == 'bad_count': binding['consumed']['count'] += 1
                elif change == 'bool_count': binding['consumed']['count'] = True
                ok, why = SB.validate(binding, root, daemon, route_overlay=False)
                self.assertFalse(ok, why)


if __name__ == '__main__':
    unittest.main()
