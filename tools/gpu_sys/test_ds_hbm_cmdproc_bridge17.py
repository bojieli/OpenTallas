import unittest
from tools.gpu_sys import ds_hbm_cmdproc_bridge17 as B
from tools.gpu_sys.test_ds_hbm_cmdproc_bridge import ENTRIES,Pins


class Token17Test(unittest.TestCase):
    def test_full_token_reaches_encoded_doorbell_without_narrowing(self):
        p=Pins(result=128799)
        p.ctl.update(cmd_op=0,cmd_idx=0,cmd_ncol=1,cmd_pos=0,cmd_toks=[128799])
        b=B.CmdprocBridge17(p,ENTRIES,noise=129264,enable=True)
        for _ in range(100):
            if b.step()['eng_done']: break
        self.assertEqual([e[2] for e in p.events if e[0]=='launch'],[0,0,128799,128799,128799,128799,0,0])
        self.assertEqual(b.launches,4)
    def test_result_high_bit_is_preserved_across_die_join(self):
        p=Pins(result=128799);p.ctl['cmd_ncol']=1
        b=B.CmdprocBridge17(p,ENTRIES,noise=129264,enable=True)
        for _ in range(100):
            if b.step()['eng_done']: break
        self.assertIn(('argmax',128799),p.events)
    def test_out_of_17bit_token_and_noise_refuse(self):
        cmd=dict(op='VLAYER',idx=0,ncol=1,pos=0,toks=[131072],tok1=0)
        with self.assertRaisesRegex(ValueError,'token17'):B.lower(cmd,ENTRIES,noise=0)
        with self.assertRaisesRegex(ValueError,'noise17'):B.lower(dict(cmd,toks=[128799]),ENTRIES,noise=131072)


if __name__=='__main__':unittest.main()
