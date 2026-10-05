import unittest
import numpy as np
from h4_c0_ds_reference_state import MappedRows
class StateTests(unittest.TestCase):
    def test_ordered_prefix_append_and_negative_slices(self):
        base=np.arange(12,dtype='<f4').reshape(3,4);r=MappedRows(base)
        r.append(np.array([12,13,14,15],dtype='<f4'))
        self.assertEqual(len(r),4);np.testing.assert_array_equal(r[-1],[12,13,14,15])
        np.testing.assert_array_equal(np.stack(r[-2:]),np.arange(8,16,dtype='<f4').reshape(2,4))
        np.testing.assert_array_equal(r[:3],base)
        with self.assertRaises(IndexError):_=r[4]
if __name__=='__main__':unittest.main()
