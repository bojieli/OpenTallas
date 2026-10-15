"""Exact wire-level regression for TP8 real ectl leaves and identity ROM slot views."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

V5 = module('v5', 'tools/qwen_kv_die/tp8b_v5.py')
BIND = module('bind', 'tools/qwen_tp8/bind_real.py')

class RealLeafBinding(unittest.TestCase):
    def test_head_word_exact_and_mutant(self):
        # qkd_ectl3 assign: {q, cl[15:4], b_row, a_row, cl[3:0]}.
        expected = [('cl', i) for i in range(4)] + [('a', i) for i in range(512)] + [('b', i) for i in range(512)] + [('cl', i) for i in range(4, 16)] + [('q', i) for i in range(519)]
        def compose(mapping):
            out = [None] * 1559
            for pn, (_, bits) in mapping.items():
                for j, bit in enumerate(bits):
                    self.assertIsNone(out[bit])
                    out[bit] = (pn.removeprefix('ti_'), j)
            return out
        self.assertEqual(compose(V5.JOIN['qkd_rhead']), expected)
        values = {}
        for pn, (_, bits) in V5.JOIN['qkd_rhead'].items():
            values.update({bit: f'{pn}[{j}]' for j, bit in enumerate(bits)})
        self.assertEqual(V5.joined_expr(values), '{ti_q[518:0], ti_cl[15:4], ti_b[511:0], ti_a[511:0], ti_cl[3:0]}')
        mutant = dict(V5.JOIN['qkd_rhead'])
        mutant['ti_a'], mutant['ti_b'] = mutant['ti_b'], mutant['ti_a']
        self.assertNotEqual(compose(mutant), expected)

    def test_alias_preserves_pin_geometry_and_all_corner_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            for master, (source, directory) in BIND.VIEW_ALIASES.items():
                vd = BIND.alias_view(ROOT, Path(tmp), master)
                self.assertIsNotNone(vd)
                src = ROOT / directory
                original = BIND.macros((src / f'{source}.lef').read_text())[source][2]
                alias = BIND.macros((vd / f'{master}.lef').read_text())[master][2]
                self.assertEqual(alias.replace('MACRO '+master, 'MACRO '+source).replace('END '+master, 'END '+source), original)
                for c in ('tt', 'ff', 'ss'):
                    old = (src / f'{source}_{c}.lib').read_text()
                    new = (vd / f'{master}_{c}.lib').read_text()
                    expected = re.sub(rf'(cell\s*\(\s*)"?{source}"?(\s*\))', rf'\1{master}\2', old)
                    self.assertEqual(new, expected)
                self.assertEqual((vd/'insertion.json').read_bytes(), (src/'insertion.json').read_bytes())

    def test_rom_wrappers_are_identity_wires(self):
        text = (ROOT / 'rtl/physical/ot_qwen_tp8_real_rom_slots.sv').read_text()
        for master, (source, _) in BIND.VIEW_ALIASES.items():
            body = re.search(rf'module {master} \((.*?)endmodule', text, re.S).group(1)
            declared = re.findall(r'(?:input|output)\s+wire\s*(?:\[[^\]]+\]\s*)?(\w+)', body)
            connected = re.findall(r'\.(\w+)\((\w+)\)', body)
            self.assertEqual(sorted(connected), sorted((pn, pn) for pn in declared))
            self.assertIn(source + ' u', body)
            self.assertNotIn('assign', body)

    def test_real_leaf_ports_available(self):
        for part in 'abc':
            vp = V5.view_pins('qkd_ectl_' + part)
            self.assertIsNotNone(vp)
            self.assertIn('ck', vp[2])
            self.assertIn('rst_n', vp[2])
            self.assertTrue(all(f'cfg[{i}]' in vp[2] for i in range(5)))
        self.assertIn('rvm_o', V5.view_pins('qkd_ectl_a')[2])
        self.assertIn('rvm_i', V5.view_pins('qkd_ectl_b')[2])

if __name__ == '__main__':
    unittest.main()
