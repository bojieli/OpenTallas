"""Literal LEF orientation checks; no synthetic view is qualified by these tests."""
import contextlib
import hashlib
import io
import json
import os
import tempfile
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

    def test_site_and_pin_symmetry_cannot_authorize_target_macro(self):
        view=self.view()
        view['text']='SITE decoy\n SYMMETRY X Y ;\nEND decoy\nMACRO test\n PIN data\n SYMMETRY X Y ;\n END data\nEND test\n'
        self.assertEqual(G.bound_view_orientation_contract(view,'test')['supported'],['R0'])

    def test_another_macro_cannot_authorize_target(self):
        view=self.view()
        view['text']='MACRO other\n SYMMETRY X Y ;\nEND other\n'+view['text']
        self.assertEqual(G.bound_view_orientation_contract(view,'test')['supported'],['R0'])

    def test_unknown_duplicate_and_malformed_declarations_fail_closed(self):
        for body in ('SYMMETRY X BAD ;','SYMMETRY X X ;','SYMMETRY X ;\nSYMMETRY Y ;',
                     'SYMMETRY X','SYMMETRY ;','SYMMETRY X ; junk'):
            with self.subTest(body=body):
                view=self.view();view['text']='MACRO test\n'+body+'\nEND test\n'
                contract=G.bound_view_orientation_contract(view,'test')
                self.assertFalse(contract['supported']);self.assertTrue(contract['errors'])

    def test_missing_or_duplicate_target_macro_fails_closed(self):
        view=self.view('X Y')
        self.assertFalse(G.bound_view_orientation_contract(view,'absent')['supported'])
        view['text']*=2
        self.assertFalse(G.bound_view_orientation_contract(view,'test')['supported'])

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

    def test_empty_verified_table_marks_all_generated_unbound(self):
        model=dict(insts=[self.inst('missing',master='missing')])
        with patch.object(G,'bound_views',return_value={}),patch.object(G,'REAL_FILES',{}), \
             patch.dict(os.environ,{'OT_S81_VIEW_BINDING_SKIP_MISFIT':'1'}),contextlib.redirect_stderr(io.StringIO()):
            G.apply_view_binding(model,{})
        self.assertFalse(model['bound_views'])
        self.assertFalse(model['view_binding_qualification']['complete'])
        self.assertFalse(model['view_binding_qualification']['native_qualification'])
        self.assertEqual(model['view_binding_qualification']['unbound_generated_instances'],1)


class OrientationQualification(unittest.TestCase):
    """--orientation-qualification: a measured table qualifies an exact (master, LEF sha256, orientation)."""
    TEXT = 'MACRO test\n PIN data\n END data\nEND test\n'

    def view(self, text=None):
        return dict(text=text or self.TEXT, w=10.0, h=10.0, lef='test.lef', tt='t.lib', ff='f.lib', ss='s.lib')

    def table(self, orient='MY', sha=None, fail=None, drop=None, verdict='PASS'):
        checks = {c: dict(verdict='PASS') for c in G.ORIENT_QUAL_CHECKS}
        if fail:
            checks[fail] = dict(verdict='FAIL', reason='measured')
        if drop:
            del checks[drop]
        sha = sha or hashlib.sha256(self.TEXT.encode()).hexdigest()
        return dict(schema=G.ORIENT_QUAL_SCHEMA, tag='t', entries=[dict(
            master='test', lef_sha256=sha, orientations={orient: dict(verdict=verdict, checks=checks)})])

    def load(self, tab):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'oq.json')
        with open(p, 'w') as f:
            json.dump(tab, f)
        G._ORIENT_QUAL.clear()
        return G.orientation_qualification(p)

    def test_default_identical_without_option(self):
        with patch.object(G, 'ORIENT_QUAL', None):
            c = G.bound_view_orientation_contract(self.view(), 'test')
        self.assertEqual(c, dict(symmetry=[], declared=['R0'], supported=['R0'], errors=[]))

    def test_positive_exact_sha_all_checks_pass(self):
        c = G.bound_view_orientation_contract(self.view(), 'test', self.load(self.table('MY')))
        self.assertEqual(c['supported'], ['R0', 'MY'])
        self.assertEqual(c['qualified'], ['MY'])
        self.assertEqual(c['declared'], ['R0'])            # the literal contract is unchanged
        self.assertNotIn('MX', c['supported'])

    def test_wrong_sha_qualifies_nothing(self):
        c = G.bound_view_orientation_contract(self.view(), 'test', self.load(self.table('MY', sha='0' * 64)))
        self.assertEqual(c['supported'], ['R0'])
        c = G.bound_view_orientation_contract(self.view(self.TEXT + '\n'), 'test', self.load(self.table('MY')))
        self.assertEqual(c['supported'], ['R0'])

    def test_failing_or_missing_check_qualifies_nothing(self):
        for kw in (dict(fail='pg_die_grid'), dict(fail='row_parity'), dict(drop='timing_clock'), dict(verdict='FAIL')):
            with self.subTest(**kw):
                c = G.bound_view_orientation_contract(self.view(), 'test', self.load(self.table('MX', **kw)))
                self.assertEqual(c['supported'], ['R0'])

    def test_missing_entry_qualifies_nothing(self):
        tab = self.table('MY')
        tab['entries'][0]['master'] = 'other'
        c = G.bound_view_orientation_contract(self.view(), 'test', self.load(tab))
        self.assertEqual(c['supported'], ['R0'])

    def test_malformed_table_fails_closed(self):
        for tab in (dict(schema='x', entries=[]), dict(schema=G.ORIENT_QUAL_SCHEMA),
                    dict(schema=G.ORIENT_QUAL_SCHEMA, entries=[dict(master='test')])):
            with self.subTest(tab=tab), self.assertRaises(SystemExit):
                self.load(tab)
        G._ORIENT_QUAL.clear()
        with self.assertRaises(SystemExit):
            G.orientation_qualification('/nonexistent/oq.json')

    def bind(self, tab, orient):
        G._ORIENT_QUAL.clear()
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'oq.json')
        with open(p, 'w') as f:
            json.dump(tab, f)
        model = dict(insts=[G.Inst('i', 'test', 0, 0, 10, 10, orient)])
        with patch.object(G, 'ORIENT_QUAL', p), patch.object(G, 'bound_views', return_value={'test': self.view()}), \
             patch.object(G, 'bound_view_pin_faults', return_value=[]), patch.object(G, 'REAL_FILES', {}), \
             patch.dict(os.environ, {'OT_S81_VIEW_BINDING_SKIP_MISFIT': '0'}), contextlib.redirect_stderr(io.StringIO()):
            G.apply_view_binding(model, {})
        return model

    def test_strict_binding_accepts_qualified_and_rejects_unqualified(self):
        m = self.bind(self.table('MY'), 'MY')
        self.assertEqual(m['bound_views']['test']['orients'], {'MY': 1})
        self.assertEqual(m['bound_views']['test']['orientation_contract']['qualified'], ['MY'])
        with self.assertRaisesRegex(SystemExit, 'test instance i is MX'):
            self.bind(self.table('MY'), 'MX')
        with self.assertRaisesRegex(SystemExit, 'test instance i is MY'):
            self.bind(self.table('MY', fail='signal_track_lattice'), 'MY')


if __name__=='__main__':unittest.main()
