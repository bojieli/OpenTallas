"""Exact-name SHP hierarchy admission and reviewed reset wiring regressions."""
import copy
import unittest
import async_fifo_hierarchy_audit as H
import async_gray_fifo_constraints as A


class ShpFifoAdmission(unittest.TestCase):
    def test_exact_yosys_module_names(self):
        for base in H.REVIEWED_FIFOS:
            for name in (base, '$paramod$'+'a'*40+'\\'+base,
                         '$paramod\\'+base+'\\WIDTH=32'):
                with self.subTest(name=name):
                    self.assertEqual(H.fifo_base(name), base)
                    self.assertTrue(H.fifo_module_type(name))
            for name in (base+'_rogue', 'rogue_'+base,
                         '$paramod$'+'a'*39+'\\'+base,
                         '$paramod\\'+base+'_rogue\\WIDTH=32'):
                with self.subTest(name=name):
                    self.assertIsNone(H.fifo_base(name))
                    self.assertFalse(H.fifo_module_type(name))

    @staticmethod
    def graph():
        cells={}
        nets={}
        for offset,side,leaf,sync,online,clk in (
                (0,'w','u_gw_leaf','u_wr_reset','wr_online','wr_clk'),
                (10,'r','u_gr_leaf','u_rd_reset','rd_online','rd_clk')):
            cells[sync]={'connections':{'sync_rst_n':[offset+1]}}
            cells[leaf]={'connections':{'rst_n_in':[offset+1], 'd':[offset+2],
                                       'clk':[offset+3], 'rst_n':[offset+4]}}
            nets[online]={'bits':[offset+2]};nets[clk]={'bits':[offset+3]}
            name='g_s[0].'+('wa' if side=='w' else 'rs')
            nets[name]={'bits':[offset+5]}
            cells[side+'_index']={'type':'$_DFF_PN0_',
                                  'connections':{'Q':[offset+5],'R':[offset+4]}}
        return {'cells':cells,'netnames':nets}

    def test_reviewed_group_reset_and_causal_miswirings(self):
        graph=self.graph();A._shp_reset_wiring(graph)
        for cell,pin,wrong in (('u_gw_leaf','rst_n_in',[99]),
                               ('u_gr_leaf','d',[99]),
                               ('u_gw_leaf','clk',[99]),
                               ('w_index','R',[14]),
                               ('r_index','R',[4])):
            mutant=copy.deepcopy(graph);mutant['cells'][cell]['connections'][pin]=wrong
            with self.subTest(cell=cell,pin=pin),self.assertRaises(ValueError):
                A._shp_reset_wiring(mutant)
        mutant=copy.deepcopy(graph);del mutant['cells']['w_index']
        with self.assertRaisesRegex(ValueError,'without a reviewed async group reset'):
            A._shp_reset_wiring(mutant)


if __name__=='__main__':unittest.main()
