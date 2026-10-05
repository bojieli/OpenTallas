import unittest
from h4_c0_ds_fullgraph_inventory import route,opcode_set

class InventoryTests(unittest.TestCase):
    def test_missing_provider_is_not_classified_as_implemented(self):
        self.assertEqual(route(dict(family='new'), 'x',dict(kind='not_a_provider')), 'UNSUPPORTED_PROVIDER_KIND')
    def test_specialist_paths_do_not_get_ordinary_view_credit(self):
        b=dict(kind='versioned_operand',native_address_view='full source value reshaped to declared LOAD shape')
        self.assertEqual(route(dict(family='index_scores'),'key_exp',b),'paired_accepted_history_rows')
        self.assertEqual(route(dict(family='index_scores'),'query_exp',b),'addressed_query_compound_fields')
        self.assertEqual(route(dict(family='all_reduce'),'parts',b),'source_group_tiled_continuation')
    def test_immutable_auxiliary_stays_required(self):
        self.assertEqual(route(dict(family='compressor'),'open_group',dict(kind='explicit_auxiliary_provider')),'immutable_auxiliary_image_required')
    def test_actual_native_set_contains_integer_abi(self):
        from pathlib import Path
        ops=opcode_set(Path(__file__).with_name('h3_deepseek_complete_native.py'))
        self.assertTrue({'IMUL','IADD','SHR','F2I','I2F','BITCAST_U','PACKET_COMMIT'}<=ops)

if __name__=='__main__':unittest.main()
