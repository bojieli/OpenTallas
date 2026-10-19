"""Source packet lifecycle/identity negatives, independent of physical timing proof."""
import copy,gzip,json,unittest
from pathlib import Path
from . import mu_cold_prefix as C
ROOT=Path(__file__).resolve().parents[2]
class ColdPrefix(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  p=ROOT/'results/rtl/mu_qwen_1018/admission'
  cls.m=C.build(json.loads((p/'F16_P2/admission.json').read_text()),json.loads(gzip.decompress((p/'F16_P2/paired_frame.json.gz').read_bytes())),(p/'cold_prefix/source_ovl_release_img.svh').read_text(),token=777,position=5,context_epoch=0x48c,image_epoch=0xbeef,generation=2)
 def test_ordered_prefetch(self):
  self.assertTrue(C.validate(self.m));self.assertEqual(self.m['steady_period'],8053632)
  self.assertEqual(self.m['plan']['provider_core_sample'],self.m['plan']['provider_first_safe_sample'])
  self.assertFalse(self.m['production_bound']);self.assertIsNone(self.m['absolute_startup']['FIRST_OFS'])
 def test_concrete_T_and_E_variants(self):
  self.assertEqual(self.m['T_prefix']['append_base'],46)
  self.assertEqual(self.m['T_prefix']['total_entries'],49)
  self.assertEqual(self.m['init_selector']['T_entry'],47)
  self.assertEqual(self.m['Ecalendar']['total_entries'],8)
  self.assertNotEqual(self.m['Ecalendar']['cold_image'],self.m['Ecalendar']['steady_image'])
 def test_wrong_T_selector(self):
  m=copy.deepcopy(self.m);m['init_selector']['T_entry']+=1
  with self.assertRaisesRegex(C.ContractError,'immutable cold prefix'):C.validate(m)
 def test_wrong_context_image(self):
  m=copy.deepcopy(self.m);m['context']['wire548']=f"{int(m['context']['wire548'],16)^(1<<78):0137x}"
  with self.assertRaisesRegex(C.ContractError,'identity mismatch'):C.validate(m)
 def test_omitted_context(self):
  m=copy.deepcopy(self.m);m['context']['present']=False
  with self.assertRaisesRegex(C.ContractError,'missing/noncanonical'):C.validate(m)
 def test_context_reordered_after_INIT(self):
  m=copy.deepcopy(self.m);m['plan']['context_checked']=m['plan']['INIT_external_pin']+1
  with self.assertRaisesRegex(C.ContractError,'order'):C.validate(m)
 def test_omitted_INIT(self):
  m=copy.deepcopy(self.m);m['init_selector']['enabled']=False
  with self.assertRaisesRegex(C.ContractError,'explicit INIT'):C.validate(m)
 def test_wrong_INIT_range(self):
  m=copy.deepcopy(self.m);m['init_selector']['first']=40
  with self.assertRaisesRegex(C.ContractError,'immutable programme'):C.validate(m)
 def test_reordered_prefetch_after_core(self):
  m=copy.deepcopy(self.m);m['plan']['provider_first_safe_sample']=m['plan']['provider_core_sample']+1
  with self.assertRaisesRegex(C.ContractError,'row not resident'):C.validate(m)
 def test_changed_steady_period(self):
  m=copy.deepcopy(self.m);m['steady_period']+=1
  with self.assertRaisesRegex(C.ContractError,'steady period'):C.validate(m)
if __name__=='__main__':unittest.main()
