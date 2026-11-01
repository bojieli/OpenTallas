import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).parent/'bf_asbuilt_1101/prepare.py'
s=importlib.util.spec_from_file_location('bf_prepare',p);M=importlib.util.module_from_spec(s);s.loader.exec_module(M)


class NXMonitor(unittest.TestCase):
    def test_only_nonexistent_forwarding_monitor_removed(self):
        tb='before\n'+M.XO_MONITOR+'\nif(ret_fault)$fatal; after'
        result=M.nx_testbench(tb,'module col_h9_l4_lp_asb_nx(output wire ret); endmodule','col_h9')
        self.assertNotIn('XO_MISMATCH',result)
        self.assertIn('if(ret_fault)$fatal;',result)
        self.assertIn('no XO pins',result)

    def test_actual_xo_port_cannot_be_excluded(self):
        with self.assertRaisesRegex(ValueError,'without XO'):
            M.nx_testbench(M.XO_MONITOR,'module col_h9_l4_lp_asb_nx(output wire ret, output wire xo); endmodule','col_h9')

    def test_wrong_selected_master_or_changed_monitor_fails_closed(self):
        for tb,plan in ((M.XO_MONITOR,'module col_h10_l4_lp_asb_nx(output wire ret); endmodule'),
                        ('changed','module col_h9_l4_lp_asb_nx(output wire ret); endmodule')):
            with self.assertRaises(ValueError):M.nx_testbench(tb,plan,'col_h9')


if __name__=='__main__':unittest.main()
