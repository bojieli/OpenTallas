"""Literal LEF orientation checks; no synthetic view is qualified by these tests."""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dsrom_s81_fulldie as G


class OrientationContract(unittest.TestCase):
    def view(self, symmetry=''):
        return dict(text='MACRO test\n'+(' SYMMETRY '+symmetry+' ;\n' if symmetry else '')+'END test\n',
                    w=10.0, h=10.0, lef='test.lef', tt='test_tt.lib', ff='test_ff.lib', ss='test_ss.lib')

    def test_declared_closure_within_placer_support(self):
        expected={'':{'R0'},'X':{'R0','MX'},'Y':{'R0','MY'},'X Y':set(G.BOUND_ORIENTS),
                  'R90':{'R0','R180'},'X R90':set(G.BOUND_ORIENTS),'Y R90':set(G.BOUND_ORIENTS),
                  'X Y R90':set(G.BOUND_ORIENTS)}
        for symmetry, legal in expected.items():
            with self.subTest(symmetry=symmetry):
                self.assertEqual(set(G.bound_view_orientation_contract(self.view(symmetry))['supported']),legal)

    def bind(self, instances, symmetry='', diagnostic=False):
        model=dict(insts=instances)
        with patch.object(G,'bound_views',return_value={'test':self.view(symmetry)}), \
             patch.object(G,'bound_view_pin_faults',return_value=[]), patch.object(G,'REAL_FILES',{}), \
             patch.dict(os.environ, {'OT_S81_VIEW_BINDING_SKIP_MISFIT':'1' if diagnostic else '0'}), \
             contextlib.redirect_stderr(io.StringIO()):
            G.apply_view_binding(model,{})
        return model

    def inst(self,name,orient='R0',master='test'):
        return G.Inst(name,master,0,0,10,10,orient)

    def test_strict_rejects_unsupported_named_instance(self):
        with self.assertRaisesRegex(SystemExit,'test instance bad is MY'):
            self.bind([self.inst('bad','MY')])

    def test_strict_accepts_declared_mirror_and_records_contract(self):
        model=self.bind([self.inst('good','MY')],'Y')
        self.assertEqual(model['bound_views']['test']['orients'],{'MY':1})
        self.assertEqual(model['bound_views']['test']['orientation_contract']['symmetry'],['Y'])

    def test_diagnostic_names_every_bad_instance_and_marks_incomplete(self):
        model=self.bind([self.inst('a','MY'),self.inst('b','MX'),self.inst('c'),self.inst('missing',master='missing')],diagnostic=True)
        self.assertFalse(model['bound_views'])
        self.assertEqual(model['view_binding_misfits']['test']['unsupported_orientations'],
                         [dict(instance='a',orient='MY'),dict(instance='b',orient='MX')])
        self.assertFalse(model['view_binding_qualification']['complete'])
        self.assertFalse(model['view_binding_qualification']['native_qualification'])
        self.assertEqual(model['view_binding_qualification']['unsupported_orientation_instances'],2)
        self.assertEqual(model['view_binding_unbound_generated']['missing']['reason'],'NO_VERIFIED_TABLE_VIEW')


if __name__=='__main__':unittest.main()
