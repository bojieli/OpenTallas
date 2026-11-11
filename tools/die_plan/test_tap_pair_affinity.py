"""QC-TYPES-6 11-07: pure tests of the default-off short-pair tap affinity planner (tap_pair_plan.tcl)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLAN = Path(__file__).with_name('tap_pair_plan.tcl')
TCLSH = shutil.which('tclsh')
pytestmark = pytest.mark.skipif(TCLSH is None, reason='tclsh not installed')


def run(regs, pairs, taps, load=None, cap=100, radius=10**6, limit=64, passes=20, merge=0, shift=0, grow=0):
    """regs {name: (x, y, tap)}; pairs [(a, b)]; taps {tap: (x, y)} -> ({name: tap}, passes)."""
    load = load or {k: sum(1 for r in regs.values() if r[2] == k) for k in taps}
    r = ' '.join(f'{{{n}}} {{opaque {x} {y} {tp}}}' for n, (x, y, tp) in regs.items())
    p = ' '.join(f'{{{e[2] if len(e) > 2 else 1} {e[0]} {e[1]}}}' for e in pairs)
    tx = ' '.join(f'{k} {{{x} {y}}}' for k, (x, y) in taps.items())
    ld = ' '.join(f'{k} {v}' for k, v in load.items())
    script = (f'source {{{PLAN}}}\n'
              f'set res [::ot_tap_pair::plan [dict create {r}] [list {p}] [dict create {tx}] [dict create {ld}] '
              f'{cap} {radius} {limit} {passes} {merge} {shift} {grow}]\n'
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
    return sum(lab[e[0]] != lab[e[1]] for e in pairs)


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


SHIFT_TAPS = {'t0': (0, 0), 't1': (4, 0), 't2': (3, 0)}


def shift_case():
    # frozen X (t0) - single s (own tap t2) - frozen Y (t1).  Label propagation sees a 1:1 tie and takes the nearer
    # tap t1, leaving the unavoidable cut on the 1-um x2-s pair; the shift moves it onto the 10-um s-y0 pair.
    regs = {f'x{i}': (i, 0, 't0') for i in range(3)}
    regs.update({f'y{i}': (5 + i, 0, 't1') for i in range(3)})
    regs['s'] = (3, 0, 't2')
    pairs = [('x0', 'x1', 1), ('x1', 'x2', 1), ('x2', 's', 1), ('s', 'y0', 10), ('y0', 'y1', 1), ('y1', 'y2', 1)]
    return regs, pairs


def test_shift_moves_the_cut_to_the_longest_pair():
    regs, pairs = shift_case()
    lab, _ = run(regs, pairs, SHIFT_TAPS, limit=2, shift=0)
    assert lab['s'] == 't1' and cross(lab, pairs) == 1
    lab, passes = run(regs, pairs, SHIFT_TAPS, limit=2, shift=5)
    assert lab['s'] == 't0' and cross(lab, pairs) == 1 and 'shift' in passes


def test_shift_never_breaks_a_coherent_pair():
    regs, pairs = shift_case()
    regs['s'] = (3, 0, 't1')  # s-y0 same tap at the start: coherent, the cut must stay on x2-s
    lab, _ = run(regs, pairs, SHIFT_TAPS, limit=2, shift=5)
    assert lab['s'] == lab['y0'] and cross(lab, pairs) == 1


def test_overfull_initial_tap_is_accepted_and_only_donates():
    # DIE-QC-97 11-09 (QC cbn_q00 clk_t11, slw_su_c): clock_taps.tcl may leave a tap above OT_TAP_MAX_SINKS (WARN,
    # no tap with room in radius); the planner must accept it, never add to it, and may move sinks off it.
    regs = {f'a{i}': (i, 0, 't0') for i in range(4)}
    regs['b'] = (10, 0, 't1')
    pairs = [('a3', 'b')]
    lab, _ = run(regs, pairs, CHAIN_TAPS, load={'t0': 4, 't1': 1}, cap=3, limit=2)
    assert lab['b'] == 't1'                              # t0 is above cap: it receives nothing
    assert sum(v == 't0' for v in lab.values()) <= 4
    regs['b'] = (10, 0, 't0')
    regs['a3'] = (9, 0, 't1')
    lab, _ = run(regs, pairs, CHAIN_TAPS, load={'t0': 4, 't1': 1}, cap=3, limit=2)
    assert lab['b'] == 't1' and cross(lab, pairs) == 0   # b leaves the over-full tap for its partner


def test_missing_or_negative_initial_load_still_fails():
    for ld in ('t0 1', 't0 1 t1 -1', 't0 1 t1 x'):
        script = (f'source {{{PLAN}}}\n'
                  'puts [catch {::ot_tap_pair::plan [dict create a {o 0 0 t0} b {o 10 0 t1}] {} '
                  f'[dict create t0 {{0 0}} t1 {{10 0}}] [dict create {ld}] 3 100 2 5}} msg]\nputs $msg\n')
        out = subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.split('\n')
        assert out[0] == '1' and 'initial tap capacity invalid: t1' in out[1], (ld, out)


def overfull_boundary(n=8):
    # DIE-QC-97 11-10 (QC sle_hc0 density taps, 8 of 15 above cap): n short pairs p_i -> r_i, 1.5 um apart, straddle
    # the boundary of two over-full taps (p on t0, r on t1).  Each pair is its own 2-register component.
    regs = {}
    for i in range(n):
        regs[f'p{i}'] = (4, i, 't0')
        regs[f'r{i}'] = (5.5, i, 't1')
    pairs = [(f'p{i}', f'r{i}') for i in range(n)]
    taps = {'t0': (0, 0), 't1': (10, 0)}
    load = {'t0': 100, 't1': 100}         # both far above cap 10
    return regs, pairs, taps, load


def test_overfull_boundary_stays_cut_without_growth():
    regs, pairs, taps, load = overfull_boundary()
    lab, _ = run(regs, pairs, taps, load=load, cap=10, limit=2)
    assert cross(lab, pairs) == len(pairs)          # donate-only: no side may receive


def test_overfull_growth_joins_every_boundary_pair_within_bound():
    regs, pairs, taps, load = overfull_boundary()
    lab, _ = run(regs, pairs, taps, load=load, cap=10, limit=2, grow=0.1)
    assert cross(lab, pairs) == 0
    for t, l0 in load.items():
        moved_in = sum(1 for n, tp in lab.items() if tp == t and regs[n][2] != t)
        moved_out = sum(1 for n, tp in lab.items() if tp != t and regs[n][2] == t)
        assert l0 + moved_in - moved_out <= l0 + int(l0 * 0.1)


def test_overfull_growth_is_bounded():
    # r_i sit 8 um from t0 (radius 7): only the p_i can move, all onto t1.  Growth 0.02 of 100 = 2 sinks, so exactly
    # two pairs join and t1 ends at 102.
    regs, pairs, taps, load = overfull_boundary()
    for i in range(len(pairs)):
        regs[f'r{i}'] = (8, i, 't1')
    lab, _ = run(regs, pairs, taps, load=load, cap=10, radius=7, limit=2, grow=0.02)
    assert len(pairs) - cross(lab, pairs) == 2
    for t, l0 in load.items():
        final = l0 + sum(1 for n, tp in lab.items() if tp == t and regs[n][2] != t) \
            - sum(1 for n, tp in lab.items() if tp != t and regs[n][2] == t)
        assert final <= l0 + 2


def test_overfull_growth_never_lets_an_under_cap_tap_exceed_cap():
    regs, pairs, taps, _ = overfull_boundary(4)
    lab, _ = run(regs, pairs, taps, load={'t0': 9, 't1': 9}, cap=10, limit=2, grow=0.5)
    for t in taps:
        final = 9 + sum(1 for n, tp in lab.items() if tp == t and regs[n][2] != t) \
            - sum(1 for n, tp in lab.items() if tp != t and regs[n][2] == t)
        assert final <= 10


def test_overfull_growth_rejects_out_of_range():
    for g in ('-0.1', '0.6', 'x'):
        script = (f'source {{{PLAN}}}\n'
                  'puts [catch {::ot_tap_pair::plan [dict create a {o 0 0 t0} b {o 10 0 t1}] {} '
                  f'[dict create t0 {{0 0}} t1 {{10 0}}] [dict create t0 1 t1 1] 3 100 2 5 0 0 {g}}} msg]\nputs $msg\n')
        out = subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.split('\n')
        assert out[0] == '1' and 'invalid overfull growth' in out[1], (g, out)


def test_overfull_grow_export_is_opt_in_and_bounded():
    sys.path.insert(0, str(Path(__file__).parent))
    from gen_phys import tap_pair_affinity_exports
    base = {'tap_radius_um': 200, 'tap_max_sinks': 1200}
    lines = tap_pair_affinity_exports({'clock': dict(base, tap_pair_affinity={})})
    assert not any('OVERFULL' in x for x in lines)
    lines = tap_pair_affinity_exports({'clock': dict(base, tap_pair_affinity={'overfull_grow': 0.1})})
    assert 'export OT_TAP_PAIR_OVERFULL_GROW = 0.1' in lines
    with pytest.raises(ValueError):
        tap_pair_affinity_exports({'clock': dict(base, tap_pair_affinity={'overfull_grow': 0.6})})


# ---------------- DIE-QC-97 11-11 CHAINS: tap_chain_affinity-owned delay-pad chains join the pair graph ----------------
def tcl(body):
    res = subprocess.run([TCLSH], input=f'source {{{PLAN}}}\n{body}\n', capture_output=True, text=True, check=True)
    return res.stdout.strip().splitlines()


def ident_dict(rows):
    """rows [(name, prefix, stage, bit)] -> a tcl dict literal."""
    return '[dict create ' + ' '.join(f'{{{n}}} {{{p} {s} {b}}}' for n, p, s, b in rows) + ']'


def chain_rows(tag, n=4, prefix=None):
    """stages 0..n-1 of one scalar delay-pad chain plus its terminal stage."""
    pre = prefix or f'u_pd10_{tag}.r'
    return [(f'{tag}_s{i}', pre, str(i), 'scalar') for i in range(n)] + [(f'{tag}_t', pre, 'terminal', 'scalar')]


def test_chain_bonds_link_consecutive_stages_and_the_terminal():
    rows = chain_rows('a', 3) + chain_rows('b', 2) + [('g0', 'u_pd9_g.r', '0', 'scalar'), ('g2', 'u_pd9_g.r', '2', 'scalar')]
    out = tcl(f'foreach e [::ot_tap_pair::chain_bonds {ident_dict(rows)}] {{puts $e}}')
    assert sorted(out) == sorted(['0 a_s0 a_s1', '0 a_s1 a_s2', '0 a_s2 a_t', '0 b_s0 b_s1', '0 b_s1 b_t'])   # no gap bond g0-g2


def test_skip_chain_owned_is_todays_rule_when_chains_is_off():
    f = lambda c, a, i: tcl(f'puts [::ot_tap_pair::skip_chain_owned {c} {a} {{{i}}}]')[0]
    assert f(0, 1, 'p 1 scalar') == '1'                                   # chain affinity on, owned flop: left alone (today)
    assert f(1, 1, 'p 1 scalar') == '0'                                   # chains on: joins the pair graph
    assert f(0, 0, 'p 1 scalar') == '0' and f(0, 1, '') == '0'            # chain affinity off / not a chain flop: never skipped


CH_TAPS = {'t0': (0, 0), 't1': (30, 0), 't2': (60, 0)}


def chain_case(split=False):
    """producer p -> chain a_s0..a_s3 -> a_t -> consumer q; the chain and p share t0, q sits on t1 (the 2.2-um hold hop)."""
    regs = {'p': (0, 0, 't0')}
    for i in range(4):
        regs[f'a_s{i}'] = (1 + i, 0, 't1' if (split and i >= 2) else 't0')
    regs['a_t'] = (5, 0, 't1' if split else 't0')
    regs['q'] = (6, 0, 't1')
    pairs = [('p', 'a_s0', 1)] + [(f'a_s{i}', f'a_s{i + 1}', 1) for i in range(3)] + [('a_s3', 'a_t', 1), ('a_t', 'q', 1)]
    return regs, pairs


def chain_bond_edges(regs):
    names = [n for n in regs if n.startswith('a_')]
    rows = [(n, 'u_pd10_a.r', 'terminal' if n == 'a_t' else n[3:], 'scalar') for n in names]
    out = tcl(f'foreach e [::ot_tap_pair::chain_bonds {ident_dict(rows)}] {{puts $e}}')
    return [(e.split()[1], e.split()[2], 0) for e in out]


def test_chain_and_consumer_land_on_one_tap_and_the_chain_stays_whole():
    regs, pairs = chain_case()
    # today: the chain flops are not in the pair graph, so the consumer has no partner and keeps its tap (the a_t -> q hop
    # stays cross-tap)
    lab0, _ = run({n: regs[n] for n in ('p', 'q')}, [], CH_TAPS, merge=128)
    assert lab0['q'] != regs['a_t'][2]
    lab, _ = run(regs, pairs + chain_bond_edges(regs), CH_TAPS, merge=128)
    assert cross(lab, pairs) == 0
    assert len({lab[n] for n in ['p', 'a_s0', 'a_s1', 'a_s2', 'a_s3', 'a_t', 'q']}) == 1


def test_a_split_chain_is_joined_never_split_further():
    regs, pairs = chain_case(split=True)
    ident = ident_dict([(n, 'u_pd10_a.r', 'terminal' if n == 'a_t' else n[3:], 'scalar') for n in regs if n.startswith('a_')])
    before = ' '.join(f'{{{n}}} {{o 0 0 {tp}}}' for n, (x, y, tp) in regs.items())
    lab, _ = run(regs, pairs + chain_bond_edges(regs), CH_TAPS, merge=128)
    after = ' '.join(f'{{{n}}} {{o 0 0 {lab[n]}}}' for n in regs)
    rep = tcl(f'puts [::ot_tap_pair::chain_tap_report {ident} [dict create {before}] [dict create {after}]]')[0]
    assert rep == '1 0 1 0'                                                 # one chain: split before, one tap after, none broken
    assert len({lab[n] for n in regs}) == 1


def test_other_chains_are_untouched_and_the_plan_is_idempotent():
    regs, pairs = chain_case()
    # chain b (all on t2 with its consumer) and a lone pair on t1: coherent, no cross pair, must not move
    for i in range(4):
        regs[f'b_s{i}'] = (61 + i, 0, 't2')
    regs['b_t'] = (65, 0, 't2'); regs['bq'] = (66, 0, 't2')
    bp = [(f'b_s{i}', f'b_s{i + 1}', 1) for i in range(3)] + [('b_s3', 'b_t', 1), ('b_t', 'bq', 1)]
    bonds = chain_bond_edges(regs) + [(f'b_s{i}', f'b_s{i + 1}', 0) for i in range(3)] + [('b_s3', 'b_t', 0)]
    lab, _ = run(regs, pairs + bp + bonds, CH_TAPS, merge=128)
    assert all(lab[n] == 't2' for n in regs if n.startswith('b'))
    assert len({lab[n] for n in ['p', 'q'] + [n for n in regs if n.startswith('a_')]}) == 1
    # idempotent: planning again from the result moves nothing
    regs2 = {n: (regs[n][0], regs[n][1], lab[n]) for n in regs}
    lab2, passes = run(regs2, pairs + bp + bonds, CH_TAPS, merge=128)
    assert lab2 == lab


def test_chains_export_is_opt_in():
    sys.path.insert(0, str(Path(__file__).parent))
    from gen_phys import tap_pair_affinity_exports
    base = {'tap_radius_um': 200, 'tap_max_sinks': 1200}
    off = tap_pair_affinity_exports({'clock': dict(base, tap_pair_affinity={})})
    assert tap_pair_affinity_exports({'clock': dict(base)}) == []
    assert not any('CHAINS' in x for x in off)
    assert tap_pair_affinity_exports({'clock': dict(base, tap_pair_affinity={'chains': False})}) == off
    on = tap_pair_affinity_exports({'clock': dict(base, tap_pair_affinity={'chains': True})})
    assert on == off + ['export OT_TAP_PAIR_CHAINS = 1']
    with pytest.raises(ValueError):
        tap_pair_affinity_exports({'clock': dict(base, tap_pair_affinity={'chains': 1})})


def test_chains_key_is_in_the_schema():
    import json

    def find(o):
        if isinstance(o, dict):
            if 'tap_pair_affinity' in o and isinstance(o['tap_pair_affinity'], dict):
                return o['tap_pair_affinity']
            for v in o.values():
                r = find(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = find(v)
                if r:
                    return r
    spec = find(json.loads(Path(__file__).with_name('die_plan.schema.json').read_text()))
    assert spec['additionalProperties'] is False and spec['properties']['chains'] == {'type': 'boolean'}
