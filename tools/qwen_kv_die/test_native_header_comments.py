"""Native binder must see ports after punctuation inside RTL comments."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
tree = ast.parse((ROOT / 'tools/qwen_kv_die/die_port_bind_kv.py').read_text())
scope = {'re': re}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name in ('header', 'evalw')], type_ignores=[]), 'binder', 'exec'), scope)


class NativeHeaderComments(unittest.TestCase):
    def test_actual_astk_ports(self):
        params, ports = scope['header']((ROOT / 'rtl/qwen_sys/split_20261014/qkd_astk_static_leaves.sv').read_text(),
                                        'qkd_astk_ep_s')
        self.assertEqual(scope['evalw'](ports['qi'][1], params), 572)
        self.assertEqual(scope['evalw'](ports['xe'][1], params), 136)
        self.assertEqual(len(ports), 16)

    def test_actual_parameterized_header(self):
        params, ports = scope['header']((ROOT / 'rtl/qwen_sys/split_20261014/qkd_pv_rtrunk.sv').read_text(),
                                        'qkd_pv_rs_hd_f')
        self.assertEqual(scope['evalw'](ports['a0v'][1], params), 31)
        self.assertEqual(scope['evalw'](ports['o_data'][1], params), 512)
        self.assertEqual(len(ports), 14)

    def test_block_comment_terminator(self):
        _, ports = scope['header']('module x(input a, /* ); */ output b); endmodule', 'x')
        self.assertEqual(set(ports), {'a', 'b'})


if __name__ == '__main__':
    unittest.main()
