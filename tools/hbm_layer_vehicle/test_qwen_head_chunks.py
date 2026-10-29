"""Finite HEAD chunks use actual packed-weight compiler and independent full-matrix golden."""
import json,tempfile,unittest
from pathlib import Path
import numpy as np
from hbm_layer_vehicle.qwen_head_chunks import plan,compile_chunks,verify_packed_weights

class HeadChunksTest(unittest.TestCase):
    def test_full_shape_partition_candidates_have_exact_ordered_coverage(self):
        for partitions,executions in ((8,40),(16,48)):
            p=plan(partitions=partitions)
            self.assertEqual(p['serialized_executions'],executions)
            self.assertEqual([r for c in p['chunks'] for r in range(c['global_row_begin'],c['global_row_end'])],list(range(18992)))
            self.assertTrue(all(c['descriptors']<=256 for c in p['chunks']))
            self.assertFalse(p['installable'])
            self.assertTrue(all(c['output']['drain_cycles'] is None for c in p['chunks']))
        with self.assertRaises(ValueError):plan(chunk_rows=513)

    def test_actual_small_capture_chunks_preserve_every_weight_row_and_fp32_output(self):
        from hgi_sim import lib
        # Distinct rows and columns make a row/half permutation visible.
        W=((np.arange(532*512).reshape(532,512)*7+np.arange(532)[:,None]*3)%251-125).astype(np.int8)
        x=((np.arange(512)%17)-8).astype(np.float32)/16
        expected=lib.sm_int8(W,x).astype(np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);kv=root/'kv';kv.mkdir()
            np.savez(kv/'sm_mv.npz',W=W,A=x,O=expected)
            meta=dict(records=[dict(rank=3,L=0,tag='head',arrays={k:dict(key=k) for k in ('W','A','O')})])
            (kv/'sm_mv.json').write_text(json.dumps(meta))
            p=compile_chunks(kv,0,3,root/'out',partitions=4,chunk_rows=80,rows=532,columns=512)
            actual=[]
            for chunk in p['chunks']:
                d=root/'out'/f"chunk{chunk['index']:03d}"
                actual.extend(int(word,16) for word in (d/'expected_fp32.mem').read_text().split())
                self.assertLessEqual(chunk['component']['budget']['descriptors'],256)
                self.assertGreater(chunk['component']['last_ingress_edge'],0)
                self.assertTrue(chunk['component']['weight_order']['bit_exact'])
                self.assertGreater(chunk['component']['compiler_drain_edges'],0)
                self.assertIsNone(chunk['component']['next_chunk_start'])
            self.assertEqual(actual,expected.view(np.uint32).tolist())
            import sm_slice_lower as source
            comp=source.compile_qwen_sm(kv,0,0,rank=3,tags=('head',),partitions=4,row_chunk=(0,80))
            comp['kinds'][0]['recs'][0]['blocks'][0]['lines'][0] ^= 1
            with self.assertRaisesRegex(ValueError,'packed weight order mismatch'):
                verify_packed_weights(comp)
            # Mutate captured weight-row order while retaining independent O: real compiler golden check rejects it.
            np.savez(kv/'sm_mv.npz',W=np.roll(W,1,axis=0),A=x,O=expected)
            with self.assertRaisesRegex(SystemExit,'golden self-test mismatch'):
                compile_chunks(kv,0,3,root/'mut',partitions=4,chunk_rows=80,rows=532,columns=512)

if __name__=='__main__':unittest.main()
