import unittest
from unittest.mock import patch
import numpy as np
from h4_c0_ds_reference_layer_observers import owned_engram_rows,build_reference_model
import hdc_golden_v41 as V
class LayerTests(unittest.TestCase):
    def test_actual_hash_owned_rows_including_repeated_and_wrapped_ids(self):
        ids=np.array([0,96,1,193],dtype='<i8');rows=np.arange(12,dtype='<f4').reshape(4,3)
        np.testing.assert_array_equal(owned_engram_rows(ids,rows,0).reshape(4,3),np.vstack([rows[:2],np.zeros((2,3))]))
        np.testing.assert_array_equal(owned_engram_rows(ids,rows,1).reshape(4,3),np.vstack([np.zeros((2,3)),rows[2:]]))
    def test_original_constructor_tuple_unpacked(self):
        m=V.Model.__new__(V.Model)
        with patch('h4_c0_ds_reference_layer_observers.LC.build_model',return_value=(m,'source')):
            result,pin=build_reference_model(None,None)
        self.assertIs(result,m);self.assertEqual(pin,'source')
if __name__=='__main__':unittest.main()
