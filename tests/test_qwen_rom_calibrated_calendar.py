"""Focused checks for the calibrated Qwen ROM KV-service calendar records."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import uarch_model_qwen_rom_calibrated_calendar as Q

REC = Q.OUT


def record(name):
    return json.loads((REC / name).read_text())


class IdentityTests(unittest.TestCase):
    def view(self, token_s=1e-4, cal='c', svc='s', **delivery):
        return dict(identity=Q.identity(**delivery), compute_calibration_id=cal, service_assumptions_id=svc, token_s=token_s)

    def test_twenty_fields_match_the_policy_review(self):
        self.assertEqual(len(Q.IDENTITY_FIELDS), 20)
        fields = json.loads((Q.INPUTS / 'policy/workload_identity.json').read_text())['q4_recommended_identity']['fields']
        self.assertEqual(tuple(fields), Q.IDENTITY_FIELDS)
        self.assertTrue(Q.DELIVERY_FIELDS < set(Q.IDENTITY_FIELDS))

    def test_workload_field_cannot_vary_or_be_declared(self):
        with self.assertRaises(Q.IdentityMismatch):
            Q.identity(decode_position=0)
        a = self.view()
        b = dict(self.view(), identity=dict(Q.identity(), speculation='dflash'))
        with self.assertRaisesRegex(Q.IdentityMismatch, 'speculation'):
            Q.compare(a, b)
        with self.assertRaisesRegex(Q.IdentityMismatch, 'only delivery'):
            Q.compare(a, b, ['speculation'])

    def test_delivery_difference_needs_declaration_and_must_differ(self):
        a = self.view(token_s=2e-4)
        b = self.view(token_s=1e-4, kv_delivery_policy='x')
        with self.assertRaisesRegex(Q.IdentityMismatch, 'undeclared: kv_delivery_policy'):
            Q.compare(a, b)
        r = Q.compare(b, a, ['kv_delivery_policy'])
        self.assertAlmostEqual(r['rate_gain_a_over_b'], 1.0)
        with self.assertRaisesRegex(Q.IdentityMismatch, 'does not differ'):
            Q.compare(a, b, ['kv_delivery_policy', 'fill_lanes'])
        with self.assertRaisesRegex(Q.IdentityMismatch, 'compute_calibration_id'):
            Q.compare(a, self.view(cal='other'))


class InputTests(unittest.TestCase):
    def test_inputs_pinned_and_measured_composition(self):
        got, l0, wid, dec, prot, nh, cool = Q.load_inputs()
        self.assertEqual(set(got), set(Q.INPUT_SHA256))
        c = Q.measured_compute(l0, nh)
        self.assertEqual((c['rest_cycles_pos0'], c['rest_cycles_8k'], c['nonlayer_cycles'], c['attention_8k_delta_cycles']),
                         (4217, 5437, 3042, 1220))
        self.assertEqual(c['measured']['me_lat_extra'], 167)

    def test_source_anchors_apply_once_and_missing_anchor_refuses(self):
        self.assertTrue(callable(Q.credit17_secded_calendar()))
        self.assertTrue(callable(Q.decoupled_credit17_secded_run()))
        with self.assertRaisesRegex(ValueError, 'anchor'):
            Q.edited('abc', {'zzz': 'y'}, 't')


class ServiceTests(unittest.TestCase):
    def test_strict_refab_issues_at_due_edge_not_at_arrival(self):
        s = Q.StrictREFab()
        nextref = s.state(0, 0)['nextref']
        s.column(0, 0, 0, False, (nextref + 5 * Q.REFI) * 1000)
        self.assertEqual(s.count['REF'], 6)
        self.assertLessEqual(s.max_refresh_lateness, 20)
        lazy = Q.S.PCService()
        lazy.column(0, 0, 0, False, (nextref + 5 * Q.REFI) * 1000)
        self.assertGreater(lazy.max_refresh_lateness, s.max_refresh_lateness)

    def test_one_layer_secded_calendar_stays_within_credit17_capacity(self):
        cal = Q.credit17_secded_calendar()
        r = cal(0, 0, Q.F(451 * 2500, 3), Q.StrictREFab())
        self.assertEqual(r['cohorts'], 2084)
        for field, bound in [('peak_live_cohorts', 136), ('peak_pending_entries_per_PC', 68),
                             ('peak_words_per_group_lane_pool', 85), ('peak_write_slots_per_PC', 4)]:
            self.assertLessEqual(r[field], bound)


class RecordTests(unittest.TestCase):
    def test_every_record_carries_identity_and_pins(self):
        for name in Q.RECORDS[:-1]:
            r = record(name)
            self.assertEqual(tuple(r['identity']), Q.IDENTITY_FIELDS, name)
            self.assertFalse(r['admission']['adoption'], name)
            self.assertFalse(r['admission']['new_RTL'], name)
            for p, h in r['pins']['review_inputs_sha256'].items():
                self.assertEqual(Q.sha(Q.ROOT / p), h, p)

    def test_statuses_and_headline_consistency(self):
        b, s, n, m = (record(x) for x in Q.RECORDS)
        self.assertTrue(b['reproduction']['reproduced'])
        self.assertTrue(s['like_for_like']['control_reproduces_baseline'])
        self.assertTrue(s['status'].startswith('REJECTED'))
        self.assertEqual(n['status'], 'SELECTED_FOR_BUILD_MODEL_ENTRY_NOT_ADOPTED')
        self.assertEqual(n['headline']['token_cycles'], 229158)
        g8 = s['like_for_like']['attention8k_unmeasured']['rate_gain']
        self.assertAlmostEqual(g8, b['sensitivity_8k_attention_unmeasured']['token_s'] / s['like_for_like']['attention8k_unmeasured']['candidate_s'] - 1)
        self.assertEqual(m['headline_numbers']['near_hbm_selected_for_build']['token_us'], n['headline']['token_us'])
        self.assertGreater(b['headline']['token_s'], n['headline']['token_s'])
        for name, verdict in m['refused_comparisons'].items():
            self.assertTrue(verdict.startswith('REFUSED'), name)
        self.assertIsInstance(n['unqualified_inputs'], list)
        self.assertTrue(any('0.9 TB/s' in u for u in n['unqualified_inputs']))
        self.assertTrue(any('floorplan' in u for u in n['unqualified_inputs']))


if __name__ == '__main__':
    unittest.main()
