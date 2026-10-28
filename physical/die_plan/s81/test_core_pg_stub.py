import unittest
from core_pg_stub import port_lines,rectangles,refresh

class CorePGTest(unittest.TestCase):
 def test_native_pair_phase_and_extent(self):
  p=rectangles(172.8,345.6)
  self.assertEqual(p['VSS'][0],[6.324,4.32,6.444,341.28])
  self.assertEqual(p['VDD'][0],[6.516,4.32,6.636,341.28])
  self.assertAlmostEqual(p['VSS'][1][0]-p['VSS'][0][0],4.32)
  self.assertEqual(len(p['VSS'])+len(p['VDD']),76)
 def test_refresh_preserves_all_functional_geometry(self):
  base='MACRO X\n  SIZE 172.8 BY 345.6 ;\n  PIN d[0]\n    PORT\n      LAYER M4 ;\n      RECT 0 1 0.084 1.024 ;\n    END\n  END d[0]\n  OBS\n    LAYER M7 ;\n    RECT 1 1 171 344 ;\n  END\nEND X\n'
  result=refresh(base)
  pg='\n'.join(port_lines(172.8,345.6))+'\n'
  self.assertEqual(result.replace(pg,''),base)
 def test_existing_pg_and_m7_views_are_not_rewritten(self):
  for layer in ['M5','M7']:
   base=f'MACRO X\n  SIZE 100 BY 100 ;\n  PIN VDD\n    PORT\n      LAYER {layer} ;\n      RECT 1 1 2 2 ;\n    END\n  END VDD\n  OBS\nEND X\n'
   with self.assertRaisesRegex(ValueError,'preserve existing'):refresh(base)
 def test_too_small_for_native_recipe_is_rejected(self):
  with self.assertRaises(ValueError):rectangles(8,100)

if __name__=='__main__':unittest.main()
