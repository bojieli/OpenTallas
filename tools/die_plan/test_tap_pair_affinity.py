"""QC-TYPES-6 11-07: pure tests of the default-off short-pair tap affinity planner (tap_pair_plan.tcl)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLAN = Path(__file__).with_name('tap_pair_plan.tcl')
TCLSH = shutil.which('tclsh')
pytestmark = pytest.mark.skipif(TCLSH is None, reason='tclsh not installed')


def run(regs, pairs, taps, load=None, cap=100, radius=10**6, limit=64, passes=20, merge=0):
    """regs {name: (x, y, tap)}; pairs [(a, b)]; taps {tap: (x, y)} -> ({name: tap}, passes)."""
    load = load or {k: sum(1 for r in regs.values() if r[2] == k) for k in taps}
    r = ' '.join(f'{{{n}}} {{opaque {x} {y} {tp}}}' for n, (x, y, tp) in regs.items())
    p = ' '.join(f'{{1 {a} {b}}}' for a, b in pairs)
    tx = ' '.join(f'{k} {{{x} {y}}}' for k, (x, y) in taps.items())
    ld = ' '.join(f'{k} {v}' for k, v in load.items())
    script = (f'source {{{PLAN}}}\n'
              f'set res [::ot_tap_pair::plan [dict create {r}] [list {p}] [dict create {tx}] [dict create {ld}] '
              f'{cap} {radius} {limit} {passes} {merge}]\n'
              'dict for {n row} [dict get $res regs] {puts "REG $n [lindex $row 3]"}\n'
              'puts "PASSES [dict get $res passes]"\n')
    res = subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True)
    out = {}
    passes = ''
    for line in res.stdout.splitlines():
        if line.startswith('REG '):
            _, n, tap = line.split()
            out[n] = tap
        elif line.startswith('PASSES '):
            passes = line[7:]
    return out, passes


def cross(lab, pairs):
    return sum(lab[a] != lab[b] for a, b in pairs)


CHAIN_TAPS = {'t0': (0, 0), 't1': (10, 0)}


def chain():
    # two coherent groups larger than the label-propagation group limit (frozen, as the 7 oversized components on
    # QC hc2) joined by one cross pair: label propagation can move neither
    regs = {f'x{i}': (i, 0, 't0') for i in range(3)}
    regs.update({f'y{i}': (3 + i, 0, 't1') for i in range(3)})
    pairs = [('x0', 'x1'), ('x1', 'x2'), ('x2', 'y0'), ('y0', 'y1'), ('y1', 'y2')]
    return regs, pairs


def test_frozen_groups_stall_without_merge():
    regs, pairs = chain()
    lab, _ = run(regs, pairs, CHAIN_TAPS, limit=2)
    assert cross(lab, pairs) == 1


def test_merge_puts_whole_component_on_one_tap():
    regs, pairs = chain()
    lab, passes = run(regs, pairs, CHAIN_TAPS, limit=2, merge=8)
    assert cross(lab, pairs) == 0 and len(set(lab.values())) == 1
    assert 'merge' in passes


def test_merge_respects_component_limit():
    regs, pairs = chain()
    lab, _ = run(regs, pairs, CHAIN_TAPS, limit=2, merge=4)
    assert cross(lab, pairs) == 1


def test_merge_respects_capacity_and_radius():
    regs, pairs = chain()
    # both taps nearly full: neither can take 3 movers
    lab, _ = run(regs, pairs, CHAIN_TAPS, load={'t0': 9, 't1': 9}, cap=10, limit=2, merge=8)
    assert cross(lab, pairs) == 1
    # radius 4: x0 is 10 from t1 and y2 is 5 from t0, so no tap is within reach of every member
    lab, _ = run(regs, pairs, CHAIN_TAPS, radius=4, limit=2, merge=8)
    assert cross(lab, pairs) == 1


def test_merge_never_cuts_a_coherent_pair():
    # a-b coherent on t0, b-c cross; c-d-e coherent on t1 (bigger) -> component moves to t1, a-b stay together
    regs = {'a': (0, 0, 't0'), 'b': (1, 0, 't0'), 'c': (2, 0, 't1'), 'd': (3, 0, 't1'), 'e': (4, 0, 't1')}
    pairs = [('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'e')]
    lab, _ = run(regs, pairs, CHAIN_TAPS, merge=8)
    assert lab['a'] == lab['b'] and cross(lab, pairs) == 0 and lab['a'] == 't1'


def test_exports_are_opt_in_and_bounded():
    sys.path.insert(0, str(Path(__file__).parent))
    from gen_phys import tap_pair_affinity_exports
    assert tap_pair_affinity_exports({'clock': {}}) == []
    lines = tap_pair_affinity_exports({'clock': {'tap_radius_um': 200, 'tap_max_sinks': 1200, 'tap_pair_affinity': {}}})
    assert 'export OT_TAP_PAIR_AFFINITY = 1' in lines and 'export OT_TAP_PAIR_MERGE = 128' in lines
    for spec in [{'radius_um': 201}, {'max_group': 1201}, {'merge_max': 1}, {'depth': 5}]:
        with pytest.raises(ValueError):
            tap_pair_affinity_exports({'clock': {'tap_radius_um': 200, 'tap_max_sinks': 1200, 'tap_pair_affinity': spec}})
