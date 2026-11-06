import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('children', Path(__file__).with_name('signed_children.py'))
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class SignedChildren(unittest.TestCase):
    def fixture(self, root, signed=True):
        v = root / 'leaf'
        v.mkdir()
        for name in ('leaf.lef', 'leaf_tt.lib', 'leaf_ff.lib'):
            (v / name).write_text('MACRO leaf\nSIZE 20 BY 30 ;\nEND leaf\n')
        (v / 'provenance.json').write_text(json.dumps(dict(views_status='signoff', verdict='SIGNED' if signed else 'NOT SIGNED')))
        (v / 'gates.json').write_text(json.dumps(dict(view_complete=True)))
        return dict(children=[dict(view='leaf', inst='u.g[0].u_leaf', at=[10, 15])]), dict(views=dict(leaf='leaf'))

    def test_signed_view_staged_as_macro_without_mutating_source_spec(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            s, r = self.fixture(p)
            out, children = C.prepare_hard_children(s, r, p, [100, 100])
            self.assertIn('children', s)
            self.assertNotIn('children', out)
            self.assertEqual(out['macros'][0]['inst'], 'u.g[0].u_leaf')
            self.assertIn('u_leaf', C.hard_children_tcl(children))

    def test_unsigned_view_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            s, r = self.fixture(p, signed=False)
            with self.assertRaisesRegex(ValueError, 'not SIGNED'):
                C.prepare_hard_children(s, r, p, [100, 100])

    def test_outside_child_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            s, r = self.fixture(p)
            s['children'][0]['at'] = [90, 90]
            with self.assertRaisesRegex(ValueError, 'outside'):
                C.prepare_hard_children(s, r, p, [100, 100])

    def test_blackbox_replaces_only_child_implementation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            parent = 'module top(input a,output y); leaf #(.P(3)) u(a,y);\nendmodule\n'
            (p / 'native.sv').write_text('module leaf(input a,output y);\nassign y=a;\nendmodule\n' + parent)
            bb = '(* blackbox *) module leaf(input a,output y);endmodule\n'
            (p / 'leaf_bb.v').write_text(bb)
            C.strip_native_children(p, {'leaf'})
            self.assertEqual((p / 'native.sv').read_text(), parent)
            self.assertEqual((p / 'leaf_bb.v').read_text(), bb)

    def test_missing_native_child_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'exactly one native'):
                C.strip_native_children(d, {'leaf'})


if __name__ == '__main__':
    unittest.main()
