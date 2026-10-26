"""Exercise real tar extraction through absolute scratch-root symlinks."""
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import unittest

loader = importlib.machinery.SourceFileLoader('ot_run_alias', str(Path(__file__).with_name('ot-run')))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)

class ScratchAliasCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.real = self.base / 'real'
        self.real.mkdir()
        self.alias = self.base / 'scratch.alias+2'
        self.alias.symlink_to(self.real, target_is_directory=True)

    def archive(self, links=False):
        stream = io.BytesIO()
        name = str(self.alias).lstrip('/')
        with tarfile.open(fileobj=stream, mode='w') as tf:
            item = tarfile.TarInfo(name + '/source.sv')
            item.size = 3
            item.mtime = int(time.time()) - 20
            tf.addfile(item, io.BytesIO(b'old'))
            if links:
                item = tarfile.TarInfo(name + '/symbolic')
                item.type = tarfile.SYMTYPE
                item.linkname = str(self.alias / 'source.sv')
                tf.addfile(item)
                item = tarfile.TarInfo(name + '/hard')
                item.type = tarfile.LNKTYPE
                item.linkname = name + '/source.sv'
                tf.addfile(item)
        return subprocess.run(['zstd', '-q', '-c'], input=stream.getvalue(), capture_output=True, check=True).stdout

    def extract(self, archive, env=None):
        return subprocess.run(['bash', '-c', m.tar_x([str(self.alias)])], input=archive,
                              capture_output=True, env=env)

    def test_absolute_alias_and_regex_characters_preserve_bytes(self):
        result = self.extract(self.archive())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.real / 'source.sv').read_bytes(), b'old')

    def test_newer_existing_file_is_preserved(self):
        file = self.real / 'source.sv'
        file.write_bytes(b'new')
        result = self.extract(self.archive())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(file.read_bytes(), b'new')

    def test_hardlink_target_transforms_but_symlink_payload_does_not(self):
        result = self.extract(self.archive(links=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(os.readlink(self.real / 'symbolic'), str(self.alias / 'source.sv'))
        self.assertEqual((self.real / 'hard').stat().st_ino, (self.real / 'source.sv').stat().st_ino)

    def test_zero_exit_cannot_stat_warning_is_not_success(self):
        bindir = self.base / 'bin'
        bindir.mkdir()
        fake = bindir / 'tar'
        fake.write_text('#!/bin/sh\ncat >/dev/null\necho "tar: source.sv: Warning: Cannot stat: Invalid cross-device link" >&2\nexit 0\n')
        fake.chmod(0o755)
        result = self.extract(self.archive(), dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ['PATH']))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Cannot stat', result.stderr)

if __name__ == '__main__':
    unittest.main()
