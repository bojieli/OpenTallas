"""Destination-local process locking, verified reuse, and atomic snapshot publication."""
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_store as K


class SnapshotFetch(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="snap-fetch-"))
        source = self.t/'input/plan.json'
        source.parent.mkdir();source.write_text('{"source": 1}')
        donor = K.snap({'inputs': [{'role': 'plan', 'path': str(source), 'required': True}]},
                       str(self.t/'donor/snaps'), store_root=str(self.t/'store'), log=lambda *a: None)
        self.original = Path(donor['dir'])
        self.dest = self.t/'target'/donor['id']
        self.dest.parent.mkdir()
        self.input = str(source)
        # A transferred manifest always names the destination absolute identity.
        self.manifest = json.loads((self.original/'MANIFEST.json').read_text())
        self.manifest['kit_inputs'] = str(self.dest/'root')

    def tearDown(self):
        shutil.rmtree(self.t)

    def copy(self, host, dest, partial):
        self.assertEqual(host, 'donor1')
        self.assertEqual(dest, str(self.dest))
        shutil.copytree(self.original, partial, dirs_exist_ok=True)
        (Path(partial)/'MANIFEST.json').write_text(json.dumps(self.manifest))
        (Path(partial)/'.verified').unlink(missing_ok=True)

    def test_two_processes_have_one_writer_then_verified_reuse(self):
        ctx = multiprocessing.get_context('fork')
        started, release, second = ctx.Event(), ctx.Event(), ctx.Event()
        copies, results = ctx.Value('i', 0), ctx.Queue()
        def worker(waiting=False):
            if waiting:second.set()
            def copy(host, dest, partial):
                with copies.get_lock():copies.value += 1
                started.set()
                if not release.wait(10):raise RuntimeError('test coordinator did not release copy')
                self.copy(host, dest, partial)
            try:results.put(('ok', K.fetch(str(self.dest), 'donor1', copy)))
            except Exception as exc:results.put(('error', str(exc)))
        first = ctx.Process(target=worker);first.start()
        self.assertTrue(started.wait(10))
        self.assertFalse(self.dest.exists(), 'partial must never be published')
        peer = ctx.Process(target=worker, args=(True,));peer.start()
        self.assertTrue(second.wait(10));release.set()
        records = [results.get(timeout=10), results.get(timeout=10)]
        first.join(10);peer.join(10)
        self.assertEqual(first.exitcode, 0);self.assertEqual(peer.exitcode, 0)
        self.assertEqual([r[0] for r in records], ['ok', 'ok'])
        self.assertEqual(sorted(r[1]['reused'] for r in records), [False, True])
        self.assertEqual(copies.value, 1)
        self.assertTrue((self.dest/'.verified').exists())
        K.verify(str(self.dest))

    def test_failed_copy_is_preserved_without_publishing_and_retry_can_finish(self):
        def broken(host, dest, partial):
            (Path(partial)/'failure.log').write_text('measured-copy-failure')
            raise OSError('copy failed')
        with self.assertRaisesRegex(K.StoreError, 'partial retained'):
            K.fetch(str(self.dest), 'donor1', broken)
        self.assertFalse(self.dest.exists())
        partials = list(self.dest.parent.glob('.*.partial.*'))
        self.assertEqual(len(partials), 1)
        self.assertEqual((partials[0]/'failure.log').read_text(), 'measured-copy-failure')
        self.assertFalse(K.fetch(str(self.dest), 'donor1', self.copy)['reused'])
        self.assertTrue(partials[0].exists())

    def test_corrupt_transfer_never_gets_verified_or_published(self):
        def corrupt(host, dest, partial):
            self.copy(host, dest, partial)
            f = Path(partial)/'root'/self.input.lstrip('/')
            f.unlink();f.write_text('bad bytes')
        with self.assertRaisesRegex(K.StoreError, 'differ from the manifest'):
            K.fetch(str(self.dest), 'donor1', corrupt)
        self.assertFalse(self.dest.exists())
        self.assertFalse(any(p.name == '.verified' for p in self.dest.parent.glob('.*.partial.*/*')))

    def test_unverified_existing_legacy_destination_is_never_changed(self):
        self.dest.mkdir();(self.dest/'active.log').write_text('legacy writer')
        with self.assertRaisesRegex(K.StoreError, 'existing unverified destination retained'):
            K.fetch(str(self.dest), 'donor1', lambda *a: self.fail('must not copy'))
        self.assertEqual((self.dest/'active.log').read_text(), 'legacy writer')

    def test_stale_verified_marker_does_not_hide_corruption(self):
        K.fetch(str(self.dest), 'donor1', self.copy)
        f = self.dest/'root'/self.input.lstrip('/')
        f.unlink();f.write_text('bad bytes')
        with self.assertRaisesRegex(K.StoreError, 'differ from the manifest'):
            K.fetch(str(self.dest), 'donor1', lambda *a: self.fail('must not copy'))
        self.assertFalse((self.dest/'.verified').exists())

    def test_legacy_writer_appearing_during_copy_is_preserved(self):
        def overlapping(host, dest, partial):
            self.copy(host, dest, partial)
            self.dest.mkdir();(self.dest/'active.log').write_text('new legacy writer')
        with self.assertRaisesRegex(K.StoreError, 'destination appeared'):
            K.fetch(str(self.dest), 'donor1', overlapping)
        self.assertEqual((self.dest/'active.log').read_text(), 'new legacy writer')
        self.assertFalse((self.dest/'.verified').exists())
        self.assertEqual(len(list(self.dest.parent.glob('.*.partial.*'))), 1)

    def test_atomic_publish_cannot_replace_even_an_empty_racing_destination(self):
        import ctypes
        from types import SimpleNamespace
        from unittest.mock import patch
        libc = ctypes.CDLL(None, use_errno=True)
        def racing_rename(*args):
            self.dest.mkdir()  # arrives after the ordinary existence check
            return libc.renameat2(*args)
        with patch('ctypes.CDLL', return_value=SimpleNamespace(renameat2=racing_rename)):
            with self.assertRaisesRegex(K.StoreError, 'File exists'):
                K.fetch(str(self.dest), 'donor1', self.copy)
        self.assertEqual(list(self.dest.iterdir()), [])
        self.assertEqual(len(list(self.dest.parent.glob('.*.partial.*'))), 1)


if __name__ == '__main__':
    unittest.main()
