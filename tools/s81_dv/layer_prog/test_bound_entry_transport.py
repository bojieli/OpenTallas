import unittest
from layer_prog.bound_entry_transport import BufferSinks

class BufferProofTest(unittest.TestCase):
    def meta(self,master='$buf'):
        return {'b':dict(module=master,kind='glue',ports={'A':dict(dir='input',width=2),'Y':dict(dir='output',width=2)})}
    def test_exact_buffer_bit_preserves_upstream_source_and_total_stages(self):
        x=BufferSinks({'t':['pin','b.Y[1]',3,True],'b.A[1]':['pin','XR.sw_v[4]',2,False]},self.meta())
        self.assertEqual(x.get('t'),['pin','XR.sw_v[4]',5,True])
        self.assertEqual(x.proofs['t']['bit'],1)
    def test_logic_is_never_declared_a_wire(self):
        raw={'t':['pin','b.Y[1]',3,True],'b.A[1]':['pin','XR.sw_v[4]',2,False]}
        self.assertEqual(BufferSinks(raw,self.meta('$not')).get('t'),raw['t'])
    def test_source_buffer_cycle_fails(self):
        with self.assertRaisesRegex(ValueError,'cycle'):
            BufferSinks({'t':['pin','b.Y[1]',0,False],'b.A[1]':['pin','b.Y[1]',0,False]},self.meta()).get('t')
    def test_swapped_bit_is_preserved_and_not_aliased(self):
        x=BufferSinks({'t':['pin','b.Y[1]',0,False],'b.A[0]':['pin','XR.sw_v[4]',2,False],'b.A[1]':['pin','XR.sw_v[3]',2,False]},self.meta())
        self.assertEqual(x.get('t')[1],'XR.sw_v[3]')

if __name__=='__main__':unittest.main()
