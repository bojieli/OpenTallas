import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from reset_sync_contract import terminal_region_follow


class ResetRegionTest(unittest.TestCase):
    def test_leaf_follows_the_terminal_clock_owner(self):
        cells = [('leaf',)]
        wires = [('net', 'rst', [('leaf', 'q0'), ('hop', 'en')])]
        clocks = {'hop': [('clk_r3', 'ck')]}
        got, bad = terminal_region_follow(cells, wires, clocks, {('hop', 'ck'): 'block'})
        self.assertEqual(got, {('leaf', 'clk'): 'block'})
        self.assertEqual(bad, [])

    def test_mixed_root_fanout_is_not_assigned_a_majority_root(self):
        got, bad = terminal_region_follow([('leaf',)], [('n', 'r', [('leaf', 'q0'), ('a', 'rst'), ('b', 'rst')])],
                                          {'a': [('clk_r3', 'ck')], 'b': [('clk_r4', 'ck')]}, {})
        self.assertEqual(got, {})
        self.assertEqual(len(bad), 1)

    def test_actual_generator_column_split_preserves_followed_leaf(self):
        source = (Path(__file__).resolve().parents[1] / 'qwen_rom_fulldie_b3r2.py').read_text()
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == '_gen16_clock_refile')
        scope = dict(os=os, REP_SEG_MM=1.3, REP_COL_UM=20., REP_COL_MIN=4)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<actual-generator>', 'exec'), scope)
        for enabled in (False, True):
            model = dict(b3r2={}, ck_follow={('r0', 'clk'): 'block'})
            regs = [dict(name='r0', kind='field', rect=[0, 0, 200, 2500])]
            by = {'block': SimpleNamespace(master='hard', x=100, y=100, w=50, h=50)}
            by.update({f'r{k}': SimpleNamespace(master='qfd_rst_rep', x=0, y=y, w=13, h=7)
                       for k, y in enumerate((0, 500, 1500, 2000))})
            per = {0: [('block', 'ck')] + [(f'r{k}', 'clk') for k in range(4)]}
            with patch.dict(os.environ, {'OT_SPLIT_RST_REGION_LAND': str(int(enabled)),
                                         'OT_SPLIT_CK_COROOT': '', 'OT_SPLIT_REGION_ONE_HARD': '0'}):
                scope['_gen16_clock_refile'](model, regs, by, per)
            self.assertEqual(('r0', 'clk') in per[0], enabled)


if __name__ == '__main__':
    unittest.main()
