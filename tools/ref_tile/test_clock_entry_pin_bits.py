import unittest

from pre_route_gate import Gate, check_pins, PortMap, module_port_ranges


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

    def test_single_bit_vector_is_scalar_after_synthesis(self):
        self.assertTrue(self.check(['one[0]'], {'one': (1, True)}))


if __name__ == '__main__':
    unittest.main()
