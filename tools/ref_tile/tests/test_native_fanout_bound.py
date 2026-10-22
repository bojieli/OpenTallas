"""FLOW-CONSTFOLD 2026-10-21: constant-identity fold + bounded cloning (tools/ref_tile/native_fanout_bound.py)."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_fanout_bound as B  # noqa: E402

LIB = Path(__file__).resolve().parents[3] / 'physical/asap7_stdcell_native_models/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib'


@pytest.fixture(scope='module')
def roles():
    cells, _ = B.NC.liberty_roles([LIB])
    pin = lambda d, f=None, ck=False: {'direction': d, 'clock': ck, 'function': f}
    cells['INVx1_ASAP7_75t_R'] = {'sequential': False, 'bus_order': {}, 'pins': {'A': pin('input'), 'Y': pin('output', '!A')}}
    cells['BUFx2_ASAP7_75t_R'] = {'sequential': False, 'bus_order': {}, 'pins': {'A': pin('input'), 'Y': pin('output', 'A')}}
    cells['FF'] = {'sequential': True, 'bus_order': {}, 'pins': {'CK': pin('input', ck=True), 'D': pin('input'),
                                                                   'Q': pin('output', 'IQ')}}
    return cells


def cell(t, **conn):
    dirs = {p: ('output' if p in ('Y', 'Q', 'H', 'L') else 'input') for p in conn}
    return {'type': t, 'parameters': {}, 'attributes': {}, 'port_directions': dirs,
            'connections': {p: [b] for p, b in conn.items()}}


def design(n_and=2, per=20, tie='1'):
    """FF q -> n_and x AND2(q, tie) -> per FF endpoints each: census sees q drive n_and*per loads."""
    cells = {'src': cell('FF', CK=2, D=3, Q=10)}
    b = 100
    for i in range(n_and):
        cells[f'g{i}'] = cell('AND2x2_ASAP7_75t_R', A=10, B=tie, Y=b)
        for j in range(per):
            cells[f'e{i}_{j}'] = cell('FF', CK=2, D=b, Q=1000 + i * 100 + j)
        b += 1
    ports = {'clk': {'direction': 'input', 'bits': [2]}, 'd': {'direction': 'input', 'bits': [3]}}
    return {'modules': {'top': {'ports': ports, 'cells': cells, 'netnames': {}}}}


def run(tmp_path, roles, d, monkeypatch, **kw):
    monkeypatch.setattr(B.NC, 'liberty_roles', lambda paths: (roles, [{'path': 'x', 'sha256': '0' * 64}]))
    inp, out, rep = tmp_path / 'in.json', tmp_path / 'out.json', tmp_path / 'rep.json'
    inp.write_text(json.dumps(d))
    rc = B.run(inp, out, 'top', ['x'], report=rep, **kw)
    return rc, (json.loads(out.read_text()) if out.exists() else None), json.loads(rep.read_text())


def test_identity_fold_then_clone_bounds_the_census(tmp_path, roles, monkeypatch):
    rc, out, rep = run(tmp_path, roles, design(), monkeypatch)
    assert rc == 0 and rep['status'] == 'BOUNDED'
    assert rep['pre_max_dynamic_loads'] == 40 and rep['old_rule_max_dynamic_loads'] == 20
    cells = out['modules']['top']['cells']
    assert not any(c['type'].startswith('AND2') for c in cells.values())          # identities folded
    copies = [n for n, c in cells.items() if c['type'] == 'FF' and c['connections']['D'] == [3]]
    assert len(copies) == 2                                                          # src + one replica
    for n in copies:
        q = cells[n]['connections']['Q'][0]
        assert sum(1 for c in cells.values() if c['connections'].get('D') == [q]) <= 24
    assert rep['post_max_dynamic_loads'] <= 24


def test_passing_netlist_is_left_alone(tmp_path, roles, monkeypatch):
    rc, out, rep = run(tmp_path, roles, design(n_and=2, per=10), monkeypatch)
    assert rc == 3 and out is None and rep['status'] == 'NO_CHANGE'


def test_real_fanout_is_a_frontier_not_cloned(tmp_path, roles, monkeypatch):
    d = design(n_and=1, per=5)
    for j in range(40):                                 # q itself drives 40 real loads before any fold
        d['modules']['top']['cells'][f'r{j}'] = cell('FF', CK=2, D=10, Q=5000 + j)
    rc, out, rep = run(tmp_path, roles, d, monkeypatch)
    assert rc == 2 and out is None and rep['status'] == 'FRONTIER'


def test_constant_function_goes_to_a_tie_and_inverse_to_inv(tmp_path, roles, monkeypatch):
    d = design(n_and=2, per=20, tie='0')               # AND(q, 0) = 0: loads to a TIELO, no driver over 32
    d['modules']['top']['cells']['n0'] = cell('NAND2xp33_ASAP7_75t_R', A=10, B='1', Y=200)
    for j in range(40):
        d['modules']['top']['cells'][f'm{j}'] = cell('FF', CK=2, D=200, Q=6000 + j)
    rc, out, rep = run(tmp_path, roles, d, monkeypatch)
    assert rc == 0, rep
    cells = out['modules']['top']['cells']
    assert rep['stats']['to_inv'] == 1                 # NAND(q, 1) = !q became an INV, then its tree was split
    drv = {c['connections'][o][0]: c for c in cells.values() for o in ('Y', 'Q', 'H', 'L') if o in c['connections']}
    assert all(drv[cells[f'm{j}']['connections']['D'][0]]['type'] == 'INVx1_ASAP7_75t_R' for j in range(40))
    assert any(c['type'].startswith('TIELO') for c in cells.values())
    assert rep['post_max_dynamic_loads'] <= 24


def test_flow_hook_opt_out_and_rc_handling(tmp_path, monkeypatch):
    """run_abi3_physical.native_fanout_bound: opt-out leaves the flow alone; a FRONTIER/NO_CHANGE never edits the
    mapped netlist; only a BOUNDED report with the written netlist replaces it."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import run_abi3_physical as R
    mapped = tmp_path / '1_2_yosys.v'
    mapped.write_text('module t(); endmodule\n')
    assert R.native_fanout_bound(tmp_path, mapped, '/work/x.v', 't', {'extra_config': {'OT_NATIVE_FANOUT_BOUND': '0'}},
                                 None) is None

    class P:
        def __init__(self, out): self.stdout, self.stderr = out, ''

    def fake(status, rc, write):
        def make(goal, log, timeout):
            (tmp_path / 'native_fanout_bound.json').write_text(json.dumps({'status': status}))
            if write:
                (tmp_path / '1_2_yosys.bound.v').write_text('module t(); wire bounded; endmodule\n')
            return P(f'NFB_RC={rc}\n')
        return make
    for status, rc in (('FRONTIER', 2), ('NO_CHANGE', 3)):
        rec = R.native_fanout_bound(tmp_path, mapped, '/work/x.v', 't', {'extra_config': {}}, fake(status, rc, False))
        assert rec['status'] == status and 'bounded' not in mapped.read_text()
    (tmp_path / 'native_fanout_bound.json').unlink()
    rec = R.native_fanout_bound(tmp_path, mapped, '/work/x.v', 't', {'extra_config': {}}, lambda g, l, t: P('NFB_RC=2\n'))
    assert rec['status'] == 'ERROR' and 'bounded' not in mapped.read_text()   # no report (tool never ran) != FRONTIER
    rec = R.native_fanout_bound(tmp_path, mapped, '/work/x.v', 't', {'extra_config': {}}, fake('BOUNDED', 0, True))
    assert rec['status'] == 'BOUNDED' and 'bounded' in mapped.read_text()
    assert (tmp_path / '1_2_yosys.prebound.v').read_text() == 'module t(); endmodule\n'
