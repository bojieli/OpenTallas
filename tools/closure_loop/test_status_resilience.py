"""An unavailable fleet-report peer must not crash dispatch or suppress intake."""
import tempfile
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
import closure_loop as cl


class StatusResilience(unittest.TestCase):
    def test_timeout_and_transport_error_preserve_status_and_next_intake(self):
        for exception in (subprocess.TimeoutExpired('ssh', 30), OSError('transport unavailable')):
            with self.subTest(exception=type(exception).__name__), tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/'STATUS.md'
                path.write_text('old status\n')
                hosts = [{'name': 'bad', 'label': 'bad', 'cores': 8}, {'name': 'good', 'label': 'good', 'cores': 16}]
                healthy = SimpleNamespace(returncode=0, stdout='4\n128\n')
                with patch.object(cl, 'STATUS_MD', path), patch.object(cl, 'all_jobs', return_value=[]), \
                     patch.object(cl, 'hosts_table', return_value=hosts), patch.object(cl, 'ssh', side_effect=[exception, healthy, exception, healthy]), \
                     patch.object(cl, 'ingest') as ingest, patch.object(cl, 'release_bulk'), patch.object(cl, 'release_deep'), \
                     patch.object(cl, 'schedule_recovery'), patch.object(cl, '_POOL', Mock()), patch.object(cl, 'STATE', Path(temp)):
                    # Exercise the real dispatch tick twice: the failed status
                    # peer from tick 1 must not prevent tick 2 from ingesting.
                    cl.tick(SimpleNamespace())
                    cl.tick(SimpleNamespace())
                    self.assertEqual(ingest.call_count, 2)
                result = path.read_text()
                self.assertIn('- bad: unreachable', result)
                self.assertIn('- good: load1 4/16', result)
                self.assertFalse(path.with_suffix('.tmp').exists())

    def test_invalid_host_metrics_are_unreachable(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cl, 'STATUS_MD', Path(temp)/'STATUS.md'), \
             patch.object(cl, 'all_jobs', return_value=[]), patch.object(cl, 'hosts_table', return_value=[{'name': 'bad', 'label': 'bad'}]), \
             patch.object(cl, 'ssh', return_value=SimpleNamespace(returncode=0, stdout='not-a-load 128')):
            cl.write_status()
            self.assertIn('bad: unreachable', (Path(temp)/'STATUS.md').read_text())


if __name__ == '__main__':
    unittest.main()
