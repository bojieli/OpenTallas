"""Unit-test the scalar alias rule without importing fleet-only die sizing."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


class ScalarAliasTests(unittest.TestCase):
    def mapper(self):
        tree = ast.parse(Path(__file__).with_name('bind_views.py').read_text())
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('pin_map', 'bit_names')]
        env = dict(KV=SimpleNamespace(BINDINGS={'dcal': dict(ports={
            'cal': ['cal_start', 'cal_seg'], 'ego': ['epoch_go']})}),
                   sliced_order=lambda base, dps: dps)
        exec(compile(ast.Module(body=funcs, type_ignores=[]), 'bind_views.py', 'exec'), env)
        return env['pin_map']

    def test_extra_scalar_uses_actual_real_pin(self):
        real = dict(cal_start=0, cal_seg=0, epoch_go=0)
        pm = self.mapper()('dcal', {'cal': 2}, real, ['ego'])
        self.assertEqual(pm, {'cal_start': 'cal[0]', 'cal_seg': 'cal[1]', 'epoch_go': 'ego[0]'})

    def test_unconnected_pin_keeps_existing_mapping(self):
        pm = self.mapper()('dcal', {'cal': 2}, dict(cal_start=0, cal_seg=0, epoch_go=0))
        self.assertNotIn('epoch_go', pm)

    def test_wide_or_unknown_extra_refuses(self):
        for extra, real in [('ego', dict(epoch_go=2)), ('unknown', dict(epoch_go=0))]:
            with self.assertRaisesRegex(ValueError, 'not a mapped scalar'):
                self.mapper()('dcal', {}, real, [extra])


if __name__ == '__main__':
    unittest.main()
