"""Admission regressions: pin identities, tracks and clocks cannot be masked."""
import copy
import unittest
from control_geometry import validate_fresh_seq

class PinAdmission(unittest.TestCase):
    def setUp(self):
        self.before=dict(w=10.,h=10.,pins=[dict(name='d[0]',layer='M4',rect=[0.,1.008,.192,1.032]),dict(name='ck[0]',layer='M5',rect=[1.008,9.808,1.032,10.])])
        self.after=copy.deepcopy(self.before)
        self.after['pins'][0]['rect']=[9.808,2.016,10.,2.04]
    def test_valid_source_identity_repin(self):
        self.assertEqual(validate_fresh_seq(self.before,self.after)['changed'],1)
    def test_missing_source_bit_refused(self):
        self.after['pins'].pop(0)
        with self.assertRaisesRegex(ValueError,'identities'):validate_fresh_seq(self.before,self.after)
    def test_silent_clock_repin_refused(self):
        self.after['pins'][1]['rect']=[1.056,9.808,1.08,10.]
        with self.assertRaisesRegex(ValueError,'clock/reset'):validate_fresh_seq(self.before,self.after)
    def test_escaped_pin_refused(self):
        self.after['pins'][0]['rect'][2]=10.01
        with self.assertRaisesRegex(ValueError,'outside'):validate_fresh_seq(self.before,self.after)
    def test_off_track_refused(self):
        self.after['pins'][0]['rect'][1]+=.001
        self.after['pins'][0]['rect'][3]+=.001
        with self.assertRaisesRegex(ValueError,'off track'):validate_fresh_seq(self.before,self.after)
if __name__=='__main__':unittest.main()
