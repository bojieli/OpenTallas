import unittest
from tools.gpu_sys.canonical_qwen_native_layout import compile_layout

class NativeLayoutTests(unittest.TestCase):
    def test_transpose_nontrivial_order(self):
        p=compile_layout('TRANSPOSE',[[2,3]],{'axes':[1,0]},[3,2])
        self.assertEqual(p['addresses'],[(0,i) for i in (0,3,1,4,2,5)])
    def test_broadcast_scalar_and_row(self):
        self.assertEqual(compile_layout('BROADCAST',[[]],{},[2,2])['addresses'],[(0,0)]*4)
        self.assertEqual(compile_layout('BROADCAST',[[2]],{},[2,2])['addresses'],[(0,0),(0,1)]*2)
    def test_negative_step_slice(self):
        self.assertEqual(compile_layout('SLICE',[[4]],dict(axis=0,start=3,stop=None,step=-1),[4])['addresses'],
                         [(0,3),(0,2),(0,1),(0,0)])
    def test_concat_retained_selection(self):
        p=compile_layout('CONCAT',[[2,1],[2,2]],{'axis':1},[2,3])
        self.assertEqual(p['addresses'],[(0,0),(1,0),(1,1),(0,1),(1,2),(1,3)])
    def test_dynamic_index_never_host_read(self):
        p=compile_layout('TAKE',[[3,4],[2]],{'axis':0},[2,4])
        self.assertEqual(p['addresses'],[]);self.assertEqual(p['dynamic']['index_bound'],3)
        p=compile_layout('SCATTER',[[3,4],[],[4]],{'axis':0},[3,4])
        self.assertTrue(p['dynamic']['range_fault_before_capture'])
    def test_literal_bits_and_iota_are_commands(self):
        p=compile_layout('CONST',[],{'dtype':'F32','bits':0x80000000},[])
        self.assertEqual(p['literal_words'],[0x80000000])
        self.assertEqual(compile_layout('IOTA',[],{},[3])['addresses'],[(0,0),(0,1),(0,2)])
    def test_wrong_extent_or_shape_rejected(self):
        for op,s,a,out in [('RESHAPE',[[129]],{},[129]),('TRANSPOSE',[[2,3]],{'axes':[0,0]},[2,3]),
                           ('BROADCAST',[[2]],{},[3]),('TAKE',[[3],[1]],{'axis':0},[3])]:
            with self.assertRaises(ValueError):compile_layout(op,s,a,out)

if __name__=='__main__':unittest.main()
