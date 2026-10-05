from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_exceptional as E

class Exceptional(unittest.TestCase):
    def test_source_payload_rounding_and_thresholds(self):
        payloads=[0x7f800001,0x7fc12345,0x7fff7fff,0x7fff8000,0x7fffffff]
        boundaries=[0,0x80000000,1,0x7e7fffff,0x7e800000,0x7e800001,0x7effffff,0x7f000000,0x7f000001,0x7f3fffff,0x7f400000,0x7f400001,0x7f7fffff]
        for special in [0x7f800000,0xff800000]+payloads+[p|0x80000000 for p in payloads]:
            bits=np.resize(np.array(boundaries+[b|0x80000000 for b in boundaries],np.uint32),128)
            bits[::32]=special
            E.witness(bits.view(np.float32))
    def test_executed_versions_and_shuffle_source_lanes(self):
        bits=np.zeros(128,np.uint32);bits[0]=0x7fc12345;bits[32]=0x7f800000
        receipt=E.witness(bits.view(np.float32),'bounded-fixture')
        shuffles=0
        for events in receipt['executed_ordinary_events'].values():
            results={}
            for event in events:
                for operand in event['operand_register_bindings']:
                    self.assertIn(operand['producer_event'],event['dependencies'])
                    self.assertEqual(results[operand['result_id']],(operand['register'],operand['warp'],operand['source_lane']))
                    if event['opcode']=='SHFL':shuffles+=1
                for result in event['result_register_bindings']:
                    self.assertNotIn(result['result_id'],results)
                    results[result['result_id']]=(result['register'],result['warp'],result['lane'])
        self.assertGreater(shuffles,0)
        self.assertFalse(receipt['DUT_RTL_executed'])
    def test_nan_matrix_shape_rejects_generic_sequential_policy(self):
        import deepseek_hbm_complete_index_consumer as C
        raw=np.zeros(128,np.uint32);raw[0]=0x7fc10001;raw[17]=0xffc20002
        with np.errstate(invalid='ignore'):
            q=E.C.V.qdq_fp4_e8m0(raw.view(np.float32))
            v=C.reference_modules();queries=np.tile(q,(32,1));keys=np.ones((2,128),np.float32)
            one=v.dots_q4(queries,keys[:1]);two=v.dots_q4(queries,keys)
        self.assertEqual(int(one[0,0].view(np.uint32)),0x7fc10000)
        self.assertEqual(int(two[0,0].view(np.uint32)),0x7fc20000)
