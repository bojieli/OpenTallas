"""Prospective W6 golden mutants; no observed hardware receipt is generated."""
import copy
from dataclasses import asdict, replace
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('w6_contract', ROOT/'tools/hbm_w6_fence_contract.py')
W = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = W
spec.loader.exec_module(W)


class W6ContractTests(unittest.TestCase):
    def setUp(self):
        self.g = W.FenceGolden(enabled=True)
        self.ident = W.Identity(7, 1, 0, 0, 0, 1)
        self.data = bytes(range(256))*2

    def issue(self):
        self.g.issue(self.ident, path='C0', address=3, data=self.data)

    def mirrors(self):
        self.issue()
        self.g.tick()
        for c in (0, 1):
            self.g.mirror_write(self.ident, copy=c, address=3, data=self.data)

    def completion(self):
        self.mirrors()
        self.g.tick()
        self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK')

    def consumer(self):
        self.completion()
        for event in ('visibility', 'consumer'):
            self.g.tick()
            self.g.offer(self.ident, event=event, data=self.data)

    def reverse(self):
        return dict(identity=asdict(self.ident), sender_domain=1, receiver_domain=1,
                    sender_epoch=0, receiver_epoch=0, sender_edge=self.g.edge+1,
                    receiver_edge=self.g.edge+2)

    def test_complete_C0_then_KV_read_finite_fullwidth(self):
        r = W.finite_bench()
        self.assertEqual(r['status'], 'PASS_FINITE_GOLDEN_C0_THEN_KV_READ_ONLY')
        self.assertEqual(sum(x['event']=='retire_accept' for x in r['trace']), 2)
        self.assertFalse(r['hardware_qualification'])

    def test_disabled_no_acceptance(self):
        with self.assertRaisesRegex(ValueError, 'disabled'):
            W.FenceGolden().issue(self.ident, path='C0', address=3, data=self.data)

    def test_foreign_owner_generation_rank_sm_epoch(self):
        self.issue()
        self.g.tick()
        for key in ('owner_tag', 'generation', 'rank', 'sm', 'reset_epoch', 'domain'):
            wrong = replace(self.ident, **{key: getattr(self.ident, key)+1})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'stale/foreign'):
                self.g.mirror_write(wrong, copy=0, address=3, data=self.data)
        self.assertEqual(self.g.mirrors, set())

    def test_duplicate_copy_and_missing_second_copy(self):
        self.issue()
        self.g.tick()
        self.g.mirror_write(self.ident, copy=0, address=3, data=self.data)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.g.mirror_write(self.ident, copy=0, address=3, data=self.data)
        self.g.tick()
        with self.assertRaisesRegex(ValueError, 'both-copy'):
            self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK')

    def test_bareACK_cannot_be_promoted_to_tagged_completion(self):
        self.mirrors()
        self.g.tick()
        with self.assertRaisesRegex(ValueError, 'common ACK'):
            self.g.complete(self.ident, address=3, data=self.data, kind='host_ack_valid')

    def test_no_zero_cycle_write_ACK_visibility_consumer(self):
        self.issue()
        with self.assertRaisesRegex(ValueError, 'positive'):
            self.g.mirror_write(self.ident, copy=0, address=3, data=self.data)
        self.g.tick()
        for c in (0, 1): self.g.mirror_write(self.ident, copy=c, address=3, data=self.data)
        with self.assertRaisesRegex(ValueError, 'positive'):
            self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK')
        self.g.tick()
        self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK')
        with self.assertRaisesRegex(ValueError, 'positive'):
            self.g.offer(self.ident, event='visibility', data=self.data)
        self.g.tick()
        self.g.offer(self.ident, event='visibility', data=self.data)
        with self.assertRaisesRegex(ValueError, 'positive'):
            self.g.offer(self.ident, event='consumer', data=self.data)

    def test_completion_backpressure_holds_owner(self):
        self.mirrors()
        self.g.tick()
        self.assertFalse(self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK', ready=False))
        self.g.tick(4)
        self.assertEqual(self.g.active, self.ident)
        self.assertEqual(self.g.phase, 'COMPLETION')
        self.assertTrue(self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK'))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK')

    def test_visibility_consumer_payload_stalls_and_duplicate(self):
        self.completion()
        for event in ('visibility', 'consumer'):
            self.g.tick()
            self.assertFalse(self.g.offer(self.ident, event=event, data=self.data, ready=False))
            self.g.tick(7)
            with self.assertRaisesRegex(ValueError, 'payload'):
                self.g.offer(self.ident, event=event, data=bytes(512))
            self.assertEqual(self.g.active, self.ident)
            self.g.offer(self.ident, event=event, data=self.data)
            self.g.tick()
            with self.assertRaisesRegex(ValueError, 'ordered'):
                self.g.offer(self.ident, event=event, data=self.data)

    def test_retirement_cannot_release_before_consumer_reverse(self):
        self.completion()
        self.g.tick()
        for event in ('consumer', 'retire', 'reverse'):
            with self.assertRaisesRegex(ValueError, 'ordered'):
                self.g.offer(self.ident, event=event)
        with self.assertRaisesRegex(ValueError, 'one outstanding'):
            self.g.issue(replace(self.ident, generation=2), path='C0', address=4, data=self.data)

    def test_reverse_domain_epoch_token_and_time_mutants(self):
        self.consumer()
        r = self.reverse()
        self.g.tick(2)
        for field, bad in [('sender_domain', 2), ('receiver_domain', 2), ('sender_epoch', 1),
                           ('receiver_epoch', 1), ('sender_edge', self.g.last_edge),
                           ('receiver_edge', r['sender_edge'])]:
            m = copy.deepcopy(r); m[field] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.g.offer(self.ident, event='reverse', reverse=m)
        m = copy.deepcopy(r); m['identity']['generation'] = 2
        with self.assertRaises(ValueError): self.g.offer(self.ident, event='reverse', reverse=m)
        self.assertEqual(self.g.phase, 'REVERSE')
        self.assertEqual(self.g.active, self.ident)

    def test_reverse_held_and_stale_duplicate_after_retire(self):
        self.consumer()
        r = self.reverse(); self.g.tick(2)
        self.g.offer(self.ident, event='reverse', reverse=r, ready=False)
        self.g.tick(2)
        changed = copy.deepcopy(r); changed['receiver_edge'] += 1
        with self.assertRaisesRegex(ValueError, 'changed under backpressure'):
            self.g.offer(self.ident, event='reverse', reverse=changed)
        self.g.offer(self.ident, event='reverse', reverse=r)
        self.g.tick()
        self.g.offer(self.ident, event='retire')
        self.g.tick()
        with self.assertRaises(ValueError): self.g.offer(self.ident, event='reverse', reverse=r)
        with self.assertRaisesRegex(ValueError, 'reused generation'):
            self.g.issue(self.ident, path='C0', address=3, data=self.data)
        new = replace(self.ident, generation=2)
        self.g.issue(new, path='C0', address=3, data=self.data)
        with self.assertRaisesRegex(ValueError, 'stale/foreign'):
            self.g.offer(self.ident, event='reverse', reverse=r)

    def test_reset_during_every_pending_phase_rejects_oldACK(self):
        for phase in ('COMPLETION', 'VISIBILITY', 'CONSUMER', 'REVERSE', 'RETIRE'):
            self.setUp()
            if phase == 'COMPLETION': self.issue()
            else: self.completion()
            if phase in ('CONSUMER', 'REVERSE', 'RETIRE'):
                self.g.tick(); self.g.offer(self.ident, event='visibility', data=self.data)
            if phase in ('REVERSE', 'RETIRE'):
                self.g.tick(); self.g.offer(self.ident, event='consumer', data=self.data)
            if phase == 'RETIRE':
                r=self.reverse(); self.g.tick(2); self.g.offer(self.ident, event='reverse', reverse=r)
            self.assertEqual(self.g.phase, phase)
            self.g.reset_assert()
            with self.assertRaises(ValueError): self.g.complete(self.ident, address=3, data=self.data, kind='W4_COMMON_MIRROR_ACK')
            with self.assertRaises(ValueError): self.g.reset_release(common_reset_drained=False)
            self.g.reset_release(common_reset_drained=True)
            new=replace(self.ident, reset_epoch=1)
            self.g.issue(new, path='C0', address=3, data=self.data)
            self.g.tick()
            with self.assertRaisesRegex(ValueError, 'stale/foreign'):
                self.g.mirror_write(self.ident, copy=0, address=3, data=self.data)

    def test_no_epoch_wrap_or_generation_wrap(self):
        g=W.FenceGolden(enabled=True, layout=W.FixtureLayout(reset_epoch=1, generation=1))
        g.reset_assert(); g.reset_release(common_reset_drained=True)
        g.reset_assert(); g.reset_release(common_reset_drained=True)
        with self.assertRaisesRegex(ValueError, 'exhausted'):
            g.issue(replace(self.ident, reset_epoch=0), path='C0', address=0, data=self.data)
        self.issue()
        self.g.reset_assert(); self.g.reset_release(common_reset_drained=True)
        with self.assertRaisesRegex(ValueError, 'bounds'):
            self.g.issue(replace(self.ident, generation=256, reset_epoch=1), path='C0', address=0, data=self.data)

    def test_KV_read_requires_positive_origin_and_exact_payload_version(self):
        data=bytes(range(32)); i=self.ident
        origin=dict(identity=asdict(i), sector=123, version=4, payload_sha256=hashlib.sha256(data).hexdigest())
        for patch in ({'version': -1}, {'sector': 124}, {'payload_sha256': '0'*64}, {'identity': asdict(replace(i, generation=2))}):
            with self.assertRaises(ValueError):
                self.g.issue(i, path='KV_READ', address=123, data=data, read_origin={**origin, **patch})
        self.g.issue(i, path='KV_READ', address=123, data=data, read_origin=origin)
        self.g.tick()
        with self.assertRaisesRegex(ValueError, 'payload'):
            self.g.complete(i, address=123, data=bytes(32), kind='W2_VERSIONED_READ_CAPTURE', read_version=4)
        for v in (None, 3, 5, True):
            with self.assertRaisesRegex(ValueError, 'versioned'):
                self.g.complete(i, address=123, data=data, kind='W2_VERSIONED_READ_CAPTURE', read_version=v)
        self.g.complete(i, address=123, data=data, kind='W2_VERSIONED_READ_CAPTURE', read_version=4)

    def test_fullwidth_geometry_address_and_F0_blocked(self):
        for address, data in [(512, self.data), (-1, self.data), (0, self.data[:32])]:
            with self.assertRaises(ValueError): self.g.issue(self.ident, path='C0', address=address, data=data)
        p=W.proposal()
        self.assertEqual(p['geometry']['SIMD_lanes'],128)
        self.assertEqual(p['geometry']['physical_RF_macros'],128)
        self.assertFalse(p['engine_RTL_ready'])
        self.assertTrue(all(v is None for v in p['prerequisite_pins'].values()))
        self.assertTrue(all(x['positive_cycles_required'] and x['production_cycles'] is None for x in p['boundary_model_requests']))


if __name__ == '__main__':
    unittest.main()
