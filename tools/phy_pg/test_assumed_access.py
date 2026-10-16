import copy
import json
from pathlib import Path
import sys
import tempfile
import random
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phy_pg.assumed_access import build
from phy_pg.apply_case import apply,patch_pdn
from phy_pg.verify_geometry import verify,intersect
from phy_pg.hbm_assumed_pg import add_hbm_pg
ROOT=Path(__file__).resolve().parents[2]
SERDES=ROOT/'physical/qwen_missing_phy/tp8_1013/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy.lef'

class AccessTest(unittest.TestCase):
 def test_declared_channels_preserve_all_pins_and_lower_obstructions(self):
  old=SERDES.read_text();new,receipt=build(old)
  self.assertEqual(new.split('  OBS\n')[0].split('\n',1)[1],old.split('  OBS\n')[0])
  self.assertEqual(new.split('  OBS\n')[1].split('    LAYER M5')[0],old.split('  OBS\n')[1].split('    LAYER M5')[0])
  self.assertEqual(receipt['area_delta_um2'],0)
  self.assertEqual(new.count('    LAYER M5 ;'),old.count('    LAYER M5 ;'))
  self.assertEqual(new.count('    RECT '),old.count('    RECT ')+2)
 def test_actual_export_rect_indentation_is_supported(self):
  old=SERDES.read_text().replace('    RECT ','      RECT ')
  new,r=build(old)
  self.assertEqual(r['status'],'ASSUMED_UNQUALIFIED')
  self.assertIn('      RECT 0.400 0 2320.056 1563.570',new)
 def test_actual_upper_pg_profile_is_preserved(self):
  text=SERDES.read_text()
  upper=text.replace('ot_qfd_serdes_112g_x12_phy','ot_qkvd_ucie_x64_phy').replace('LAYER M4 ;','LAYER M7 ;')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'elements.lef').write_text(text+'\n'+upper)
   (p/'die.v').write_text('ot_qfd_serdes_112g_x12_phy serdes();\not_qkvd_ucie_x64_phy upper();\n')
   (p/'pdn.tcl').write_text('define_pdn_grid -macro -instances {^serdes$ ^upper$} -name pg\n')
   record=apply(p)
   self.assertEqual(record['instances'],['serdes'])
   self.assertIn(upper,(p/'elements.lef').read_text())
   self.assertIn('-instances {^upper$}',(p/'pdn.tcl').read_text())
 def test_actual_case_rejects_frozen_odb_and_replaces_grid_ownership(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'elements.lef').write_text(SERDES.read_text())
   (p/'die.v').write_text('module die(); ot_qfd_serdes_112g_x12_phy serdes_host(); endmodule\n')
   (p/'pdn.tcl').write_text('define_pdn_grid -macro -instances {^serdes_host$ ^other$} -name pg\nadd_pdn_connect -grid pg -layers {M7 M8}\n')
   (p/'floorplan.odb').touch()
   with self.assertRaisesRegex(ValueError,'precede any ODB'):apply(p)
   (p/'floorplan.odb').unlink();apply(p)
   self.assertIn('-instances {^other$}',(p/'pdn.tcl').read_text())
   self.assertIn('ot_assumed_phy_pg_grids',(p/'pdn.tcl').read_text())
   self.assertTrue((p/'elements.historical-original.lef.txt').exists())
   with self.assertRaisesRegex(ValueError,'already applied'):apply(p)
 def test_empty_grid_removed(self):
  out=patch_pdn('define_pdn_grid -macro -instances {^phy$} -name pg\nadd_pdn_stripe -grid pg -layer M8\nadd_pdn_connect -grid pg -layers {M7 M8}\n', ['phy'])
  self.assertNotIn('-grid pg',out);self.assertNotIn('define_pdn_grid',out)
 def test_regexp_selector_is_rejected_without_broadening(self):
  line='if {[regexp {^(ot_hbm3e_phy|ot_qfd_serdes_112g_x12_phy)$} $name]} {lappend phy $name}'
  with self.assertRaisesRegex(ValueError,'unsupported PHY selector'):patch_pdn(line,[])
  line='foreach pp {ot_hbm3e_phy* OT_PDN_BBOX_ot_hbm3e_phy* ot_qfd_serdes_112g_x12_phy* OT_PDN_BBOX_ot_qkvd_ucie_x64_phy*} {puts $pp}'
  out=patch_pdn(line,[])
  self.assertIn('foreach pp {ot_hbm3e_phy* OT_PDN_BBOX_ot_hbm3e_phy*}',out)
  self.assertNotIn('^|',out)
 def test_hbm_supply_interface_is_cloned_without_signal_or_obs_edits(self):
  target='MACRO qkd_hbm3e_phy_pc\n  SIZE 833.496 BY 12000.120 ;\n  PIN dfi\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M4 ;\n      RECT 0 1 0.192 1.024 ;\n    END\n  END dfi\n  OBS\n    LAYER M4 ;\n    RECT 0 0 833.496 12000.120 ;\n  END\nEND qkd_hbm3e_phy_pc\n'
  source='MACRO ot_hbm3e_phy\n  SIZE 833.496 BY 12000.120 ;\n'
  for net in ['VDD','VSS']:
   source+='  PIN '+net+'\n    PORT\n      LAYER M4 ;\n      RECT .480 1 833.016 1.288 ;\n    END\n  END '+net+'\n'
  source+='END ot_hbm3e_phy\n'
  out,r=add_hbm_pg(target,source)
  self.assertEqual(r['area_delta_um2'],0);self.assertEqual(r['latency_delta_cycles'],0)
  self.assertEqual(target.split('  OBS')[1],out.split('  OBS')[1])
  self.assertIn(target.split('  OBS')[0],out)
  for net in ['VDD','VSS']:self.assertIn('  PIN '+net+'\n',out)
  self.assertIn('qkd_hbm3e_phy_pc OT_PDN_BBOX_qkd_hbm3e_phy_pc',patch_pdn('foreach pp {ot_hbm3e_phy*} {puts $pp}',[],True))
 def test_actual_generated_compute_and_kv_pdn_snapshots(self):
  source=Path(__file__).with_name('evidence_integration_20261015')
  for case in ['compute','compute_generated','kv']:
   receipt=json.loads((source/(case+'.apply.json')).read_text())
   original=(source/(case+'.original.pdn.tcl')).read_text()
   patched=patch_pdn(original,receipt['instances'],bool(receipt['hbm_pg']))
   self.assertEqual(patched,(source/(case+'.patched.pdn.tcl')).read_text())
   if case=='kv':
    self.assertIn('ot_hbm3e_phy* OT_PDN_BBOX_ot_hbm3e_phy* qkd_hbm3e_phy_pc OT_PDN_BBOX_qkd_hbm3e_phy_pc',patched)
   else:
    self.assertIn('^ucie_kv$',patched)
    self.assertNotIn('^io_serdes$',patched)
 def test_spatial_short_index_matches_all_pairs_including_bucket_edges(self):
  rng=random.Random(1715);shapes=[]
  for k in range(250):
   x=rng.randrange(-100000,150000);y=rng.randrange(-100000,150000)
   shapes.append(['VDD' if k%2 else 'VSS','M4' if k%3 else 'M8',x,y,x+rng.randrange(1,90000),y+rng.randrange(1,90000),'via'])
  expected=sum(a[0]!=b[0] and a[1]==b[1] and intersect(a[2:6],b[2:6]) is not None for k,a in enumerate(shapes) for b in shapes[k+1:])
  self.assertEqual(verify(dict(shapes=shapes,instances=[]))['shorts'],expected)
 def test_m8_signal_spacing_is_checked_beyond_overlap(self):
  data=dict(shapes=[['VDD','M8',0,500,970,600,'wire']],instances=[dict(name='phy',orient='R0',bbox=[0,0,2000,2000],width=2000,height=2000,obs=[],pins=[['clk','SIGNAL','M8',1000,500,1100,600]])])
  r=verify(data);self.assertEqual(r['signal_pin_overlaps'],0);self.assertEqual(r['m8_signal_spacing40_violations'],1)
 def test_auditor_detects_real_short_and_obstruction(self):
  d=dict(shapes=[['VDD','M5',100,100,220,1000,'wire']],instances=[])
  self.assertEqual(verify(d)['status'],'PASS')
  d['shapes'].append(['VSS','M5',150,900,270,2000,'via'])
  self.assertGreater(verify(d)['shorts'],0)
  d['shapes'].pop()
  d['instances']=[dict(name='phy',orient='R0',bbox=[0,0,2000,2000],width=2000,height=2000,pins=[],obs=[['M5',0,0,2000,2000]])]
  self.assertGreater(verify(d)['obstruction_violations'],0)
if __name__=='__main__':unittest.main()
