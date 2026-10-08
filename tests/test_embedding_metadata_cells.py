import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('metadata', Path(__file__).parents[1] / 'tools/check_embedding_metadata_cells.py')
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)


def ff(bit):
    return {'type': 'DFFHQNx1_ASAP7_75t_R', 'connections': {'Q': [bit], 'D': [99]}}


def inv(source, target, kind='INVx1_ASAP7_75t_R'):
    return {'type': kind, 'connections': {'A': [source], 'Y': [target]}}


def module(primary=1, shadow=2):
    return {'netnames': {'primary': {'bits': [primary]}, 'shadow': {'bits': [shadow]}},
            'cells': {'a': ff(1), 'b': ff(2)}}


class MetadataStorageTests(unittest.TestCase):
    def assert_separate(self, m):
        left = metadata.storage(m, 'primary')
        right = metadata.storage(m, 'shadow')
        self.assertFalse(left & right)

    def test_direct(self):
        self.assert_separate(module())

    def test_independent_inverted_and_buffered(self):
        m = module(3, 5)
        m['cells'].update({'i': inv(1, 3), 'j': inv(2, 4), 'k': inv(4, 5, 'BUFx2_ASAP7_75t_R')})
        self.assert_separate(m)

    def test_fractional_drive_inverter(self):
        m = module(3)
        m['cells']['i'] = inv(1, 3, 'INVxp33_ASAP7_75t_R')
        self.assert_separate(m)

    def test_split_vector(self):
        m=module()
        del m['netnames']['primary']
        m['netnames']['primary[0]']={'bits':[1]}
        self.assertEqual(metadata.storage(m,'primary'),{'a'})

    def test_missing_split_bit_rejected(self):
        m=module()
        del m['netnames']['primary']
        m['netnames']['primary[1]']={'bits':[1]}
        with self.assertRaises(AssertionError):
            metadata.storage(m,'primary')

    def test_actual_fractional_buffer(self):
        m=module(3)
        m['cells']['i']=inv(1,3,'BUFx4f_ASAP7_75t_R')
        self.assert_separate(m)

    def test_shadow_just_inverted_primary_rejected(self):
        m = module(1, 3)
        m['cells']['i'] = inv(1, 3)
        with self.assertRaises(AssertionError):
            self.assert_separate(m)

    def test_no_storage_rejected(self):
        m = module(3)
        m['cells']['i'] = inv(90, 3)
        with self.assertRaises(AssertionError):
            metadata.storage(m, 'primary')

    def test_arbitrary_combinational_gate_rejected(self):
        m = module(3)
        m['cells']['i'] = inv(1, 3, 'AND2x2_ASAP7_75t_R')
        with self.assertRaises(AssertionError):
            metadata.storage(m, 'primary')

    def test_cyclic_cone_rejected(self):
        m = module(3)
        m['cells'].update({'i': inv(4, 3), 'j': inv(3, 4)})
        with self.assertRaises(AssertionError):
            metadata.storage(m, 'primary')

    def test_aliased_bits_rejected(self):
        m = module()
        m['netnames']['primary']['bits'] = [1, 3]
        m['cells']['i'] = inv(1, 3)
        with self.assertRaises(AssertionError):
            metadata.storage(m, 'primary')

    def test_dual_output_single_ff_is_not_independent(self):
        m = module()
        del m['cells']['b']
        m['cells']['a']['connections']['QN'] = [2]
        with self.assertRaises(AssertionError):
            self.assert_separate(m)

    def test_multiple_drivers_rejected(self):
        m = module()
        m['cells']['i'] = inv(2, 1)
        with self.assertRaises(AssertionError):
            metadata.storage(m, 'primary')


if __name__ == '__main__':
    unittest.main()
