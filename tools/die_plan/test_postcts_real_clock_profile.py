"""Exercise real/virtual clock classification with native Tcl semantics, no STA."""
from pathlib import Path
import tkinter
import unittest


class RealClockProfile(unittest.TestCase):
    def run_profile(self, names):
        t = tkinter.Tcl()
        t.eval('proc all_clocks {} {return $::names}; proc get_property {c p} {return [dict get $::sources $c]}; proc set_propagated_clock {x} {set ::propagated $x}')
        t.setvar('names', tuple(names))
        t.call('set', 'sources', t.call('dict', 'create', *[x for n, s in names.items() for x in (n, tuple(s))]))
        src = Path(__file__).with_name('postcts_gate.tcl').read_text()
        a = src.index('set ot_pg_virtual {}')
        b = src.index('set_clock_latency -source $ot_pg_bound', a)
        t.eval(src[a:b])
        line = next(l for l in src.splitlines() if l.startswith('set_propagated_clock '))
        t.eval(line)
        return tuple(t.splitlist(t.getvar('propagated'))), tuple(t.splitlist(t.getvar('ot_pg_virtual')))

    def test_forwarded_generated_and_arbitrary_real_names_are_propagated(self):
        names = {'clk': ['clk_t0'], 'fclk_in_u1_i': ['fclk_in_u1_i'],
                 'fclk_out_d1_o': ['fclk_out_d1_o'], 'recovered_lane9': ['rx_ck'], 'vclk': []}
        real, virtual = self.run_profile(names)
        self.assertEqual(real, ('clk', 'fclk_in_u1_i', 'fclk_out_d1_o', 'recovered_lane9'))
        self.assertEqual(virtual, ('vclk',))

    def test_missing_or_ambiguous_io_reference_refused(self):
        for names in ({'clk': ['clk']}, {'clk': ['clk'], 'vclk': [], 'other_ideal': []}):
            with self.assertRaises(tkinter.TclError): self.run_profile(names)

    def test_no_physical_root_refused(self):
        with self.assertRaises(tkinter.TclError): self.run_profile({'vclk': []})


if __name__ == '__main__':
    unittest.main()
