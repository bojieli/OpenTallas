import tempfile
import unittest
from pathlib import Path
import numpy as np
from h4_c0_ds_whole_reference import ComparisonStore, template_fields

class WholeReferenceTests(unittest.TestCase):
    def spec(self):
        return [dict(PC=21,version='v',rank=r,field='data',shape=[2],dtype='<f4') for r in (0,1)]
    def store(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        return ComparisonStore(Path(self.tmp.name)/'new',self.spec())
    def test_identical_rank_bytes_deduplicated(self):
        s=self.store();p=dict(independent_golden=True)
        for r in (0,1):s.append((21,'v',r,'data'),np.array([1,2],dtype='<f4'),p)
        self.assertEqual(len(list(s.out.glob('*.npy'))),1)
        self.assertEqual(len(s.contract()['expectations']),2)
    def test_signed_zero_not_deduplicated(self):
        s=self.store();p=dict(independent_golden=True)
        s.append((21,'v',0,'data'),np.array([0,1],dtype='<f4'),p)
        s.append((21,'v',1,'data'),np.array([-0.,1],dtype='<f4'),p)
        self.assertEqual(len(list(s.out.glob('*.npy'))),2)
    def test_oracle_provider_provenance_refused(self):
        s=self.store()
        with self.assertRaisesRegex(ValueError,'comparison-only'):
            s.append((21,'v',0,'data'),np.zeros(2,dtype='<f4'),dict(independent_golden=True,runtime_operand_source=True))
    def test_shape_dtype_and_duplicate_refused(self):
        s=self.store();p=dict(independent_golden=True)
        with self.assertRaisesRegex(ValueError,'shape/dtype'):s.append((21,'v',0,'data'),np.zeros(2,dtype='<f8'),p)
        s.append((21,'v',0,'data'),np.zeros(2,dtype='<f4'),p)
        with self.assertRaisesRegex(ValueError,'duplicate'):s.append((21,'v',0,'data'),np.zeros(2,dtype='<f4'),p)
    def test_integer_select_and_float_conversion_widths(self):
        t=dict(code=[dict(dst='a',op='IOTA',shape=[2],src=[]),
          dict(dst='b',op='I2F',shape=[2],src=['a']),
          dict(dst='c',op='FCMP_GT',shape=[2],src=['b','b']),
          dict(dst='d',op='SELECT',shape=[2],src=['c','a','a']),
          dict(dst='e',op='F2I',shape=[2],src=['b'])],outputs=dict(mask='c',ids='d',converted='e',floating='b'))
        f=template_fields(t)
        self.assertEqual({k:v['dtype'] for k,v in f.items()},dict(mask='<u4',ids='<i8',converted='<i8',floating='<f4'))
    def test_unknown_instruction_refused(self):
        with self.assertRaisesRegex(ValueError,'dtype rule'):
            template_fields(dict(code=[dict(dst='v',op='UNKNOWN',shape=[],src=[])],outputs=dict(out='v')))
if __name__=='__main__':unittest.main()
