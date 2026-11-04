"""Actual admission age survives cgroupfs timestamp refreshes."""
import importlib.machinery
import importlib.util
import pathlib
import types
import unittest
from unittest.mock import patch
loader = importlib.machinery.SourceFileLoader('scope_age', str(pathlib.Path(__file__).with_name('ot-heavy-reconcile')))
R = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(R)

class ScopeAge(unittest.TestCase):
    def snapshot(self, stamp):
        ages = {}
        output = f'Id=oth-test-1-100.scope\nControlGroup=/user.slice/test.scope\nActiveEnterTimestampMonotonic={stamp}\n'
        with patch.object(R.subprocess, 'run', return_value=types.SimpleNamespace(stdout=output)), patch.object(R.os.path, 'isdir', return_value=True), patch.object(R.time, 'monotonic', return_value=10000):
            paths = R.scope_cgroup_snapshot(['oth-test-1-100'], ages)
        return paths, ages
    def test_old_scope_uses_systemd_start(self):
        paths, ages = self.snapshot(1000000000)
        self.assertEqual(ages['oth-test-1-100'], 9000)
        self.assertEqual(paths['oth-test-1-100'], '/sys/fs/cgroup/user.slice/test.scope')
    def test_new_scope_remains_young(self):
        self.assertEqual(self.snapshot(9990000000)[1]['oth-test-1-100'], 10)
    def test_unavailable_timestamp_preserves_fallback(self):
        for stamp in ('', '0', 'unknown'):
            self.assertEqual(self.snapshot(stamp)[1], {})
    def test_no_negative_age(self):
        self.assertEqual(self.snapshot(10001000000)[1]['oth-test-1-100'], 0)
if __name__ == '__main__': unittest.main()
