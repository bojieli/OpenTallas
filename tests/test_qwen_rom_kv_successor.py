"""Finite PC replacement protocol/address fixtures; no payload qualification."""
from pathlib import Path
import json
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_kv_successor as S

class SuccessorTests(unittest.TestCase):
    def test_pending_combined64_credits_and_immutable25edge_due(self):
        p=S.PendingReads()
        for i in range(64):p.issue((i,0),i,42,99,10)
        with self.assertRaisesRegex(ValueError,'64'):p.issue((100,0),100,42,99,10)
        for sector,producer,transport,edge in ((1,42,99,35),(0,43,99,35),(0,42,100,35),(0,42,99,34)):
            with self.assertRaisesRegex(ValueError,'identity/due'):p.returned((0,0),sector,producer,transport,edge,b'x'*32)
        self.assertEqual(len(p.pending),64);self.assertFalse(p.raw)
        p.returned((63,0),63,42,99,35,b'a'*32)
        with self.assertRaisesRegex(ValueError,'64'):p.issue((100,0),100,42,99,36)
        self.assertEqual(p.consume((63,0)),b'a'*32);p.issue((100,0),100,42,99,36)

    def test_return_duplicates_and_payload_provider_refused(self):
        p=S.PendingReads();p.issue((0,0),4,9,13,0)
        with self.assertRaisesRegex(ValueError,'payload'):p.returned((0,0),4,9,13,25,None)
        self.assertEqual(len(p.pending),1)
        p.returned((0,0),4,9,13,25,b'q'*32)
        with self.assertRaises(ValueError):p.returned((0,0),4,9,13,26,b'q'*32)
        with self.assertRaises(ValueError):p.issue((0,0),4,9,13,26)
        self.assertEqual(p.consume((0,0)),b'q'*32)

    def test_request_macro_capture_nextedge_and_whole_record(self):
        q=S.Lookahead();record=dict(sector=0,write=False,producer=11,transport=23,data=b'z'*32)
        q.edge(record);record['transport']=99
        self.assertIsNone(q.select(lambda _:True));q.edge()
        c=q.select(lambda _:True);self.assertEqual(c[2]['transport'],23)
        self.assertEqual(q.commit(c,lambda _:True)['data'],b'z'*32)

    def test_actual64slots16cache_and_no_whole_RAM_shift(self):
        q=S.Lookahead()
        for i in range(64):q.edge(dict(sector=i,write=False,producer=i,transport=i))
        for _ in range(17):q.edge()
        self.assertEqual(len(q.cache),16)
        with self.assertRaisesRegex(ValueError,'64'):q.edge(dict(sector=99,write=False))
        c=q.select(lambda r:r['sector']==7);q.commit(c,lambda _:True)
        self.assertEqual(q.ram[8][1]['sector'],8)
        q.edge(dict(sector=100,write=False));self.assertEqual(len(q.ram),64)
        with self.assertRaisesRegex(ValueError,'stale'):q.commit(c,lambda _:True)

    def test_alias_and_registered_final_revalidation_refusal(self):
        q=S.Lookahead()
        q.edge(dict(sector=1,write=True));q.edge(dict(sector=1,write=False));q.edge()
        self.assertIsNone(q.select(lambda r:not r['write']))
        c=q.select(lambda _:True)
        with self.assertRaisesRegex(ValueError,'revalidation'):q.commit(c,lambda _:False)
        self.assertEqual(len(q.ram),2)
        q.commit(c,lambda _:True)
        self.assertIsNone(q.select(lambda _:True,pending_aliases=[dict(sector=1,write=True)]))

    def test_bypass_is_bounded16_then_oldest_required(self):
        q=S.Lookahead()
        for i in range(32):q.edge(dict(sector=i,write=False))
        for _ in range(17):q.edge()
        for i in range(16):
            c=q.select(lambda r:r['sector']>0);self.assertIsNotNone(c);q.commit(c,lambda _:True)
            for _ in range(2):q.edge()
        self.assertEqual(q.skips,16);self.assertIsNone(q.select(lambda r:r['sector']>0))
        q.commit(q.select(lambda _:True),lambda _:True);self.assertEqual(q.skips,0)

    def test_native_deadlines_banks_maintenance_and_shared_command_slots(self):
        s=S.PCService()
        rd=s.column(0,0,0,False,0)
        wr=s.column(0,0,0,True,0)
        self.assertGreaterEqual(wr-rd,10000)
        again=s.column(0,0,0,False,0)
        self.assertGreaterEqual(again-wr,16000)
        future=s.column(0,0,131072,False,5000000)
        self.assertGreater(future,5000000)
        self.assertGreater(s.count['REF'],0);self.assertGreater(s.count['PREALL'],0)
        self.assertGreater(s.count['ACT'],1)
        self.assertEqual(sum(len(v) for paths in s.bus for v in paths),sum(s.count.values()))

    def test_PC_wait_does_not_lease_entire_shared_command_path(self):
        s=S.PCService();s.state(0,0)['refblock']=1000
        future=s.column(0,0,0,False,0)
        other=s.column(0,0,4,False,0) # PC1, same global command path
        self.assertLess(other,future)

    def test_ready_calendar_respects_group_lane_pool_and_reverse_credits(self):
        f=S.ready_layer_calendar(0,0,375834,S.PCService())
        self.assertLessEqual(f['peak_live_cohorts'],128)
        self.assertLessEqual(f['peak_words_per_group_lane_pool'],80)
        self.assertEqual(f['global_assembly_slots'],4480)
        self.assertEqual(f['command_count_per_stack'],[32736]*4)
        self.assertEqual(f['owned_data_and_grant_count_per_stack'],[65472]*4)
        self.assertTrue(f['all_reverse_grants_reserved'])
        self.assertGreaterEqual(f['end_ps'],f['fill_end_ps'])

if __name__=='__main__':unittest.main()
