from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_service_plan as P
class Service(unittest.TestCase):
    def test_source_wire_and_nonalias_lifetimes(self):
        m=P.plan();self.assertIn('IKD1 unchanged',m['wire']);self.assertFalse(m['hardware_admitted'])
        self.assertTrue(m['capacity_fits_64KiB_only'])
        ids={p['id']:p for p in m['lifetimes']}
        self.assertIn('controller_actual_WRACK',ids['payload_WRcommit']['requires'])
        self.assertIn('consumer_done',ids['credit_return_and_reuse']['requires'])
        self.assertFalse(m['packed_key_reuse_model_only']['wholeprogram_all_keys_packed_claim'])
    def test_metadata_needs_independent_expected_context(self):
        def execute(wrong):
            mem={}
            for family,n in [('descriptor',8),('external_lease',16)]:
                for w in range(n):
                    mem[f'{family}{w}']=np.full((1,32),w,np.uint32)
                    mem[f'protected_expected_{family}{w}']=np.full((1,32),w,np.uint32)
            if wrong:mem['descriptor2'][0,1]+=1
            return P.authority_execute(mem,trace=True)
        good=execute(False);bad=execute(True)
        self.assertEqual(good.stores['authority_difference'][0,0],0)
        self.assertNotEqual(bad.stores['authority_difference'][0,0],0)
        self.assertEqual(good.metrics['shared_warp_issues'],49)
    def test_IKD1_epoch64_highhalf_is_compared_not_truncated(self):
        import struct
        for epoch in [1,(1<<32)+1,(1<<63)+3,(1<<64)-1]:
            descriptor=struct.pack('<4sBBHQ',b'IKD1',1,0,68,epoch)+bytes(16)
            words=np.frombuffer(descriptor,dtype='<u4')
            memory={}
            for family,n in [('descriptor',8),('external_lease',16)]:
                for word in range(n):
                    value=int(words[word]) if family=='descriptor' else 0
                    memory[f'{family}{word}']=np.full((1,32),value,np.uint32)
                    memory[f'protected_expected_{family}{word}']=np.full((1,32),value,np.uint32)
            self.assertEqual(P.authority_execute(memory,trace=True).stores['authority_difference'][0,0],0)
            if epoch>>32:
                memory['descriptor3'][0,:2]=0
                self.assertNotEqual(P.authority_execute(memory,trace=True).stores['authority_difference'][0,0],0)
    def test_diverse_fixture_has_distinct_heads_keys_scales_and_weights(self):
        qr,kr,w=P.fixture_inputs('diverse-r2');q,k=P.fixture_decoded(qr,kr)
        self.assertEqual(len({row.tobytes() for row in q}),32)
        self.assertNotEqual(k[0].tobytes(),k[1].tobytes())
        self.assertEqual(len(set(w.tolist())),32)
        self.assertTrue(np.all(np.isfinite(q)) and np.all(np.isfinite(k)))
        e=np.array([P.X.decode(q[:,b*32:(b+1)*32])[1] for b in range(4)])
        self.assertGreater(len(set(e.reshape(-1).tolist())),4)
    def test_diverse_source_bits_reject_swapped_head_address(self):
        qr,kr,w=P.fixture_inputs('diverse-r2');q,k=P.fixture_decoded(qr,kr);model=P.plan()
        runner=P.E.TracedSIMT((1,32),{'input':q[:,0].view(np.uint32)[None,:]},kernel='head_alias_negative').run([P.ins('LOAD','v','input')])
        event=runner.trace[0];base=model['fallback_local2_nonalias_regions']['query']['base']
        event['source_mapped_shared_accesses']=[{'warp':0,'lane':lane,'address':base+4*lane,'bytes':4} for lane in range(32)]
        self.assertEqual(P.validate_mapped_values([runner],model,q,k,w)['verdict'],'PASS')
        wrong=next(head for head in range(1,32) if q.view(np.uint32)[head,0]!=q.view(np.uint32)[0,0])
        event['source_mapped_shared_accesses'][0]['address']=base+4*wrong
        with self.assertRaisesRegex(AssertionError,'mapped LOAD differs'):P.validate_mapped_values([runner],model,q,k,w)
