import json
from pathlib import Path
import tempfile
import unittest
from kvsys_classify import main, pin_world, placed_def


class ClassificationGeometry(unittest.TestCase):
    def test_named_launch_pin_cannot_be_replaced_by_nearer_other_pin(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            c = p/'case_kv'
            c.mkdir()
            (p/'libs').mkdir()
            (p/'libs/views.json').write_text(json.dumps({'views': {'leaf': {'bound': True}}}))
            (c/'die.v').write_text('  leaf a (.x(n));\n  leaf b (.x(n));\n')
            (c/'place.tcl').write_text('[findInst a] 0 0 R0\n[findInst b] 100 0 MY\n')
            (c/'elements.lef').write_text('''MACRO leaf
SIZE 100 BY 20 ;
PIN x
RECT 0 0 0 0 ;
END x
PIN unrelated
RECT 100 0 100 0 ;
END unrelated
END leaf
''')
            (p/'sta_kv_tt').mkdir()
            (p/'sta_kv_tt/grt_tt_summary.rpt').write_text('a/x (leaf) b/x (leaf) -10\n')
            out = p/'report.json'
            main(['--run', str(p), '--out', str(out)])
            row = json.loads(out.read_text())['corners']['tt']['rows'][0]
            self.assertEqual(row['named_pin_manhattan_um'], 200)
            self.assertEqual(row['nearest_pin_um'], 100)
            (c/'floorplan_placed.def').write_text('''VERSION 5.8 ;
UNITS DISTANCE MICRONS 1000 ;
COMPONENTS 2 ;
- a leaf + FIXED ( 0 0 ) N ;
- b leaf + FIXED ( 200000 0 ) FN ;
END COMPONENTS
END DESIGN
''')
            self.assertEqual(placed_def(c/'floorplan_placed.def')['b'], (200, 0, 'FN'))
            main(['--run', str(p), '--out', str(out)])
            actual = json.loads(out.read_text())
            self.assertEqual(actual['placement']['scope'], 'REALIZED_DEF_ORIGINS')
            self.assertEqual(actual['corners']['tt']['rows'][0]['named_pin_manhattan_um'], 300)

    def test_mirrors_and_unrecognized_orientation(self):
        self.assertEqual(pin_world((2, 3), (100, 200), (10, 20), 'MX'), (102, 217))
        self.assertEqual(pin_world((2, 3), (100, 200), (10, 20), 'MY'), (108, 203))
        self.assertEqual(pin_world((2, 3), (100, 200), (10, 20), 'R180'), (108, 217))
        with self.assertRaises(ValueError):
            pin_world((2, 3), (0, 0), (10, 20), 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
