import copy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / 'tools/h4_hbm_selected_intervals.py'
SPEC = importlib.util.spec_from_file_location('selected_intervals', PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class FiniteIntervals(unittest.TestCase):
    def setUp(self):
        self.inventory = dict(source_native_sha256='native', source_dispatch_sha256='dispatch', calls=[
            dict(call_id='0:0:0', PC=0, rank=0, template='t0', dependencies=[]),
            dict(call_id='1:0:0', PC=1, rank=0, template='t1', dependencies=[0])])
        self.event = dict(kind='L2_read128', die=0, SM=0, slice=0, bank=0,
                          bank_byte_address=0, generation=1, lease='lease',
                          provider_reference='actual home', existing_interval_id='retained interval',
                          source_operand=dict(code_index=0, operand='src:0', typed_offset=0, typed_bytes=128),
                          backend_bound_edges=2, consumer_bound_edges=3, reverse_bound_edges=4)
        self.bindings = dict(source_native_sha256='native', source_dispatch_sha256='dispatch', calls={
            '0:0:0': dict(template='t0', commands=[copy.deepcopy(self.event)]),
            '1:0:0': dict(template='t1', commands=[copy.deepcopy(self.event)])})

    def test_visible_consumer_reverse_and_pc_dependency(self):
        r = M.compose(self.inventory, self.bindings)
        a, b = r['intervals']
        self.assertEqual((a['visible_ACK'], a['consumer'], a['reverse_grant']), (15, 18, 22))
        self.assertEqual(b['start'], 22)
        self.assertEqual(r['selected_movement_retirement_edge_upper'], 44)
        self.assertEqual(r['existing_RF_I64_RMW_C0_provider_charges_added'], 0)
        self.assertIsNone(r['complete_token_latency'])

    def test_different_banks_overlap_same_bank_serializes(self):
        self.inventory['calls'][1]['dependencies'] = []
        r = M.compose(self.inventory, self.bindings)
        self.assertEqual(r['intervals'][1]['contention_edges'], 22)
        self.bindings['calls']['1:0:0']['commands'][0]['bank'] = 1
        r = M.compose(self.inventory, self.bindings)
        self.assertEqual(r['intervals'][1]['start'], 0)

    def test_missing_wait_does_not_become_zero(self):
        for field in ('backend_bound_edges', 'consumer_bound_edges', 'reverse_bound_edges'):
            for value in (None, 0, -1, True):
                with self.subTest(field=field, value=value):
                    b = copy.deepcopy(self.bindings)
                    b['calls']['0:0:0']['commands'][0][field] = value
                    with self.assertRaises(ValueError):
                        M.compose(self.inventory, b)

    def test_missing_call_refuses_complete_and_partial_has_no_full_bound(self):
        del self.bindings['calls']['1:0:0']
        with self.assertRaisesRegex(ValueError, 'finite operator intervals'):
            M.compose(self.inventory, self.bindings)
        r = M.compose(self.inventory, self.bindings, require_complete=False)
        self.assertIsNone(r['selected_movement_retirement_edge_upper'])

    def test_unknown_opcode_template_and_source_reject(self):
        for field, value in [('kind', 'host_oracle'), ('bank', 8), ('SM', 32),
                             ('bank_byte_address', 262144), ('lease', None)]:
            b = copy.deepcopy(self.bindings)
            b['calls']['0:0:0']['commands'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                M.compose(self.inventory, b)
        self.bindings['source_native_sha256'] = 'stale'
        with self.assertRaises(ValueError):
            M.compose(self.inventory, self.bindings)

    def test_eight_shared_groups_exact_capacity(self):
        commands = []
        for group in range(8):
            e = copy.deepcopy(self.event)
            e.update(kind='shared_write64', scratch_byte_address=65024+64*group, group=group)
            e['source_operand']['typed_bytes'] = 64
            commands.append(e)
        self.bindings['calls']['0:0:0']['commands'] = commands
        r = M.compose(self.inventory, self.bindings)
        self.assertEqual([e['bytes'] for e in r['intervals'][:8]], [64]*8)
        commands[-1]['scratch_byte_address'] = 65536
        with self.assertRaises(ValueError):
            M.compose(self.inventory, self.bindings)

    def test_serialized_third_operand_no_free_third_port(self):
        commands = []
        for slots in ([0, 1], [2, 2]):
            e = copy.deepcopy(self.event)
            e.update(kind='RF_read_pair', RF_slots=slots)
            e['source_operand']['typed_bytes'] = 1024
            commands.append(e)
        self.bindings['calls']['0:0:0']['commands'] = commands
        r = M.compose(self.inventory, self.bindings)
        self.assertEqual(r['intervals'][1]['start'], r['intervals'][0]['reverse_grant'])
        commands[0]['RF_slots'] = [0, 1, 2]
        with self.assertRaises(ValueError):
            M.compose(self.inventory, self.bindings)

    def test_empty_commands_do_not_bind_zero(self):
        self.bindings['calls']['0:0:0']['commands'] = []
        with self.assertRaises(ValueError):
            M.compose(self.inventory, self.bindings)


class SourceInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = M.selected_inventory()

    def test_actual_call_count_and_group_correction(self):
        calls = self.inventory['calls']
        self.assertEqual(len(calls), 193316)
        self.assertEqual(len({c['call_id'] for c in calls}), 193316)
        self.assertEqual(sum(c['corrected_eight_group'] for c in calls), 3840)
        self.assertEqual(self.inventory['PCs'], 2213)

    def test_source_missing_intervals_fail_complete(self):
        b = {f: self.inventory[f] for f in ('source_native_sha256', 'source_dispatch_sha256')}
        b['calls'] = {}
        with self.assertRaisesRegex(ValueError, '193316 selected calls'):
            M.compose(self.inventory, b)

    def test_installed_endpoint_and_cts_are_not_prebuild_blockers(self):
        r = M.receipt(self.inventory)
        self.assertTrue(r['source_preparation_allowed'])
        self.assertTrue(r['existing_endpoint_installed_is_not_a_prebuild_requirement'])
        self.assertNotIn('installed CTS', r['pre_engine_build_missing'])
        self.assertIn('installed CTS', r['downstream_PR_checks'])
        self.assertFalse(r['contextual_engine_build_allowed'])

    def test_qwen_all_pc_worker_and_actual_provider_references(self):
        q = M.qwen_inventory()
        self.assertEqual(len(q['calls']), 1737)
        self.assertEqual(len({c['family'] for c in q['calls']}), 21)
        self.assertEqual([c['PC'] for c in q['calls']], list(range(1737)))
        self.assertTrue(all(c['rank'] == 0 for c in q['calls']))
        self.assertTrue(all('source_provider_references' in c for c in q['calls']))
        self.assertTrue(all(c['movement_intervals'] is None for c in q['calls']))


if __name__ == '__main__':
    unittest.main()
