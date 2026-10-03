"""Constructor-free original-class fixtures; never checkpoint payload evidence."""
import ast
from collections import Counter
import json
import math
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import h4_c0_pc40_provider_capture_r1 as C


def fixture():
    path = C.BASE / 'inputs/h3_qwen_bounded_native.py'
    tree = ast.parse(path.read_bytes())
    selected = [n for n in tree.body if isinstance(n, ast.ClassDef)
                and n.name in ('TileWords', 'AddressedTileWords')]
    module = ModuleType('original_fixture_only')
    module.__file__ = str(path)
    module.__dict__.update(np=np, F=np.float32, math=math, Counter=Counter)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), module.__dict__)
    store = module.TileWords.__new__(module.TileWords)
    store.values = {C.VERSION: {'homes': [{'rank': 0, 'SM': sm, 'home': {}}
                                         for sm in (0, 24)], 'retire_pc': 40}}
    store.homes = {(C.VERSION, 0, sm): {'word_count': 256, 'home': {'class': 'RF', 'slot_first': slot}}
                   for sm, slot in ((0, 38), (24, 32))}
    store.shapes = {C.VERSION: ((12288,), 'F32')}
    store.live = {C.VERSION}; store.published = {C.VERSION}
    store.owners = {key: C.VERSION for _, key in C.HOMES.values()}
    store.pages = {key: [np.arange(128, dtype=np.uint32).copy() for _ in range(2)]
                   for _, key in C.HOMES.values()}
    store.cache = None; store.counters = Counter(); store.worker_rank = 0; store.worker_SM = 0
    store.events = [{'event': 'publish', 'version': C.VERSION}]
    return module, store


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.module, self.store = fixture()
        self.capture = C.PublicationCapture(self.module, Path(self.temp.name) / 'capture', enabled=True)
        self.op = dict(pc=39, opcode='SCALAR_MUL', writes=[C.VERSION])

    def publish(self):
        return self.capture.observe_publication(self.op, self.store)

    def test_actual_original_methods_and_order_fixture(self):
        self.publish(); gate, up = self.capture.read_pair(self.store)
        self.assertEqual(gate.shape, (128,)); self.assertEqual(up.dtype, np.float32)
        x = json.loads((self.capture.directory / 'caller_reads.json').read_text())
        self.assertEqual([e['role'] for e in x['events']], ['gate', 'up'])
        self.assertEqual(x['events'][1]['software_provider_counter_delta']['NoC_source_read_bits'], 4096)
        self.assertFalse(x['installed_NoC_delivery_observed']); self.assertFalse(x['hardware_admitted'])
        self.assertIn(C.VERSION, self.store.published); self.assertEqual(len(self.store.owners), 2)

    def test_default_off(self):
        with self.assertRaises(ValueError): C.PublicationCapture(self.module, Path(self.temp.name) / 'off')

    def test_wrong_owner(self):
        self.store.owners[('RF', 0, 24, 32)] = 'stale'
        with self.assertRaises(ValueError): self.publish()

    def test_unpublished(self):
        self.store.published.clear()
        with self.assertRaises(ValueError): self.publish()

    def test_mirror_disagreement(self):
        self.store.pages[('RF', 0, 24, 32)][1][0] = 99
        with self.assertRaises(ValueError): self.publish()

    def test_width(self):
        self.store.pages[('RF', 0, 0, 38)] = [np.zeros(127, np.uint32)] * 2
        with self.assertRaises(ValueError): self.publish()

    def test_dtype(self):
        self.store.shapes[C.VERSION] = ((12288,), 'U32')
        with self.assertRaises(ValueError): self.publish()

    def test_wrong_source_home(self):
        self.store.homes[C.VERSION, 0, 24]['home']['slot_first'] = 33
        with self.assertRaises(ValueError): self.publish()

    def test_no_class_exemption(self):
        self.store.__class__ = type('Derived', (self.module.TileWords,), {})
        with self.assertRaises(ValueError): self.publish()

    def test_no_method_substitution(self):
        self.module.TileWords.read = lambda *a: None
        with self.assertRaises(ValueError): self.publish()

    def test_wrong_caller(self):
        self.publish(); self.store.worker_SM = 1
        with self.assertRaises(ValueError): self.capture.read_pair(self.store)

    def test_retired_publication(self):
        self.publish(); self.store.live.clear()
        with self.assertRaises(ValueError): self.capture.read_pair(self.store)

    def test_no_early_release_contract(self):
        self.store.values[C.VERSION]['retire_pc'] = 39
        with self.assertRaises(ValueError): self.publish()

    def test_changed_payload(self):
        self.publish()
        for p in self.store.pages[('RF', 0, 24, 32)]: p[0] = 500
        with self.assertRaises(ValueError): self.capture.read_pair(self.store)

    def test_different_store(self):
        self.publish(); _, other = fixture()
        with self.assertRaises(ValueError): self.capture.read_pair(other)

    def test_no_fake_workspace_lease(self):
        self.publish()
        self.assertFalse(self.capture.record['installed_workspace_lease_observed'])
        self.assertEqual(self.capture.record['selected_workspace_source_owners'], {'17': None, '18': None, '19': None})

    def test_cache_hit_is_not_new_RF_handshake(self):
        self.publish(); self.store.read(C.VERSION, 0, 128)
        self.capture.read_pair(self.store)
        x = json.loads((self.capture.directory / 'caller_reads.json').read_text())
        self.assertEqual(x['events'][0]['software_provider_counter_delta']['RF_read'], 0)


if __name__ == '__main__': unittest.main()
