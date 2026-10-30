"""Exact approved collective identity, never a wildcard clock/reset exemption."""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import static_id_contracts as C
import face_shell as F
import parent_id_straps as P
import sdc_lint as S

def load_sdc():
    tree = ast.parse((HERE / 'gen_core_kit_hbm.py').read_text())
    node = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'sdc')
    ns = dict(IO_BUDGET=.4, UNC_SETUP_PS=60, UNC_HOLD_PS=25, UNC_SPLIT=.5, IO_LOAD_FF=2,
              re=__import__('re'), _reset_sdc=lambda *a: '')
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<real generator sdc>', 'exec'), ns)
    return ns['sdc']

class TestStaticIds(unittest.TestCase):
    def test_exact_ring_two_bit_only(self):
        self.assertEqual(C.static_inputs(C.RING_MASTER, {'strap_qid':2}, {'strap_qid':'input'}), ['strap_qid'])
        for module in ('ot_hgi_sm_xload_cl2_bdring', 'unrelated'):
            self.assertEqual(C.static_inputs(module, {'strap_qid':2}, {'strap_qid':'input'}), [])
        for width, direction in ((1,'input'), (3,'input'), (2,'output')):
            with self.assertRaises(ValueError): C.static_inputs(C.RING_MASTER, {'strap_qid':width}, {'strap_qid':direction})

    def test_shell_wire_id_data_still_registered(self):
        widths={'clk':1,'strap_qid':2,'data':3,'out':3}
        dirs={'clk':'input','strap_qid':'input','data':'input','out':'output'}
        passthrough={'clk', *C.static_inputs(C.RING_MASTER,widths,dirs)}
        sv=F.emit_shell(C.RING_MASTER, 'body', {}, widths, dirs, widths, passthrough, 'clk')
        self.assertNotIn('u_bin_strap_qid',sv)
        self.assertIn('.strap_qid(strap_qid)',sv)
        self.assertIn('u_bin_data',sv)
        # Mutant/wrong master retains the face flop: cannot silently borrow the exemption.
        bad=F.emit_shell('other','body',{},widths,dirs,widths,{'clk'},'clk')
        self.assertIn('u_bin_strap_qid',bad)

    def test_parent_only_native_nw2_ne3(self):
        for value in (2,3):
            d={'module':C.RING_MASTER,'parent_id_straps':{'strap_qid':{'width':2,'value':value}}}
            self.assertEqual(P.validate_parent_id_straps(d, inputs={'strap_qid':2}, actual_module=C.RING_MASTER),d['parent_id_straps'])
            with self.assertRaises(ValueError): P.validate_parent_id_straps(d, actual_module='ot_hgi_sm_xload_cl2_bdring')
        with self.assertRaises(ValueError):
            P.validate_parent_id_straps({'module':C.RING_MASTER,'parent_id_straps':{'strap_qid':{'width':2,'value':0}}})

    def test_sdc_exact_declared_only_and_no_fake_clock_reset(self):
        text=load_sdc()(833,250,40,['clk'],[], 'ring', straps=['strap_qid'])
        kw=dict(period_ps=833,insertion_ps=250,insertion_tol_ps=40,clock_ports=['clk'],inputs=['strap_qid','data'],outputs=['out'],straps=['strap_qid'])
        self.assertEqual(S.lint(text,**kw),[])
        self.assertTrue(S.lint(text+'set_false_path -from [get_ports {data}]\n',**kw))
        self.assertTrue(S.lint(text.replace('{strap_qid}', '{lane_lane_id}'),**kw))
        self.assertNotIn('create_clock -name strap_qid',text)
        self.assertNotIn('set_false_path -to',text)

    def test_default_has_no_identity_change(self):
        text=load_sdc()(833,250,40,['clk'],[],'plain')
        self.assertNotIn('set_false_path',text)
        self.assertEqual(C.static_inputs('plain',{'data':2},{'data':'input'}),[])

    def test_su_native_is_prep_never_physical_exemption(self):
        result=C.su_native_prep(C.SU_MASTER,{'lane_lane_id':11},{'lane_lane_id':'input'})
        self.assertFalse(result['physical_exemption'])
        self.assertEqual(C.static_inputs(C.SU_MASTER,{'lane_lane_id':11},{'lane_lane_id':'input'}),[])
        with self.assertRaises(ValueError): C.su_native_prep(C.SU_MASTER,{'lane_lane_id':9},{'lane_lane_id':'input'})

if __name__=='__main__': unittest.main()
