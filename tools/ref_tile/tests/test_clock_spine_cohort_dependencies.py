import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as RT

class CohortDependencies(unittest.TestCase):
    def test_actual_lepa_spine_archive_binding(self):
        root = Path(__file__).resolve().parents[3]
        kit = 'physical/ref_tile/s81sl_lepmua_r6v'
        spec = json.loads((root / kit / 'spec.json').read_text())
        paths = RT.referenced_paths(spec, kit)
        self.assertIn('physical/common_flow/clock_spine.tcl', paths)
        self.assertEqual(paths.count('physical/common_flow/clock_spine_cohorts.tcl'), 1)
        spec['clock'] = 'cts'
        self.assertNotIn('physical/common_flow/clock_spine_cohorts.tcl', RT.referenced_paths(spec, kit))

if __name__ == '__main__':
    unittest.main()
