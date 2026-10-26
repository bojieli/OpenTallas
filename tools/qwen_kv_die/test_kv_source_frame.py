"""Identity and closure separation for diagnostic source-frame geometry."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from kv_source_frame import load


class SourceFrame(unittest.TestCase):
    def test_source_frame_identity_and_refusals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kit = 'physical/ref_tile/actual_ovl'
            spec = dict(top='actual_ovl', params=dict(NTX=3), sources=['rtl/actual.sv'],
                        io_tcl=kit+'/assigned_pins.tcl', outline=dict(w=500, h=320))
            files = {'rtl/actual.sv': 'module actual_ovl; endmodule',
                     kit+'/spec.json': json.dumps(spec), kit+'/assigned_pins.tcl': 'actual pins',
                     kit+'/floorplan.json': '{}', kit+'/pin_geometry_plan.json': '{}',
                     'frames/actual_ovl.lef': 'MACRO actual_ovl\n SIZE 500 BY 320 ;\nEND actual_ovl\n'}
            for name, text in files.items():
                p = root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            sha = lambda name: hashlib.sha256((root/name).read_bytes()).hexdigest()
            receipt = dict(schema='opentallas.kv_d2d_source_frame.v1', kit=kit, top='actual_ovl',
                           params=spec['params'], spec_sha256=sha(kit+'/spec.json'),
                           source_sha256={'rtl/actual.sv': sha('rtl/actual.sv')},
                           pin_recipe_sha256={n: sha(n) for n in files if n.endswith(('.tcl', 'floorplan.json', 'pin_geometry_plan.json'))},
                           lef='frames/actual_ovl.lef', lef_sha256=sha('frames/actual_ovl.lef'),
                           outline=[500, 320], qualification='SOURCE_FRAME_DIAGNOSTIC_ONLY')
            manifest = root/'frame.json'
            manifest.write_text(json.dumps(receipt))
            self.assertEqual(load(root, 'frame.json', 'actual_ovl', 'actual_ovl')[0], root/receipt['lef'])
            for change in (dict(params=dict(NTX=4)), dict(outline=[501, 320]),
                           dict(lef='physical/ref_tile/actual_ovl/views/actual_ovl.lef'),
                           dict(qualification='CLOSED')):
                manifest.write_text(json.dumps({**receipt, **change}))
                with self.subTest(change=change), self.assertRaises(ValueError):
                    load(root, 'frame.json', 'actual_ovl', 'actual_ovl')
            manifest.write_text(json.dumps(receipt))
            (root/'rtl/actual.sv').write_text('changed actual source')
            with self.assertRaisesRegex(ValueError, 'identity changed'):
                load(root, 'frame.json', 'actual_ovl', 'actual_ovl')


if __name__ == '__main__':
    unittest.main()
