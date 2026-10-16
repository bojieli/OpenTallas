import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phy_pg.assumed_access import build
from phy_pg.apply_case import apply,patch_pdn
from phy_pg.verify_geometry import verify
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
 def test_auditor_detects_real_short_and_obstruction(self):
  d=dict(shapes=[['VDD','M5',100,100,220,1000,'wire']],instances=[])
  self.assertEqual(verify(d)['status'],'PASS')
  d['shapes'].append(['VSS','M5',150,900,270,2000,'via'])
  self.assertGreater(verify(d)['shorts'],0)
  d['shapes'].pop()
  d['instances']=[dict(name='phy',orient='R0',bbox=[0,0,2000,2000],width=2000,height=2000,pins=[],obs=[['M5',0,0,2000,2000]])]
  self.assertGreater(verify(d)['obstruction_violations'],0)
if __name__=='__main__':unittest.main()
