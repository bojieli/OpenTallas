"""Client-affine VM banking (vm_slice_affinity + static_vm_reservations opt-in): positive and negative witnesses."""
import copy
import importlib.util
import sys
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('reservations', HERE / 'static_vm_reservations.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import vm_slice_affinity as A  # noqa: E402


def ev(eid, kind, client, row, cycle, slot=0, tag=0):
    e = dict(id=eid, kind=kind, client=client, slot=slot, row=row, tag=tag, issue_cycle=cycle, ingress_cycle=cycle + 1,
             bank_enqueue_cycle=cycle + 1, service_cycle=cycle + 2, deadline_cycle=cycle + 8)
    e['response_cycle' if kind == 'read' else 'commit_cycle'] = cycle + 4
    return e


class LayoutTests(unittest.TestCase):
    def test_striped_region_is_the_historical_map(self):
        reg = A.validate(dict(regions=[A.striped()], client_reach={}))[0][0]
        for row in (0, 1, 33, 4097, 16383):
            ch = A.chunks(row, reg)
            self.assertEqual([c[0] for c in ch], [0, 1, 2, 3])
            self.assertEqual({c[1] for c in ch}, {row})
            self.assertEqual({c[2] for c in ch}, {A.xor_bank(row)})

    def test_every_row_bank_distinct_within_slice(self):
        for sl in ([0, 1], [3], [0, 2]):
            per = 4 // len(sl)
            reg = A.validate(dict(regions=[dict(name='t', first_row=100, rows=4000, slices=sl,
                                                phys_base={s: 8 * per for s in sl})], client_reach={}))[0][0]
            for row in range(100, 4100, 7):
                ch = A.chunks(row, reg)
                per_slice = {}
                for s, p, b in ch:
                    per_slice.setdefault(s, []).append(b)
                self.assertEqual(sorted(per_slice), sorted(sl))
                for banks in per_slice.values():
                    self.assertEqual(len(banks), len(set(banks)), (sl, row))

    def test_sixteen_sequential_rows_fill_two_slices_conflict_free(self):
        # SU streams 16 rows/edge; on a 2-slice set that is 32 bank ops per slice = every bank once
        reg = A.validate(dict(regions=[dict(name='su', first_row=0, rows=1024, slices=[0, 1], phys_base={0: 0, 1: 0})],
                              client_reach={}))[0][0]
        for start in range(0, 1024, 16):
            used = {}
            for row in range(start, start + 16):
                for s, p, b in A.chunks(row, reg):
                    used.setdefault(s, []).append(b)
            for s, banks in used.items():
                self.assertEqual(sorted(banks), list(range(32)), (start, s))

    def test_rejects_bad_regions(self):
        def bad(r):
            return A.validate(dict(regions=[r], client_reach={}))[1]
        self.assertTrue(bad(dict(name='x', first_row=0, rows=8, slices=[0, 1, 2], phys_base={0: 0, 1: 0, 2: 0})))
        self.assertTrue(bad(dict(name='x', first_row=0, rows=8, slices=[0, 1], phys_base={0: 1, 1: 0})))   # misaligned
        self.assertTrue(bad(dict(name='x', first_row=0, rows=8193, slices=[3], phys_base={3: 0})))         # capacity
        two = [dict(name='a', first_row=0, rows=8, slices=[0, 1], phys_base={0: 0, 1: 0}),
               dict(name='b', first_row=8, rows=8, slices=[0, 2], phys_base={0: 8, 2: 0})]
        self.assertTrue(any('physical_overlap:slice0' in x for x in A.validate(dict(regions=two, client_reach={}))[1]))
        two[1]['phys_base'] = {0: 16, 2: 0}
        self.assertEqual(A.validate(dict(regions=two, client_reach={}))[1], [])

    def test_allocate_reports_overflow(self):
        out = A.allocate([dict(name='a', rows=5000, slices=[3])])
        self.assertTrue(out['overflow'])
        out = A.allocate([dict(name='a', rows=4096, slices=[3]), dict(name='b', rows=8192, slices=[0, 1])])
        self.assertFalse(out['overflow'])
        self.assertEqual(out['slice_rows_used'], {0: 16384, 1: 16384, 2: 0, 3: 16384})


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.contract = dict(stream_period_ps=1, vm_period_ps=1, stream_phase_ps=0, vm_phase_ps=0, banks=32,
            bank_mapping='xor_row7_5_shift2', bank_queue_capacity=4, bank_ops_per_cycle=1,
            read_ingress_per_cycle=32, write_ingress_per_cycle=32, request_min_ps=1, read_min_ps=1, commit_min_ps=1,
            slot_capacity={f'{c}/{k}/{s}': 1 for c in ('su', 'hc') for k in ('read', 'write') for s in range(32)},
            client_capacity={'su': 64, 'hc': 64}, measured_native_bounds=True,
            slice_affinity=dict(regions=[
                dict(name='su_t', first_row=0, rows=1024, slices=[0, 1], phys_base={0: 0, 1: 0}),
                dict(name='hc_t', first_row=1024, rows=512, slices=[3], phys_base={3: 0})],
                client_reach=dict(su=dict(read=[0, 1], write=[0, 1, 3]), hc=dict(read=[3], write=[3]))))
        self.schedule = dict(trace_complete=True, events=[], jobs=[])

    def run_check(self):
        for e in self.schedule['events']:
            if e['kind'] == 'write' and not any(j['tag'] == e['tag'] and j['client'] == e['client'] for j in self.schedule['jobs']):
                self.schedule['jobs'].append(dict(client=e['client'], tag=e['tag'], done_cycle=e['commit_cycle']))
        if not self.schedule['jobs']:
            self.schedule['jobs'].append(dict(client='su', tag=99, done_cycle=20))
        return m.check(self.schedule, self.contract)

    def kinds(self):
        return {x['kind'] for x in self.run_check()['violations']}

    def test_su_16_rows_per_edge_on_two_slices_pass(self):
        self.schedule['events'] = [ev(f'r{i}', 'read', 'su', i, 0, slot=i) for i in range(16)]
        r = self.run_check()
        self.assertEqual(r['status'], 'pass', r['violations'])
        self.assertFalse(r['qualified'])

    def test_17th_row_same_edge_collides_on_a_slice_bank(self):
        self.schedule['events'] = [ev(f'r{i}', 'read', 'su', i, 0, slot=i) for i in range(16)]
        self.schedule['events'].append(ev('r16', 'read', 'su', 16, 0, slot=16))
        self.assertIn('bank_collision', self.kinds())

    def test_same_rows_striped_do_not_collide(self):
        # same 17 accesses on the historical striped layout use 17 distinct banks per slice: no collision
        self.contract['slice_affinity']['regions'] = [A.striped()]
        self.contract['slice_affinity']['client_reach']['su'] = dict(read=[0, 1, 2, 3], write=[0, 1, 2, 3])
        self.schedule['events'] = [ev(f'r{i}', 'read', 'su', i, 0, slot=i) for i in range(16)]
        self.schedule['events'].append(ev('r16', 'read', 'su', 16, 0, slot=16))
        self.assertNotIn('bank_collision', self.kinds())

    def test_disjoint_sets_serve_two_clients_on_one_edge(self):
        self.schedule['events'] = [ev(f'r{i}', 'read', 'su', i, 0, slot=i) for i in range(16)]
        self.schedule['events'] += [ev(f'h{i}', 'read', 'hc', 1024 + i, 0, slot=i) for i in range(8)]
        self.assertEqual(self.run_check()['status'], 'pass')

    def test_hc_ninth_row_on_one_slice_collides(self):
        self.schedule['events'] = [ev(f'h{i}', 'read', 'hc', 1024 + i, 0, slot=i) for i in range(9)]
        self.assertIn('bank_collision', self.kinds())

    def test_unwired_client_access_rejected(self):
        self.schedule['events'] = [ev('h0', 'read', 'hc', 5, 0)]
        self.assertIn('affinity_unwired_access', self.kinds())

    def test_cross_set_write_allowed_only_when_wired(self):
        self.schedule['events'] = [ev('w0', 'write', 'su', 1030, 0)]
        self.assertNotIn('affinity_unwired_access', self.kinds())
        self.contract['slice_affinity']['client_reach']['su']['write'] = [0, 1]
        self.assertIn('affinity_unwired_access', self.kinds())

    def test_unmapped_row_rejected(self):
        self.schedule['events'] = [ev('r0', 'read', 'su', 3000, 0)]
        self.assertIn('affinity_row_unmapped', self.kinds())

    def test_invalid_affinity_contract_blocks_everything(self):
        self.contract['slice_affinity']['regions'][1]['slices'] = [0, 1, 2]
        r = self.run_check()
        self.assertEqual(r['status'], 'fail')
        self.assertEqual(r['violations'][0]['kind'], 'invalid_contract')

    def test_absent_affinity_keeps_historical_behaviour(self):
        del self.contract['slice_affinity']
        self.schedule['events'] = [ev(f'r{i}', 'read', 'su', i, 0, slot=i) for i in range(17)]
        self.assertEqual(self.run_check()['status'], 'pass')


if __name__ == '__main__':
    unittest.main()
