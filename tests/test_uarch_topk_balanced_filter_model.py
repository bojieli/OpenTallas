import json
from pathlib import Path
import random
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import uarch_topk_balanced_filter_model as M

class BalancedFilter(unittest.TestCase):
    def test_exact_model_replay(self):
        self.assertEqual(M.build(),json.loads((M.BASE/'model.json').read_text()))
    def test_exhaustive_16lane_prefix_and_compaction(self):
        ids=[0xffffffff-i*17 for i in range(16)]
        for mask in range(65536):
            bits=[(mask>>i)&1 for i in range(16)]
            prefixes,total=M.exclusive_binary_prefix(bits)
            self.assertEqual(prefixes,[sum(bits[:i]) for i in range(16)])
            self.assertEqual(total,sum(bits))
            out,n=M.stable_compact(bits,ids)
            want=[id for b,id in zip(bits,ids) if b]
            self.assertEqual(n,len(want));self.assertEqual(out,want+[0]*(16-len(want)))
    def test_exact_source_quota_small_exhaustive(self):
        ids=[0,0x80000000,3,0xffffffff]
        for g in range(16):
            for e in range(16):
                gt=[(g>>i)&1 for i in range(4)];eq=[(e>>i)&1 for i in range(4)]
                for quota in range(8):
                    self.assertEqual(M.balanced_row(gt,eq,ids,quota,4),M.serial_row(gt,eq,ids,quota,4))
    def test_actual64_256lanes_and_quota_boundaries(self):
        rng=random.Random(20261002)
        for p,cb in [(64,14),(256,18)]:
            patterns=[[0]*p,[1]*p,[i&1 for i in range(p)]]+[[rng.randrange(2) for _ in range(p)] for _ in range(32)]
            for eq in patterns:
                gt=[rng.randrange(2) and not e for e in eq];ids=[rng.getrandbits(32) for _ in range(p)]
                for q in [0,1,p-1,p,p+1,(1<<cb)-1]:
                    self.assertEqual(M.balanced_row(gt,eq,ids,q,cb),M.serial_row(gt,eq,ids,q,cb))
    def test_continuous_rows_and_bubbles_use_consumer_quota(self):
        for p,cb in [(64,14),(256,18)]:
            rows=[([0]*p,[1]*p,list(range(i*p,(i+1)*p))) if i%3!=1 else None for i in range(20)]
            quota=p+3;want=[];q=quota
            for i,row in enumerate(rows):
                if row is not None:
                    out,q=M.serial_row(*row,q,cb);want.append((i,out))
            out,left,trace=M.row_pipeline(rows,quota,cb)
            self.assertEqual(out,want);self.assertEqual(left,q)
            self.assertEqual([x['quota_before'] for x in trace[:3]],[quota,3,0])
            h=M.T.clog2(p);sort_depth=len(M.bitonic_stages(p))
            self.assertTrue(all(x['quota_cycle']-x['input_ordinal']==h for x in trace))
            self.assertTrue(all(x['output_cycle']-x['quota_cycle']==sort_depth+1 for x in trace))
            # Baseline consumes quota at row edge and compacts two edges later.
            self.assertEqual(h+sort_depth+1-2,h+sort_depth-1)
            # Speculative upstream snapshot of quota would incorrectly reuse it.
            stale=[M.balanced_row(*r,quota,cb)[0] for r in rows if r is not None]
            self.assertNotEqual(stale,[v for _,v in want])
    def test_full_ROM512_2048_public_stable_ties(self):
        words0=[0x80000000,0,0x3f800000,0xbf800000,0x7f800000,0xff800000,1,0x80000001]
        def key(x):
            c=0 if x==0x80000000 else x
            return (~c)&0xffffffff if c>>31 else c|0x80000000
        for n in [512,2048]:
            words=[words0[i%len(words0)] for i in range(4*n)]
            floats=[struct.unpack('!f',struct.pack('!I',w))[0] for w in words]
            ids=[(i//n)*(2*n)+i%n for i in range(4*n)]
            for k in [1,n,4*n]:
                ranked=sorted(range(4*n),key=lambda i:(-floats[i],ids[i]))
                expected=sorted(ids[i] for i in ranked[:k]);th=key(words[ranked[k-1]])
                rr=k-sum(key(w)>th for w in words);rows=[]
                for start in range(0,4*n,64):
                    row=words[start:start+64]
                    rows.append(([int(key(w)>th) for w in row],[int(key(w)==th) for w in row],ids[start:start+64]))
                outputs,left,_=M.row_pipeline(rows,rr,14)
                self.assertEqual([id for _,out in outputs for id in out],expected)
                self.assertEqual(left,0)
                emitted_words=M.public_words(outputs,64)
                self.assertEqual([id for w in emitted_words for id in w],expected+[0]*((-k)%16))
                self.assertEqual(len(emitted_words),(k+15)//16)
    def test_network_stages_disjoint_all_lanes(self):
        for p,count in [(64,21),(256,36)]:
            stages=M.bitonic_stages(p);self.assertEqual(len(stages),count)
            for stage in stages:
                self.assertEqual(sorted(i for a,b,_ in stage for i in [a,b]),list(range(p)))
    def test_mutants_lane_reverse_and_count_truncation_detected(self):
        take=[1]*64;ids=list(range(64))
        good,_=M.stable_compact(take,ids);wrong,_=M.stable_compact(take,ids,mutant='reverse_lane')
        self.assertNotEqual(good,wrong)
        _,total=M.exclusive_binary_prefix(take)
        self.assertEqual(total,64);self.assertNotEqual(total,total&63)
    def test_state_cycles_and_slot_replacement_ledger(self):
        r=M.build()
        self.assertEqual([s['filter']['additional_bits']['total'] for s in r['shapes']],[65011,65011,449299,449299])
        self.assertEqual([s['extra_cycles_vs_original_DIG8'] for s in r['shapes']],[142,142,175,175])
        for s in r['shapes']:
            p=s['compiled'];self.assertEqual(p['NMAX'],2048)
            self.assertEqual(s['filter']['old_retained_state_credit'],0)
            self.assertEqual(s['filter']['initiation_interval_rows'],1)
            self.assertFalse(s['clock']['SS_FF_closed'])
        self.assertEqual(r['composition']['ROM']['added_cycles_per_position'],1278)
        self.assertEqual(r['composition']['HBM_conditional_same_provider']['added_cycles_per_position'],1575)
        self.assertGreater(r['slot_proposal']['additional_proxy_area_mm2'],0)
        self.assertFalse(r['slot_proposal']['owner_accepted'])
        overlay=r['slot_proposal']['known_service_overlay']
        self.assertTrue(overlay['known_service_only_no_overlap'])
        self.assertEqual(len(overlay['revised_rectangles']),2)
        self.assertEqual(overlay['revised_rectangles'][0]['bbox_DBU'][3],overlay['revised_rectangles'][1]['bbox_DBU'][1])
        self.assertIsNone(overlay['whole_system_area_delta_mm2'])
        self.assertFalse(r['G0']['engine_RTL_admitted']);self.assertFalse(r['G0']['PR_admitted'])
    def test_no_ECC_and_acceptance_scope_preserved(self):
        r=M.build();h=r['no_ROM_ECC_source_calendar']
        self.assertFalse(h['policy']['ROM_ECC_required'])
        self.assertFalse(h['policy']['parity_sidecar_gather_required'])
        self.assertFalse(h['policy']['ECC_checker_wait_required'])
        self.assertFalse(h['policy']['offered_profile_grants_acceptance_or_timing_credit'])
        self.assertEqual(h['actual_LAT8_evidence']['observed_root_return_events'],0)
        self.assertFalse(r['RTL_or_PR_launched'])

if __name__=='__main__':unittest.main()
