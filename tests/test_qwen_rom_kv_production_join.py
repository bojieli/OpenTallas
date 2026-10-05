"""Protocol-only fixtures; no second token or synthetic qualification."""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_persistent_kv_g0 import Owner
from qwen_rom_kv_identity_binding import identity, pack
from qwen_rom_kv_production_join import (
    ProducerJoin, Receipts, RefillJoin, CANONICAL, decoded_fp8, producer_byte,
    producer_write_plan, tail_sizing)


def event(op, beat=0, t=0, owner=None, generation=1, tag=3, write=False, sectors=1):
    owner = owner or Owner(0, 3, 35, 7)
    return dict(event=op, service_cycle=t, endpoint=owner.rank>>1, stack=2,
                physical_tag=tag, identity=hex(pack(identity(owner, 2, 100, generation, 1, tag%16, pc=67))),
                owner=vars(owner), producer_pc=67, write=write, sectors=sectors,
                beat=beat, sector=100+beat, payload_hex=bytes(32*sectors if op == 'allocate' else 32).hex())


class ProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['QWEN_O4_TP'] = '4'
        os.environ['QWEN_O4_GROUPS'] = '6144'
        os.environ['HDC_SU_WIDTH'] = '64'

    def test_canonical_inverse_all_source_values(self):
        self.assertEqual(len(CANONICAL), 253)
        for bits, code in CANONICAL.items():
            self.assertEqual(producer_byte(bits), code)
            self.assertEqual(decoded_fp8(code), bits)
        for bits in (0x80000000, 0x7f800000, 0x7fc00000, 0x3f800001, decoded_fp8(127)):
            with self.assertRaises(ValueError): producer_byte(bits)

    def test_actual_encoded_shape_addresses_and_accepted_issue(self):
        # Source compiler only; these are shapes, never checkpoint/numerical state.
        import hdc_qwen_fullshape_program_w12 as source
        profile = source.profile(0)
        image = ('\n'.join(profile['program_hex'])+'\n').encode()
        for pos in (0, 15, 16, 8191):
            join = ProducerJoin(image, Owner(0, 0, 35, 9), pos)
            self.assertEqual(sorted(map(len, join.expected.values())), [128, 128, 256])
            pc = next(iter(join.expected))
            address = next(iter(join.expected[pc]))
            with self.assertRaisesRegex(ValueError, 'accepted producer'):
                join.lane_write(pc, address, 0)
            for pc, addresses in join.expected.items():
                join.issue(pc)
                for address in addresses: join.lane_write(pc, address, 0x3f800000)
            self.assertEqual(join.state(), {'K': bytes([56])*256, 'V': bytes([56])*256})
            with self.assertRaises(ValueError): join.issue(pc)
            with self.assertRaises(ValueError): join.lane_write(pc, address, 0)

    def test_source_producer_full_sector_plan_has_no_partial_rmw(self):
        # profile() was imported with TP4 by the preceding source shape test.
        import hdc_qwen_fullshape_program_w12 as source
        image = ('\n'.join(source.profile(0)['program_hex'])+'\n').encode()
        residence = RefillJoin(1)
        for pos in range(16):
            join = ProducerJoin(image, Owner(0, 3, 35, 7), pos)
            for pc, addresses in join.expected.items():
                join.issue(pc)
                for a in addresses: join.lane_write(pc, a, decoded_fp8(pos+1))
            plan = producer_write_plan(join, residence)
            self.assertEqual(len(plan['requests']), 136 if pos == 15 else 8)
            self.assertTrue(all(len(bytes.fromhex(r['payload_hex'])) == 32 for r in plan['requests']))
            self.assertEqual({r['endpoint'] for r in plan['requests']}, {1})
            self.assertEqual({r['die'] for r in plan['requests']}, {1})

    def test_wrong_image_and_incomplete_state(self):
        with self.assertRaisesRegex(ValueError, 'exactly the TP4'):
            ProducerJoin(b'0\n', Owner(0, 0, 0, 0), 0)


class ReceiptTests(unittest.TestCase):
    def test_read_requires_allocate_return_drain_credit_and_consumed_grant(self):
        r = Receipts()
        with self.assertRaises(ValueError): r.apply(event('credit'))
        r.apply(event('allocate', sectors=2))
        with self.assertRaises(ValueError): r.apply(event('credit'))
        r.apply(event('return'))
        e = event('acquire'); e['reader'] = 0; r.apply(e)
        with self.assertRaises(ValueError): r.apply(event('credit'))
        e['event'] = 'drain'; r.apply(e)
        r.apply(event('credit'))
        with self.assertRaises(ValueError): r.apply(event('retire'))
        with self.assertRaises(ValueError): r.apply(event('allocate', generation=2))
        r.apply(event('grant_consumed'))
        for op in ('return', 'credit', 'grant_consumed'): r.apply(event(op, beat=1))
        r.apply(event('retire'))
        with self.assertRaises(ValueError): r.apply(event('allocate'))
        r.apply(event('allocate', generation=2))

    def test_write_backing_payload_and_source_eight_cycle_visibility(self):
        r = Receipts(); r.apply(event('allocate', write=True))
        with self.assertRaises(ValueError): r.apply(event('return', write=True))
        with self.assertRaises(ValueError): r.apply(event('backing', write=True))
        r.apply(event('write_command', write=True))
        bad = event('backing', t=8, write=True); bad['payload_hex'] = bytes([1]*32).hex()
        with self.assertRaises(ValueError): r.apply(bad)
        with self.assertRaises(ValueError): r.apply(event('backing', t=7, write=True))
        r.apply(event('backing', t=8, write=True))
        for op in ('return', 'credit', 'grant_consumed', 'retire'):
            r.apply(event(op, t=8, write=True))
        self.assertFalse(r.live)

    def test_owner_stack_pc_identity_and_duplicate_rejection(self):
        r = Receipts(); r.apply(event('allocate')); r.apply(event('return'))
        for field, value in [('identity', event('credit', generation=2)['identity']),
                             ('producer_pc', 68), ('sector', 101), ('endpoint', 0), ('stack', 1)]:
            e = event('credit'); e[field] = value
            with self.assertRaises(ValueError): r.apply(e)
        with self.assertRaises(ValueError): r.apply(event('return'))
        r.apply(event('credit'))
        with self.assertRaises(ValueError): r.apply(event('credit'))

    def test_die_part_of_physical_tag_key_and_write_residents_finite(self):
        r = Receipts()
        for rank in (2, 3):
            for tag in range(4):
                r.apply(event('allocate', owner=Owner(0, rank, 0, 0), tag=tag, write=True))
            with self.assertRaisesRegex(ValueError, 'resident'):
                r.apply(event('allocate', owner=Owner(0, rank, 0, 0), tag=4, write=True))
        self.assertEqual(len(r.live), 8)

    def test_source_burst_and_assembly_credits_are_finite(self):
        r = Receipts(reader_limit=1); r.apply(event('allocate')); r.apply(event('return'))
        a = event('acquire'); a['reader'] = 0; r.apply(a)
        a['reader'] = 1
        with self.assertRaisesRegex(ValueError, 'assembly'): r.apply(a)
        # Different physical tag, same IRS slot: reject before receipt allocation.
        a = event('allocate', tag=19)
        with self.assertRaisesRegex(ValueError, 'slot reuse'): r.apply(a)


class PolicyTests(unittest.TestCase):
    def test_literal_tail_bank_slot_sizing_and_prototype_geometry_join(self):
        s = tail_sizing()
        self.assertEqual(s['required_LOG_TW'], 9)
        self.assertEqual(s['mutable_state_bytes_per_rank'], 294912)
        self.assertEqual(s['owner_rows_per_bank'], 144)
        self.assertIsNone(s['area_slot_fit'])
        self.assertIsNone(s['per_user_latency'])
        locations = set()
        for layer in range(36):
            for head in range(2):
                for dim in range(128):
                    for parity in range(2):
                        # Literal write-adapter row after dropping LOG_HD7+LOG_TW9.
                        word = (head*512+parity)*128+dim
                        row = ((word >> 16) << 1) | ((word & 127) >> 6)
                        bank = ((word >> 7)&1)*64+(word&63)
                        location = (bank, layer*4+row)
                        self.assertNotIn(location, locations)
                        locations.add(location)
        self.assertEqual(len(locations), 128*144)

    def test_descriptor_demand_hits_layer_hops_and_no_implicit_zero(self):
        calls = []
        def provider(owner, sector):
            calls.append((owner, sector)); return bytes([sector[3]])*32
        r = RefillJoin(2)
        a, b = Owner(0, 0, 0, 1), Owner(0, 0, 1, 1)
        s0, s1, s2 = (0,0,0,0), (0,0,0,1), (0,0,0,2)
        self.assertEqual(r.demand(a, [s0, s1], provider), 2)
        self.assertEqual(r.demand(a, [s0, s1], provider), 0)
        self.assertEqual(r.demand(a, [s1], provider), 0)
        self.assertEqual(r.demand(b, [s1], provider), 1)
        self.assertEqual((r.read_bytes, r.hits), (96, 3))
        with self.assertRaises(ValueError): r.demand(a, [s0, s1, s2], provider)
        with self.assertRaises(ValueError): r.demand(a, [s0], lambda *_: None)
        with self.assertRaises(ValueError): r.demand(a, [(1,0,0,0)], provider)
        self.assertEqual(len(calls), 3)

    def test_open_k_tail_preserved_across_layers_no_overwrite_before_backing(self):
        r = RefillJoin(1)
        owners = [Owner(0, 0, layer, 0) for layer in range(36)]
        for pos in range(16):
            for owner in owners:
                closed = r.append_k(owner, pos, bytes([pos])*256)
                self.assertEqual(closed, pos == 15)
        a = owners[0]
        closed = r.closed_k(a)
        self.assertEqual(closed, bytes(range(16))*256)
        with self.assertRaises(ValueError): r.append_k(a, 16, bytes(256))
        with self.assertRaises(ValueError): r.retire_k(a, bytes(4096))
        r.retire_k(a, closed)
        self.assertFalse(r.append_k(a, 16, bytes(256)))
        self.assertEqual(len(r.tails), 36)

    def test_current_open_tail_reads_and_actual_provider_recovery(self):
        class Provider:
            def validate(self, owner, count):
                if count != 15: raise ValueError('fixture prefix')
            def read_byte(self, owner, kind, head, position, dim):
                return position+1
        owner = Owner(0, 0, 0, 0)
        r = RefillJoin(1); p = Provider()
        r.bind_open_k(owner, 15, p)
        r.append_k(owner, 15, bytes([77])*256)
        self.assertEqual(r.read_k(owner, 1, 15, 127, p), 77)
        self.assertEqual(r.read_k(owner, 0, 14, 0, p), 15)
        with self.assertRaises(ValueError): r.bind_open_k(owner, 15, p)


if __name__ == '__main__': unittest.main()
