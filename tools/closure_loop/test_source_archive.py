import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from source_archive import build_archive, check_runtime


class SourceArchiveTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        for p in ('tools/run.py', 'physical/macro.v', 'compiler/models/config.json', 'results/model.json'):
            target = self.root / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(p)
        self.git('add', '--', 'tools', 'physical', 'compiler', 'results')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'fixture')
        self.inventory = dict(paths=['tools', 'physical'], required_files=['tools/run.py', 'physical/macro.v'])

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.root), *args], check=True, stdout=subprocess.DEVNULL)

    def build(self):
        return build_archive(self.root, 'HEAD', self.inventory, self.root / 'source.tar')

    def test_omitted_macro_is_rejected_before_output(self):
        self.inventory['paths'] = ['tools']
        with self.assertRaisesRegex(ValueError, 'physical/macro.v'):
            self.build()
        self.assertFalse((self.root / 'source.tar').exists())

    def test_model_extra_is_required_and_pinned_not_worktree(self):
        self.inventory['required_files'].append('results/model.json')
        with self.assertRaisesRegex(ValueError, 'results/model.json'):
            self.build()
        self.inventory['extra_paths'] = ['results/model.json']
        (self.root / 'results/model.json').write_text('uncommitted change')
        receipt = self.build()
        self.assertEqual(receipt['required_sha256']['results/model.json'], hashlib.sha256(b'results/model.json').hexdigest())
        with self.assertRaises(FileExistsError):
            self.build()

    def test_export_ignore_is_not_a_successful_archive(self):
        (self.root / '.gitattributes').write_text('physical/macro.v export-ignore\n')
        self.git('add', '--', '.gitattributes')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'ignore macro')
        with self.assertRaisesRegex(ValueError, 'physical/macro.v'):
            self.build()

    def test_runtime_checkpoint_missing_changed_and_verified(self):
        p = self.root / 'checkpoint'
        row = dict(path=str(p), sha256=hashlib.sha256(b'checkpoint').hexdigest())
        with self.assertRaises(FileNotFoundError):
            check_runtime([row])
        p.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            check_runtime([row])
        p.write_bytes(b'checkpoint')
        self.assertEqual(check_runtime([row])[0]['bytes'], 10)

    def test_invalid_paths_and_empty_inventory(self):
        for path in ('../physical', '/physical', '.', ':glob:*'):
            self.inventory['required_files'] = [path]
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                self.build()
        self.inventory['required_files'] = []
        with self.assertRaises(ValueError):
            self.build()


if __name__ == '__main__':
    unittest.main()
