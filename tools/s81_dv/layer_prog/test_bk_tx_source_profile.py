"""IDX FACE2 source selection and its compiled static tree reservation."""
import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parent

def load(name):
    s=importlib.util.spec_from_file_location(name,ROOT/(name.split('_test')[0]+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class TestTxSourceProfile(unittest.TestCase):
    def test_source_profile_uses_selected_parent(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'parent.sv'
            p.write_text('module dsdv_bk_sel_vmtx; dsdv_idx_tx_n32 #(.FACE(2), .PDC(1)) u_tx (.ck(clk)); endmodule')
            m=load('bk_tx_source_profile');r=m.profile(p)
            self.assertEqual(r['environment'],{'OT_BK_TX_FACE':'2'})
            self.assertEqual(r['internal_output_edges'],3)
            self.assertFalse(r['transport_included'])
            p.write_text(p.read_text().replace('.FACE(2)', '.FACE(unknown)'))
            with self.assertRaisesRegex(ValueError,'explicit supported'):m.profile(p)

    def test_face2_preserves_real_reserved_tree_slots(self):
        scores=(np.arange(4096,dtype=np.float32).view(np.uint32)&np.uint32(0xffff0000)).view(np.float32)
        local=np.concatenate([np.arange(i*1024+512,(i+1)*1024,dtype=np.int64) for i in range(4)])
        allp={};mods={}
        for face in (0,2):
            with patch.dict(os.environ,{'OT_BK_TX_FACE':str(face)}):m=load('lower_bk_test'+str(face))
            m.load_op=lambda fx,name:scores if name=='attn.idx.score' else local
            plans,summary=m.job_rank_tree_rd('synthetic',k_dies=3,layer='L14',leg=845)
            self.assertTrue(summary['closure']);allp[face]=plans;mods[face]=m
        for die in (1,2):
            a,b=allp[0][die]['tx'],allp[2][die]['tx']
            self.assertEqual(a['dly']-b['dly'],3);self.assertGreaterEqual(b['dly'],1)
            self.assertEqual((a['first'],a['arrive'],a['words']),(b['first'],b['arrive'],b['words']))
            self.assertLess(((a['payload']^b['payload'])>>69),(1<<16))
        self.assertEqual(allp[0][0]['egress'],allp[2][0]['egress'])
        with self.assertRaisesRegex(ValueError,'needs first slot'):mods[2].tx_slot_delay(110,100)

    def test_unsupported_source_face_rejected(self):
        with patch.dict(os.environ,{'OT_BK_TX_FACE':'3'}):
            with self.assertRaisesRegex(ValueError,'selected transmitter'):load('lower_bk_testbad')

if __name__=='__main__':unittest.main()
