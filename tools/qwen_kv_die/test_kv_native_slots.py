"""Real reservation geometry regressions without importing the production graph."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

SRC = Path(__file__).with_name('kv_static_die.py')

def load_geometry(on):
    tree = ast.parse(SRC.read_text())
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'free_spot':
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('FRAME', 'NATIVE_SLOTS') for t in node.targets):
            nodes.append(node)
        elif isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == 'NATIVE_SLOTS':
            nodes.append(node)
    env = {'os': SimpleNamespace(environ={'OT_KV_NATIVE_SLOTS': str(int(on))})}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SRC), 'exec'), env)
    return env

class NativeSlots(unittest.TestCase):
    def test_legacy_geometry_is_default(self):
        self.assertEqual(load_geometry(False)['FRAME']['ctl'], (1123.2, 172.8))

    def test_portrait_ctl_refuses_legacy_thin_channel(self):
        e = load_geometry(True)
        self.assertEqual(e['FRAME']['ctl'], (345.6, 475.2))
        m = {'die': {'w': 1400, 'h': 400}, 'insts': [], 'keepouts': []}
        e['free_spot'](m, 1123.2, 172.8, (700, 200), 2.16, 2.16, rmax=432)
        with self.assertRaisesRegex(ValueError, 'no free'):
            e['free_spot'](m, *e['FRAME']['ctl'], (700, 200), 2.16, 2.16, rmax=432)

    def test_square_group_preserves_full_outline_keepout_and_halo(self):
        e = load_geometry(True)
        m = {'die': {'w': 1600, 'h': 1600}, 'insts': [],
             'keepouts': [('busy', 540, 540, 432, 432)]}
        x, y = e['free_spot'](m, 388.8, 388.8, (756, 756), 2.16, 2.16, rmax=864)
        self.assertTrue(x + 388.8 <= 518.4 or x >= 993.6 or y + 388.8 <= 518.4 or y >= 993.6)
        m['insts'].append(SimpleNamespace(x=x, y=y, w=388.8, h=388.8))
        x2, y2 = e['free_spot'](m, 388.8, 388.8, (756, 756), 2.16, 2.16, rmax=864)
        self.assertTrue(x2 + 388.8 <= x-21.6+1e-6 or x2 >= x+410.4-1e-6 or y2 + 388.8 <= y-21.6+1e-6 or y2 >= y+410.4-1e-6)

if __name__ == '__main__':
    unittest.main()
