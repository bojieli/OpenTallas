import copy
import unittest
from operand_layout import generate, scalar_destination, source_matrices, quantized_block_view, LAYOUT


class ReleasedOperandLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrices=source_matrices()
        cls.plan=generate(cls.matrices)

    def test_all40layers_actual_matrix_fragments_join_consumer_shapes(self):
        self.assertEqual(self.plan['source_matrices'],160)
        self.assertEqual(self.plan['rank_fragments'],640)
        self.assertFalse(self.plan['dispatch_eligible'])
        for join in self.plan['joins']:
            for key in ('destination_first','destination_last'):
                dest=join[key];allocation=LAYOUT[dest['tensor']]
                self.assertGreaterEqual(dest['row'],allocation['base_row'])
                self.assertLess(dest['row'],allocation['base_row']+allocation['nrows'])
                self.assertLess(dest['row'],16384)

    def test_actual_wq_b_second_fragment_continues_same_native_tensor(self):
        matrix=next(m for m in self.matrices if m['layer']==0 and m['alias']=='wq_b.rows4608')
        for rank in range(4):
            first=scalar_destination(matrix,rank,rank*8192+4608)
            last=scalar_destination(matrix,rank,(rank+1)*8192-1)
            self.assertEqual((first['row'],first['word']),(4304+288,0))
            self.assertEqual((last['row'],last['word']),(4815,15))
            self.assertEqual(last['consumer_rank'],rank)

    def test_qn_kv_scalar_identity_survives_rank_boundaries(self):
        for alias,base,width in [('wq_a',4096,320),('wkv',4224,128)]:
            matrix=next(m for m in self.matrices if m['layer']==0 and m['alias']==alias)
            for rank in range(4):
                first=scalar_destination(matrix,rank,rank*width)
                last=scalar_destination(matrix,rank,(rank+1)*width-1)
                self.assertEqual(first['row'],base+rank*width//16)
                self.assertEqual(last['word'],15)
                self.assertEqual(first['consumer_rank'],'all-four-after-real-allgather')

    def test_wrong_rank_and_unsupported_tensor_cannot_rebind(self):
        matrix=next(m for m in self.matrices if m['layer']==0 and m['alias']=='wq_a')
        with self.assertRaisesRegex(ValueError,'rank source slice'):
            scalar_destination(matrix,0,320)
        wrong=copy.deepcopy(matrix);wrong['alias']='unknown-reference-producer'
        with self.assertRaisesRegex(ValueError,'unbound source tensor'):
            scalar_destination(wrong,0,0)

    def test_field_reads_actual_interleaved_qn_code_and_exponent_rows(self):
        views=[quantized_block_view('QN',b) for b in range(40)]
        self.assertEqual(views[7]['code_row'],4179)
        self.assertEqual(views[7]['exponent_row'],4180)
        self.assertEqual(views[8]['code_row'],4181)
        self.assertEqual(views[8]['exponent_row'],4185)
        code_slices={(v['code_row'],v['code_lsb']) for v in views}
        exponent_slices={(v['exponent_row'],v['exponent_lsb']) for v in views}
        self.assertEqual(len(code_slices),40);self.assertEqual(len(exponent_slices),40)
        self.assertEqual({v['scalar_begin'] for v in views},set(range(0,1280,32)))
        self.assertEqual(quantized_block_view('KV',15)['exponent_row'],4264)
        with self.assertRaises(ValueError):
            quantized_block_view('QN',40)

    def test_missing_actual_fragment_rejected(self):
        with self.assertRaisesRegex(ValueError,'incomplete actual consumer|producer scope|gapped'):
            generate(self.matrices[:-1])


if __name__=='__main__':
    unittest.main()
