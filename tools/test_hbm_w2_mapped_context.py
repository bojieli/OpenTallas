import copy,unittest
import hbm_w2_mapped_context as C
class ContextTests(unittest.TestCase):
 def fixture(self):
  m=C.inputs()['full_controller_model.json']
  return dict(source_sha256=m['source_sha256'],parameters=m['parameters'],corner='SS',stage='synthesis',CW_rows=[dict(index=i,cells=[f'CW{i}_b{j}' for j in range(72)]) for i in range(219)],standard_cell_area_um2=200000,mapped_netlist_sha256='schema-test-only',SS_report_sha256='schema-test-only')
 def test_source_fullsize_deficit_and_neighbors(self):
  r=C.worksheet();self.assertEqual(r['protected_FF_required'],15768);self.assertGreater(r['global_screen']['footprint_mm2_per_128'],r['global_screen']['current_r11_service_bands_mm2']);self.assertTrue(r['global_screen']['neighbor_collisions_if_stretched']);self.assertFalse(r['physical_admitted']);self.assertEqual(r['local_context']['clock_reset_additional_debit_um2'],0)
 def test_schema_binding_is_not_mapping_verification(self):
  r=C.worksheet(self.fixture());self.assertTrue(r['mapped_input_present']);self.assertFalse(r['independent_mapping_verified']);self.assertFalse(r['physical_admitted'])
 def test_pruned_CW_refused(self):
  r=self.fixture();r['CW_rows'][0]['cells'].pop()
  with self.assertRaises(ValueError):C.worksheet(r)
 def test_redistributed_duplicate_cells_refused(self):
  r=self.fixture();r['CW_rows'][1]['cells'][0]=r['CW_rows'][0]['cells'][0]
  with self.assertRaises(ValueError):C.worksheet(r)
 def test_stale_source_refused(self):
  r=self.fixture();r['source_sha256']={}
  with self.assertRaises(ValueError):C.worksheet(r)
 def test_already_CTS_mapping_refused(self):
  r=self.fixture();r['stage']='CTS'
  with self.assertRaises(ValueError):C.worksheet(r)
if __name__=='__main__':unittest.main()
