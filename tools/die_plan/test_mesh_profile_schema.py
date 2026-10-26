"""The real mesh plan writer must round-trip through both canonical schemas."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import jsonschema
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as CM
import schema as S


class MeshProfileSchema(unittest.TestCase):
    def emitted_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = root / 'plan.json'
            plan.write_text(json.dumps(dict(die=dict(name='profile', outline_um=[800, 800], reach_um=405),
                                            partition_types={}, partitions=[], ports=[], lanes=[], clock={})))
            regions = CM.region_boxes(8, 8, 3, W=800, H=800)
            meta = dict(nx=8, ny=8, m=2, rep_um=450, ndr='4w', pitch_um=[100, 100],
                        regions_depth=3, regions=regions)
            (root / 'mesh.json').write_text(json.dumps(dict(meta=meta)))
            (root / 'place.json').write_text(json.dumps(dict(clock=dict(x=10, y=10, kind='node'))))
            subprocess.run([sys.executable, str(Path(__file__).with_name('apply_clkmesh_sites.py')),
                            str(plan), str(root), '--write', '--delta-id', 'D-TEST-MESH'],
                           check=True, capture_output=True, text=True)
            return json.loads(plan.read_text())['clock']['mesh']

    def validators(self):
        static = json.loads(Path(__file__).with_name('die_plan.schema.json').read_text())
        for raw in (S.SCHEMA, static):
            yield jsonschema.Draft202012Validator(raw['properties']['clock']['properties']['mesh'])

    def test_real_generated_regional_profile_accepts_both_schemas(self):
        profile = self.emitted_profile()
        self.assertEqual(len(profile['regions']), 8)
        for validator in self.validators():
            self.assertEqual(list(validator.iter_errors(profile)), [])
            with_strap = copy.deepcopy(profile)
            with_strap['regions'][0]['strap_box_um'] = [.214, .214, 199.786, 399.786]
            self.assertEqual(list(validator.iter_errors(with_strap)), [])

    def test_unknown_fields_and_invalid_region_are_rejected(self):
        profile = self.emitted_profile()
        for validator in self.validators():
            for mutate in ('profile', 'region', 'tag'):
                bad = copy.deepcopy(profile)
                if mutate == 'profile': bad['unrecognized'] = True
                elif mutate == 'region': bad['regions'][0]['unrecognized'] = True
                else: bad['regions'][0]['tag'] = 'wrong-root'
                self.assertTrue(list(validator.iter_errors(bad)), mutate)


if __name__ == '__main__': unittest.main()
