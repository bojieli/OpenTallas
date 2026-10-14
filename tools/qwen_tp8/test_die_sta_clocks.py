#!/usr/bin/env python3
"""Regression fixture and optional actual OpenSTA probe (run heavy probe via ot-run).
python3 test_die_sta_clocks.py --fixture /tmp/probe
Then mount that directory at /work in openroad/orfs:asap7lock and run probe.tcl.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_libs as D


def fixture(out):
    out.mkdir(parents=True, exist_ok=True)
    D.E.write_lib('tt', {'A': {'ck': 1, 'd': 1, 'q': 1}, 'B': {'ck': 1, 'd': 1, 'q': 1}}, {m: {'q': ['output', 0, set()]} for m in ['A', 'B']}, out / 'probe.lib')
    text = (out / 'probe.lib').read_text()
    # Use the actual ETM min/max clock-tree Liberty arc types.
    for master, r in [('A', 100), ('B', 300)]:
        start = text.index(f'  cell ({master})')
        at = text.index('clock : true; capacitance : 2.0; }', start)
        tree = '\n'.join(f'timing () {{ timing_type : {kind}_clock_tree_path; cell_rise (load1) {{ index_1 ("1, 2"); values ("{r}, {r}"); }} cell_fall (load1) {{ index_1 ("1, 2"); values ("{r}, {r}"); }} }}' for kind in ['min', 'max'])
        text = text[:at] + text[at:].replace('clock : true; capacitance : 2.0; }', 'clock : true; capacitance : 2.0;\n' + tree + '\n}', 1)
    (out / 'probe.lib').write_text(text)
    (out / 'probe.v').write_text('module probe(input ck, input d, output q); wire n; A a(.ck(ck),.d(q),.q(n)); B b(.ck(ck),.d(n),.q(q)); endmodule\n')
    leaves = {'A': {'tt': {'ck': 100}}, 'B': {'tt': {'ck': 300}}}
    doms = {'stream': [('a/ck', 'A', 'ck'), ('b/ck', 'B', 'ck')]}
    (out / 'clocks.tcl').write_text(D.clock_tcl(doms, leaves, 'tt'))
    (out / 'probe.lef').write_text('VERSION 5.8 ;\n' + ''.join(f'MACRO {m}\n CLASS BLOCK ;\n ORIGIN 0 0 ;\n SIZE 10 BY 10 ;\n' + ''.join(f' PIN {p}\n DIRECTION {d} ;\n USE SIGNAL ;\n PORT\n LAYER M2 ;\n RECT 1 1 2 2 ;\n END\n END {p}\n' for p, d in [('ck','INPUT'),('d','INPUT'),('q','OUTPUT')]) + f'END {m}\n' for m in ['A','B']) + 'END LIBRARY\n')
    early = {'A': {'tt': {'ck': 100}}, 'B': {'tt': {'ck': 400}}}
    (out / 'early.tcl').write_text(D.clock_tcl(doms, early, 'tt'))
    (out / 'probe.tcl').write_text('''read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /work/probe.lef
read_liberty /work/probe.lib
read_verilog /work/probe.v
link_design probe
set_cmd_units -time ps
create_clock -name stream -period 833.333 [get_pins {a/ck b/ck}]
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 150 [all_clocks]
set_clock_uncertainty -hold 100 [all_clocks]
puts BASELINE
set baseline [get_property [lindex [find_timing_paths -from a/q -to b/d -path_delay max] 0] slack]
report_checks -from a/q -to b/d -path_delay max -format full_clock_expanded -digits 3
source /work/clocks.tcl
puts COMPENSATED
set compensated [get_property [lindex [find_timing_paths -from a/q -to b/d -path_delay max] 0] slack]
puts "SOURCE_LATENCY_DELTA [expr {$compensated - $baseline}]"
if {abs($compensated - $baseline + 200.0) > 0.001} {error "source compensation did not change setup slack by -200ps"}
report_checks -from a/q -to b/d -path_delay max -format full_clock_expanded -digits 3
report_checks -from a/q -to b/d -path_delay min -format full_clock_expanded -digits 3
set backward [get_property [lindex [find_timing_paths -from b/q -to a/d -path_delay max] 0] slack]
source /work/early.tcl
puts RELATED_EARLY_LEVEL
set forward_early [get_property [lindex [find_timing_paths -from a/q -to b/d -path_delay max] 0] slack]
set backward_early [get_property [lindex [find_timing_paths -from b/q -to a/d -path_delay max] 0] slack]
if {abs($forward_early - $compensated + 160) > 0.001} {error "forward early budget: expected -100 phase -60 uncertainty"}
if {abs($backward_early - $backward - 40) > 0.001} {error "backward early budget: expected +100 phase -60 uncertainty"}
report_checks -from a/q -to b/d -path_delay max -format full_clock_expanded -digits 3
report_checks -from b/q -to a/d -path_delay max -format full_clock_expanded -digits 3
puts PAIR_BUDGET_ASSERTIONS_PASS
exit
''')


def test():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        # Multiclock mapping must use each independently measured corner.
        lib = p / 'leaf.lib'
        lib.write_text('''library (l) {
 time_unit : "1ps";
 cell (leaf) {
 pin (ck) {
 direction : input;
 clock : true;
 timing () {
 timing_type : max_clock_tree_path;
 cell_rise (t) {
 values ("100");
 }
 }
 }
 }
}
''')
        ins = p / 'insertion.json'
        ins.write_text(json.dumps({'clock': 'ck', **{c: {'boundary': {'mean': r, 'n': 2}} for c, r in [('tt', 110), ('ff', 80), ('ss', 160)]}}))
        for c, r in [('tt', 110), ('ff', 80), ('ss', 160)]:
            assert D.measured_clock_refs(lib, ins, c) == {'ck': r}
        ins.unlink()
        try:
            D.measured_clock_refs(lib, ins, 'tt')
            raise AssertionError('missing insertion accepted')
        except ValueError:
            pass
        ins.write_text('{"clock":"ck","tt":{"boundary":{"mean":110}}}')
        try:
            D.measured_clock_refs(lib, ins, 'ss')
            raise AssertionError('missing SS accepted')
        except ValueError:
            pass
        fixture(p)
        s = (p / 'clocks.tcl').read_text()
        assert '-100.000000' in s and '-300.000000' in s
        assert s.count('create_clock ') == 1 and 'set_propagated_clock' in s
        assert '-setup 150.000000' in s and '-hold 100.000000' in s
        deep = D.clock_tcl({'stream': [('a/ck', 'A', 'ck'), ('b/ck', 'B', 'ck')]},
                           {'A': {'tt': {'ck': 100}}, 'B': {'tt': {'ck': 301}}}, 'tt')
        assert '-setup 210.000000' in deep and '-setup 150.000000' in deep
        assert '-from [get_clocks stream] -to [get_clocks stream__early]' in deep
        assert '-from [get_clocks stream__early] -to [get_clocks stream]' in deep
        assert deep.count('create_clock ') == 2 and 'set_clock_groups' not in deep
        both_deep = D.clock_tcl({'stream': [('a/ck', 'A', 'ck'), ('b/ck', 'B', 'ck')]},
                               {'A': {'tt': {'ck': 371.2}}, 'B': {'tt': {'ck': 400}}}, 'tt')
        assert both_deep.count('create_clock ') == 1
        assert '-setup 150.000000' not in both_deep
        assert '-setup 210.000000 -from [get_clocks stream__early] -to [get_clocks stream__early]' in both_deep
        assert '-hold 100.000000' in both_deep and 'set_clock_groups' not in both_deep
        multi = D.clock_tcl({'stream': [('a/ck', 'A', 'ck'), ('b/ck', 'B', 'ck')],
                             'serial': [('c/ck', 'A', 'ck')]},
                            {'A': {'tt': {'ck': 100}}, 'B': {'tt': {'ck': 301}}}, 'tt')
        assert '-group [get_clocks {stream stream__early}]' in multi
        assert '-group [get_clocks {stream__early}]' not in multi
        assert 'set_false_path' not in s and 'set_clock_groups' not in s
        consumer = Path(__file__).resolve().parents[1] / 'qwen_kv_die/chain/sta_tcl.py'
        (p / 'clocks_ff.tcl').write_text(s.replace('COMPENSATED tt', 'COMPENSATED ff'))
        env = dict(os.environ, OT_STA_CLOCKS=str(p / 'clocks.tcl'))
        args = [sys.executable, str(consumer), 'r22k', 'ff', str(p / 'sta.tcl')]
        subprocess.run(args, env=env, check=True, capture_output=True)
        assert '# INSERTION_COMPENSATED ff' in (p / 'sta.tcl').read_text()
        assert 'set_clock_uncertainty -hold 25 [all_clocks]' not in (p / 'sta.tcl').read_text()
        assert subprocess.run(args + ['forbidden_plan.json'], env=env, capture_output=True).returncode != 0
        (p / 'clocks_ff.tcl').unlink()
        assert subprocess.run(args, env=env, capture_output=True).returncode != 0
    print('PASS: actual per-corner references, missing measurement refusal, related same-domain clocks')


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--fixture', type=Path)
    args = a.parse_args()
    test()
    if args.fixture:
        fixture(args.fixture)
