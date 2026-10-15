import unittest
from sfu_vector_calendar import compile_vector
from sfu_control_image import encode, unpack

class LoweringTest(unittest.TestCase):
    def test_production_shapes_and_tail(self):
        for size in (4096,7168,28672,7171):
            for sfu in (0,1,4,5):
                program=compile_vector(words=size,bases=(0,65536,131072,196608,262144),sfu=sfu)
                rows=[unpack(w) for w in encode(program)]
                self.assertEqual(sum(row['ld'] for row in rows),1)
                emitted=[row for row in rows if row['emit']]
                self.assertEqual([row['i_v'] for row in emitted],list(range(0,size,16)))
                self.assertEqual(sum(min(16,size-row['i_v']) for row in emitted),size)
                for row in emitted:
                    self.assertEqual([row['vb']>>(24*i)&0xffffff for i in range(5)],
                                     [base+row['i_v'] for base in (0,65536,131072,196608,262144)])
                self.assertFalse(any(row['emit'] for row in rows[-program['drain_horizon']:]))
                for row in rows:self.assertEqual(row['cs_sfu'],sfu)

    def test_actual_scalar_operand_address_and_offsets(self):
        rows=encode(compile_vector(words=3072,bases=(0,12672,0,0,0),strides=(1,0,1,1,1),sfu=5,e1=1,e2=1,rnd=1))
        for word in rows:
            row=unpack(word)
            if row['emit']:
                self.assertEqual(row['vb']>>24&0xffffff,12672)
                self.assertEqual(row['ld_c']>>(24*10)&((1<<(24*10))-1),0)

    def test_refuse_missing_side_hardware_or_address_overflow(self):
        for sfu in (2,3,6,7):
            with self.assertRaises(ValueError): compile_vector(words=7168,bases=(0,)*5,sfu=sfu)
        with self.assertRaises(ValueError): compile_vector(words=7168,bases=(0,0,0,0,0xffff00))
        for bad in (-1,1<<32):
            with self.assertRaises(ValueError): compile_vector(words=7168,bases=(0,)*5,imm3=bad)

if __name__=='__main__':unittest.main()
