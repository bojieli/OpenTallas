import copy
import unittest
from coll_safe2_parent_table import candidate

SOURCE='module ot_s81sl_slice_lepw_mu_coll_safe2(input wire clk, input wire [1103:0] bi, output wire [559:0] rt); endmodule\n'

class SafeParentTable(unittest.TestCase):
    def table(self):
        return {'masters':{'west':{'module':'ot_s81sl_slice_lepw_mu','rst':['rst_n','low']}},
                'rtl_widths':{'ot_s81sl_slice_lepw_mu':{'clk':1,'bi':1104,'rt':560,'tf':2}},
                'defines':['DSFD_PQ_STATIC_X2'],'rtl_files':['legacy.sv']}

    def test_required_widths_come_from_source_and_input_is_preserved(self):
        t=self.table();before=copy.deepcopy(t);r=candidate(t,SOURCE)
        self.assertEqual(t,before)
        self.assertEqual(r['rtl_widths']['ot_s81sl_slice_lepw_mu_coll_safe2'],{'clk':1,'bi':1104,'rt':560})
        self.assertEqual(r['masters']['west']['rst'],['rst_n','low'])
        self.assertIn('OT_S81PH_COLL_TF_CLEANUP',r['defines'])

    def test_stale_legacy_width_refuses(self):
        t=self.table();t['rtl_widths']['ot_s81sl_slice_lepw_mu']['bi']=1103
        with self.assertRaisesRegex(ValueError,'differs'):candidate(t,SOURCE)

    def test_missing_selected_width_contract_refuses(self):
        t=self.table();t['rtl_widths']={}
        with self.assertRaisesRegex(ValueError,'differs'):candidate(t,SOURCE)

    def test_obsolete_port_or_missing_module_refuses(self):
        with self.assertRaisesRegex(ValueError,'obsolete'):candidate(self.table(),SOURCE.replace(');',', output wire tf);'))
        with self.assertRaisesRegex(ValueError,'missing'):candidate(self.table(),SOURCE.replace('_coll_safe2','_other'))

if __name__=='__main__':unittest.main()
