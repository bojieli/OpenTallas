import unittest
from types import SimpleNamespace
import kv_die as K

class ActualBitReach(unittest.TestCase):
    def model(self, capture_pitch=10, capture_bits=200, orient='R0'):
        a=K.F.Master('a',10,300,5,'test');a.face('word',200,'E','M4',150,2)
        b=K.F.Master('b',10,300,5,'test');b.face('word',capture_bits,'W','M4',150,capture_pitch)
        insts=[SimpleNamespace(name='a',master='a',x=0,y=0,w=10,h=300,orient='R0'),
               SimpleNamespace(name='b',master='b',x=30,y=0,w=10,h=300,orient=orient)]
        return dict(insts=insts,buses=[('seam','stack_local',200,[('a','word'),('b','word')])]),{'a':a,'b':b}
    def test_unequal_pitch_exposes_hidden_end_bit(self):
        m,masters=self.model()
        self.assertEqual(abs(K.pin_xy(m['insts'][0],masters['a'],'word')[0]-
                             K.pin_xy(m['insts'][1],masters['b'],'word')[0]),20)
        result=K.stack_local_reach(m,masters,reach=50)
        self.assertEqual(result['bits_checked'],200)
        self.assertEqual(result['violations'],1)
        self.assertGreater(result['max_um'],50)
    def test_mirrored_word_bit_order_is_measured(self):
        m,masters=self.model(capture_pitch=2,orient='MX')
        result=K.stack_local_reach(m,masters,reach=30)
        self.assertEqual(result['violations'],1)
        self.assertGreater(result['max_um'],35)
    def test_missing_bits_do_not_count_as_measured(self):
        m,masters=self.model(capture_bits=100)
        result=K.stack_local_reach(m,masters)
        self.assertEqual(result['unmeasured'],1)
        self.assertEqual(result['bits_checked'],0)
    def test_identical_facing_words_pass(self):
        m,masters=self.model(capture_pitch=2)
        result=K.stack_local_reach(m,masters,reach=30)
        self.assertEqual((result['violations'],result['unmeasured']),(0,0))
        self.assertLess(result['max_um'],21)

if __name__=='__main__':unittest.main()
