import importlib.util, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("census",Path(__file__).parents[1]/"tools/dsrom_nonexpert_header_census.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CensusTests(unittest.TestCase):
 def test_mtp_not_main_expert(self):
  self.assertEqual(m.family("mtp.0.ffn.experts.7.w1.weight"),("MTP","auxiliary_MTP"))
 def test_scale_not_hc_scale(self):
  self.assertEqual(m.family("layers.2.hc_attn_scale"),("HC","main_text"))
 def test_unknown_fails_closed(self):
  with self.assertRaises(ValueError):m.family("future.unbound.weight")
 def test_partial_slice_not_qualified(self):
  self.assertEqual(m.coverage([1024,512],[dict(rows=[r*128,(r+1)*128],columns=None) for r in range(4)]),"incomplete_or_overlapping")
 def test_overlap_rejected(self):
  self.assertEqual(m.coverage([512,512],[dict(rows=[0,512],columns=[0,256]),dict(rows=[0,512],columns=[0,256])]),"incomplete_or_overlapping")
 def test_column_partition(self):
  self.assertEqual(m.coverage([512,512],[dict(rows=None,columns=[r*128,(r+1)*128]) for r in range(4)]),"exact_reference_partition")
 def test_reference_copies_distinct(self):
  self.assertEqual(m.coverage([512,512],[dict(rows=None,columns=None)]*4),"full_reference_copies")
if __name__=="__main__":unittest.main()
