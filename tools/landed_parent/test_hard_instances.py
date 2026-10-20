import unittest,tempfile
from pathlib import Path
import lp
class HardInstances(unittest.TestCase):
    def test_source_preprocessing_and_default_identity(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'child.sv').write_text(lp.SELFTEST_CHILD);(p/'top.sv').write_text(lp.SELFTEST_TOP)
            s=dict(top='lpt_top',out_dir=str(p),sources=[str(p/'top.sv')],child_sources=[str(p/'child.sv')],clock_ports=['clk'],clock_pins=['clk'],reset_port='rst_n',reset_pins=['rst_n'],regions=[dict(name='ra',insts=['u0','u3'],centre=[0,0]),dict(name='rb',insts=['u1','u2'],centre=[900,0])])
            m=lp.Parent(s);plain=m.emit(m.plan(),'lpt_top_lp')[0]
            h=lp.Parent(dict(s,synthesis_hard_instances=['u0']));guard=h.emit(h.plan(),'lpt_top_lp')[0]
            def instances(text,defines):return {x['inst']:x for x in lp.parse_body(lp.parse_module(lp.preprocess(text,defines),'lpt_top_lp')['body'])[2]}
            self.assertEqual(instances(plain,[])['u0']['params'],instances(guard,[])['u0']['params'])
            self.assertEqual(instances(guard,['SYNTHESIS'])['u0']['params'],'')
            self.assertTrue(instances(guard,['SYNTHESIS'])['u1']['params'])
            e=lp.Parent(dict(s,synthesis_hard_instances=[]));self.assertEqual(plain,e.emit(e.plan(),'lpt_top_lp')[0])
            with self.assertRaisesRegex(SystemExit,'unknown'):lp.Parent(dict(s,synthesis_hard_instances=['TYPO']))
if __name__=='__main__':unittest.main()
