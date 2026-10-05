import copy
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / 'tools/h4_hbm_mtp_invocation_model.py'
spec = importlib.util.spec_from_file_location('mtp_invocation', P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class InvocationTests(unittest.TestCase):
    def plan(self, accepted=2, gamma=5, iteration=0, anchor=7):
        drafts = [10 + i for i in range(gamma)]
        targets = drafts[:accepted] + [100 + i for i in range(gamma + 1 - accepted)]
        return m.InvocationCompiler().compile(iteration, anchor, 9, drafts, targets, accepted,
            [dict(rank=17, SM=3, scope='protocol_control', directory_sha256='control-directory',
                  provider_reference='explicit-control-provider')])

    def test_released_source_shape_and_method_pins(self):
        d = m.model()
        c = d['source_contract']['configuration']
        self.assertEqual((c['n_layers'], c['n_mtp_layers'], c['dspark_n_routed_experts'],
                          c['dspark_n_activated_experts']), (40, 3, 128, 3))
        self.assertFalse(d['AR_program_is_MTP'])
        self.assertIsNone(d['actual_draft_native_program'])

    def test_six_actual_verify_positions_and_all_five_draft_rows(self):
        p = self.plan()
        stages = [v for v in p['invocations'] if v['identity']['phase'] == 'draft']
        verify = [v for v in p['invocations'] if v['identity']['phase'] == 'verify']
        self.assertEqual(len(stages), 15)
        self.assertEqual(len(verify), 240)
        self.assertEqual([v['identity']['position'] for v in verify[:6]], list(range(8, 14)))
        self.assertTrue(all(v['identity']['rank'] == 17 and v['identity']['SM'] == 3 for v in verify))
        self.assertEqual(verify[6]['dependencies'], [v['eventID'] for v in verify[:6]])
        self.assertTrue(all(v['native_operand_views'] is None for v in p['invocations']))

    def test_markov_sampling_is_dependent_and_source_bonus_unprocessed(self):
        p = self.plan(2)
        samples = [v for v in p['invocations'] if v['identity']['phase'] == 'markov']
        self.assertEqual(len(samples), 5)
        self.assertEqual(samples[1]['dependencies'], [samples[0]['eventID']])
        self.assertEqual(p['committed_positions'], [8, 9, 10])
        self.assertEqual(p['rejected_positions'], [11, 12, 13])
        self.assertEqual(p['next_anchor'], 10)
        self.assertEqual(p['bonus_position'], 11)
        self.assertFalse(p['bonus_KV_published'])
        self.assertEqual(p['emitted_tokens'], [10, 11, 100])

    def test_all_prefix_boundaries(self):
        for a in range(6):
            p = self.plan(a)
            self.assertEqual(len(p['committed_positions']), a + 1)
            self.assertEqual(len(p['rejected_positions']), 5 - a)
            self.assertEqual(p['compressor_rebuild']['count'], 9 + a)
            self.assertEqual(p['ring8']['required_verify_plus_anchor'], 7)

    def test_clipped_gamma_does_not_shrink_draft_attention_block(self):
        p = self.plan(1, gamma=2)
        self.assertEqual(sum(v['identity']['phase'] == 'draft' for v in p['invocations']), 15)
        self.assertEqual(sum(v['identity']['phase'] == 'markov' for v in p['invocations']), 5)
        self.assertEqual(sum(v['identity']['phase'] == 'verify' for v in p['invocations']), 120)

    def test_context_boundary_plain_verify_no_draft(self):
        p = self.plan(0, gamma=0)
        self.assertFalse(any(v['identity']['phase'] == 'draft' for v in p['invocations']))
        self.assertEqual(sum(v['identity']['phase'] == 'verify' for v in p['invocations']), 40)

    def test_repeated_iterations_do_not_alias_event_or_lease_ids(self):
        first = self.plan(iteration=0)
        second = self.plan(iteration=1, anchor=first['next_anchor'])
        self.assertFalse({v['eventID'] for v in first['invocations']} &
                         {v['eventID'] for v in second['invocations']})
        self.assertFalse({v['identity']['lease'] for v in first['invocations']} &
                         {v['identity']['lease'] for v in second['invocations']})

    def test_wrong_prefix_or_out_of_namespace_tokens_refuse(self):
        c = m.InvocationCompiler()
        b = [dict(rank=0, SM=0, scope='protocol_control', directory_sha256='x', provider_reference='x')]
        for drafts, targets, a in [([2], [3, 4], 1), ([2], [2, 4], 0), ([129280], [2, 3], 0)]:
            with self.assertRaises(ValueError):
                c.compile(0, 0, 1, drafts, targets, a, b)
        with self.assertRaises(ValueError):
            c.compile(0, 7, 1, [2], [3, 4], 0, b, max_position=9)

    def test_no_invented_rank_to_SM_or_AR_native_admission(self):
        c = m.InvocationCompiler()
        with self.assertRaises(ValueError):
            c.compile(0, 0, 1, [], [2], 0, [])
        with self.assertRaises(ValueError):
            c.compile(0, 0, 1, [], [2], 0, [dict(rank=17, SM=17, scope='production')])
        self.assertFalse(self.plan()['actual_native_iteration_admitted'])

    def lease(self, book, p, position, version='state-v1'):
        ident = m.identity(p['iteration'], position - p['anchor'] - 1, position,
                           'verify_state', 17, 3, version, 0, f'lease-{position}')
        book.reserve(ident, dict(kind='HBM_NATIVE_STATE', version=version,
            provider_reference='state-provider', physical_home_reference=f'actual-home-{position}'))
        return ident['lease']

    def test_persistent_state_need_not_have_fixed_home_SM(self):
        book = m.PositionLeases()
        lease = self.lease(book, self.plan(), 8)
        self.assertNotIn('SM', book.rows[lease]['home'])
        self.assertEqual(book.rows[lease]['identity']['SM'], 3)

    def test_rejected_suffix_debt_cannot_vanish_on_rollback(self):
        p = self.plan()
        book = m.PositionLeases()
        lease = self.lease(book, p, 11)
        book.debt(lease, 'accepted-read-0')
        book.resolve(p)
        drain = {k: True for k in m.DRAIN}
        rebuild = dict(source_slotrec_rebuilt=True, engram_snapshot_restored=True)
        with self.assertRaises(ValueError):
            book.discard(lease, drain, rebuild)
        with self.assertRaises(ValueError):
            book.reverse(lease, 'wrong', True)
        book.reverse(lease, 'accepted-read-0', True)
        with self.assertRaises(ValueError):
            book.discard(lease, dict(drain, reverse_CDC_matched=False), rebuild)
        with self.assertRaises(ValueError):
            book.discard(lease, drain, {})
        book.discard(lease, drain, rebuild)
        self.assertFalse(book.rows)

    def test_generation_cannot_reuse_retained_physical_home(self):
        book = m.PositionLeases()
        lease = self.lease(book, self.plan(), 11)
        row = book.rows[lease]
        ident = dict(row['identity'], generation=1, lease='new-gen')
        with self.assertRaises(ValueError):
            book.reserve(ident, row['home'])

    def test_commit_requires_actual_visibility_and_atomic_failure(self):
        p = self.plan()
        book = m.PositionLeases()
        a = self.lease(book, p, 8)
        b = self.lease(book, p, 9)
        book.visible(a)
        with self.assertRaises(ValueError):
            book.resolve(p)
        self.assertEqual(book.rows[a]['state'], 'reserved')
        book.visible(b)
        book.resolve(p)
        self.assertEqual(book.rows[a]['state'], 'committed')

    def test_once_only_cost_replacement_and_no_zero_or_fake_fetch(self):
        old = [dict(eventID='actual-child-return', source_receipt='source-A', ns=10)]
        replacement = dict(eventID='actual-child-return', source_receipt='source-A',
                           ns=12, clock_source='explicit nonzero source clock sensitivity')
        self.assertEqual(m.reconcile(old, [replacement])[0]['ns'], 12)
        for r in [dict(replacement, ns=0), dict(replacement, source_receipt='other'),
                  dict(replacement, eventID='blanket38.97fetch')]:
            with self.assertRaises(ValueError):
                m.reconcile(old, [r])
        with self.assertRaises(ValueError):
            m.reconcile(old, [replacement, replacement])

    def test_positive_finite_calendar_requires_every_invocation_span(self):
        p = self.plan()
        spans = [dict(eventID=v['eventID'], ns=1.0, source_receipt='control-' + v['eventID'],
                      clock_source='positive test assumption, not SS clock', scope='protocol_control')
                 for v in p['invocations']]
        c = m.compose_selected_intervals(p, spans)
        self.assertEqual(c['selected_invocation_span_ns_assumed'], len(spans))
        self.assertIsNone(c['full_iteration_ns'])
        with self.assertRaises(ValueError):
            m.compose_selected_intervals(p, spans[:-1])
        spans[0]['ns'] = 0
        with self.assertRaises(ValueError):
            m.compose_selected_intervals(p, spans)


if __name__ == '__main__':
    unittest.main()
