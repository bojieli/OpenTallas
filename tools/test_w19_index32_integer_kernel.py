import unittest
import numpy as np
import w19_index32_integer_kernel as K

class Index32(unittest.TestCase):
    def check(self,q,k,eq,ek):
        got,trace=K.execute(q,k,eq,ek)
        a=np.asarray(q,np.float64)*np.exp2(eq-1);b=np.asarray(k,np.float64)*np.exp2(ek-1)
        with np.errstate(over='ignore',under='ignore'):
            expected=np.asarray(np.float32(a@b)+np.float32(0),np.float32).view(np.uint32).item()
        self.assertEqual(got,expected)
        self.assertLessEqual(len(trace),K.worst(K.program()))
        return got
    def test_random_admissible_block_rounding(self):
        r=np.random.default_rng(1932)
        for _ in range(2000):
            self.check(r.choice(K.UNITS,32).tolist(),r.choice(K.UNITS,32).tolist(),int(r.integers(-126,125)),int(r.integers(-126,125)))
    def test_subnormal_ties_zero_overflow(self):
        for n in [0,1,2,3,5,7,12]:
            for e in [-126,-100,-75,-74,-73,0,124]:
                q=[1]*n+[0]*(32-n);k=[1]*32
                self.check(q,k,e,e);self.check([-x for x in q],k,e,e)
        self.assertEqual(self.check([1,-1]+[0]*30,[1]*32,-126,127),0)
        self.assertEqual(self.check([12]*32,[12]*32,124,124),0x7f800000)
    def test_contract_rejects_invalid_inputs_and_no_admission(self):
        for args in [([2]*31,[2]*32,0,0),([5]*32,[2]*32,0,0),([12]*32,[2]*32,127,0),([2]*32,[2]*32,-127,0)]:
            with self.assertRaises(ValueError):K.execute(*args)
        b=K.build();self.assertIsNone(b['INT_area_mm2']);self.assertFalse(b['adopted'])
        def visit(p):
            for i in p:
                self.assertLessEqual(len(i['src']),2)
                if i['op'].startswith('B'):visit(i['yes']);visit(i['no'])
        visit(b['program'])

if __name__=='__main__':unittest.main()
