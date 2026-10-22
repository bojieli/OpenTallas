import contextlib
import io
from unittest.mock import patch
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import types
import unittest

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location('walker', HERE/'remote_walk.py')
W = importlib.util.module_from_spec(spec); spec.loader.exec_module(W)
spec = importlib.util.spec_from_file_location('preserve', HERE/'git_reconstruction.py')
P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)


class NestedGit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.root = self.base/'umbrella'; self.root.mkdir()
        self.repo = self.root/'nested'; self.repo.mkdir()
        self.git('init')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.repo/'pristine').write_text('tracked original\n')
        (self.repo/'modified').write_text('before\n')
        (self.repo/'deleted').write_text('delete me\n')
        (self.repo/'.gitignore').write_text('ignored\n')
        os.symlink('pristine', self.repo/'link')
        self.git('add', '.')
        self.git('commit', '-m', 'initial')
        (self.repo/'modified').write_text('staged content\n'); self.git('add', 'modified')
        (self.repo/'deleted').unlink()
        (self.repo/'untracked').write_text('unique\n')
        (self.repo/'ignored').write_text('ignored but required\n')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.DEVNULL)

    def preservation(self):
        capture = self.base/'capture'
        P.capture(self.root, capture)
        proof = self.base/'verified.json'
        P.verify(capture, proof)
        return capture, json.loads(proof.read_text())['worktrees']

    def test_nested_valid_proof_excludes_only_pristine(self):
        capture, proofs = self.preservation()
        pristine = W.pristine_files(str(self.repo), proofs, require_proof=True)
        self.assertIn('pristine', pristine)
        self.assertNotIn('modified', pristine)  # staged changes also preserved
        self.assertNotIn('deleted', pristine)
        self.assertNotIn('untracked', pristine)
        self.assertNotIn('ignored', pristine)
        # Symlinks are handled before pristine exclusion by the walker.
        self.assertTrue((self.repo/'link').is_symlink())
        proof = proofs[str(self.repo)]
        self.assertIn(b'deleted', (capture/proof['metadata_dir']/'working.diff').read_bytes())
        self.assertEqual(P.sha(self.repo/'.git/index'), proof['index_sha256'])

    def test_actual_nested_walk_preserves_changes_ignored_and_links(self):
        _, proofs = self.preservation()
        proof = self.base/'proof.json'; proof.write_text(json.dumps(dict(worktrees=proofs)))
        lists = self.base/'lists'; lists.mkdir()
        out = io.StringIO()
        payload = dict(roots=[str(self.root)], hash=True, git_proofs=str(proof))
        with patch.object(W, 'LST', str(lists)), patch('sys.stdin', io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(out):
            W.main()
        rid = json.loads(out.getvalue())[str(self.root)]['id']
        names = {line.split('\t')[0] for line in (lists/(rid+'.lst')).read_text().splitlines()}
        self.assertNotIn('nested/pristine', names)
        self.assertTrue({'nested/modified', 'nested/ignored', 'nested/untracked', 'nested/link'} <= names)

    def test_missing_unique_head_in_bundle_refuses_proof(self):
        out = self.base/'capture'; P.capture(self.root, out)
        self.git('commit', '-m', 'not present in saved bundle')
        head = self.git('rev-parse', 'HEAD').decode().strip()
        manifest = json.loads((out/'source_manifest.json').read_text())
        manifest['worktrees'][str(self.repo)]['head'] = head
        (out/'source_manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(subprocess.CalledProcessError):
            P.verify(out, self.base/'bad-proof.json')
        self.assertFalse((self.base/'bad-proof.json').exists())

    def test_unique_head_without_closure_copies_all(self):
        self.assertEqual(W.pristine_files(str(self.repo), {}, True), set())
        capture, proofs = self.preservation()
        self.git('commit', '-m', 'unique unpublished head')
        self.assertEqual(W.pristine_files(str(self.repo), proofs, True), set())

    def test_changed_index_or_diff_refuses_old_proof(self):
        _, proofs = self.preservation()
        (self.repo/'modified').write_text('later working change\n')
        self.assertEqual(W.pristine_files(str(self.repo), proofs, True), set())
        self.git('add', 'modified')
        self.assertEqual(W.pristine_files(str(self.repo), proofs, True), set())

    def test_missing_bundle_or_corruption_never_verifies(self):
        out = self.base/'capture'; P.capture(self.root, out)
        bundle = next(out.glob('*.bundle'))
        bundle.write_bytes(bundle.read_bytes()[:-10]+b'corruption')
        with self.assertRaises(AssertionError):
            P.verify(out, self.base/'bad-proof.json')
        self.assertFalse((self.base/'bad-proof.json').exists())

    def test_broken_nested_git_pointer_preserves_full_copy(self):
        broken = self.root/'broken'; broken.mkdir()
        (broken/'.git').write_text('gitdir: /missing/preexisting-worktree-metadata\n')
        (broken/'source').write_text('unique surviving source\n')
        out, proofs = self.preservation()
        manifest = json.loads((out/'source_manifest.json').read_text())
        self.assertIn(str(broken), manifest['errors'])
        self.assertNotIn(str(broken), proofs)
        self.assertEqual(W.pristine_files(str(broken), proofs, True), set())
        self.assertIn('pristine', W.pristine_files(str(self.repo), proofs, True))

    def test_new_unique_ref_invalidates_same_head_index_proof(self):
        _, proofs = self.preservation()
        tree = self.git('rev-parse', 'HEAD^{tree}').decode().strip()
        extra = subprocess.check_output(['git', '-C', str(self.repo), 'commit-tree', tree], input=b'unique ref-only commit\n').decode().strip()
        self.git('update-ref', 'refs/heads/unpublished-extra', extra)
        self.assertEqual(W.pristine_files(str(self.repo), proofs, True), set())

    def test_fsync_failure_cannot_publish_verified_proof(self):
        out = self.base/'capture'; P.capture(self.root, out)
        proof = self.base/'proof.json'
        with patch.object(P, 'sync_tree', side_effect=OSError('forced fsync failure')):
            with self.assertRaises(OSError):
                P.verify(out, proof)
        self.assertFalse(proof.exists())

    def test_verification_sync_precedes_durable_proof(self):
        out = self.base/'capture'; P.capture(self.root, out)
        proof = self.base/'proof.json'; events = []; actual = P.durable_json
        def save(path, data):
            self.assertEqual(events, ['synced'])
            events.append('proof')
            actual(path, data)
        with patch.object(P, 'sync_tree', side_effect=lambda path: events.append('synced')), patch.object(P, 'durable_json', side_effect=save):
            P.verify(out, proof)
        self.assertEqual(events, ['synced', 'proof'])

    def test_stat_only_change_cannot_refresh_live_source_index(self):
        before = P.sha(self.repo/'.git/index')
        st = (self.repo/'pristine').stat()
        os.utime(self.repo/'pristine', ns=(st.st_atime_ns, st.st_mtime_ns+2000000000))
        _, proofs = self.preservation()
        self.assertEqual(P.sha(self.repo/'.git/index'), before)
        # With refresh disabled, Git conservatively names a stat-only change: copy the extra file.
        self.assertNotIn('pristine', W.pristine_files(str(self.repo), proofs, True))
        self.assertEqual(P.sha(self.repo/'.git/index'), before)

    def test_missing_proof_does_not_run_unnecessary_git_diff(self):
        with patch('subprocess.run') as run:
            self.assertEqual(W.pristine_files(str(self.repo), {}, True), set())
            run.assert_not_called()

    def test_raw_source_index_and_refs_unchanged(self):
        before = P.sha(self.repo/'.git/index')
        refs = self.git('for-each-ref')
        self.preservation()
        self.assertEqual(P.sha(self.repo/'.git/index'), before)
        self.assertEqual(self.git('for-each-ref'), refs)


class RequiredRoots(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('retire_required', HERE/'epyc6_retire.py')
        self.m = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.m.STATE = self.tmp.name; self.m.LOG = str(pathlib.Path(self.tmp.name)/'watch.log')
        self.root = '/srv/opentallas-scratch/claude/qwen-kvsys'
        self.args = types.SimpleNamespace(no_copy=False)

    def check(self, resolved, error=None):
        with patch.object(self.m, 'jload', side_effect=lambda p, d: {'roots':[self.root]} if p.endswith('required_roots.json') else d), \
             patch.object(self.m, 'pending_roots', return_value=[]), patch.object(self.m, 'work_dirs', return_value=set()), \
             patch.object(self.m, 'resolve', return_value=resolved), patch.object(self.m, 'note_pending'), \
             patch.object(self.m, 'check_required_archive_inputs', return_value=[]), \
             patch.object(self.m, 'copy_roots', return_value=({self.root:{'bytes':10}}, {self.root:error} if error else {}, {})) as copy:
            result = self.m.check_pending(True, {}, self.args)
            return result, copy.call_args

    def test_required_umbrella_uses_filtered_copy_and_hash_gate(self):
        (ok, why), call = self.check({self.root:{'dir':self.root,'depth':4,'kb':3_000_000_000}})
        self.assertTrue(ok, why)
        self.assertEqual(call.args[0], [self.root]); self.assertTrue(call.kwargs['final'])

    def test_required_unresolved_never_silently_skipped(self):
        (ok, why), _ = self.check({})
        self.assertFalse(ok); self.assertIn('not resolved exactly', str(why))

    def test_required_full_copy_over_capacity_remains_wait(self):
        (ok, why), _ = self.check({self.root:{'dir':self.root,'depth':4,'kb':3_000_000_000}}, 'archive floor blocks full copy')
        self.assertFalse(ok); self.assertIn('archive floor', str(why))


if __name__ == '__main__':
    unittest.main()
