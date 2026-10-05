import unittest
from decimal import Decimal as D
from tools.w10_q_power_envelope import coefficients

class PowerEnvelopeTest(unittest.TestCase):
    def test_bus_capacitance_is_per_bit(self):
        text='''type (a) { bit_width : 12; }
        type (y) { bit_width : 274; }
        cell (rom) { cell_leakage_power : 20;
          bus (address) { bus_type : a; direction : input; capacitance : .5; }
          bus (data) { bus_type : y; direction : output; max_capacitance : 46.08; }
          pin (clk) { direction : input; capacitance : 8;
            internal_power () { rise_power (scalar) { values ("9"); }
              fall_power (scalar) { values ("0"); } } } }'''
        x=coefficients(text,'rom',D('1e-9'))
        self.assertEqual(sum(p['max_cap_fF'] for p in x['pins'].values()),D('12625.92'))
        self.assertEqual(sum(p['cap_fF'] for p in x['pins'].values()),D('14'))
        self.assertEqual(x['leakage_W'],D('2e-8'))
    def test_absolute_maxima_sum_even_exclusive_arcs(self):
        text='''cell (c) { pin (A) { direction : input; capacitance : 1;
        internal_power () { rise_power (p) { values ("-3,2"); }
        fall_power (p) { values ("4,1"); } }
        internal_power () { rise_power (p) { values ("5"); } } } }'''
        self.assertEqual(coefficients(text,'c',D('1e-12'))['internal_cycle_fJ'],D('12'))
    def test_missing_energy_is_not_zero(self):
        with self.assertRaises(ValueError):
            coefficients('cell (c) { pin (A) { direction : input; } }','c',D('1e-12'))
    def test_duplicate_cell_fails(self):
        with self.assertRaises(ValueError):coefficients('cell (c) {} cell (c) {}','c',D('1e-12'))
if __name__=='__main__':unittest.main()
