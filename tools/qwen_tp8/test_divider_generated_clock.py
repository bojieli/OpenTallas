"""QW-GENPREP 10-21 (QW-COLLIO): coll_blk from the real qfd_ckdiv6 is a generated clock (-divide_by 6) of stream."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_libs as D

DIE = """module die();
wire n_clk_coll; wire n_clk_coll_blk; wire rst;
PLL root(.pll_c(n_clk_coll));
qfd_ckdiv6 ckdiv_coll_blk(.ck(n_clk_coll),.rst_n(rst),.blk_o(n_clk_coll_blk));
IO io(.clk(n_clk_coll),.blk_ck({n_clk_coll_blk,n_clk_coll_blk}));
endmodule
"""


class DividerGeneratedClock(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = Path(self.td.name) / 'die.v'
        self.p.write_text(DIE)
        self.leaves = {'IO': {c: {'clk': 10., 'blk_ck[0]': 20., 'blk_ck[1]': 30.} for c in ('tt', 'ff', 'ss')},
                       'qfd_ckdiv6': {c: {'ck': 0.} for c in ('tt', 'ff', 'ss')}}
        dirs = {'PLL': {'pll_c': 'output'}, 'qfd_ckdiv6': {'ck': 'input', 'rst_n': 'input', 'blk_o': 'output'},
                'IO': {'clk': 'input', 'blk_ck': 'input'}}
        self.drv, sinks, pins = D.clock_connections(self.p, dirs, self.leaves, {'IO': ['clk', 'blk_ck']})
        self.doms = {}
        for net in sorted(sinks):
            for inst, m, pin in pins[net]:
                self.doms.setdefault(D.domain(net), []).append((f'{inst}/{pin}', m, pin))

    def tearDown(self):
        self.td.cleanup()

    def test_generated_from_divider(self):
        g = D.divider_clocks(self.p, self.drv)
        self.assertEqual(g['coll_blk']['source'], 'ckdiv_coll_blk/ck')
        self.assertEqual(g['coll_blk']['master'], 'stream')
        text = D.clock_tcl(self.doms, self.leaves, 'tt', {'stream': 2500 / 3, 'coll_blk': 5000.},
                           [('stream', 'coll_blk')], 'die', g)
        self.assertIn('create_generated_clock -name coll_blk -source [get_pins {ckdiv_coll_blk/ck}] '
                      '-master_clock [get_clocks stream] -divide_by 6', text)
        self.assertNotIn('create_clock -name coll_blk', text)
        self.assertLess(text.index('create_clock -name stream'), text.index('create_generated_clock'))
        self.assertIn('-from [get_clocks stream] -to [get_clocks coll_blk]', text)
        self.assertNotIn('set_clock_groups', text)

    def test_period_mismatch_refused(self):
        g = D.divider_clocks(self.p, self.drv)
        with self.assertRaisesRegex(ValueError, 'period'):
            D.clock_tcl(self.doms, self.leaves, 'tt', {'stream': 2500 / 3, 'coll_blk': 4000.},
                        [('stream', 'coll_blk')], 'die', g)

    def test_opt_out_keeps_independent_create_clock(self):
        self.assertEqual(D.divider_clocks(self.p, self.drv, enabled=False), {})


if __name__ == '__main__':
    unittest.main()
