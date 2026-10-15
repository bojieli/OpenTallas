import copy
import unittest
import full_su_operand_layout as F

class FullLayoutTests(unittest.TestCase):
    def test_full_spatial_capacity_and_all80_bank_edges(self):
        x=F.verify_layout(F.layout())
        self.assertEqual(x['moe_requests'],560)
        self.assertEqual(x['moe_bank_conflicts'],0)
        self.assertLess(x['highest_reserved_row'],16384)
    def test_actual_scalar_identity_selected_expert_and_shared(self):
        m=dict(alias='exp7.w1',stage=3,rank_slices=[dict(rows=[576*r,576*(r+1)]) for r in range(4)])
        y=F.field_destination(m,2,1152+575,selected=[1,5,7,9,11,383])
        self.assertEqual((y['tensor'],y['row'],y['word']),('sw_gu2',10752+256+35,15))
        m=dict(alias='shared.w2',stage=0,rank_slices=[dict(rows=[1280*r,1280*(r+1)]) for r in range(4)])
        y=F.field_destination(m,3,3840+1279)
        self.assertEqual((y['tensor'],y['row'],y['word']),('moe_e6',7954+4*79,15))
    def test_missing_native_selector_never_defaults_to_expert0(self):
        m=dict(alias='exp0.w1',stage=0,rank_slices=[dict(rows=[576*r,576*(r+1)]) for r in range(4)])
        with self.assertRaisesRegex(ValueError,'native EIDs'):F.field_destination(m,0,0)
    def test_all72_actual_w2_blocks_and_no_padding_blocks(self):
        seen=[]
        for rank in range(4):
            for block in range(18):
                v=F.sw_block(0,rank,block,gathered=True)
                seen.extend(range(v['global_w2_scalar_begin'],v['global_w2_scalar_begin']+32))
        self.assertEqual(seen,list(range(2304)))
        with self.assertRaises(ValueError):F.sw_block(0,0,18,gathered=False)
    def test_qb64_blocks_cover2048_source_columns(self):
        seen=[]
        for block in range(64):
            v=F.qb_block(block);seen.extend(range(v['scalar_begin'],v['scalar_begin']+32))
        self.assertEqual(seen,list(range(2048)))
        self.assertEqual(F.qb_block(32)['code_row'],10624+49)
    def test_reserved_ranges_reject_overlap_even_in_stride_holes(self):
        x=F.layout();x['moe_y']['base_row']=6001
        with self.assertRaisesRegex(ValueError,'overlap'):F.verify_layout(x)
    def test_all42_sw576_read_bursts_have12_distinct_banks(self):
        for slot in range(7):
            for burst in range(6):
                rows=[10752+128*slot+12*burst+p for p in range(12)]
                self.assertEqual(len({F.bank(r) for r in rows}),12)
                self.assertTrue(all(r%4==p%4 for p,r in enumerate(rows)))
    def test_stride_gaps_are_not_declared_committed(self):
        x=F.layout()['moe_e3']
        self.assertEqual((x['nrows'],x['used_rows'],x['row_stride']),(320,80,4))
        self.assertEqual(x['sparse_commit_profile']['expected_words'],1280)
        self.assertIsNone(x['sparse_commit_profile']['CHECK_after_last_commit'])
    def test_unimplemented576_kernel_never_uses_zero_padding(self):
        x=F.layout()['sw_gu0']
        self.assertEqual((x['used_rows'],x['required_hardware_lanes']),(72,576))
        self.assertFalse(x['native_kernel_bound'])

if __name__=='__main__':unittest.main()
