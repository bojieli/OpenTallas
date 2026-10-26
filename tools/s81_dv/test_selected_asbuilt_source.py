"""Actual source selection must match the binder when physical copies supersede RTL."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from layer_prog.slice_source import resolve


class SelectedAsbuiltTest(unittest.TestCase):
    def fixture(self, root):
        paths = {}
        definitions = {
            'rtl/base.sv': 'module ot_s81sl_slice;\n ot_xg u_xg();\n ot_cap u_cap();\n ot_s81sl_xrt1 u_xr();\nendmodule\n',
            'physical/preferred.sv': 'module ot_s81sl_slice;\n ot_xg u_xg();\n ot_cap u_cap();\n ot_s81sl_xrt3 u_xr();\nendmodule\n',
            'rtl/children.sv': 'module ot_xg;\n ot_s81sl_xs u_s();\n ot_ring u_r();\nendmodule\n'
                'module ot_cap; endmodule\nmodule ot_s81sl_xs; endmodule\nmodule ot_ring; endmodule\n'
                'module ot_s81sl_xrt1; endmodule\nmodule ot_s81sl_xrt3; endmodule\n',
        }
        for name, text in definitions.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        spec=dict(base='.',files=list(definitions),prefer=['physical/preferred.sv'],defines=['ACTUAL'])
        p=root/'asbuilt.json';p.write_text(json.dumps(spec))
        return p,spec

    def test_preferred_source_used_and_manifest_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,_=self.fixture(root)
            with patch.dict(os.environ,{'OT_S81_SELECTED_ASBUILT_MANIFEST':str(path),'OT_S81_SELECTED_DEFINES':'ACTUAL'}):
                r=resolve(SimpleNamespace(inst={'s':dict(master='ot_s81sl_slice',params='')}),'s',root)
            self.assertEqual(r['xr'],'ot_s81sl_xrt3')
            self.assertEqual(r['resolved_module_sources']['ot_s81sl_slice'],'physical/preferred.sv')
            self.assertIn('asbuilt.json',r['source_sha256'])
            self.assertNotIn('rtl/base.sv',r['source_sha256'])

    def test_unresolved_duplicate_and_wrong_defines_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,spec=self.fixture(root)
            env={'OT_S81_SELECTED_ASBUILT_MANIFEST':str(path),'OT_S81_SELECTED_DEFINES':'WRONG'}
            die=SimpleNamespace(inst={'s':dict(master='ot_s81sl_slice',params='')})
            with patch.dict(os.environ,env):
                with self.assertRaisesRegex(ValueError,'defines differ'):resolve(die,'s',root)
            spec['prefer']=[];path.write_text(json.dumps(spec));env['OT_S81_SELECTED_DEFINES']='ACTUAL'
            with patch.dict(os.environ,env):
                with self.assertRaisesRegex(ValueError,'missing/ambiguous'):resolve(die,'s',root)

    def test_explicit_children_cannot_replace_manifest_module(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,_=self.fixture(root)
            (root/'extra.sv').write_text('module ot_cap; endmodule\n')
            with patch.dict(os.environ,{'OT_S81_SELECTED_ASBUILT_MANIFEST':str(path),
                    'OT_S81_SELECTED_DEFINES':'ACTUAL','OT_S81_SELECTED_CHILD_FILES':'extra.sv'}):
                with self.assertRaisesRegex(ValueError,'override manifest modules'):
                    resolve(SimpleNamespace(inst={}), 's', root)

    def test_absent_current_source_cannot_fall_back(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path,spec=self.fixture(root);(root/'physical/preferred.sv').unlink()
            with patch.dict(os.environ,{'OT_S81_SELECTED_ASBUILT_MANIFEST':str(path),'OT_S81_SELECTED_DEFINES':'ACTUAL'}):
                with self.assertRaisesRegex(ValueError,'input absent'):resolve(SimpleNamespace(inst={}), 's',root)

if __name__=='__main__':unittest.main()
