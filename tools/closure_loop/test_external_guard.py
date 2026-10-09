import json
from pathlib import Path
import tempfile
import unittest

from external_reservations import remaining_bytes


class ExternalGuardTests(unittest.TestCase):
    def test_live_peak_remainder_and_pid_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pid = root / 'proc' / '123'
            pid.mkdir(parents=True)
            (pid / 'cmdline').write_bytes(b'verilator\0pinned-source\0')
            (pid / 'status').write_text('VmRSS: 134217728 kB\n')
            record = root / 'claims.json'
            record.write_text(json.dumps([dict(pid=123, command_match='pinned-source', peak_ram_gb=250)]))
            self.assertEqual(remaining_bytes(record, root / 'proc'), 122 * 2**30)
            (pid / 'cmdline').write_bytes(b'other-job\0')
            self.assertEqual(remaining_bytes(record, root / 'proc'), 0)
            (pid / 'cmdline').unlink()
            self.assertEqual(remaining_bytes(record, root / 'proc'), 0)

    def test_malformed_claims_cannot_silently_admit(self):
        with tempfile.TemporaryDirectory() as td:
            record = Path(td) / 'claims.json'
            record.write_text('{')
            with self.assertRaises(json.JSONDecodeError):
                remaining_bytes(record)


if __name__ == '__main__':
    unittest.main()
