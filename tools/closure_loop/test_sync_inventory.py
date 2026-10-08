import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import closure_loop as C


class SyncInventoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'tools').mkdir()
        (self.root / 'tools/run.py').write_text('pinned runner')
        (self.root / 'model.json').write_text('pinned model')
        self.git('add', '--', 'tools', 'model.json')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'fixture')
        self.git('update-ref', 'refs/remotes/origin/fixture', 'HEAD')
        commit = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], text=True).strip()
        self.job = {'host': 'localhost', 'run': str(self.root / 'remote'), 'spec': {'source': {
            'branch': 'fixture', 'commit': commit, 'paths': ['tools'], 'extra_paths': ['model.json'],
            'required_files': ['tools/run.py', 'model.json']}}}

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.root), *args], check=True)

    def sync(self):
        with patch.object(C, 'REPO', self.root), patch.object(C, 'gfetch'), patch.object(C, 'ship_helpers'):
            C.sync_source(self.job)

    def test_missing_dependency_fails_before_remote_command(self):
        self.job['spec']['source']['extra_paths'] = []
        with patch.object(C, 'ssh', side_effect=AssertionError('remote touched')) as remote:
            with self.assertRaisesRegex(ValueError, 'model.json'):
                self.sync()
            remote.assert_not_called()
        self.assertFalse((self.root / 'remote').exists())
        self.assertFalse(self.job['source_synced'])

    def test_transfers_identical_checked_tar_and_pinned_sources(self):
        (self.root / 'tools/run.py').write_text('uncommitted wrong runner')
        run = subprocess.run
        transferred = []
        def inspect(cmd, **kw):
            if isinstance(cmd, list) and cmd[:2] == ['bash', '-c'] and cmd[-1].startswith('tar -xf -'):
                stream = kw['stdin']; position = stream.tell()
                transferred.append(hashlib.sha256(stream.read()).hexdigest())
                stream.seek(position)
            return run(cmd, **kw)
        with patch.object(C.subprocess, 'run', side_effect=inspect):
            self.sync()
        receipt = self.job['source_archive']
        self.assertEqual(transferred, [receipt['archive_sha256']])
        self.assertEqual((self.root / 'remote/src/tools/run.py').read_text(), 'pinned runner')
        self.assertEqual(json.loads((self.root / 'remote/cl/source_archive.json').read_text()), receipt)
        self.assertTrue(self.job['source_synced'])

    def test_legacy_inventory_absent_uses_existing_stream(self):
        del self.job['spec']['source']['required_files']
        with patch.object(C, 'build_archive', side_effect=AssertionError('legacy preflight changed')):
            self.sync()
        self.assertNotIn('source_archive', self.job)
        self.assertTrue(self.job['source_synced'])

    def test_empty_inventory_fails_before_remote_command(self):
        self.job['spec']['source']['required_files'] = []
        with patch.object(C, 'ssh', side_effect=AssertionError('remote touched')):
            with self.assertRaisesRegex(ValueError, 'nonempty'):
                self.sync()

if __name__ == '__main__':
    unittest.main()
