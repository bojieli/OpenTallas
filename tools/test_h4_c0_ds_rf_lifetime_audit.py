import unittest
from h4_c0_ds_rf_lifetime_audit import audit_prefix, all_nested_source_references


class LifetimeTests(unittest.TestCase):
    def case(self, read):
        homes = [dict(version=v, SM=1, rank_group=[0], home=dict(class_='RF')) for v in ('a', 'b')]
        for h in homes: h['home'] = dict(**{'class': 'RF'}, slot_first=32, vectors=2)
        ops = [dict(pc=0, writes=[dict(version='a', home_indices=[0])], reads=[], rank_bindings=[dict(rank=0)]),
               dict(pc=1, writes=[dict(version='b', home_indices=[1])], reads=[dict(version='a')] if read else [], rank_bindings=[dict(rank=0)])]
        return dict(instructions=ops), homes

    def test_zero_reader_output_is_retained_by_actual_driver_rule(self):
        n, h = self.case(False)
        r = audit_prefix(n, h, 1)['first_collision']
        self.assertEqual((r['publication_PC'], r['retained_version']), (1, 'a'))
        self.assertIsNone(r['last_consumer'])
        self.assertEqual(r['shared_SM_slots'], [[1, 32], [1, 33]])

    def test_last_consumer_current_PC_still_live_during_publication(self):
        n, h = self.case(True)
        r = audit_prefix(n, h, 1)['first_collision']
        self.assertEqual(r['last_consumer'], 1)
        self.assertIn('not retired', r['retained_reason'])

    def test_last_consumer_prior_PC_releases_before_reuse(self):
        n, h = self.case(True)
        n['instructions'][1]['writes'] = []
        n['instructions'].append(dict(pc=2, writes=[dict(version='b', home_indices=[1])], reads=[], rank_bindings=[dict(rank=0)]))
        self.assertIsNone(audit_prefix(n, h, 2)['first_collision'])

    def test_aux_nested_reference_is_not_silently_dead(self):
        n, _ = self.case(False)
        n['instructions'][1]['provider_bindings'] = {'template': {'aux':
            {'kind': 'explicit_auxiliary_provider', 'identity_from_versions': ['a']}}}
        refs = all_nested_source_references(n)
        self.assertEqual(refs['a'][0]['PC'], 1)
        self.assertEqual(refs['a'][0]['path'][-2:], ['identity_from_versions', 0])

    def test_source_output_declaration_is_not_a_hidden_reader(self):
        n, _ = self.case(False)
        n['instructions'][0]['source_outputs'] = [dict(version='a')]
        self.assertNotIn('a', all_nested_source_references(n))
        n['instructions'][1]['source_outputs'] = [dict(version='a')]
        self.assertEqual(all_nested_source_references(n)['a'][0]['PC'], 1)


if __name__ == '__main__': unittest.main()
