import tempfile
from pathlib import Path
import unittest

from pre_route_gate import Gate, check_pins, PortMap, module_port_ranges, rtl_ports


class ClockEntryPinBits(unittest.TestCase):
    def check(self, clocks, ports):
        gate = Gate()
        spec = dict(top='entries', pins={'W': list(ports)}, clock='hybrid_entries',
                    clock_port=clocks[0], clock_ports=clocks)
        ports = PortMap(ports, {k: [0, w-1] for k, (w, v) in ports.items() if v})
        check_pins(gate, spec, ports)
        return [item for item in gate.items if item['severity'] == 'FAIL']

    def test_vector_entries_and_scalar_root(self):
        self.assertEqual([], self.check(['hard[0]', 'hard[17]', 'soft'],
                                        {'hard': (18, True), 'soft': (1, False)}))

    def test_missing_and_out_of_range_entries(self):
        for clock in ['hard[18]', 'absent[0]', 'soft[0]', 'hard[-1]']:
            with self.subTest(clock=clock):
                self.assertTrue(self.check(['hard[0]', clock],
                                          {'hard': (18, True), 'soft': (1, False)}))

    def test_actual_nonzero_and_ascending_bounds(self):
        for declaration in ['input wire [35:18] hard', 'input wire [18:35] hard']:
            ranges = module_port_ranges(' (' + declaration + '); endmodule')
            self.assertEqual([18, 35], ranges['hard'])
            for bit, fail in [(0, True), (17, True), (18, False), (35, False), (36, True)]:
                gate = Gate()
                spec = dict(top='entries', pins={'W': ['hard']}, clock_port=f'hard[{bit}]')
                check_pins(gate, spec, PortMap({'hard': (18, True)}, ranges))
                self.assertEqual(fail, any(i['severity'] == 'FAIL' for i in gate.items))

    def test_single_bit_vector_retains_declared_clock_index(self):
        self.assertEqual([], self.check(['one[0]'], {'one': (1, True)}))

    def test_actual_parsed_single_bit_vector_and_scalar_clocks(self):
        # Parse real RTL declarations rather than supplying a width-only map:
        # equal vector bounds preserve their index, while scalar ports have none.
        for declaration, allowed, rejected in [
                ('input wire [0:0] ck', ['ck[0]'], ['ck[1]', 'ck[4]']),
                ('input wire [4:4] ck', ['ck[4]'], ['ck[0]', 'ck[3]', 'ck[5]']),
                ('input wire ck', ['ck'], ['ck[0]', 'ck[4]'])]:
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'entries.v').write_text('module entries(' + declaration + '); endmodule')
                ports = rtl_ports(['entries.v'], 'entries', root=root)
                self.assertIsNotNone(ports)
                for clock in allowed + rejected:
                    with self.subTest(clock=clock):
                        gate = Gate()
                        spec = dict(top='entries', pins={'W': ['ck']}, clock_port=clock)
                        check_pins(gate, spec, ports)
                        self.assertEqual(clock in rejected,
                                         any(i['severity'] == 'FAIL' for i in gate.items))


if __name__ == '__main__':
    unittest.main()
