import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fullwidth_service_r6_tests', ROOT / 'tools/h3_complete_native_calendar_fullwidth_service_r6.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FullWidthTests(unittest.TestCase):
    def calendar(self, **kwargs):
        return m.FullWidthCalendar(m.prospective_parameters(8, 8), **kwargs)

    def submit(self, c, token=0, SM=0, tag=0xdeadbeef, generation=0):
        return c.admit(occurrence=str(token), owner=m.owner46(127, 5, tag, generation), SM=SM, RF_slot=511)

    def test_exact_fullwidth_original_tag_and_echo(self):
        for tag in (0, 0xffff, 0xffffffff):
            x = m.owner46(127, 5, tag, 15)
            self.assertEqual(m.unpack_owner(x), dict(physical_PC=127, client=5, original_tag=tag, generation=15))
        row = self.submit(self.calendar())
        self.assertEqual(row['owner55'] >> 9, row['owner46'])
        self.assertEqual(row['owner55'] & 511, 511)
        c=self.calendar()
        row=self.submit(c)
        for event in c.events:
            self.assertEqual(event['owner46'],row['owner46'])
            self.assertEqual(event['backend_PT35'],(5<<32)|0xdeadbeef)
            self.assertEqual(event['backend_generation4'],0)
        with self.assertRaises(ValueError):
            m.owner46(0, 6, 1, 0)
        with self.assertRaises(ValueError):
            m.owner46(0, 5, 1 << 32, 0)

    def test_every_positive_term_and_source_latency_floor(self):
        p = m.prospective_parameters(8, 8)
        for term in m.TERMS:
            with self.subTest(term=term):
                with self.assertRaises(ValueError):
                    m.FullWidthCalendar(dict(p, **{term:0}))
        with self.assertRaises(ValueError):
            m.FullWidthCalendar(dict(p, forward=1))
        c = self.calendar()
        row = self.submit(c)
        self.assertEqual(len(c.events), len(m.TERMS) + 45)
        self.assertEqual(row['retire'], 781)
        self.assertEqual([e['kind'] for e in c.events[-10:]], list(m.TERMS[6:]))
        for kind in ('backend_read','return_data','response_capture'):
            self.assertEqual(sum(e['kind']==kind for e in c.events),16)

    def test_owner_and_slot_remain_until_reverse_CDC_and_drain(self):
        c = self.calendar()
        first = self.submit(c)
        second = self.submit(c, token=1, tag=10)
        self.assertGreaterEqual(second['admit'], first['all_copies_drain_end'])
        self.assertEqual(c.events[-1]['kind'], 'all_copies_drain')
        for e in c.events:
            self.assertGreater(e['end'], e['start'])

    def test_actual_route_II40_competing_SM_and_candidate_replacement(self):
        for route, ii in [('held',40), ('elastic_proposal',1)]:
            c = self.calendar(route=route)
            for sm in range(32):
                self.submit(c, token=sm, SM=sm, tag=sm)
            forwards = [e for e in c.events if e['kind'] == 'forward']
            for e in forwards:
                self.assertEqual(e['resource_release'] - e['start'], ii)
            for resource in {tuple(e['resource']) for e in c.events}:
                for seat in range(4):
                    events = sorted((e for e in c.events if tuple(e['resource']) == resource and e['seat'] == seat), key=lambda e:e['start'])
                    for a,b in zip(events,events[1:]):
                        self.assertGreaterEqual(b['start'], a['resource_release'])
            self.assertFalse(c.summary()['hardware_admitted'])

    def test_modulo_wrap_not_cap_and_positive_quiescence_wait(self):
        c = self.calendar()
        previous = None
        for i in range(81):
            row = self.submit(c, token=i, generation=i % 16)
            if previous:
                self.assertGreaterEqual(row['admit'], previous['all_copies_drain_end'])
            previous = row
        self.assertEqual(c.summary()['modulo16_wraps'], 5)
        self.assertIsNone(c.summary()['generation_cap'])
        self.assertEqual(c.summary()['actual_production_calls'], 0)
        with self.assertRaises(ValueError):
            self.submit(c, token='bad', generation=2)

    def test_paid_occurrence_keeps_resource_reservation_and_no_double_charge(self):
        paid = {'0:forward':dict(kind='forward',duration=44)}
        c = self.calendar(already_paid=paid)
        self.submit(c)
        summary = c.summary()
        self.assertEqual(summary['retained_existing_edges'],44)
        self.assertEqual(summary['incrementally_paid_edges'],sum(e['duration'] for e in c.events)-44)
        self.assertEqual(next(e for e in c.events if e['kind']=='forward')['resource_release'],41)
        bad = self.calendar(already_paid={'0:forward':dict(kind='forward',duration=1)})
        with self.assertRaises(ValueError):
            self.submit(bad)
        self.assertEqual(bad.events, [])
        self.assertEqual(bad.pools, {})

    def test_prospective_sensitive_to_endpoint_and_drain_bounds(self):
        times=[]
        for bound in (8,64,256):
            c=m.FullWidthCalendar(m.prospective_parameters(bound,bound))
            times.append(self.submit(c)['retire'])
        self.assertEqual(times,[781,1421,5261])

    def test_source_archives_and_full_program_unknown_preserved(self):
        import json
        out=m.model_outputs()
        model=json.loads(out['model.json'])
        self.assertEqual(model['W2_minimum']['total_raw_bits'],466944)
        self.assertFalse(model['fields']['new_directory_client'])
        self.assertFalse(model['production_admitted'])
        self.assertFalse(model['selected_source_inventory']['actual_journal_composed'])
        self.assertIsNone(model['whole_token_ns'])
        transport=model['transport_identity_replacement']
        self.assertEqual(transport['incremental_protected_bits'],700416)
        self.assertEqual(transport['directions']['request']['cut_bits_per_SM'],1736)
        self.assertEqual(transport['directions']['return']['cut_bits_per_SM'],1448)
        self.assertEqual(model['selected_source_inventory']['source_PC_counts'],dict(Qwen=1737,DS=2213))


if __name__ == '__main__':
    unittest.main()
