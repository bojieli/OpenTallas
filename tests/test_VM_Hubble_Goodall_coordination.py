import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'results/uarch/VM_Hubble_Goodall_coordination_20261002'


class Coordination(unittest.TestCase):
    def test_fresh_lease_snapshot_and_RAM_conflict(self):
        x = json.loads((D / 'opentallas-VM-Hubble-Goodall-coordination-20261002-fresh.json').read_text())
        self.assertEqual(x['slot_owners'], {})
        self.assertEqual(x['reserved_threads'], 0)
        self.assertEqual(x['status']['compute_threads'], 0)
        free = x['status']['free_gib']
        self.assertGreaterEqual(free - 80, 24)
        self.assertLess(free - 88, 24)
        self.assertTrue(x['UTC'].startswith('2026-10-02T12:24:'))

    def test_checkpoint_inventory_and_no_duplicate_action(self):
        x = json.loads((D / 'coordination.json').read_text())
        self.assertEqual(len(x['checkpoint_inventory']), 7)
        self.assertEqual(sum(e['size_bytes'] for e in x['checkpoint_inventory']), x['checkpoint_bytes'])
        self.assertEqual(x['new_downloads_or_compiles'], 0)
        self.assertTrue(x['source_GO_required_before_converter_or_compile'])
        self.assertFalse(x['owner_acknowledgements'])
        probe = json.loads((D / 'opentallas-Goodall-VM-checkpoint-discovery-20261002.json').read_text())
        self.assertEqual(probe['downloads'], 0)
        self.assertEqual(probe['remote_result']['candidate_files'], [])
        self.assertEqual(probe['remote_result']['transfer_or_conversion_processes'], [])

    def test_native_R3_diff_is_only_supported_AS_path_and_name(self):
        old = ROOT / 'results/uarch/native_build_future_launcher_audit_20261002/launchers'
        s = (old / 'remote_gate_native_unlimited.base.py').read_text()
        expected = s.replace(' --ulimit as=-1:-1', '').replace(
            "inner = 'python3 ' + q(cwd + '/tools/native_build_unlimited_exec.py') + ' -- ' + inner",
            "inner = 'prlimit --as=unlimited:unlimited --cpu=unlimited:unlimited --fsize=unlimited:unlimited -- python3 ' + q(cwd + '/tools/native_build_unlimited_exec.py') + ' -- ' + inner")
        actual = (D / 'native_transport_r3/remote_gate_native_unlimited_r3.base.py').read_text()
        self.assertEqual(actual, expected)
        self.assertNotIn('--ulimit as=', actual)
        ast.parse(actual)
        guard = (D / 'native_transport_r3/remote_gate_native_unlimited_r3_guarded.py').read_text()
        self.assertEqual(guard, (old / 'remote_gate_native_unlimited_guarded.py').read_text().replace(
            "'remote_gate_native_unlimited.base.py'", "'remote_gate_native_unlimited_r3.base.py'"))
        ast.parse(guard)


if __name__ == '__main__':
    unittest.main()
