"""Source-hash cursor/credit scheduling checks, not provider qualification."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_kv_credit_allocator as A

class CreditAllocatorTests(unittest.TestCase):
    def test_exact_all36_source_extents_once_and_per_group_order(self):
        for layer in range(36):
            actual=[]
            for group in range(8):
                cursor=A.GroupCursor(layer,group);records=[]
                while cursor.head is not None:
                    kind,base,n=cursor.head
                    self.assertEqual(A.burst_group(base,n),group)
                    if kind in ('KW','VW'):self.assertEqual(n,1)
                    records.append(cursor.head);cursor.advance()
                self.assertEqual(len(records),len(set(records)));actual.extend(records)
            expected=[]
            for head in range(2):
                k=(layer*2+head)*8192;v=k+589824
                for kind,base,length in [('K',k,8160),('V',v,8192),('KW',k+8176,16),('VW',v+8188,4)]:
                    while length:
                        n=1 if kind in ('KW','VW') else min(length,16-base%16);expected.append((kind,base,n));base+=n;length-=n
            self.assertCountEqual(actual,expected)
            for group in range(8):
                c=A.GroupCursor(layer,group);ordered=[]
                while c.head is not None:ordered.append(c.head);c.advance()
                self.assertEqual(ordered,[r for r in expected if A.burst_group(r[1],r[2])==group])

    def test_credit_blocked_group_cannot_block_other_heads(self):
        self.assertEqual(A.select_group([2,5],0),2)
        self.assertEqual(A.select_group([2,5],3),5)
        self.assertIsNone(A.select_group([],0))

    def test_rotating_fairness_all_eligible_within_eight_accepts(self):
        for start in range(8):
            seen=[];rr=start
            for _ in range(8):
                g=A.select_group(list(range(8)),rr);seen.append(g);rr=(g+1)%8
            self.assertEqual(len(set(seen)),8)

    def test_invalid_partition_is_refused(self):
        for layer,group in ((36,0),(0,8),(-1,0)):
            with self.assertRaises(ValueError):A.GroupCursor(layer,group)
        with self.assertRaises(ValueError):A.select_group([8],0)

    def test_finite_calendar_reverse_credits_and_exact_bytes(self):
        r=A.credit_layer_calendar(0,0,375834,A.S.PCService())
        self.assertEqual(r['cohorts'],2084);self.assertEqual(sum(r['group_issues'].values()),2084)
        self.assertEqual(r['maximum_descriptor_heads'],8)
        self.assertLessEqual(r['peak_live_cohorts'],128)
        self.assertLessEqual(r['peak_pending_entries_per_PC'],64)
        self.assertLessEqual(r['peak_write_slots_per_PC'],4)
        self.assertLessEqual(r['peak_words_per_group_lane_pool'],80)
        self.assertEqual(r['command_count_per_stack'],[32736]*4)
        self.assertEqual(r['owned_data_and_grant_count_per_stack'],[65472]*4)
        self.assertEqual(r['allocator_registered_edges'],3)
        self.assertGreaterEqual(r['end_ps'],r['fill_end_ps'])
        self.assertTrue(r['all_reverse_grants_reserved'])
        self.assertFalse(r['physical_or_payload_qualification'])

if __name__=='__main__':unittest.main()
