#!/usr/bin/env python3
"""spec io_budget for single-clock tiles: tightening only, reaches route, post-CTS boundary and sign-off."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ref_tile as RT  # noqa: E402

BASE = dict(name='t', top='t', kind='tile', clock_port='ck', reset_ports=['rst_n'])


class IoBudget(unittest.TestCase):
    def test_default_is_nominal_and_unchanged(self):
        self.assertEqual(RT.spec_io_budget(dict(BASE)), (0.2, 0.2))
        self.assertEqual(RT.io_budget_env(dict(BASE)), {})

    def test_tightened_reaches_env_and_route_sdc(self):
        s = dict(BASE, io_budget={'in': 0.6, 'out': 0.6})
        env = RT.io_budget_env(s)
        self.assertEqual(env, {'OT_IO_IN_BUDGET_PS': 500.0, 'OT_IO_OUT_BUDGET_PS': 500.0})
        sdc = RT.gen_sdc(s, 770)
        self.assertIn('set_input_delay 500.000', sdc)
        self.assertIn('set_output_delay 500.000', sdc)
        so = RT.gen_signoff(s, '*', 'none_*')
        self.assertIn('set ::env(OT_IO_IN_BUDGET_PS) 500.0', so)
        self.assertLess(so.index('OT_IO_IN_BUDGET_PS'), so.index('set ot_ib'))

    def test_loosening_and_unknown_keys_refused(self):
        for bad in ({'in': 0.1}, {'out': 0.9}, {'inp': 0.5}):
            with self.assertRaises(RT.SpecError):
                RT.spec_io_budget(dict(BASE, io_budget=bad))

    def test_clock_entry_modes_use_domains(self):
        with self.assertRaises(RT.SpecError):
            RT.spec_io_budget(dict(BASE, clock='multiple_cts_roots', io_budget={'out': 0.6}))


if __name__ == '__main__':
    unittest.main()
