import copy
import json
from pathlib import Path
import unittest

from head_prepare_schedule import reserve


class HeadReservations(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.component = json.loads((root/'results/token_pass/codex_qwen_current_1029/native_current/head_prepare_bound.json').read_text())
        self.gen = 'a' * 64  # Deliberately synthetic selection; not an actual GEN receipt.
        self.timeline = dict(schema='opentallas.qwen.head_prepare_timeline.v1',
            compute_gen_sha256=self.gen, forbidden_send_slots=[],
            outgoing=dict(send_slot_to_bank_sample_edges=-1, send_slot_to_record_capture_edges=0,
                          path='TEST ONLY: head record producer + wrapper output capture'),
            events=[dict(user=u, token=123+u, position=79,
                         calendar_sample_edge=100*u, run_start_edge=100*u,
                         latest_send_slot_edge=100*u+90) for u in range(4)])
        self.timeline['events'][0]['host_at_sysface'] = dict(
            endpoint='sys_face.host_tuple', interval_basis='post_edge_publication',
            first_core_edge=24, last_core_edge=32,
            tag=(16 << 43) | (123 << 19) | (79 << 6), epoch=16,
            generation=2, fused_capability=True)

    def result(self):
        return reserve(self.component, self.timeline, self.gen)

    def test_real_bound_ages_late_host_and_all_mu_owners(self):
        result = self.result()
        self.assertEqual(result['head_prepare_edges'], 39)
        row = result['reservations'][0]
        self.assertEqual((row['native_prepare_capture_edge'], row['descriptor_core_edge'],
                          row['held_bank_ready_edge']), (12, 31, 37))
        self.assertEqual(result['reservations'][1]['held_bank_ready_edge'], 120)
        self.assertFalse(result['physical_qualified'])

    def test_early_host_obeys_pending_edge_not_filler_minimum(self):
        host = self.timeline['events'][0]['host_at_sysface']
        host.update(first_core_edge=0, last_core_edge=32)
        result = self.result()
        self.assertEqual(result['reservations'][0]['held_bank_ready_edge'], 21)
        self.assertEqual(result['head_prepare_edges'], 23)

    def test_filler_has_real_priority_over_pending_host(self):
        row = self.timeline['events'][1]
        row.update(calendar_sample_edge=17, run_start_edge=17)
        result = self.result()
        self.assertEqual(result['reservations'][0]['descriptor_core_edge'], 32)
        self.assertEqual(result['head_prepare_edges'], 40)

    def test_port_collision_moves_the_shared_slot(self):
        self.timeline['forbidden_send_slots'] = [39, 40]
        self.assertEqual(self.result()['head_prepare_edges'], 41)

    def test_actual_callback_leads_record_capture_and_consumes_bank_later(self):
        self.timeline['outgoing'].update(send_slot_to_bank_sample_edges=10,
                                         send_slot_to_record_capture_edges=18)
        result = self.result()
        self.assertEqual(result['head_prepare_edges'], 28)
        row = result['reservations'][0]
        self.assertEqual((row['reserved_bank_sample_edge'],row['reserved_record_capture_edge']), (38,46))

    def test_wrong_cohort_cannot_be_scheduled_later(self):
        self.timeline['events'][0]['host_at_sysface']['tag'] ^= 1 << 19
        with self.assertRaisesRegex(ValueError, 'tuple does not match'):
            self.result()

    def test_adjacent_deadline_and_live_bank_overwrite_fail(self):
        self.timeline['events'][0]['latest_send_slot_edge'] = 38
        with self.assertRaisesRegex(ValueError, 'deadline'):
            self.result()
        self.timeline['events'][0]['latest_send_slot_edge'] = 90
        duplicate = copy.deepcopy(self.timeline['events'][0])
        duplicate.update(calendar_sample_edge=1, run_start_edge=1)
        self.timeline['events'].append(duplicate)
        with self.assertRaisesRegex(ValueError, 'pending HOST'):
            self.result()


if __name__ == '__main__':
    unittest.main()
