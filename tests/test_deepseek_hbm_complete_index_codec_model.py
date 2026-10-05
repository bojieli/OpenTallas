from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_codec_model as M
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_packed_index_provider as P
import deepseek_hbm_complete_memory as Memory

class ModelProvider(unittest.TestCase):
    def test_pitch33_transpose_all_source_words_and_banks(self):
        source=set()
        for row in [0,32]:
            for term in [0,32,64,96]:
                t=M.transpose(row,term)
                for e in t['copy_events']:
                    self.assertEqual(len({a//4%32 for a in e['source_addresses']}),32)
                    self.assertEqual(len({a//4%32 for a in e['scratch_addresses']}),32)
                    source.update(e['source_addresses'])
                for e in t['packer_read_events']:self.assertEqual(len({a//4%32 for a in e['addresses']}),32)
                self.assertIsNone(t['qualified_cycles'])
        self.assertEqual(len(source),8192)
        self.assertEqual(M.END,59264);self.assertLess(M.END,65536)
        query={a for term in [0,32,64,96] for e in M.transpose(0,term,32,'query')['copy_events'] for a in e['source_addresses']}
        self.assertEqual(len(query),4096);self.assertFalse(query&source)
    def test_full_phase_costs_not_zero_or_proxy_clocks(self):
        m=M.build();self.assertEqual(m['full_tile_shared_demand']['combined_bytes'],303616)
        self.assertEqual(m['full_tile_shared_demand']['serialized_warp_shared_issues_candidate'],3178)
        self.assertEqual(m['shared_allocation_bytes'],63488);self.assertLess(m['shared_allocation_bytes'],65536)
        for p in m['profiles'].values():
            self.assertTrue(p['RF32_fit']);self.assertIsNone(p['serial_dependency_cycles_upper_candidate'])
            self.assertTrue(p['unbound_opcode_counts'])
        self.assertIsNone(m['qualified_cycles']);self.assertEqual(m['physical_admission'],'FAIL_CLOSED')
    def test_actual_produced68B_software_publication_and_read(self):
        memory=Memory.PersistentMemory();base=np.zeros((2,128),np.float32)
        state=P.PackedIndexStateArray(base,memory,'ik',0);b=C.ProducerBinding()
        inputs=np.linspace(-3,2,128,dtype=np.float32);row=b.qdq_fp4_e8m0(inputs)
        state[1]=row
        epoch=state.current_generation[1]
        self.assertEqual(memory.values[('KV','ik',0,1,'generation',epoch)][:68],row.wire_payload)
        self.assertEqual(len(row.wire_payload),68)
        self.assertTrue(np.array_equal(state[1].view(np.uint32),row.view(np.uint32)))
        self.assertTrue(np.array_equal(state[[0,1]][1].view(np.uint32),row.view(np.uint32)))
        self.assertGreater(memory.events['software_backing_store_write_commit'],0)
        self.assertFalse(memory.summary()['physical_backend_bound']);memory.fence()
        with self.assertRaises(ValueError):state[1]=np.asarray(row)
        tampered=C.ProducedRow(row,b'\x00'*68)
        with self.assertRaises(ValueError):state[1]=tampered
    def test_partial_tile_transpose_capacity_and_no_invented_read(self):
        t=M.transpose(32,96,33)
        self.assertEqual(len(t['copy_events']),1)
        self.assertTrue(all(len(r['addresses'])==1 for r in t['packer_read_events']))
        self.assertEqual(t['copy_shared_warp_issues'],2)
    def test_actual_compressor_callsite_publishes_same_produced_generation(self):
        from types import FunctionType,SimpleNamespace
        import w19_hbm_tp96_isa as H
        memory=Memory.PersistentMemory();base=np.zeros((2,128),np.float32)
        array=P.PackedIndexStateArray(base,memory,'ik',0);binding=C.ProducerBinding()
        v=SimpleNamespace(**vars(C.V))
        v.qdq_fp4_e8m0=binding.qdq_fp4_e8m0
        # Upstream values are unit-test stimuli. This test qualifies the actual
        # callsite and producer/store connection, not upstream matrix/norm RTL.
        v.rmsnorm_bf16=lambda x,w,eps:x;v.linear_bf16=lambda w,x:x
        v.rope_cs=lambda f,p:None;v.rope_tail=lambda x,cs:x
        inputs=np.linspace(-4,3,128,dtype=np.float32)
        class Rank:
            r=0
            def __init__(self):self.values={'cmp':inputs}
            def get(self,name):return self.values[name]
            def put(self,name,value):self.values[name]=value
        rank=Rank();state=SimpleNamespace(ik={0:array},ckv={0:np.zeros((2,128),np.float32)},n={0:0})
        m=SimpleNamespace(ratio={0:1},lw=lambda l,n:None,eps=np.float32(1e-6),freqs_yarn=None)
        owner=SimpleNamespace(m=m,st=state,pos=0)
        fn=FunctionType(H.Executor.f_compressor.__code__,{**H.Executor.f_compressor.__globals__,'V':v})
        fn(owner,rank,{'layer':0,'group':0})
        self.assertEqual(state.n[0],1)
        epoch=array.current_generation[0]
        self.assertEqual(memory.values[('KV','ik',0,0,'generation',epoch)][:68],binding.last_payload)
        expected=C.V.qdq_fp4_e8m0(inputs)
        self.assertTrue(np.array_equal(rank.values['new_ik'].view(np.uint32),expected.view(np.uint32)))

if __name__=='__main__':unittest.main()
