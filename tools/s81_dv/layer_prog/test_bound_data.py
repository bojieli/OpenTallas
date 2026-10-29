#!/usr/bin/env python3
"""TOK-S81-2: bound data transports (layer_prog/bound_data.py) on a synthetic die + bind, incl. mutants that MUST fail."""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from layer_prog import bound_data as BD  # noqa: E402


def link(src, dst, n, K=None, landing=None, age=None):
    landed = landing is not None
    a = (-(-n // 2) + K + 1) if landed else n / 2
    return dict(stations=n, landing=landing, internal_landing=None, K=K, E=K, src=src, dst=dst,
                age_edges=a if age is None else age, land_master=None)


class FakeDie:
    def __init__(self):
        self.die_sha = 'ab' * 32
        self.inst = {n: {} for n in ('u_a', 'u_b', 'u_c', 'u_d', 'ld_hc', 'st_cw_0', 'u_e1', 'u_e2')}
        self.links = {
            # landing removed by the bind: as-built 4 + K2+1 = 7 stages (legacy 2 + 3 = 5 cycles)
            'cw': link([('u_a', 'cw_o')], [('u_b', 'cw_i')], 4, K=2, landing='ld_cw'),
            # landing tile kept in the sink partition: bits sink at ld_hc
            'hc': link([('u_a', 'hc_o')], [('u_c', 'hc_i')], 2, K=1, landing='ld_hc'),
            # two sub-lanes of one bundle on the same ports (n 4 / 6), 2 in-instance stages each
            'x_l0': link([('u_a', 'x')], [('u_d', 'x')], 4),
            'x_l1': link([('u_a', 'x')], [('u_d', 'x')], 6),
            # both endpoints in one partition: kept as-built
            'e': link([('u_e1', 'o')], [('u_e2', 'i')], 2, K=1, landing='ld_e'),
            # dead: no die-level sink
            'dead': link([('u_a', 'q')], [], 8),
            # abutted with 3 in-instance stages, bound 2: the bind removed one the unit model counts
            'r': link([('u_b', 'r_o')], [('u_c', 'r_i')], 0, age=0),
        }


def member(sink, sport, lo, hi, source, a, b, lane):
    return dict(sink=sink, sink_part='P', src_part='Q',
                members=[dict(sink_port=sport, sink_bits=[[lo, hi]], source=source, source_bits=[[lo, hi]],
                              asbuilt_stages=a, bound_stages=b, landed_stages=b, lane=lane)])


def bind_dir(tmp, errors=0, landing=None, internal=None):
    d = Path(tmp)
    d.mkdir(parents=True, exist_ok=True)
    land = landing if landing is not None else [
        member('u_b', 'cw_i', 0, 7, 'u_a.cw_o', 7, 9, 'L_cw'),
        member('ld_hc', 'i', 0, 3, 'u_a.hc_o', 2, 4, 'L_hc'),
        member('u_d.u_in', 'x', 0, 3, 'u_a.u_x.x', 6, 10, 'L_x'),
        member('u_d.u_in', 'x', 4, 7, 'u_a.u_x.x', 8, 10, 'L_x'),
        member('u_c.u_r', 'r_i', 0, 1, 'u_b.u_s.r_o', 3, 2, 'L_r'),
    ]
    (d / 'bind_report.json').write_text(json.dumps(dict(n_errors=errors, errors=['E'] * errors, type_splits=[])))
    (d / 'provenance_bind.json').write_text(json.dumps(dict(provenance=dict(manifest='m.json'))))
    g = dict(landing=land)
    if internal:
        g['internal'] = internal
    (d / 'bus_groups.json').write_text(json.dumps(g))
    (d / 'bind_latency.json').write_text(json.dumps(dict(buses=[dict(lane=l, bound_stages=b) for l, b in
                                                                 (('L_cw', 9), ('L_hc', 4), ('L_x', 10), ('L_r', 2))])))
    (d / 'bind_names.json').write_text(json.dumps({'P.u_e1': 'u_e1', 'P.u_e2': 'u_e2', 'Q.u_a': 'u_a', 'R.u_b': 'u_b'}))
    return d


def run(tmp, **kw):
    die = FakeDie()
    B = BD.load_bind(bind_dir(Path(tmp) / 'b', **kw), diagnostic=kw.get('errors', 0) > 0)
    return die, BD.rebind_links(die, B, diagnostic=kw.get('errors', 0) > 0)


def test_ages():
    with tempfile.TemporaryDirectory() as t:
        die, rec = run(t)
        R = rec['rows']
        assert R['cw']['status'] == 'PASS' and die.links['cw']['age_edges'] == 9, R['cw']          # bound replaces 5
        assert die.links['cw']['legacy_age_edges'] == 5
        assert R['hc']['status'] == 'PASS' and die.links['hc']['age_edges'] == 3 + 4 - 1, R['hc']  # landing K+1 kept
        assert die.links['x_l0']['age_edges'] == 8 and die.links['x_l1']['age_edges'] == 8, (R['x_l0'], R['x_l1'])
        assert R['x_l0']['bundle_x'] == 2
        assert R['e']['cls'] == 'INTRA' and die.links['e']['age_edges'] == R['e']['legacy_age']
        assert R['dead']['status'] == 'BLOCKED' and R['r']['status'] == 'BLOCKED' and '< 0' in R['r']['reason']
        assert rec['verdict'] == 'BLOCKED' and rec['counts']['CROSSING_PASS'] == 4


def test_blocked_reads_fail_closed():
    with tempfile.TemporaryDirectory() as t:
        die, _ = run(t)
        for read in (lambda L: L['age_edges'], lambda L: L.get('age_edges', 0), lambda L: max([L['age_edges']])):
            try:
                read(die.links['dead'])
            except BD.BoundBlocked:
                pass
            else:
                raise AssertionError('blocked link age was readable')
        try:                                  # a lowering that swallows the error is still caught by the hit log
            die.links['r'].get('age_edges', 0)
        except Exception:
            pass
        assert die.bound_blocked_hits[-1] == 'r' and len(die.bound_blocked_hits) == 4
        assert 'age_edges' not in dict(die.links['dead']).keys() and 'legacy_age_edges' in dict(die.links['dead'])
        assert not isinstance(BD.BoundBlocked('x'), KeyError)


def test_intra_change_applied():
    with tempfile.TemporaryDirectory() as t:
        inner = [dict(source='u_e1.o', sink='u_e2.i', asbuilt_stages=3, landed_stages=5)]
        die, rec = run(t, internal=inner)
        assert die.links['e']['age_edges'] == rec['rows']['e']['legacy_age'] + 2


def test_mutant_mixed_bound_depth_blocks():
    """MUTANT: one cw bit range lands one cycle later than the rest -> the link has no single bound age"""
    with tempfile.TemporaryDirectory() as t:
        land = [member('u_b', 'cw_i', 0, 3, 'u_a.cw_o', 7, 9, 'L_cw'), member('u_b', 'cw_i', 4, 7, 'u_a.cw_o', 7, 10, 'L_cw')]
        die, rec = run(t, landing=land)
        assert rec['rows']['cw']['status'] == 'BLOCKED' and 'mixed' in rec['rows']['cw']['reason']


def test_mutant_legacy_passthrough_is_caught():
    """MUTANT: a re-ager that returns the legacy age (ignores the bind) must differ from the bound ages"""
    with tempfile.TemporaryDirectory() as t:
        die, rec = run(t)
        mutant = {k: r['legacy_age'] for k, r in rec['rows'].items() if r['status'] == 'PASS'}
        real = {k: die.links[k]['age_edges'] for k in mutant}
        assert any(mutant[k] != real[k] for k in mutant), 'legacy pass-through indistinguishable'
        assert real['cw'] != mutant['cw'] and real['x_l0'] != mutant['x_l0']


def test_mutant_bundle_stage_collision_blocks():
    """MUTANT: bundle bits whose as-built stages fit no single common in-instance count"""
    with tempfile.TemporaryDirectory() as t:
        land = [member('u_d.u_in', 'x', 0, 3, 'u_a.u_x.x', 6, 10, 'L_x'), member('u_d.u_in', 'x', 4, 7, 'u_a.u_x.x', 9, 10, 'L_x')]
        die, rec = run(t, landing=land)
        assert rec['rows']['x_l0']['status'] == 'BLOCKED' and rec['rows']['x_l1']['status'] == 'BLOCKED'


def test_strict_refuses_unclean_bind_and_wrong_netlist():
    with tempfile.TemporaryDirectory() as t:
        d = bind_dir(Path(t) / 'b', errors=3)
        try:
            BD.load_bind(d)
        except ValueError as e:
            assert 'clean strict bind' in str(e)
        else:
            raise AssertionError('unclean bind accepted')
        die, rec = run(Path(t) / 'c', errors=3)
        assert rec['verdict'] == 'DIAGNOSTIC' and rec['bind_errors'] == 3
        B = BD.load_bind(bind_dir(Path(t) / 'd'))
        B['netlist_sha256'] = 'cd' * 32
        try:
            BD.rebind_links(FakeDie(), B)
        except ValueError as e:
            assert 'not the legacy tree die.v' in str(e)
        else:
            raise AssertionError('netlist mismatch accepted')
        try:
            BD.load_bind(bind_dir(Path(t) / 'e'), manifest='other.json', root=t)
        except ValueError as e:
            assert 'bind manifest' in str(e)
        else:
            raise AssertionError('manifest mismatch accepted')


if __name__ == '__main__':
    n = 0
    for k, f in sorted(globals().items()):
        if k.startswith('test_'):
            f()
            n += 1
            print('PASS', k)
    print(f'{n}/{n} PASS')
