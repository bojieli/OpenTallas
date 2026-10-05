from pathlib import Path
import sys,unittest
from types import FunctionType,SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_codec as I
import deepseek_hbm_complete_index as X
import w19_hbm_tp96_isa as H

class Codec(unittest.TestCase):
    def test_all_reachable_scales_codes_decode_reference_BF16(self):
        codes=np.tile(np.arange(16,dtype=np.uint8),8)
        payload=np.empty((253,68),np.uint8)
        payload[:,:64]=codes[::2]|(codes[1::2]<<4)
        payload[:,64:]=np.arange(1,254,dtype=np.uint8)[:,None]
        for start in range(0,253,64):
            rows=payload[start:start+64];got,_=I.unpack(rows)
            e=rows[:,64:].astype(np.int32)-127
            q=I.V.E2M1[codes].reshape(4,32)
            with np.errstate(over='ignore',under='ignore'):
                expected=I.G.to_bf16((q[None,:,:]*np.exp2(e[:,:,None])).astype(np.float32)).reshape(-1,128)
            self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)))
        for invalid in [0,254,255]:
            p=payload[:1].copy();p[:,64:]=invalid
            with self.assertRaises(ValueError):I.unpack(p)
    def test_quantizer_source_midpoints_neighbors_all_exponents(self):
        rows=[]
        for e in range(-126,127):
            values=[]
            with np.errstate(over='ignore',under='ignore'):
                for midpoint in np.array(I.MID_BITS,np.uint32).view(np.float32):
                    f=np.float32(float(midpoint)*2.0**e)
                    if np.isfinite(f):
                        values += [np.nextafter(f,np.float32(0)),f,np.nextafter(f,np.float32(np.inf))]
            anchor=np.float32(6*2.0**e) if e<=125 else np.finfo(np.float32).max
            row=np.zeros(128,np.float32)
            row[:len(values)]=values;row[32:32+len(values)]=-np.asarray(values,np.float32)
            row[31]=anchor;row[63]=-anchor;row[95]=anchor;row[127]=-anchor
            row[64:68]=np.array([0.,-0.,np.nextafter(np.float32(0),np.float32(1)),-np.nextafter(np.float32(0),np.float32(1))],np.float32)
            rows.append(row)
        rows=np.array(rows,np.float32)
        for start in range(0,len(rows),64):
            fixture=rows[start:start+64]
            packed,got,_=I.quantize_pack(fixture)
            with np.errstate(over='ignore',under='ignore'):expected=np.stack([I.V.qdq_fp4_e8m0(row) for row in fixture])
            self.assertTrue(np.array_equal(got.view(np.uint32),expected.view(np.uint32)))
            self.assertTrue(np.all((packed[:,64:]>=1)&(packed[:,64:]<=253)))
    def test_binding_existing_source_query_handler_without_mutating_source(self):
        b=I.ProducerBinding();before=I.V.qdq_fp4_e8m0
        # Actual existing f_index_q call site, with synthetic current produced
        # input and coefficient identity fixture, not a checkpoint/reference cut.
        v=SimpleNamespace(**vars(I.V));v.qdq_fp4_e8m0=b.qdq_fp4_e8m0
        v.rope_cs=lambda freqs,pos:(np.ones(32,np.float32),np.zeros(32,np.float32))
        v.rope_tail=lambda a,cs:a
        class Rank:
            def __init__(self):self.values={'iq':np.linspace(-2,3,32*128,dtype=np.float32),'iwr':np.ones(32,np.float32)}
            def get(self,name):return self.values[name]
            def put(self,name,value):self.values[name]=value
        r=Rank();m=SimpleNamespace(ih=32,ihd=128,freqs_yarn=None,index_w_scale=np.float32(1))
        owner=SimpleNamespace(m=m,pos=1048575)
        fn=FunctionType(H.Executor.f_index_q.__code__,{**H.Executor.f_index_q.__globals__,'V':v})
        fn(owner,r,{'layer':0})
        expected=np.stack([before(row) for row in r.values['iq'].reshape(32,128)])
        self.assertTrue(np.array_equal(r.values['iqf'].view(np.uint32),expected.view(np.uint32)))
        self.assertEqual(len(b.receipts),32);self.assertEqual(len(b.last_payload),68)
        self.assertIs(before,I.V.qdq_fp4_e8m0)
    def test_finite_input_overflow_and_negativezero_are_preserved(self):
        row=np.zeros((1,128),np.float32);row[0,0]=np.finfo(np.float32).max;row[0,1]=-1e-10
        p,got,_=I.quantize_pack(row)
        with np.errstate(over='ignore'):expected=I.V.qdq_fp4_e8m0(row[0])
        self.assertEqual(int(p[0,64]),253)
        self.assertTrue(np.array_equal(got[0].view(np.uint32),expected.view(np.uint32)))
        self.assertEqual(int(got[0,1].view(np.uint32)),0x80000000)
        self.assertTrue(np.isinf(got[0,0]))
        row[0,0]=np.inf
        with self.assertRaises(ValueError):I.quantize_pack(row)

if __name__=='__main__':unittest.main()
