#!/usr/bin/env python3
"""TOK-DS-10 (10-27): frame_bench.frame_pairs resolves frame masters through a module index (binder manifest
precedence), not one file per module.  The current S81 die binds col_h*_l4_lp_asb_{x,nx}, which live in
physical/die_plan/s81/bind/models/s81_asb_models.sv; the old lookup opened rtl/.../frame/<master>.sv and raised
FileNotFoundError (TOK-DS-9 L0/L2/L14/L20 compiles)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(HERE / 'layer_prog')]
import frame_bench as B  # noqa: E402
import lower_xs as LX  # noqa: E402

ELEM = 'ot_v41_rom_elem_q_qxpq_w10 #(.P(1)) u_e{k} (.clk(c));\n'
BF = 'dsfd_bf_front_roots #(.P(1)) u_e{k} (.clk(c));\n'
CLEAN = {k: v for k, v in os.environ.items() if not k.startswith('OT_S81_SELECTED')}


def _root(td, extra=''):
    r = Path(td)
    (r / 'm').mkdir()
    # two band modules in ONE file and the composition in another: no file is named after its module
    (r / 'm/bands.sv').write_text(
        'module fr_l4_lp_r0 (input c);\n' + ELEM.format(k=0) + BF.format(k=1) + 'endmodule\n'
        'module fr_l4_lp_r1 (input c);\n' + ELEM.format(k=2) + ELEM.format(k=3) + 'endmodule\n' + extra)
    (r / 'm/models.sv').write_text(
        'module col_h77_l4_lp_asb_x (input c);\n'
        '  col_h77_r0 #(.I(1)) u_r0 (.c(c));\n  col_h77_r1 u_r1 (.c(c));\nendmodule\n'
        'module col_h77_r0 (input c);\n' + ELEM.format(k=0) + BF.format(k=1) + 'endmodule\n'
        'module col_h77_r1 (input c);\n' + ELEM.format(k=2) + BF.format(k=3) + 'endmodule\n')
    (r / 'man.json').write_text(json.dumps(dict(files=['m/bands.sv', 'm/models.sv'], prefer=[], defines=[])))
    return r


class FramePairsIndex(unittest.TestCase):
    def test_asb_composition_resolved_by_index(self):
        with tempfile.TemporaryDirectory() as td:
            r = _root(td)
            env = dict(CLEAN, OT_S81_SELECTED_SOURCE_ROOT=str(r), OT_S81_SELECTED_ASBUILT_MANIFEST=str(r / 'man.json'))
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(B.frame_pairs('col_h77_l4_lp_asb_x'), ([0, 2], [1, 3]))
                self.assertEqual(B.frame_module_source('col_h77_l4_lp_asb_x')[0].name, 'models.sv')

    def test_missing_master_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            r = _root(td)
            env = dict(CLEAN, OT_S81_SELECTED_SOURCE_ROOT=str(r), OT_S81_SELECTED_ASBUILT_MANIFEST=str(r / 'man.json'))
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ValueError):
                    B.frame_pairs('col_h78_l4_lp_asb_x')

    def test_duplicate_element_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)
            (r / 'a.sv').write_text('module col_h79_l4_lp_asb_x (input c);\n  col_h79_r0 u_r0 (.c(c));\n'
                                    '  col_h79_r0 u_r1 (.c(c));\nendmodule\n'
                                    'module col_h79_r0 (input c);\n' + ELEM.format(k=0) + BF.format(k=1) + 'endmodule\n')
            (r / 'man.json').write_text(json.dumps(dict(files=['a.sv'], prefer=[], defines=[])))
            env = dict(CLEAN, OT_S81_SELECTED_SOURCE_ROOT=str(r), OT_S81_SELECTED_ASBUILT_MANIFEST=str(r / 'man.json'))
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(AssertionError):
                    B.frame_pairs('col_h79_l4_lp_asb_x')

    def test_asb_frame_schedule_fails_closed(self):
        # neither the LP rf3r schedule nor flat timing may stand in for an as-built band frame
        for m in ('col_h10_l4_lp_asb_x', 'col_h9_l4_lp_asb_nx'):
            with self.assertRaises(ValueError):
                LX.source_frame_schedule(m)
        self.assertIsNone(LX.source_frame_schedule('col_h10'))

    @unittest.skipUnless((ROOT / 'physical/die_plan/s81/bind/asbuilt_b178_coll.json').is_file(), 'repo manifest')
    def test_repo_asb_frames_equal_flat_frames(self):
        with patch.dict(os.environ, CLEAN, clear=True):
            flat = {m: B.frame_pairs(m) for m in ('col_h9', 'col_h10')}
        man = json.loads((ROOT / 'physical/die_plan/s81/bind/asbuilt_b178_coll.json').read_text())
        env = dict(CLEAN, OT_S81_SELECTED_SOURCE_ROOT=str(ROOT), OT_S81_SELECTED_DEFINES=','.join(man['defines']),
                   OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/asbuilt_b178_coll.json')
        with patch.dict(os.environ, env, clear=True):
            for m in ('col_h9', 'col_h10'):
                for v in ('x', 'nx'):
                    self.assertEqual(B.frame_pairs(f'{m}_l4_lp_asb_{v}'), flat[m], (m, v))


if __name__ == '__main__':
    unittest.main()
