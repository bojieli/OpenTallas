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

    def test_only_selected_parameterization_is_hardened(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            native = 'module leaf #(parameter P=0)(input a,output y);\nassign y=a^P;\nendmodule\n'
            parent = 'module top(input a,output yh,ys);\nleaf #(.P(0)) u_hard(a,yh);\nleaf #(.P(4)) u_soft(a,ys);\nendmodule\n'
            (p / 'native.sv').write_text(native + parent)
            bb = '(* blackbox *) module leaf(input a,output y);endmodule\n'
            (p / 'leaf_bb.v').write_text(bb)
            C.specialize_native_children(p, [dict(master='leaf', inst='top.u_hard')])
            result = (p / 'native.sv').read_text()
            self.assertIn('module leaf__soft #', result)
            self.assertIn('assign y=a^P;', result)
            self.assertIn('leaf u_hard(a,yh);', result)
            self.assertIn('leaf__soft #(.P(4)) u_soft(a,ys);', result)
            self.assertEqual((p / 'leaf_bb.v').read_text(), bb)

    def test_nested_parameters_and_comments(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            source = '// leaf should stay in this comment\nmodule leaf(input a,output y);\nassign y=a;\nendmodule\nmodule top(input a,output y);\nleaf #(.P((2 == 2) ? 1 : 0)) u_hard(a,y);\nendmodule\n'
            (p/'a.sv').write_text(source)
            C.specialize_native_children(p, [dict(master='leaf',inst='u_hard')])
            result = (p/'a.sv').read_text()
            self.assertTrue(result.startswith('// leaf should stay in this comment'))
            self.assertIn('leaf u_hard', result)
            self.assertNotIn('.P((2 == 2)', result)

    def test_missing_native_child_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'exactly one native'):
                C.specialize_native_children(d, [dict(master='leaf',inst='u_hard')])


if __name__ == '__main__':
    unittest.main()
