"""COORD 11-09 loopgap-153x-1109: census <=64 loads admitted for the S81 svc provider kits (s81svc_*) only."""
import copy
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_census as N
import pre_route_gate as P


def actual():
    r = json.loads((Path(__file__).parent / 'fixtures/mc3c7_native_r2_cts.json').read_text())
    r['kit'] = 's81svc_irg_hsfp'
    r['top'] = 'ot_hdc_v41x_idx_hslice_fp'
    r['violations'][0]['loads'] = 64
    r['max_dynamic_loads'] = 64
    return r


def out(r):
    return 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r)


def test_scoped_kit_admits_with_warning_and_raw_fail():
    r = actual()
    before = copy.deepcopy(r)
    assert N.s81svc_scoped_admission(r, 's81svc_irg_hsfp')
    g = P.Gate()
    assert P.check_native_census(g, out(r), 's81svc_irg_hsfp')
    assert r == before and r['status'] == 'FAIL'
    assert any(i['severity'] == 'WARN' for i in g.items)


@pytest.mark.parametrize('change', ['over64', 'max', 'gate_kit_mismatch', 'no_gate_kit', 'other_kit', 'bare_prefix',
                                    'role_error', 'limit', 'raw_pass', 'schema', 'netlist'])
def test_outside_scope_refuses(change):
    r = actual()
    kit = 's81svc_irg_hsfp'
    if change == 'over64': r['violations'][0]['loads'] = 65
    elif change == 'max': r['max_dynamic_loads'] = 65
    elif change == 'gate_kit_mismatch': kit = 's81svc_other'
    elif change == 'no_gate_kit': kit = None
    elif change == 'other_kit': r['kit'] = kit = 'hdie_pc_ctrl_h9c'
    elif change == 'bare_prefix': r['kit'] = kit = 's81svc_'
    elif change == 'role_error': r['role_errors'] = ['x']
    elif change == 'limit': r['limit'] = 64
    elif change == 'raw_pass': r['status'] = 'PASS'
    elif change == 'schema': r['schema'] += '_x'
    elif change == 'netlist': r['netlist']['sha256'] = 'z'
    if kit is not None:
        assert not N.s81svc_scoped_admission(r, kit)
    assert not P.check_native_census(P.Gate(), out(r), kit)


def test_scope_bound_to_spec():
    r = actual()
    assert P.check_native_census(P.Gate(), out(r), P.native_scope_kit(Path('/k/s81svc_irg_hsfp'),
                                                                        {'name': 's81svc_irg_hsfp', 'top': r['top']}))
    assert not P.check_native_census(P.Gate(), out(r), P.native_scope_kit(Path('/k/s81svc_irg_hsfp'),
                                                                            {'name': 'other', 'top': r['top']}))


# COORD 11-10: (a) a kit outside the scope is gated exactly as on main: with the S81 svc admission removed
# (monkeypatched to False, i.e. the main code path) every outside-scope kit gets the same verdict and the same items.
@pytest.mark.parametrize('kit', [None, 'hdie_pc_ctrl_h9c', 'hdie_pc_ctrl_mc3c7_cts', 's81svc_', 'xs81svc_irg', 'S81SVC_IRG'])
@pytest.mark.parametrize('loads', [33, 56, 64, 65, 200])
def test_outside_scope_gated_exactly_as_main(monkeypatch, kit, loads):
    r = actual()
    r['kit'] = kit if kit is not None else 'other'
    r['violations'][0]['loads'] = loads
    r['max_dynamic_loads'] = max(loads, max(v['loads'] for v in r['violations']))
    g_new = P.Gate()
    v_new = P.check_native_census(g_new, out(r), kit)
    monkeypatch.setattr(N, 's81svc_scoped_admission', lambda report, kit=None: False)
    g_main = P.Gate()
    v_main = P.check_native_census(g_main, out(r), kit)
    assert v_new == v_main
    assert g_new.items == g_main.items


# (b) the raw FAIL receipt is kept: the census CLI writes status FAIL, the violations and max unchanged, and adds
# only the admission record; exit code 0 only through the scoped admission.
def test_raw_fail_receipt_kept(tmp_path, monkeypatch):
    r = actual()
    raw = copy.deepcopy(r)
    assert N.s81svc_scoped_admission(r)
    assert r == raw and r['status'] == 'FAIL' and r['violations'] and r['max_dynamic_loads'] == 64
    src = (Path(N.__file__).read_text())
    assert "report['admission'] = {'status': 'PASS_WITH_SCOPED_WAIVER', 'authority': S81SVC_SCOPE," in src
    assert "'raw_status': 'FAIL'" in src


def test_defaults_unchanged():
    # no default limit moved: the global census limit stays 32 and the earlier scopes keep their bounds
    assert N.MC3C7_MAX == 56 and N.S81SVC_MAX == 64
    r = actual(); r['kit'] = 'hdie_pc_ctrl_h9c'
    assert not P.check_native_census(P.Gate(), out(r), 'hdie_pc_ctrl_h9c')
