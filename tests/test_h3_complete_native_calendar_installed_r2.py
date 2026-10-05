import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

m = load('installed_services_r2_test', 'tools/h3_complete_native_calendar_installed_r2.py')
g = load('grants_r1_installed_test', 'tools/h3_complete_native_calendar_grants_r1.py')

class InstalledPCtests(unittest.TestCase):
    def test_round_robin_accepted_grants(self):
        pc = m.InstalledQwenPC()
        req = {i: dict(tag=i, write=False) for i in range(6)}
        self.assertEqual([pc.step(req, backend_ready=True)['grant'] for _ in range(12)], list(range(6))*2)
        self.assertEqual(pc.counts, [2]*6)
        self.assertEqual(pc.fairness()['eligible_request_other_accepted_grants_upper'], 5)
        self.assertIsNone(pc.fairness()['conditional_acceptance_edge_upper'])

    def test_blocked_backend_never_rotates_or_retires(self):
        pc = m.InstalledQwenPC()
        for _ in range(20):
            self.assertFalse(pc.step({2: dict(tag=9, write=True)}, backend_ready=False)['request_accepted'])
        self.assertEqual(pc.head, 0)
        self.assertEqual(pc.counts, [0]*6)

    def test_old_full_credit_blocks_same_edge_return(self):
        pc = m.InstalledQwenPC(); pc.counts[0] = 16
        req = {0: dict(tag=5, write=True)}
        row = pc.step(req, backend_ready=True, write_done=dict(client=0, tag=123))
        self.assertFalse(row['request_accepted']); self.assertEqual(pc.counts[0], 15)
        self.assertTrue(pc.step(req, backend_ready=True)['request_accepted'])

    def test_held_read_and_unmatched_write_source_deficiency(self):
        pc = m.InstalledQwenPC()
        pc.step({0: dict(tag=5, write=False)}, backend_ready=True)
        pc.step({}, backend_ready=False, read_return=dict(client=0, tag=5))
        self.assertEqual(pc.counts[0], 1)
        row = pc.step({}, backend_ready=False, write_done=dict(client=0, tag=999))
        self.assertEqual(pc.counts[0], 0)
        self.assertFalse(row['full_tag_generation_checked_by_installed_source'])

    def test_fault_wrap_does_not_gate_other_client(self):
        pc = m.InstalledQwenPC()
        pc.step({}, backend_ready=False, write_done=dict(client=0, tag=5))
        self.assertEqual(pc.counts[0], 31); self.assertTrue(pc.fault)
        self.assertTrue(pc.step({1: dict(tag=5, write=True)}, backend_ready=True)['request_accepted'])

    def test_simultaneous_returns_old_credit_underflow(self):
        pc = m.InstalledQwenPC(); pc.counts[0] = 1
        pc.step({}, backend_ready=False, read_return=dict(client=0, tag=3), read_ready=[0], write_done=dict(client=0, tag=4))
        self.assertEqual(pc.counts[0], 31); self.assertTrue(pc.fault)

    def test_fairness_is_conditional_positive_edges_only(self):
        x = m.InstalledQwenPC().fairness(backend_acceptance_gap=7, credit_return_upper=19)
        self.assertEqual(x['conditional_acceptance_edge_upper'], 61)
        self.assertFalse(x['hardware_qualified'])
        with self.assertRaises(ValueError): m.InstalledQwenPC().fairness(backend_acceptance_gap=0)

class ActualSRAMOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.bindings, _ = g.build_inventory()
    def setUp(self):
        self.ledger = g.CausalGrantLedger(self.bindings)
        self.parent = next(p for p in self.bindings['parents'].values() if p['scope'] == 'actual_all96_PC0_RMW')
        self.edge = 0
        self.owner = m.CausalTransportOwners(1)
        self.key = (0, 3, 7)
        d = self.bindings['children'][self.parent['children'][1]]
        self.identity = dict(zip(('generation','PC','sequence','rank','SM'), self.parent['owner']))
        self.identity.update(lease=self.parent['lease'], provider_reference=d['provider_reference'],
                             source_command_sha256=d['source_command_sha256'], write=d['write'])
        self.token = self.owner.accept(self.key, self.identity)
    def ev(self, name, **kw):
        row = dict(parent=self.parent['id'], binding_sha256=self.parent['binding_sha256'], owner=self.parent['owner'],
                   lease=self.parent['lease'], domain='H1_streaming', edge=self.edge,
                   origin='directed_verifier_control', event=name, accepted=True)
        row.update(kw); self.ledger.observe(row)
    def child(self, child, reverse=True):
        d = self.bindings['children'][child]
        self.ev('child_issue', child=child, source_command_sha256=d['source_command_sha256'], provider_reference=d['provider_reference'], valid=True, ready=True)
        for bank in d['expected_SRAMs']: self.ev('SRAM_accept', child=child, SRAM=bank, write=d['write'])
        self.edge += 1
        if not d['write']:
            for bank in d['expected_SRAMs']: self.ev('SRAM_capture', child=child, SRAM=bank)
            self.edge += 1
        self.ev('child_ACK', child=child, valid=True, ready=True); self.edge += 1
        if reverse: self.ev('child_reverse', child=child); self.edge += 1
    def local_ack(self):
        self.ev('parent_grant')
        self.child(self.parent['children'][0])
        self.child(self.parent['children'][1], reverse=False)
        self.owner.event(self.key, self.token, 'backend_completion')
        self.receipt = dict(parent=self.parent['id'], child=self.parent['children'][1], binding_sha256=self.parent['binding_sha256'])
        self.owner.event(self.key, self.token, 'local_SRAM_ACK', SRAM_receipt=self.receipt, SRAM_ledger=self.ledger)
    def test_resolved_common_ACK_to_actual_visibility_consumer_reverse(self):
        self.local_ack()
        with self.assertRaisesRegex(ValueError, 'visibility fence'): self.owner.event(self.key, self.token, 'visibility')
        self.ev('child_reverse', child=self.parent['children'][1]); self.edge += 1
        self.child(self.parent['children'][2])
        self.ev('visibility_fence'); self.edge += 1
        self.owner.event(self.key, self.token, 'visibility')
        self.ev('consumer'); self.edge += 1
        self.owner.event(self.key, self.token, 'consumer')
        with self.assertRaisesRegex(ValueError, 'reverse still held'): self.owner.event(self.key, self.token, 'reverse')
        self.ev('reverse'); self.edge += 1
        with self.assertRaisesRegex(ValueError, 'CDC'): self.owner.event(self.key, self.token, 'reverse')
        self.owner.event(self.key, self.token, 'reverse', CDC_receipt=dict(sender_domain='CORE',sender_edge=17,
                         receiver_domain='H1_streaming',receiver_edge=9,token=self.token))
        self.assertFalse(self.owner.live); self.assertEqual(len(self.owner.retired), 1)
        self.assertEqual(self.ledger.summary()['physical_credit_debt'], 0)
        self.assertFalse(self.ledger.summary()['hardware_qualified'])
    def test_backend_only_never_retires(self):
        self.owner.event(self.key, self.token, 'backend_completion')
        with self.assertRaises(ValueError): self.owner.event(self.key, self.token, 'reverse')
        with self.assertRaises(ValueError): self.owner.event(self.key, self.token, 'local_SRAM_ACK', SRAM_receipt=True)
        self.assertEqual(len(self.owner.live), 1)
    def test_duplicate_capacity_and_wrong_generation_hold_credit(self):
        with self.assertRaises(ValueError): self.owner.accept(self.key, self.identity)
        with self.assertRaises(ValueError): self.owner.accept((0,3,8), self.identity)
        with self.assertRaises(ValueError): self.owner.event(self.key, '0'*64, 'backend_completion')
        self.assertEqual(len(self.owner.live), 1)
    def test_foreign_source_reference_cannot_bind_actual_SRAM(self):
        self.owner.live[self.key]['identity']['source_command_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'source-resolved'): self.local_ack()
        self.assertEqual(self.owner.live[self.key]['phase'], 'LOCAL_ACK')

class SourceAndStorageTests(unittest.TestCase):
    def test_archived_source_inventory_and_model(self):
        base = ROOT / m.OUT
        pins = json.loads((base/'inputs_manifest.json').read_bytes())
        source = {}
        for name, pin in pins.items():
            raw = (base/'inputs'/name).read_bytes()
            self.assertEqual(m.sha(raw), pin['sha256']); self.assertEqual(len(raw), pin['bytes']); source[name] = raw
        model = m.inventory(source)
        self.assertEqual(model['installed_Qwen_PC']['total_count_credit'], 12288)
        self.assertEqual(model['minimal_source_owner_successor']['entry_bits'], 324)
        self.assertEqual(model['minimal_source_owner_successor']['metadata_upper_bits'], 3981312)
        self.assertFalse(model['hardware_qualified']); self.assertIsNone(model['physical_wait_upper'])
        self.assertEqual(model, json.loads((base/'model.json').read_bytes()))
        source['RF.sv'] = b'exporter claims ACK'
        with self.assertRaises(ValueError): m.inventory(source)
    def test_r55_distinct_journal_aggregate_not_old_single_floor(self):
        floor = 819950818992 + 7423370948
        available = 827982553088
        self.assertEqual(available-floor, 608363148)
        x = m.aggregate_r55(819950818992, 700000000, 7423370948, 1, available=available)
        self.assertFalse(x['storage_fits']); self.assertFalse(x['constructor_GO'])
        y = m.aggregate_r55(10, 20, 30, 40, available=100)
        self.assertTrue(y['storage_fits']); self.assertFalse(y['production_numerical_GO'])
        with self.assertRaises(ValueError): m.aggregate_r55(10,0,30,40,available=100)

if __name__ == '__main__': unittest.main()
