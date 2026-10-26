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


class CollectivePhyClocks(unittest.TestCase):
    """Q-DIE11-COLL 10-18: SerDes link-side face roots leave clk_coll; per-bit related clocks reach the stand-in lib."""

    def test_link_side_face_roots_leave_the_core_trunk(self):
        from qwen_split import native_static_io_bind as B
        ports = {'face_ck': (55, 'input'), 'relay_ck': (30, 'input')}
        core = B.core_clock_pins(ports, True)
        self.assertEqual(B.serdes_face_bits(0), [23, 25, 26, 28, 29, 30, 31, 32])
        for b in range(55):
            self.assertEqual(f'face_ck{b}' in core, b < 22 or b % 11 in B.FACE_CORE_SLOTS)
        self.assertEqual(len(B.core_clock_pins(ports)), len(core) + 24)

    def test_related_pins_follow_the_rtl_capture_roots(self):
        from qwen_split import native_static_io_bind as B
        ports = {'face_ck': (55, 'input'), 'relay_ck': (30, 'input'), 'serdes_tx': (1791, 'output'),
                 'serdes_rx': (1791, 'input'), 'serdes_tx_valid': (3, 'output'), 'serdes_rx_valid': (3, 'input'),
                 'serdes_up': (3, 'input'), 'shared_tx': (1043, 'output'), 'shared_tx_valid': (1, 'output'),
                 'shared_rx': (1043, 'input'), 'shared_rx_valid': (1, 'input'), 'ucie_up': (1, 'input')}
        rel = B.related_pins(ports, True)
        self.assertEqual(rel['serdes_rx'][0], 'face_ck[28]')
        self.assertEqual(rel['serdes_rx'][597], 'face_ck[39]')
        self.assertEqual(rel['serdes_tx'][1790], 'face_ck[50]')
        self.assertEqual(rel['srx2'], ['face_ck[50]'] * 597)
        self.assertEqual(rel['shared_rx'][5], 'fdi_rx_ck')
        self.assertEqual(rel['shared_tx_valid'], ['fdi_ck'])
        self.assertEqual(B.related_pins(ports, False), {})
        ports['serdes_rx'] = (1790, 'input')
        with self.assertRaises(ValueError):
            B.related_pins(ports, True)

    def test_stand_in_lib_emits_per_bit_related_clocks(self):
        import qwen_die_element_lib as E
        lef = {'coll': {'clk': 1, 'face_ck': 3, 'fdi_ck': 1, 'd': 2, 'q': 1}}
        E.IDX.update({('coll', 'clk'), ('coll', 'fdi_ck')})
        stubs = {'coll': {'d': ['input', 0, set()], 'q': ['output', 0, set()]}}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'x.lib'
            E.write_lib('tt', lef, stubs, out, clock_ports={'coll': ['clk', 'face_ck', 'fdi_ck']},
                        related_pins={'coll': {'d': ['face_ck[2]', 'fdi_ck'], 'q': ['fdi_ck']}})
            text = out.read_text()
            self.assertIn('pin (d[0]) { direction : input', text)
            self.assertIn('related_pin : "face_ck[2]"', text)
            self.assertIn('related_pin : "fdi_ck[0]"', text)
            E.write_lib('tt', lef, stubs, out, clock_ports={'coll': ['clk', 'face_ck', 'fdi_ck']})
            self.assertNotIn('face_ck[2]', out.read_text())
