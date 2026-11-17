"""The WQB stream builder must select its actual frame for both row witnesses."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent

def load_layer_field(path):
    node = next(n for n in ast.parse(path.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'layer_field')
    scope = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), scope)
    return scope['layer_field']

class FrameInstanceTest(unittest.TestCase):
    def run_field(self, selected):
        seen = []
        def plan(*args, **kwargs):
            seen.append(kwargs.get('frame_instance'))
            if kwargs.get('frame_instance') != selected:
                raise ValueError('no shape-global schedule; choose actual frame')
            return dict(faults=0, stream=[17])
        groups = dict(groups=[[[1]], [[2]]], x=[0])
        xp = SimpleNamespace(XS_OPS={}, NPAIRS=1, NSLICE=2,
            phase_list=lambda *a:[('attn.wq_b',0,0,1,1)],
            op_groups=lambda *a:[groups], make_mat=lambda *a:SimpleNamespace(K=16),
            phase_plan=plan, TP=SimpleNamespace(chunk=lambda group, rows, *a:rows))
        modules = dict(xs_place=xp, frame_bench=SimpleNamespace(frame_pairs=lambda *a:([0],[])),
            lower_xs=SimpleNamespace(base_master=lambda m:m), xs_topo=SimpleNamespace(TOPO=None))
        with patch.dict(sys.modules, modules):
            result = load_layer_field(HERE/'xs_wqb_die.py')({}, 'L0', 'col_h10_l4_lp_asb_x', 2,
                                                         iters=0, frame_instance=selected)
        self.assertEqual(seen,[selected,selected])
        self.assertEqual(result[2],[17])

    def test_actual_frame_for_initial_and_other_rows(self):
        self.run_field('u_f_0L01')

    def test_legacy_no_instance_retains_none(self):
        self.run_field(None)

if __name__ == '__main__':
    unittest.main()
