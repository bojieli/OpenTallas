import tempfile
import unittest
from pathlib import Path
import kv_fault_reset_loads as R


class ResetLoadTests(unittest.TestCase):
    def test_counts_exact_registered_chain_and_preserves_clocks(self):
        a=('leaf',0);b=('root',0)
        d=R.trace_reset(a,{a:[dict(instance='s0',input_bit=list(b),clock='c')]})
        self.assertEqual(d['registered_depth'],1);self.assertEqual(d['root_bit'],list(b));self.assertEqual(d['chain'][0]['clock'],'c')
    def test_cycle_refused(self):
        a=('a',0);b=('b',0)
        with self.assertRaisesRegex(ValueError,'cycle'):R.trace_reset(a,{a:[dict(input_bit=b)],b:[dict(input_bit=a)]})
    def test_multiple_drivers_refused(self):
        with self.assertRaisesRegex(ValueError,'multiple'):R.trace_reset(('a',0),{('a',0):[{},{}]})
    def test_regional_root_stays_explicit_and_unknown_root_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'case_kv').mkdir();(root/'case_kv/die.v').write_text('''module die();
wire ck,raw,region,leaf,unknown,dly;
qkd_host_rt host (.rst(raw));
qkd_rst_region rel (.ck(ck),.a(raw),.b(region),.dly(dly));
qkd_rlys_1 r (.ck(ck),.a(region),.b(leaf));
endmodule
''')
            (root/'case_kv/place.tcl').write_text('findInst r] 0 0 R0\nfindInst rel] 10 0 R0\nfindInst host] 20 0 R0\n')
            (root/'case_kv/elements.lef').write_text('MACRO qkd_rlys_1\n SIZE 2 BY 2 ;\n PIN b\n RECT 0 0 1 1 ;\n END b\nEND qkd_rlys_1\nMACRO qkd_rst_region\n SIZE 2 BY 2 ;\n PIN b\n RECT 0 0 1 1 ;\n END b\nEND qkd_rst_region\n')
            view=root/'physical/ref_tile/qkd_astk_fault_join/views/qkd_astk_fault_join';view.mkdir(parents=True)
            (view/'qkd_astk_fault_join.lef').write_text('PIN rst_n\n DIRECTION INPUT ;\n RECT 10 0 12 2 ;\n END rst_n')
            node=dict(id='fault_0',master='qkd_astk_fault_join',reset='leaf',clock='ck',placement=dict(x=20,y=30,orient='R0'))
            doc=R.derive(root,dict(nodes=[node]),root);load=doc['loads'][0]
            self.assertEqual(load['native_pin_xy'],[31,31]);self.assertEqual(load['root_instance'],'rel');self.assertEqual(load['required_target_depth'],1)
            self.assertIn('OPEN',doc['status']);node['reset']='unknown';doc=R.derive(root,dict(nodes=[node]),root)
            self.assertEqual(doc['unknown_root_loads'],1);self.assertIsNone(doc['loads'][0]['required_target_depth'])

if __name__=='__main__':unittest.main()
