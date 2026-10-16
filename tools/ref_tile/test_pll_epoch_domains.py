"""A real /12 epoch clock must retain fixed frequencies and ordinary STA."""
import copy
import unittest
import clock_entry_constraints as C


class EpochDomains(unittest.TestCase):
    def fixture(self, core_divider=3, other_divider=12):
        from fractions import Fraction
        ratio = Fraction(other_divider, core_divider)
        return dict(kind='tile', clock='multiple_cts_roots',
                    clock_port='ck', clock_ports=['ck', 'ck_other'],
                    clock_data_paths='related_pll_dividers',
                    clock_relationship=dict(kind='same_pll_fixed_phase', phase_ps=0,
                                            vco_dividers=dict(core=core_divider, other=other_divider)),
                    route=dict(period_ps=770 * core_divider / 3,
                               signoff_period_ps=833.333 * core_divider / 3),
                    clock_entry_domains=dict(
                        core=dict(ratio=[1, 1], ports=['ck'], inputs=['d'], outputs=[]),
                        other=dict(ratio=[ratio.numerator, ratio.denominator], ports=['ck_other'],
                                   inputs=[], outputs=['q'])))

    def test_four_to_one_source_capture_and_one_to_three_serial_release(self):
        source = self.fixture()
        self.assertTrue(C.related_data(source))
        clock = C.clocks(source, 833.333)
        self.assertIn('ot_entry_1 -period 3333.332000000', clock)
        serial = self.fixture(12, 4)
        self.assertTrue(C.related_data(serial))
        clock = C.clocks(serial, 3333.332)
        self.assertIn('ot_entry_1 -period 1111.110666667', clock)
        for forbidden in ('set_false_path', 'set_clock_groups', 'set_max_delay', 'set_multicycle_path'):
            self.assertNotIn(forbidden, clock)

    def test_all_three_roots_share_a_single_declared_phase_origin(self):
        spec = self.fixture()
        spec['clock_ports'].append('ck_serial')
        spec['clock_relationship']['vco_dividers']['serial'] = 4
        spec['clock_entry_domains']['serial'] = dict(ratio=[4, 3], ports=['ck_serial'], inputs=[], outputs=[])
        self.assertEqual(set(C.domains(spec)), {'core', 'other', 'serial'})
        clock = C.clocks(spec, 833.333)
        self.assertEqual(clock.count('create_clock'), 6)
        self.assertNotIn('-waveform', clock)

    def test_mutated_phase_ratio_divider_frequency_and_ownership_are_refused(self):
        mutations = [
            lambda s: s['clock_relationship'].update(phase_ps=1),
            lambda s: s['clock_relationship']['vco_dividers'].update(other=6),
            lambda s: s['clock_relationship']['vco_dividers'].update(other=True),
            lambda s: s['clock_relationship']['vco_dividers'].pop('other'),
            lambda s: s['clock_entry_domains']['other'].update(ratio=[2, 1]),
            lambda s: s['route'].update(signoff_period_ps=1000),
            lambda s: s['clock_entry_domains']['other'].update(ports=['ck']),
            lambda s: s['clock_entry_domains']['other'].update(asynchronous=True),
            lambda s: s.update(clock_relationship=['not-an-object']),
        ]
        for mutation in mutations:
            spec = copy.deepcopy(self.fixture())
            mutation(spec)
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                C.clocks(spec, 833.333)

    def test_old_ratio_policy_does_not_implicitly_enable_epoch_roots(self):
        spec = self.fixture()
        spec['clock_data_paths'] = 'related_pll_ratio'
        spec['clock_relationship'] = dict(kind='same_pll_fixed_phase', ratio=[4, 3], phase_ps=0)
        with self.assertRaises(ValueError):
            C.clocks(spec, 833.333)


if __name__ == '__main__':
    unittest.main()
