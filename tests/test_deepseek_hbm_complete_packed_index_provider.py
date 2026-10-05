from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_packed_index_provider as P
import deepseek_hbm_complete_memory as M

class DualFormat(unittest.TestCase):
    def make(self):
        return P.PackedIndexStateArray(np.zeros((6,128),np.float32),M.PersistentMemory(),'ik',0)
    def test_actual_nonfinite_source_bits_payloads_and_format(self):
        values=np.array([0x7fc12345,0xffc76543,0x7f800000,0xff800000,0x80000000,0x3f800000],np.uint32).view(np.float32)
        state=self.make();binding=C.ProducerBinding()
        for i,value in enumerate(values[:4]):
            row=np.zeros(128,np.float32);row[:len(values)]=values;row[0]=value
            produced=binding.qdq_fp4_e8m0(row)
            with np.errstate(invalid='ignore',over='ignore'):expected=C.V.qdq_fp4_e8m0(row)
            self.assertEqual(produced.format_tag,C.DECODED_F32);self.assertEqual(len(produced.wire_payload),512)
            self.assertEqual(produced.wire_payload,expected.astype('<f4').tobytes())
            state[i]=produced
            self.assertTrue(np.array_equal(state[i].view(np.uint32),expected.view(np.uint32)))
            self.assertFalse(binding.receipts[-1]['ordinary_GPU_producer_lowered'])
    def test_publication_waits_actual_payload_commit_and_old_consumers(self):
        state=self.make();binding=C.ProducerBinding()
        first=binding.qdq_fp4_e8m0(np.ones(128,np.float32));state[0]=first
        second=binding.qdq_fp4_e8m0(np.full(128,np.inf,np.float32))
        ticket=state.begin_publish(0,second)
        self.assertTrue(np.array_equal(state[0].view(np.uint32),first.view(np.uint32)))
        with self.assertRaises(ValueError):state.publish_descriptor(ticket)
        state.commit_payload(ticket)
        lease,payload=state.acquire(0)
        with self.assertRaises(M.Backpressure):state.publish_descriptor(ticket)
        self.assertEqual(payload,first.wire_payload);state.release(lease);state.publish_descriptor(ticket)
        self.assertTrue(np.array_equal(state[0].view(np.uint32),second.view(np.uint32)))
        with self.assertRaises(ValueError):state.commit_payload(ticket)
        with self.assertRaises(ValueError):state.release(lease)
        fmt,length,epoch=P.parse_descriptor(state.memory.values[('KV','ik',0,0,'descriptor')])
        self.assertEqual((fmt,length),(C.DECODED_F32,512));self.assertEqual(epoch,ticket.epoch)
        self.assertEqual(len(state.publications)+len(state.leases),0)
    def test_joint_four_buffers_and_no_zero_or_timer_completion(self):
        state=self.make();row=C.ProducerBinding().qdq_fp4_e8m0(np.zeros(128,np.float32))
        tickets=[state.begin_publish(i,row) for i in range(4)]
        with self.assertRaises(M.Backpressure):state.begin_publish(4,row)
        for t in tickets:state.commit_payload(t);state.publish_descriptor(t)
        leases=[state.acquire(i)[0] for i in range(4)]
        with self.assertRaises(M.Backpressure):state.begin_publish(4,row)
        with self.assertRaises(M.Backpressure):state.acquire(0)
        for lease in leases:state.release(lease)
        self.assertTrue(all(e['hardware_cycle'] is None for e in state.row_events))
        self.assertFalse(state.memory.summary()['physical_backend_bound'])
    def test_descriptor_roundtrip_rejects_corruption_and_bit_copy_preserves_snan(self):
        for fmt,length in [(1,68),(2,512)]:self.assertEqual(P.parse_descriptor(P.descriptor(fmt,length,42)),(fmt,length,42))
        with self.assertRaises(ValueError):P.descriptor(1,512,0)
        with self.assertRaises(ValueError):P.descriptor(2,512,2**64)
        raw=P.descriptor(2,512,0);bad=raw[:-1]+b'\x01'
        with self.assertRaises(ValueError):P.parse_descriptor(bad)
        bits=np.resize(np.array([0x7f812345,0xffc76543,0x80000000,0x7f800000],np.uint32),128)
        decoded=C.decode_payload(2,bits.astype('<u4').tobytes())
        self.assertTrue(np.array_equal(decoded.view(np.uint32),bits))

if __name__=='__main__':unittest.main()
