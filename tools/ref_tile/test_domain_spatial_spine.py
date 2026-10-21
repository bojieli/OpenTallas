"""Focused schema/ownership causals; physical spine/signoff pairing is separate."""
import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

import domain_spatial_spine as D

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    domains = {name: dict(ports=[port]) for name, port in [('core', 'ck_core'), ('hr', 'ck_hr')]}
    spec = dict(clock='multiple_cts_roots', clock_ports=['ck_core', 'ck_hr'])
    spec['domain_spatial_spine'] = dict(version=1,
        roots=[dict(domain='core', port='ck_core'), dict(domain='hr', port='ck_hr')],
        symmetric=True, bin_um=30, leaf_max=16, iterations=10,
        rc_cal=False, macro_leaf=False, macro_pin_leaf=False)
    return spec, domains


class Schema(unittest.TestCase):
    def test_default_has_no_generated_bytes_or_dependencies(self):
        self.assertIsNone(D.validate({}, {}, ROOT))
        self.assertEqual(D.before_entries({}), [])
        self.assertEqual(D.after_entries({}), [])
        self.assertEqual(D.dependencies({}), [])

    def test_existing_roots_only(self):
        s, domains = fixture()
        self.assertEqual(D.validate(s, domains, ROOT), s['domain_spatial_spine'])
        self.assertIn(D.PG_BINDING, D.dependencies(s))
        for mutation in ('root', 'domain', 'duplicate', 'subset', 'reorder'):
            b = copy.deepcopy(s); r = b['domain_spatial_spine']['roots']
            if mutation == 'root': r[1]['port'] = 'new_clock'
            if mutation == 'domain': r[1]['domain'] = 'core'
            if mutation == 'duplicate': r[1] = r[0]
            if mutation == 'subset': r.pop()
            if mutation == 'reorder': r.reverse()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                D.validate(b, domains, ROOT)

    def test_strict_knobs_and_engine_binding(self):
        s, domains = fixture()
        for key, value in [('new_hook', 'x.tcl'), ('version', True), ('leaf_max', 33),
                           ('iterations', 0), ('bin_um', float('nan')),
                           ('rc_cal', True), ('symmetric', 1)]:
            b = copy.deepcopy(s); b['domain_spatial_spine'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                D.validate(b, domains, ROOT)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/D.ENGINE; p.parent.mkdir(parents=True); p.write_text('wrong engine')
            with self.assertRaisesRegex(ValueError, 'canonical engine'):
                D.validate(s, domains, temp)

    def test_shell_requires_distinct_macro_pin_leaves(self):
        s, domains = fixture()
        s['soft_root_macro_bindings'] = {'u_mem': {'clock_pins': {'rclk': 'ck_core', 'wclk': 'ck_hr'}}}
        with self.assertRaisesRegex(ValueError, 'dual-clock raw'):
            D.validate(s, domains, ROOT)
        s['domain_spatial_spine'].update(macro_leaf=True, macro_pin_leaf=True)
        D.validate(s, domains, ROOT)


class Ownership(unittest.TestCase):
    def test_tcl_owner_causals(self):
        # The pure admission takes real physical/Liberty terminal identities,
        # not STA-reported sink counts (a different measurement basis).
        script = f'source {{{ROOT / D.GUARD}}}\n' + r'''
set roots {ck_core ck_hr}
set nets {ck_core net_c ck_hr net_h}
set contacts {{ff0/CLK net_c} {ff1/CLK net_h} {mem/rclk net_c} {mem/wclk net_h}}
if {[ot_dsp::validate $roots $nets $contacts {}] ne {ck_core 2 ck_hr 2}} {error "positive counts differ"}
foreach bad {
    {ot_dsp::validate $roots {ck_core net_c} $contacts {}}
    {ot_dsp::validate $roots {ck_core net_c ck_hr net_c} $contacts {}}
    {ot_dsp::validate $roots $nets [concat $contacts {{ff0/CLK net_h}}] {}}
    {ot_dsp::validate $roots $nets [concat $contacts {{foreign/CLK net_x}}] {}}
    {ot_dsp::validate $roots $nets $contacts {ff0/D}}
    {ot_dsp::validate $roots $nets {{ff0/CLK net_c}} {}}
} {
    if {![catch {eval $bad} message]} {error "mutant escaped: $bad"}
    puts "MUTANT_CAUGHT $message"
}
puts "DOMAIN_SPINE_OWNERSHIP PASS"
'''
        p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(p.stderr, p.stderr)
        self.assertEqual(p.stdout.count('MUTANT_CAUGHT'), 6)
        self.assertIn('DOMAIN_SPINE_OWNERSHIP PASS', p.stdout)


if __name__ == '__main__':
    unittest.main()
