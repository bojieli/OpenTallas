"""Pinned source/Liberty and full-target composition tests; no compiler or STA."""
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('context',ROOT/'tools/model_dsrom_return_wake_context.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class ContextTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model=M.model()
 def test_exact_model_reproduction_and_pins(self):
  self.assertEqual(self.model,json.loads((ROOT/'results/rtl/dsrom_return_wake_context_prepare_20261002/model.json').read_text()))
  for path,pin in self.model['source_pins'].items():self.assertEqual(pin['sha256'],M.sha(M.source(pin['commit'],path)))
  for path,pin in self.model['evidence_sha256'].items():self.assertEqual(pin,M.sha((ROOT/path).read_bytes()))
 def test_actual_fullfield_replication_and_no_small_surrogate(self):
  f=self.model['actual_field_return'];self.assertEqual(8192,f['target_geometry']['pair_slots']);self.assertEqual(1024,f['target_geometry']['BF_capable_pair_slots'])
  self.assertEqual((16384,128,7,16256),(f['macro_leaves'],f['roots'],f['region_tree_levels'],f['return_nodes']))
  self.assertEqual(65*(2*16256+128),f['tree_all_links_bits_per_cycle']);self.assertEqual(69*128,f['root_public_bits_per_cycle'])
  field=M.source(M.CONTRACT,'rtl/v41die/ot_v41_field_w17w10.sv').decode();self.assertIn('localparam integer NL = 2 * NP;',field);self.assertIn('localparam integer LS = L - LR;',field)
  self.assertIn('assign busy = |p_busy;',field)
 def test_field_tag_codec_boundaries(self):
  field=M.source(M.CONTRACT,'rtl/v41die/ot_v41_field_w17w10.sv').decode()
  self.assertIn('{ppos[3*m +: 3], prow[16*m +: 16], pseg[5*m +: 5], 3\'d0, pnseg[5*m +: 5]}',field)
  for pos in (0,5):
   for row in (0,65535):
    for lo in (0,31):
     for nseg in (1,31):
      t=(pos<<29)|(row<<13)|(lo<<8)|nseg
      self.assertEqual((pos,row,lo,0,nseg),(t>>29,(t>>13)&65535,(t>>8)&31,(t>>5)&7,t&31))
 def test_selected_ICG_SS_arc_tables_not_FF_qualification(self):
  w=self.model['actual_wake_context'];arcs=w['ICG_SS_ENA_arcs'];self.assertEqual(4,len(arcs))
  setup=[a for a in arcs if a['type']=='setup_rising'];self.assertEqual(2,len(setup))
  self.assertEqual({'!SE',None},{a['when'] for a in setup})
  self.assertEqual(154.748,setup[0]['tables']['rise_constraint']['maximum'])
  for a in arcs:
   for table in a['tables'].values():self.assertEqual((7,7),(len(table['values']),len(table['values'][0])))
  self.assertIsNone(w['ICG_FF_ENA_arcs']);self.assertIsNone(w['root_leaf_insertion_skew']);self.assertIn('fullSEQ_SS',w['ICG_time_unit'])
 def test_ROM_own_corners_and_two_cycle_source_capture(self):
  w=self.model['actual_wake_context'];rom=w['ROM_corner_arcs']
  self.assertEqual('1ps',rom['ss']['time_unit']);self.assertEqual(839.0934,rom['ss']['CLK_to_Q']['cell_rise']['maximum'])
  self.assertEqual(492.2447,rom['ff']['CLK_to_Q']['cell_rise']['minimum']);self.assertEqual(711.852,rom['ss']['min_period'])
  self.assertAlmostEqual(766.9066,w['ROM_worst_table_2cycle_margin_before_endpoint_setup_wire_skew_ps'])
  e=M.source(M.JOIN,'rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv').decode()
  for text in ('i1_v <= issue; i2x_v <= i1_v;','if (i2x_v && !i2x_bk) cap0 <= rd0;','if (i2x_v && i2x_bk) cap1 <= rd1;','pp_last_b == a_ctr[0]'):
   self.assertIn(text,e)
  # Source pipeline contract, before-NBA samples: readN, i1N, i2xN+1, captureN+2.
  i1=i2=0;captures=[]
  for n in range(4):
   if i2:captures.append(n)
   i1,i2=int(n==0),i1
  self.assertEqual([2],captures)
 def test_no_physical_or_fullfield_admission(self):
  self.assertFalse(any(self.model['claims'].values()));self.assertFalse(self.model['execution']['STA_PNR_authorized']);self.assertFalse(self.model['execution']['field_build_authorized'])
  self.assertIn('OPEN',self.model['actual_wake_context']['source_legal_DRAIN'])
  self.assertIn('five-stage',self.model['actual_field_return']['clock_scope'])
 def test_liberty_quote_balance_and_malformed_refusal(self):
  self.assertEqual([('a',' text:"{quoted}"; ')],list(M.groups('cell(a){ text:"{quoted}"; }','cell')))
  with self.assertRaises(ValueError):list(M.groups('cell(a){','cell'))
 def test_sourceplan_pins_and_preserved_manufacturing_refusal(self):
  p=json.loads((ROOT/'results/rtl/dsrom_return_wake_context_prepare_20261002/sourceplan.json').read_text())
  self.assertEqual(M.sha((ROOT/p['model']).read_bytes()),p['model_sha256'])
  self.assertEqual(M.sha((ROOT/p['model_generator']).read_bytes()),p['model_generator_sha256'])
  self.assertEqual(self.model['source_pins'],p['source_pins'])
  area=p['physical_manufacturing_prerequisite']
  self.assertEqual('CAPTURE_PIN_BAND_OVERFLOW_PHYSICAL_HOLD',area['prior_capture_pinband_verdict'])
  prior=area['prior_wake_area_record']
  self.assertAlmostEqual(prior['area_deficit_with_escape_um2']+area['RNE_incremental_stdcell_area_proxy_um2']/prior['requested_placement_density'],area['same_core_50pct_exclusive_escape_deficit_after_RNE_proxy_um2'])
  self.assertGreater(area['same_core_50pct_exclusive_escape_deficit_after_RNE_proxy_um2'],0)
  self.assertIn('ot-pve2 or ot-pve3',p['execution']['host_plan'])
  self.assertFalse(any(p['execution'][k] for k in ('new_launch','PNR','STA','field_build')))
if __name__=='__main__':unittest.main()
