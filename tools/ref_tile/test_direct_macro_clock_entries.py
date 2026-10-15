"""Source-bound SRAM admission and real OpenROAD/Liberty clock-wire probe.

The SPEF is an explicit nonzero-RC test fixture, not routed-layout evidence.
Run remote heavy probe with --openroad-probe OUT via ot-run.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import direct_macro_clock_entries as D

ROOT = Path(__file__).resolve().parents[2]
MASTER = 'ot_sram_1r1w_32x546_m1'
VIEW = f'physical/asap7_memory_macros/{MASTER}'


def spec():
    return dict(clock='entries', clock_ports=['ca', 'cb'], macros=[
        dict(view=VIEW, inst=f'u_{i}', count=1,
             clock_entry=dict(port=p, pin='clk', reference='raw_liberty_clock_pin'))
        for i, p in enumerate(('ca', 'cb'))])


class Admission(unittest.TestCase):
    def test_real_macro_all_corners(self):
        result = D.load(spec(), ROOT)
        self.assertEqual(len(result['entries']), 2)
        self.assertEqual(result['entries'][0]['dimensions_um'], [177.768, 81.0])
        self.assertIn('ot_ce_direct_rows', result['bindings_tcl'])

    def test_full_entry_generator_counts_real_raw_macro_pins(self):
        import clock_entry_constraints as C
        s=spec();s.update(kind='cluster',clock_port='ca',children=[])
        generated=C.generate(s,ROOT)
        self.assertIn('foreach row [ot_ce_direct_rows $corner]',generated)
        self.assertIn('set ::ot_ce_direct_masters',generated)
        self.assertNotIn('set_false_path',generated)
        s['clock_ports'].append('extra')
        with self.assertRaisesRegex(ValueError,'bound child clock pins'):C.generate(s,ROOT)

    def test_bad_identity_and_policy(self):
        for field, value in [('port', 'unknown'), ('pin', 'r_ce_in'), ('reference', 'ETM')]:
            with self.subTest(field=field):
                s = spec(); s['macros'][0]['clock_entry'][field] = value
                with self.assertRaises(ValueError): D.load(s, ROOT)
        s = spec(); s['clock_cts_roots'] = ['ca']
        with self.assertRaises(ValueError): D.load(s, ROOT)
        s = spec(); s['macros'][0]['count'] = 2
        with self.assertRaises(ValueError): D.load(s, ROOT)

    def test_actual_source_mutants(self):
        mutations = [('clock : true', 'clock : false'),
                     ('timing_type : hold_rising', 'timing_type : recovery_rising'),
                     (f'library ({MASTER}_ff)', f'library ({MASTER}_tt)')]
        for old, new in mutations:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); dest = root/VIEW
                shutil.copytree(ROOT/VIEW, dest)
                for path in dest.glob('*.lib'):
                    path.write_text(path.read_text().replace(old, new))
                with self.assertRaises(ValueError): D.load(spec(), root)


def probe(out):
    import clock_entry_constraints as C
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    s = spec(); s.update(clock_port='ca',kind='cluster',children=[])
    generated = D.load(s, ROOT)
    (out/'source_manifest.json').write_text(json.dumps(generated['entries'], indent=2)+'\n')
    (out/'probe.v').write_text('module probe(input ca, cb, en, output [545:0] qa,qb);\n' +
        '\n'.join(f'{MASTER} u_{i}(.clk({p}),.r_ce_in(en),.rd_out(q{p[-1]}));'
                  for i,p in enumerate(('ca','cb'))) + '\nendmodule\n')
    spef = ['*SPEF "IEEE 1481-1998"','*DESIGN "probe"','*DATE "2026-10-15"',
            '*VENDOR "OpenTallas"','*PROGRAM "direct-macro-fixture"','*VERSION "1"',
            '*DESIGN_FLOW "PIN_CAP NONE"','*DIVIDER /','*DELIMITER :','*BUS_DELIMITER [ ]',
            '*T_UNIT 1 PS','*C_UNIT 1 FF','*R_UNIT 1 OHM','*L_UNIT 1 HENRY']
    for i,p in enumerate(('ca','cb')):
        spef += [f'*D_NET {p} 10','*CONN',f'*P {p} I',f'*I u_{i}:clk I',
                 '*CAP',f'1 {p} 5',f'2 u_{i}:clk 5','*RES',
                 f'1 {p} u_{i}:clk {1000*(i+1)}','*END']
    (out/'probe.spef').write_text('\n'.join(spef)+'\n')
    receipts = []
    for corner in D.CORNERS:
        base = 'read_lef {/OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef}\n'
        base += f'read_lef {{{ROOT/VIEW}/{MASTER}.lef}}\n'
        base += f'read_liberty {{{ROOT/VIEW}/{MASTER}_{corner}.lib}}\n'
        base += f'read_verilog {{{out}/probe.v}}\nlink_design probe\n'
        base += C.clocks(s, 833.333)
        base += f'read_spef {{{out}/probe.spef}}\nset_propagated_clock [get_clocks ot_entry_*]\n'
        base += 'set_input_delay 0 -clock core_clk [get_ports en]\nset_output_delay 0 -clock core_clk [get_ports q*]\n'
        integrated = base + 'set ::ot_ce_require_wire 1\n' + C.generate(s,ROOT) + f'\nputs INTEGRATED_RAW_MACRO_PASS_{corner}\n'
        base += C.BODY[:C.BODY.index('# Match ck_insertion.py')]
        base += generated['bindings_tcl']
        base += 'set ::ot_ce_ports {ca cb}\nset ::ot_ce_cts_roots {}\n'
        base += 'set ::ot_ce_source_domains {ca core cb core}\nset ::ot_ce_domains {core {clock core_clk}}\nset ::ot_ce_require_wire 1\n'
        checks = r'''
sta::worst_slack_cmd max
set rows [ot_ce_direct_rows CORNER]
if {[llength $rows] != 2} {error "probe missing rows"}
set phi 0; set wires {}
foreach row $rows {
  lassign $row port pin wire lo mean hi clock ttmean domain
  if {$wire <= 0 || $mean != 0 || $lo != 0 || $hi != 0} {error "probe incorrect raw pin algebra"}
  lappend wires $wire; set phi [expr {max($phi,$wire)}]
}
if {abs([lindex $wires 0]-[lindex $wires 1]) < 1} {error "probe failed to measure unequal RC wires"}
set before {}
foreach row $rows {
  lassign $row port pin wire lo mean hi clock
  set paths [find_timing_paths -from $pin -to [all_outputs] -path_delay max -group_path_count 1]
  if {![llength $paths]} {error "probe missing real SRAM clock-to-Q path"}
  lappend before [get_property [lindex $paths 0] slack]
  set_clock_latency -source [expr {$phi-$wire}] $clock
}
sta::worst_slack_cmd max
set i 0
foreach row $rows {
  lassign $row port pin wire lo mean hi clock
  set actual [ot_ce_clock_wire $pin $clock]
  if {abs($actual-$phi)>0.02} {error "probe source balancing failed $actual != $phi"}
  set paths [find_timing_paths -from $pin -to [all_outputs] -path_delay max -group_path_count 1]
  set after [get_property [lindex $paths 0] slack]
  if {abs($after-[lindex $before $i]+($phi-$wire))>0.02} {error "probe modified internal SRAM arcs"}
  incr i
}
puts "RAW_MACRO_PROBE_PASS CORNER wires=$wires phi=$phi SRAM-clock-to-Q-arcs-retained"
'''.replace('CORNER', corner)
        for kind in ('pass', 'wrong_source', 'wrong_corner', 'integrated'):
            script = base
            if kind == 'wrong_source':
                script += 'set e [lindex $::ot_ce_direct_entries 0]; lset e 2 cb; lset ::ot_ce_direct_entries 0 $e\n'
            if kind == 'wrong_corner':
                script += 'set e [lindex $::ot_ce_direct_entries 0]; lset e 4 {tt wrong ff wrong ss wrong}; lset ::ot_ce_direct_entries 0 $e\n'
            script = integrated if kind == 'integrated' else script + checks + '\nexit\n'
            path = out/f'{corner}_{kind}.tcl'; path.write_text(script)
            result = subprocess.run([os.environ.get('OPENROAD', 'openroad'),'-exit',str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (out/f'{corner}_{kind}.log').write_text(result.stdout)
            ok = result.returncode == 0 and (f'INTEGRATED_RAW_MACRO_PASS_{corner}' if kind == 'integrated' else f'RAW_MACRO_PROBE_PASS {corner}') in result.stdout
            if (kind in ('pass','integrated')) != ok:
                raise RuntimeError(f'{corner}/{kind}: unexpected status {result.returncode}\n{result.stdout[-3000:]}')
            if kind not in ('pass','integrated') and 'OT_DIRECT_MACRO:' not in result.stdout:
                raise RuntimeError('mutant did not fail in actual ownership/corner guard')
            receipts.append(dict(corner=corner, kind=kind, returncode=result.returncode, expected=(kind in ('pass','integrated'))))
    (out/'receipt.json').write_text(json.dumps(receipts, indent=2)+'\n')
    print('RAW_MACRO_PROBE_SUITE_PASS all three corners, source/corner mutants rejected')


if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1] == '--openroad-probe': probe(sys.argv[2])
    else: unittest.main()
