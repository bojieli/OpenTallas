import copy,json,tempfile,unittest
from pathlib import Path
import kv_hhp_historical_mesh_prepare as H
class Controls(unittest.TestCase):
    def test_default_off_without_inputs(self):
        self.assertEqual(H.prepare(None,None,None,None,None),{'status':'DISABLED','qualified':False})
    def test_wrong_cohort_rejects_before_read(self):
        with self.assertRaisesRegex(ValueError,'explicit PRIVATE'):
            H.prepare(None,None,None,None,None,enabled=True,cohort='PRODUCTION')
    def test_wrong_manifest_rejects_before_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'recovered manifest'):
                H.prepare(d,d,d,p,Path(d)/'out',enabled=True,cohort=H.COHORT)
            self.assertFalse((Path(d)/'out').exists())
    def test_parameterized_boundary_preserves_body(self):
        s='module m #(parameter X=1) (\n input wire clk\n);\n assign q=clk;\nendmodule\n'
        t=H.inject_header(s,'m',['ckm_w_n0','ckm_w_n1','ckm_w_n2','ckm_w_n3'])
        self.assertEqual(t.split(');',1)[1],s.split(');',1)[1]);self.assertEqual(t.count('output wire ck_mesh,'),1)
        with self.assertRaisesRegex(ValueError,'already present'):H.inject_header(t,'m',['ckm_w_n0'])
    def test_copied_bit_models_coherent(self):
        m={'pdecl':{},'part_conn':{},'pin_class':{}};old=copy.deepcopy(m)
        r=H.append_ft(m,[{'input_port':'ft_ck_i_0','output_port':'ft_ck_o_0','input_net':'ckm_w_n0','output_net':'ck_mesh'}])
        self.assertEqual(m,old);self.assertEqual(set(r['part_conn']),set(r['pin_class']));self.assertEqual(r['part_conn'][('ft_ck_o_0',None)],('ck_mesh',0))
    def test_normal_ft_shared_mesh_rejection_is_preserved(self):
        import ft_ports as FT
        with self.assertRaisesRegex(FT.FtError,'output is driven by two'):
            FT.declaration([{'cell':'real0','source':'ckm_w_n0','sink':'ck_mesh','kind':'clock'},{'cell':'real1','source':'ckm_w_n1','sink':'ck_mesh','kind':'clock'}],'PRIVATE HISTORICAL')
if __name__=='__main__':unittest.main()
