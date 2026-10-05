"""Address maps and source-backed input metadata controls, no math oracle."""
import unittest
from tools.gpu_sys.canonical_qwen_native_banked_join import movement_map,initial_model
from tools.gpu_sys.canonical_qwen_transport import TransportError

class MovementSuccessorTests(unittest.TestCase):
    def request(self,op,shapes,attrs=None):
        return dict(lowered_primitive=op,operands=[dict(shape=s) for s in shapes],attrs=attrs or {})
    def entries(self,map_value,n):return [(map_value>>(10*i))&1023 for i in range(n)]
    def test_copy_actual_MOV_indices_nonzero_valid(self):
        m=movement_map(self.request('COPY',[[4]]),[4])
        self.assertEqual(self.entries(m,4),[512,513,514,515])
        self.assertEqual(m>>40,0)
    def test_transpose_and_slice_are_not_identity_or_zero(self):
        m=movement_map(self.request('TRANSPOSE',[[2,3]],{'axes':[1,0]}),[3,2])
        self.assertEqual(self.entries(m,6),[512+i for i in [0,3,1,4,2,5]])
        m=movement_map(self.request('SLICE',[[4]],dict(axis=0,start=1,stop=4)),[3])
        self.assertEqual(self.entries(m,3),[513,514,515])
    def test_concat_selects_actual_retained_operand(self):
        m=movement_map(self.request('CONCAT',[[1],[2]]),[3])
        self.assertEqual(self.entries(m,3),[512,640,641])
    def test_arithmetic_map_unused_zero_explicit(self):
        self.assertEqual(movement_map(self.request('FADD',[[4],[4]]),[4]),0)
    def test_dynamic_or_unenrolled_literal_refused(self):
        with self.assertRaisesRegex(TransportError,'index generator'):
            movement_map(self.request('TAKE',[[3],[2]],{'axis':0}),[2])
        with self.assertRaisesRegex(TransportError,'literal RF'):
            movement_map(self.request('CONST',[],{'dtype':'F32','bits':0}),[])
    def test_initial_model_literal_allocation_not_ideal_HBM(self):
        m=initial_model()
        self.assertEqual((m['source_banks'],m['source_slots']),([0,32],[32,33]))
        self.assertEqual((m['raw_bits'],m['protected_bits']),(335,432))
        self.assertEqual(m['HBM_initial_fetch_bytes'],0)
        self.assertFalse(m['headline_credit'])

if __name__=='__main__':unittest.main()
