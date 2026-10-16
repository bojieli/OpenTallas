import unittest

from pre_route_gate import Gate, check_pins


class ClockEntryPinBits(unittest.TestCase):
    def check(self, clocks, ports):
        gate = Gate()
        spec = dict(top='entries', pins={'W': list(ports)}, clock='hybrid_entries',
                    clock_port=clocks[0], clock_ports=clocks)
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

    def test_single_bit_vector_is_scalar_after_synthesis(self):
        self.assertTrue(self.check(['one[0]'], {'one': (1, True)}))


if __name__ == '__main__':
    unittest.main()
