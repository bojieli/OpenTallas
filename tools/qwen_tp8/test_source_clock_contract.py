"""Actual r10 vector roots and ordinary related-clock timing must be retained."""
import sys
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_libs as D
from qwen_split.clock_contract import build
from qwen_split.native_static_io_bind import core_clock_pins


class SourceClockContract(unittest.TestCase):
    def test_r10_block_roots_are_not_core_roots(self):
        ports = {'face_ck':(5,'input'),'relay_ck':(30,'input'),'blk_ck':(2,'input')}
        self.assertFalse(any(p.startswith('blk_ck') for p in core_clock_pins(ports)))

    def test_manifest_uses_real_clock_port_identity_and_refuses_missing_block_source(self):
        model = dict(insts=[SimpleNamespace(name='root',master='pll'),
                            SimpleNamespace(name='io',master='collective')],
                     buses=[('clk_coll_blk','clock_trunk',1,[('root','block'),('io','blk_ck0'),('io','blk_ck1')])],
                     port_join={'collective':{'blk_ck0':('blk_ck',[0]),'blk_ck1':('blk_ck',[1])}},
                     native_static_io_bind={'master':'collective'})
        contract = build(model, Path(__file__).resolve().parents[2])
        self.assertEqual(contract['clock_ports']['collective'], ['blk_ck'])
        self.assertEqual(contract['periods_ps']['coll_blk'],5000.)
        model['buses'] = []
        with self.assertRaisesRegex(ValueError,'200 MHz'):
            build(model, Path(__file__).resolve().parents[2])

    def test_vector_connections_preserve_actual_physical_bit_and_source_net(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'die.v'
            p.write_text("""module die();
wire n_clk_coll; wire n_clk_coll_blk; wire n_clk_ucie;
PLL root(.pll_c(n_clk_coll),.pll_b(n_clk_coll_blk),.pll_f(n_clk_ucie));
IO io(.clk(n_clk_coll),.blk_ck({n_clk_coll_blk,n_clk_coll_blk}),.fdi(n_clk_ucie));
endmodule
""")
            leaves = {'IO':{'tt':{'clk':0.,'blk_ck[0]':0.,'blk_ck[1]':0.,'fdi':0.}}}
            dirs = {'PLL':{'pll_c':'output','pll_b':'output','pll_f':'output'}}
            declared = {'IO':['clk','blk_ck','fdi']}
            drv,sinks,pins = D.clock_connections(p,dirs,leaves,declared)
            self.assertEqual(sinks,{'n_clk_coll','n_clk_coll_blk','n_clk_ucie'})
            self.assertEqual(pins['n_clk_coll_blk'], [('io','IO','blk_ck[0]'),('io','IO','blk_ck[1]')])
            self.assertEqual(drv['n_clk_coll_blk'],['root/pll_b'])
            leaves['IO']['tt'].pop('blk_ck[1]')
            with self.assertRaisesRegex(ValueError,'2 connected clock bits but 1 physical'):
                D.clock_connections(p,dirs,leaves,declared)

    def test_r10_all_related_clocks_are_timed_without_async_or_multicycle_cut(self):
        domains = {d:[(f'{d}/ck','leaf','ck')] for d in ('stream','ucie','coll_blk')}
        leaves = {'leaf':{'tt':{'ck':100.}}}
        text = D.clock_tcl(domains, leaves,'tt',
                           {'stream':2500/3,'ucie':1000.,'coll_blk':5000.},
                           [('stream','ucie','coll_blk')])
        self.assertIn('-period 1000.000000',text)
        self.assertIn('-period 5000.000000',text)
        self.assertNotIn('set_clock_groups',text)
        self.assertNotIn('set_false_path',text)
        self.assertNotIn('set_multicycle_path',text)
        self.assertIn('-from [get_clocks stream] -to [get_clocks coll_blk]',text)
        self.assertIn('-from [get_clocks coll_blk] -to [get_clocks stream]',text)

    def test_assumed_vector_roots_are_explicit_and_unqualified(self):
        ports = {'blk_ck':'input','face_ck':'input','data':'input'}
        with patch.object(D.E,'IDX',{('IO','blk_ck'),('IO','face_ck')}):
            refs = D.assumed_clock_refs('IO',ports,{'blk_ck':2,'face_ck':5,'data':10},
                                        {'IO':['blk_ck','face_ck']})
        self.assertEqual(len(refs),7)
        self.assertIn('blk_ck[1]',refs)
        self.assertIn('face_ck[4]',refs)
        self.assertNotIn('data',refs)


if __name__=='__main__':
    unittest.main()
