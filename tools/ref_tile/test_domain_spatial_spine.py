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
                           ('rc_cal', 1), ('symmetric', 1)]:
            b = copy.deepcopy(s); b['domain_spatial_spine'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                D.validate(b, domains, ROOT)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/D.ENGINE; p.parent.mkdir(parents=True); p.write_text('wrong engine')
            with self.assertRaisesRegex(ValueError, 'canonical engine'):
                D.validate(s, domains, temp)

    def test_rc_cal_true_accepted_with_helper(self):
        s, domains = fixture(); s['domain_spatial_spine']['rc_cal'] = True
        D.validate(s, domains, ROOT)  # SQC-CTLM 10-22: calibrated-RC spine balancing (tools/orfs_hold_mm.tcl present)

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


def child_root(temp):
    """a temp source root with two hard children: 'wtn' (one clock, top-level boundary record) and 'hr' (per-pin record:
    CTS-root ck_head with a boundary, raw ck_pm0 without one -> landed_raw_pins refs), plus the canonical engine/guard"""
    import json
    import shutil
    root = Path(temp)
    for rel in (D.ENGINE, D.GUARD, D.CHILD_INS):
        (root/rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/rel, root/rel)

    def lib(name, pins):
        return (f'library({name}) {{ cell({name}) {{ '
                + ' '.join(f'pin({p}) {{ direction : input; clock : true; }}' for p in pins)
                + ' pin(d) { direction : input; } } }')
    v = root/'views/wtn'
    v.mkdir(parents=True)
    (v/'wtn_tt.lib').write_text(lib('wtn', ['ck']))
    (v/'insertion.json').write_text(json.dumps({'tt': {'boundary': {'n': 266, 'mean': 141.6, 'min': 130.1, 'max': 150.0}}}))
    h = root/'views/hr'
    h.mkdir(parents=True)
    (h/'hr_tt.lib').write_text(lib('hr', ['ck_head', 'ck_pm0']))
    (h/'insertion.json').write_text(json.dumps({'clock_measurements': {
        'ck_head': {'tt': {'boundary': {'n': 9, 'mean': 303.1}}}, 'ck_pm0': {'tt': {'all': {'n': 1, 'mean': 15.2}}}}}))
    return root


DSCI_TCL = '''
proc ot_sp_env {n d} { if {[info exists ::env($n)]} { return $::env($n) }; return $d }
proc ot_sp_leaf_arrivals {} { return [dict create L1 1000.0 L2 700.0 L3 990.0 L4 650.0] }
proc mk {it inst master blk pin} {
  proc $it {op} "if {\\$op eq {getInst}} {return $inst} else {return mt_$it}"
  proc mt_$it {op} "return $pin"
  proc $inst {op} "return m_$inst"
  proc m_$inst {op} "if {\\$op eq {isBlock}} {return $blk} else {return $master}"
}
mk i1 f1 DFF 0 CLK; mk i2 c1 wtn 1 ck; mk i3 m1 sram 1 clk; mk i4 h1 hr 1 ck_head
ENVLINE
set ::ot_sp_members [dict create L1 {i1} L2 {i2} L3 {i3} L4 {i4}]
set ::ot_sp_child_ins [dict create wtn/ck 141.6 hr/ck_head 303.1]
source HELPER
set a [ot_sp_leaf_arrivals]
if {[dict get $a L1] != 1000.0 || [dict get $a L3] != 990.0} {error "flop / unkeyed macro leaf moved: $a"}
if {abs([dict get $a L2] - 841.6) > 1e-6 || abs([dict get $a L4] - 953.1) > 1e-6} {error "child leaf not offset: $a"}
set ::ot_sp_members [dict create L1 {i1 i2} L2 {} L3 {i3} L4 {i4}]
if {![catch {ot_sp_leaf_arrivals} m] || ![string match "OT_DSCI*mixes*" $m]} {error "mixed leaf escaped: $m"}
puts "DSCI_WRAPPER PASS"
'''


class ChildInsertion(unittest.TestCase):
    def spec(self):
        s, domains = fixture()
        s['domain_spatial_spine'].update(macro_leaf=True, macro_pin_leaf=True, child_insertion='boundary_record')
        s['children'] = [dict(view='views/wtn', inst='u_wtn'), dict(view='views/hr', inst='u_hr')]
        return s, domains

    def test_targets_on_the_gate_basis(self):
        import clock_entry_constraints as C
        s, domains = self.spec()
        with tempfile.TemporaryDirectory() as temp:
            root = child_root(temp)
            raw = {'ck_pm0': {'ref': 'ck_head', 'refs': {'tt': [15.2, 15.2, 15.2]}}}
            orig = C.landed_raw_pins
            C.landed_raw_pins = lambda view, r: raw if Path(view).name == 'hr' else {}
            try:
                t = D.child_insertion_targets(s, root)
                self.assertEqual(t, {'wtn/ck': 141.6, 'hr/ck_head': 303.1, 'hr/ck_pm0': 15.2})
                self.assertEqual(D.validate(s, domains, root), s['domain_spatial_spine'])
                tcl = D.child_insertion_tcl(s, root)
                self.assertTrue(tcl[1].startswith('set ::ot_sp_child_ins [dict create'))
                self.assertEqual(tcl[2], f'source /src/{D.CHILD_INS}')
                deps = D.dependencies(s, root)
                self.assertIn(D.CHILD_INS, deps)
                self.assertIn('views/hr/insertion.json', deps)
                C.landed_raw_pins = lambda view, r: {}
                with self.assertRaisesRegex(ValueError, 'neither a boundary nor a raw'):
                    D.child_insertion_targets(s, root)
            finally:
                C.landed_raw_pins = orig

    def test_option_absent_is_byte_identical_and_strict(self):
        s, domains = fixture()
        self.assertNotIn(D.CHILD_INS, D.dependencies(s))
        self.assertEqual(D.child_insertion_tcl(s, ROOT), [])
        s, domains = self.spec()
        with tempfile.TemporaryDirectory() as temp:
            root = child_root(temp)
            for key, value in [('child_insertion', 'lib_max'), ('macro_pin_leaf', False), ('symmetric', False)]:
                b = copy.deepcopy(s)
                b['domain_spatial_spine'][key] = value
                with self.subTest(key=key), self.assertRaises(ValueError):
                    D.validate(b, domains, root)

    def test_tcl_wrapper_offsets_only_child_pin_leaves(self):
        base = DSCI_TCL.replace('HELPER', '{' + str(ROOT / D.CHILD_INS) + '}')
        good = base.replace('ENVLINE', 'set ::env(OT_SPINE_MACRO_LEAF) 1; set ::env(OT_SPINE_MACRO_PIN_LEAF) 1')
        p = subprocess.run(['tclsh'], input=good, text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(p.stderr, p.stderr)
        self.assertIn('DSCI_WRAPPER PASS', p.stdout)
        q = subprocess.run(['tclsh'], input=base.replace('ENVLINE', 'set ::env(OT_SPINE_MACRO_LEAF) 1'),
                           text=True, capture_output=True)
        self.assertIn('OT_DSCI: child insertion requires OT_SPINE_MACRO_LEAF=1 and OT_SPINE_MACRO_PIN_LEAF=1',
                      q.stdout + q.stderr)


if __name__ == '__main__':
    unittest.main()
