import unittest
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from case_reach import branches, multicast_relay_ages, typed_clock_pins, xf


class BranchReach(unittest.TestCase):
    def test_d4_schema_far_branch_and_top_reset_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'views').mkdir()
            def macro(name, ports):
                return f'MACRO {name}\n SIZE 10 BY 10 ;\n' + ''.join(
                    f' PIN {p}\n DIRECTION {d} ;\n USE SIGNAL ;\n PORT\n LAYER M4 ;\n RECT 0 0 0.024 0.024 ;\n END\n END {p}\n'
                    for p, d in ports) + f'END {name}\n'
            (root / 'views' / 'test.lef').write_text(macro('Src', [('o', 'OUTPUT')]) + macro('Dst', [('i', 'INPUT'), ('rst_n', 'INPUT')]))
            (root / 'manifest.json').write_text(json.dumps(dict(placement={
                'near': dict(m='Dst', o='R0', x=10, y=0), 'far': dict(m='Dst', o='R0', x=12750, y=0),
                'source': dict(m='Src', o='R0', x=0, y=0)})))
            (root / 'die.v').write_text('module die(input wire rst_n);\n'
                '  Dst near (\n .i(data),\n .rst_n(rst_n)\n );\n'
                '  Dst far (\n .i(data),\n .rst_n(rst_n)\n );\n'
                '  Src source (\n .o(data)\n );\nendmodule\n')
            subprocess.run([sys.executable, str(Path(__file__).with_name('case_reach.py')), tmp],
                           capture_output=True, text=True, check=True)
            r = json.loads((root / 'reach.json').read_text())
            self.assertEqual(r['multicast']['data']['longest_um'], 12750)
            self.assertEqual(len(r['top_driven_nets']['rst_n']['loads']), 2)
            self.assertEqual(r['top_driven_nets']['rst_n']['reset_forest'], 'UNQUALIFIED')

    def test_far_branch_and_driver_last(self):
        ends = [('near', 'i', (10, 0)), ('far', 'i', (12750, 0)), ('source', 'o', (0, 0))]
        directions = {('source', 'o'): 'OUTPUT', ('near', 'i'): 'INPUT', ('far', 'i'): 'INPUT'}
        bs = branches(ends, directions)
        self.assertEqual([b[2] for b in bs], [10, 12750])
        self.assertEqual(len(bs), 2)

    def test_multiple_drivers_fail_closed(self):
        ends = [('a', 'p', (0, 0)), ('b', 'p', (1, 0))]
        self.assertIsNone(branches(ends, {('a', 'p'): 'OUTPUT', ('b', 'p'): 'OUTPUT'}))

    def test_all_oriented_pin_transforms(self):
        expected = {'R0': (12, 23), 'R90': (27, 22), 'R180': (18, 37), 'R270': (13, 28),
                    'MX': (12, 37), 'MY': (18, 23), 'MXR90': (13, 22), 'MYR90': (27, 28)}
        for orient, result in expected.items():
            with self.subTest(orient=orient):
                self.assertEqual(xf({'x': 10, 'y': 20, 'orient': orient}, 10, 20, 2, 3), result)

    def test_direct_and_two_cycle_multicast_are_not_equal_age(self):
        def edge(a, b):
            return dict(source=[*a, 0, 1], sink=[*b, 0, 1], bits=1)
        c = dict(instances={n: dict(master='hbfd_rly_48_NS' if n.startswith('r') else 'opaque')
                            for n in ('source', 'near', 'far', 'r0', 'r1')},
                 edges=[edge(('source', 'o'), ('near', 'i')), edge(('source', 'o'), ('r0', 'i')),
                        edge(('r0', 'o'), ('r1', 'i')), edge(('r1', 'o'), ('far', 'i'))])
        result = multicast_relay_ages(c)
        self.assertEqual(result['unequal_relay_age'], 1)
        self.assertEqual(result['rows'][0]['min_relay_cycles'], 0)
        self.assertEqual(result['rows'][0]['max_relay_cycles'], 2)
        self.assertIn('UNPROVEN', result['rows'][0]['compiled_equal_age_calendar'])

    def test_clock_abi_handles_signal_use_and_vector_clocks(self):
        c = dict(instances={'tile': dict(ports={'clk': dict(bits=1), 'clk_rf': dict(bits=2), 'rst_n': dict(bits=1)})},
                 clock_resets=[dict(instance='tile', port='clk', bits=1, kind='clock'),
                               dict(instance='tile', port='clk_rf', bits=2, kind='clock'),
                               dict(instance='tile', port='rst_n', bits=1, kind='reset')])
        self.assertEqual(typed_clock_pins(c), {('tile', 'clk'), ('tile', 'clk_rf[0]'), ('tile', 'clk_rf[1]')})


if __name__ == '__main__':
    unittest.main()
