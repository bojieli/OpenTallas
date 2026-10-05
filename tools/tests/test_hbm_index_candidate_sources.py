import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_index_candidate_model import candidate_local, key, final_source
from hbm_index_candidate_sources import bind_candidate


class Boundary(unittest.TestCase):
    def test_actual_newest_owner_and_masked_nonowner(self):
        self.assertEqual(candidate_local([(1047552+i,0xff80) for i in range(8)],rank=0,position=1048575)['published'],[])
        owner=candidate_local([(1048568+i,0xff80) for i in range(8)],rank=31,position=1048575)
        self.assertEqual(owner['published'],[131071])
        self.assertEqual(owner['newest_owner'],31)

    def test_lowest_global_block_tie_and_signed_zero(self):
        self.assertEqual(key(0),key(0x8000))
        rows=[(8*b+i,0x3f80) for b in (0,96) for i in range(8)]
        self.assertEqual(candidate_local(rows,rank=0,position=1048575,k=1)['published'],[0])

    def test_foreign_rank_id_and_nan_refused(self):
        with self.assertRaises(ValueError): candidate_local([(8,0)],rank=0,position=1048575)
        with self.assertRaises(ValueError): key(0x7fc1)

    def test_final_rankmajor_order_gap_not_silently_sorted(self):
        rows=[(i,0x3f80) for i in range(96*512)]
        rows[0],rows[1]=(768,0x3f80),(8,0x3f80)
        with self.assertRaisesRegex(ValueError,'canonical global-ID gather missing'): final_source(rows)
        self.assertEqual(rows[:2],[(768,0x3f80),(8,0x3f80)])

    def test_program_retains_literal_ids_and_empty_quarters(self):
        empty=dict(last=True,global_ids=[0]*16,scores_bf16=[0xff80]*16,lane_valid=[False]*16)
        frame=dict(job=0xfedc1234,gen=13,position=1048575,rank=0,held_valid=True)
        r=bind_candidate(frame,[[empty],[empty],[empty],[empty]])
        self.assertEqual(r['held_frame'],frame)
        self.assertEqual(r['actual_keys'],0)
        self.assertFalse(r['reference_activation_operands'])

if __name__=='__main__': unittest.main()
