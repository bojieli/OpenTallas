"""Safety tests for the optional PDN-only conservative obstruction transform."""
import unittest
from pdn_bbox_obs import aliases, compact_obs


class BboxTests(unittest.TestCase):
    def test_actual_pins_and_master_attributes_are_unchanged(self):
        before = '''  CLASS BLOCK ;
  FOREIGN leaf 0 0 ;
  SIZE 20 BY 30 ;
  PIN VDD
    USE POWER ;
    PORT
      LAYER M7 ;
        RECT 1 1 2 29 ;
    END
  END VDD
'''
        text = 'MACRO leaf\n' + before + '''  OBS
    LAYER M1 ;
      RECT 0 0 4 4 ;
      RECT 8 9 20 30 ;
  END
END leaf
'''
        result = aliases(text, {'leaf'})
        self.assertIn(before, result)
        self.assertIn('RECT 0 0 20 30 ;', result)
        self.assertIn('MACRO OT_PDN_BBOX_leaf', result)
        self.assertIn('END OT_PDN_BBOX_leaf', result)

    def test_repeated_layers_merge_conservatively(self):
        body = '  OBS\nLAYER M2 ; RECT 1 2 3 4 ; LAYER M1 ; RECT -2 -1 2 9 ; LAYER M2 ; RECT -1 1 2 8 ;\n  END\n'
        result = compact_obs(body)
        self.assertEqual(result.count('LAYER M2'), 1)
        self.assertIn('RECT -1 1 3 8 ;', result)
        self.assertIn('RECT -2 -1 2 9 ;', result)

    def test_unsupported_geometry_fails_closed(self):
        for statement in ['POLYGON 0 0 1 0 1 1', 'RECT MASK 2 0 0 1 1',
                          'LAYER M1 EXCEPTPGNET', 'SPACING 0.4', 'RECT 2 0 1 1']:
            with self.subTest(statement=statement), self.assertRaises(ValueError):
                compact_obs('  OBS\nLAYER M1 ; ' + statement + ' ;\n  END\n')

    def test_missing_or_duplicate_master_refused(self):
        text = 'MACRO leaf\n SIZE 1 BY 1 ;\nEND leaf\n'
        with self.assertRaises(ValueError):
            aliases(text, {'missing'})
        with self.assertRaises(ValueError):
            aliases(text + text, {'leaf'})

    def test_nonselected_cells_not_emitted(self):
        text = 'MACRO leaf\n SIZE 1 BY 1 ;\nEND leaf\nMACRO other\n SIZE 2 BY 2 ;\nEND other\n'
        result = aliases(text, {'leaf'})
        self.assertNotIn('other', result)


if __name__ == '__main__':
    unittest.main()
