import copy
import json
from pathlib import Path
import unittest
from head_norm_ring_book import book

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'results/token_pass/ds_head_ring_1029'


class RingBooking(unittest.TestCase):
    def setUp(self):
        self.booking = json.loads((DATA/'source_booking.json').read_text())
        self.network = json.loads((DATA/'source_exchange.json').read_text())

    def test_actual_collision_and_payload_preserving_repair(self):
        result = book(self.booking, self.network)
        report = result['ring_booking']
        self.assertEqual(report['engine_phase_edges'], {'VN': 0, 'VS': 1})
        self.assertEqual(report['original_collisions'], [dict(local=0, forward_origin=5,
            direction='E', hop=3, forward_delay_edges=56)])
        self.assertFalse(report['candidate_collisions'])
        self.assertEqual(report['extra_control_span_edges'], 1)
        self.assertEqual([r['ctl_payload'] for r in self.booking['rows']],
                         [r['ctl_payload'] for r in result['rows']])
        for original, fixed in zip(self.booking['rows'], result['rows']):
            self.assertEqual(fixed['issue_vo_edge']-original['issue_vo_edge'],
                             int(original['engine']=='VS'))
        self.assertFalse(result['adoption'])
        self.assertFalse(report['rtl_execution_qualified'])

    def test_missing_required_link_refused(self):
        self.network['transport']['nx_boundary'] = [r for r in self.network['transport']['nx_boundary']
            if not (r['status']=='PASS' and r['from_sid']==0 and r['from_port']=='ro_e')]
        with self.assertRaisesRegex(ValueError, 'open required hop'):
            book(self.booking, self.network)

    def test_same_issuer_collision_requires_redesign(self):
        # A VS phase cannot separate two VS partial groups.
        groups = {g['sid']: g for g in self.booking['groups']}
        groups[2]['aligned_partial_edge_excluding_common_local_vp_latency'] = (
            groups[0]['aligned_partial_edge_excluding_common_local_vp_latency']+11)
        with self.assertRaisesRegex(ValueError, 'same-issuer'):
            book(self.booking, self.network)

    def test_stale_graph_and_unaccounted_endpoint_refused(self):
        bad = copy.deepcopy(self.network)
        bad['die_sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'exact bound source'):
            book(self.booking, bad)
        self.network['transport']['xfin_endpoints'][0]['edges']['eo->nx_eo'] = 1
        with self.assertRaisesRegex(ValueError, 'endpoint'):
            book(self.booking, self.network)


if __name__ == '__main__':
    unittest.main()
