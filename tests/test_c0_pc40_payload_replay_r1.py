"""Directed bit-rule negatives; fixture values are not checkpoint evidence."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_c0_pc40_payload_replay_r1 as P

class BitReplayTests(unittest.TestCase):
    def frames(self):
        gate=[0.,-0.,10.,87.,88.,-100.,100.,-10.]*16
        a=struct.pack('<128f',*gate);bits=struct.unpack('<128I',a)
        negative=struct.pack('<128I',*(b^0x80000000 for b in bits))
        constant=struct.pack('<128I',*((0xc2ae0000,)*128))
        result=struct.pack('<128f',*(max(-v,-87.) for v in gate))
        return dict(gate=a,negative=negative,constant=constant,FMAX=result)
    def test_finite_sign_and_clamp_rules(self):
        self.assertEqual(P.verify_bits(self.frames())['FMAX_bit_mismatches'],0)
    def test_wrong_gate_sign(self):
        x=self.frames();x['negative']=x['gate']
        with self.assertRaisesRegex(ValueError,'negation'):P.verify_bits(x)
    def test_wrong_constant(self):
        x=self.frames();x['constant']=struct.pack('<128f',*([-88.]*128))
        with self.assertRaisesRegex(ValueError,'minus87'):P.verify_bits(x)
    def test_wrong_result(self):
        x=self.frames();x['FMAX']=x['negative']
        with self.assertRaisesRegex(ValueError,'output bits'):P.verify_bits(x)
    def test_nonfinite_rejected_not_silently_maximized(self):
        x=self.frames();x['gate']=struct.pack('<128f',*([float('nan')]*128))
        with self.assertRaisesRegex(ValueError,'finite released gate'):P.verify_bits(x)

if __name__=='__main__':unittest.main()
