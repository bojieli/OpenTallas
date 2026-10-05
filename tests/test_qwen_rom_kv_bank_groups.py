"""Finite bank/credit fixtures and source-priced requirement screen only."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_kv_bank_groups as G

PARENT='6bb3ac9e7b05185e3e87ca0cdbe2dd8df1909359'

def record(tag,beat,callback=lambda:b'c'*32,base=0):
    return dict(tag=tag,beat=beat,pc=G.pc_of(base+beat),sector=base+beat,data=bytes([beat])*32,provider=callback)

class GroupsTests(unittest.TestCase):
    def test_aligned_bursts_follow_actual_XOR_PC_group(self):
        for base in range(0,131072,16):
            expected=((base>>4)^(base>>9)^(base>>14))&7
            self.assertEqual(G.burst_group(base,16),expected)
            self.assertEqual({G.pc_of(base+b)//4 for b in range(16)},{expected})
        with self.assertRaises(ValueError):G.burst_group(15,2)
        with self.assertRaises(ValueError):G.pc_of(703125000)

    def test_layer_homes_do_not_alias_and_total_debit_matches(self):
        total=[0,0]
        for l in range(36):
            for st in range(4):
                rs,ws=G.ranges(l,st)
                for i,intervals in enumerate((rs,ws)):total[i]+=sum(n for _,n in intervals)*32
                for base,n in rs+ws:self.assertLessEqual(base+n,703125000)
                if l:
                    prev,_=G.ranges(l-1,st)
                    self.assertEqual(rs[0][0]-prev[0][0],16384)
        self.assertEqual(total,[150690816,156672])
        with self.assertRaises(ValueError):G.ranges(35,3,user=596)

    def test_all1536_disjoint_destinations_and_real_fill_lane_skew(self):
        c=G.fill_destinations();self.assertEqual(len(c),1536)
        self.assertEqual(sum(c),65408)
        counts=[sum(n for t,n in enumerate(c) if t%6==lane) for lane in range(6)]
        self.assertEqual(counts,[10912]*4+[10880]*2)
        self.assertEqual([sum(t%6==lane for t in range(1536)) for lane in range(6)],[256]*6)
        self.assertGreater(max(counts),sum(counts)/6)

    def test_four_stack_cohort_binds_cross_stack_V_quarters_and_K_local_pairs(self):
        for layer in (0,1,35):
            for head in range(2):
                k=(layer*2+head)*8192;v=k+589824
                words,stacks=G.cohort_words(layer,k)
                self.assertEqual(len(words),32);self.assertEqual([len(s) for s in stacks],[8]*4)
                self.assertFalse(stacks[0]&stacks[1])
                words,stacks=G.cohort_words(layer,v)
                self.assertEqual(len(words),32);self.assertTrue(all(s==words for s in stacks))
        self.assertEqual(128*32,4096)

    def test_same_bank_early_capture_preserves12edge_output(self):
        q=G.GroupLedger();q.allocate(0,0,16);captured=[];returned=[]
        for e in range(30):
            rr=[record(0,e,lambda e=e:(captured.append((q.tick,e)) or bytes([e])*32))] if e<16 else []
            accepted,out=q.edge(rr,take=[0])
            if e<16:self.assertEqual(accepted,[(0,e)])
            returned.extend((e,r['beat'],r['context']) for r in out)
        self.assertEqual(captured,[(e+1,e) for e in range(16)])
        self.assertEqual([(e,b) for e,b,_ in returned],[(b+13,b) for b in range(16)])
        self.assertEqual([x for _,b,x in returned],[bytes([b])*32 for b in range(16)])

    def test_shared_namespace_atomic_eight_retire_plus_allocation(self):
        q=G.GroupLedger()
        for g in range(8):q.allocate(g,g*16,1)
        accepted,_=q.edge([record(g,0,base=g*16) for g in range(8)])
        self.assertEqual(len(accepted),8)
        for _ in range(12):q.edge()
        _,out=q.edge(take=range(8),allocation=(100,0,1))
        self.assertEqual(len(out),8);self.assertEqual(q.live_tags,1)
        self.assertEqual(set(q.tags),{100});self.assertEqual(q.quarantine,set(range(8)))
        with self.assertRaises(ValueError):q.allocate(0,64,1)

    def test_duplicate_inflight_and_actual_matching_grant_before_reuse(self):
        q=G.GroupLedger();q.allocate(0,0,1);q.edge([record(0,0)])
        with self.assertRaisesRegex(ValueError,'duplicate'):q.edge([record(0,0)])
        with self.assertRaises(ValueError):q.grant(0,0)
        for _ in range(12):q.edge()
        q.edge(take=[0])
        with self.assertRaises(ValueError):q.release(0,True,True)
        q.grant(0,0)
        with self.assertRaises(ValueError):q.release(0,True,False)
        q.release(0,True,True);q.allocate(0,0,1)

    def test_finite_return_RAM_and_group_credits(self):
        q=G.GroupLedger()
        for tag in range(16):q.allocate(tag,0,16)
        self.assertEqual([q.reserved_pc[p] for p in range(4)],[64]*4)
        with self.assertRaisesRegex(ValueError,'16group'):q.allocate(16,0,16)
        for g in range(1,8):
            for i in range(16):q.allocate(g*16+i,g*16,16)
        self.assertEqual(len(q.tags),128)
        self.assertTrue(all(n==64 for n in q.reserved_pc.values()))

    def test_quarantine_retains_group_burst_allocation_credits(self):
        q=G.GroupLedger()
        for tag in range(16):q.allocate(tag,0,1)
        for e in range(30):q.edge([record(e,0)] if e<16 else [],take=[0])
        self.assertEqual(q.quarantine,set(range(16)))
        with self.assertRaisesRegex(ValueError,'16group'):q.allocate(100,0,1)
        q.grant(0,0);q.release(0,True,True);q.allocate(100,0,1)

    def test_output_backpressure_has32_pre_reserved_slots(self):
        q=G.GroupLedger();q.allocate(0,0,16);q.allocate(1,0,16);q.allocate(2,0,1)
        for i in range(32):self.assertEqual(q.edge([record(i//16,i%16)])[0],[(i//16,i%16)])
        for _ in range(20):self.assertEqual(q.edge([record(2,0)])[0],[])
        self.assertEqual(len(q.output[0]),32)
        self.assertEqual(q.edge([record(2,0)],take=[0])[0],[(2,0)])

    def test_missing_actual_context_callback_not_qualified(self):
        q=G.GroupLedger();q.allocate(0,0,1)
        q.edge([record(0,0,lambda:None)])
        with self.assertRaisesRegex(ValueError,'provider'):q.edge()

    def test_actual_PC_and_sector_are_checked_not_repaired(self):
        q=G.GroupLedger();q.allocate(0,0,16)
        for key,value in (('pc',31),('sector',1)):
            bad=record(0,0);bad[key]=value
            with self.assertRaisesRegex(ValueError,'PC/sector'):q.edge([bad])
            self.assertEqual(q.tick,0);self.assertFalse(q.inflight)

    def test_joint_minimum_model_retains_concrete_source_and_slot_deficits(self):
        m=G.build(PARENT);c=m['configuration']
        self.assertEqual((c['bank_groups_per_stack'],c['command_paths_per_stack'],c['global_fill_lanes']),(8,4,6))
        self.assertEqual(c['physical_context_RAM_replication'],0)
        self.assertEqual(c['owner_lookup_output_latency_edges'],12)
        self.assertFalse(c['physical_capture_admitted'])
        self.assertGreater(m['source_gates']['native_PC_read_lower_s'],1/3000)
        self.assertGreater(m['source_gates']['prior12edge_bank_hold_capacity_s'],1/3000)
        self.assertEqual(m['routing']['track_deficit'],5565)
        self.assertGreater(m['routing']['candidate_array_w_um'],26000)
        self.assertFalse(m['slot']['slot_fit']);self.assertIsNone(m['PHY']['actual_sustained_Bps'])
        self.assertIsNone(m['calendar']['adopted_rate'])
        self.assertEqual([r['layer'] for r in m['calendar']['rows']],list(range(36)))
        done=0
        for row in m['calendar']['rows']:
            r=row['optimistic_reservation'];self.assertGreaterEqual(r['compute_begin_ps'],done)
            self.assertEqual(r['window'],row['layer']%2);done=r['compute_end_ps']
            f=row['finite_conditional_reservation']
            self.assertEqual(f['command_count_per_stack'],[32736]*4)
            self.assertEqual(f['owned_data_and_grant_count_per_stack'],[65472]*4)
            self.assertTrue(f['all_reverse_grants_reserved'])
            self.assertGreaterEqual(f['attention_begin_ps'],f['prefix_ready_ps'])

if __name__=='__main__':unittest.main()
