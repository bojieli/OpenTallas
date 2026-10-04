"""Source layout and launch contracts; numerical gate runs separately."""
import unittest
from unittest.mock import patch
from tools.gpu_sys import v41_dspark_connected as C


class LayoutLaunchTest(unittest.TestCase):
    def test_actual_hidden_span_fits_every_slot(self):
        layout=C.column_layout()
        self.assertEqual(layout['end'],4644)
        self.assertEqual(layout['old_overlap_bytes'],36)
        self.assertEqual(layout['stride'],4736)
        self.assertEqual(layout['added_bytes_total'],3328)
        for slot in range(layout['slots']-1):
            self.assertLessEqual(slot*layout['stride']+layout['end'],(slot+1)*layout['stride'])

    def test_successor_allocates_stride_before_generating_kernels(self):
        program=C.ConnectedProgram.__new__(C.ConnectedProgram)
        program.a={};program.cur=4096;program.CSTR=C.OLD_STRIDE
        program.put('COL',C.D.NCOLSLOT*C.OLD_STRIDE)
        self.assertEqual(program.CSTR,4736)
        self.assertEqual(program.cur-program.a['COL'],13*4736)
        program.put('AFTER',64)
        self.assertGreaterEqual(program.a['AFTER'],program.a['COL']+13*4736)

    def test_six_verify_columns_launch_real_existing_layer_kernels(self):
        cmd=dict(op='VLAYER',idx=0,ncol=6,pos=8,toks=[3,4,5,6,7,8],tok1=0)
        C.validate_command(cmd,noise=3519)
        launches=C.D.expand(cmd)
        self.assertEqual(len(launches),24)
        self.assertEqual([v for v in launches if v[0]=='embed'],[('embed',t,8+i) for i,t in enumerate(cmd['toks'])])
        self.assertEqual([v for v in launches if v[0]=='swapout'],[('swapout',i,8+i) for i in range(6)])

    def test_draft_block_all_fronts_precede_back_phase(self):
        cmd=dict(op='DSTAGE',idx=0,ncol=5,pos=7,toks=[],tok1=5)
        C.validate_command(cmd,noise=3519)
        with patch.object(C.D,'NOISE',3519):
            launches=C.D.expand(cmd)
        positions=[i for i,v in enumerate(launches) if v[0]=='dsa']
        backs=[i for i,v in enumerate(launches) if v[0]=='dsb']
        self.assertEqual(len(positions),5)
        self.assertLess(max(positions),min(backs))
        self.assertEqual([v for v in launches if v[0]=='demb'],[('demb',5,0)]+[('demb',3519,0)]*4)

    def test_current_cmdproc_refuses_fullshape_token_truncation(self):
        cmd=dict(op='VLAYER',idx=0,ncol=1,pos=0,toks=[128799],tok1=0)
        with self.assertRaisesRegex(ValueError,'token16'):
            C.validate_command(cmd,noise=3519)

    def test_out_of_source_column_state_cannot_be_admitted(self):
        cmd=dict(op='VHEAD',idx=0,ncol=6,pos=28,toks=[],tok1=0)
        with self.assertRaisesRegex(ValueError,'storage extent'):
            C.validate_command(cmd,noise=3519)


if __name__=='__main__':
    unittest.main()
