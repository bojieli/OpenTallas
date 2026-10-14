import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('leafgate', Path(__file__).with_name('bound_leaf_internal_gate.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def fixture():
    source = {'top': 'real_leaf', 'params': {'N': 8}, 'sources': {'rtl/leaf.sv': 'sourcehash'}}
    leaf = {'master': 'real_leaf', 'instances': 7, 'required': True,
            'libs': {'ss': {'sha256': 'sshash'}, 'ff': {'sha256': 'ffhash'}},
            'expected_clocks_ps': {'core': 833.333}, 'routed_spec': source}
    receipt = {'libs': {'ss': 'sshash', 'ff': 'ffhash'}, 'routed_spec': source,
               'original_constraints_verified': True, 'source_params_verified': True,
               'constraints_review_basis': 'immutable original SDC sequence and uncertainty checked',
               'corners': {}, 'minimum_period_review': {}}
    for c in ('ss', 'ff'):
        receipt['corners'][c] = {'returncode': 0, 'done': True, 'log_sha256': c,
             'clocks_ps': {'core': 833.333}, 'structural_reg2reg_pairs': 8,
             'coverage': {m: {'endpoints': 8, 'unconstrained': 0, 'worst_ps': 10} for m in ('max', 'min')},
             'reg2reg': {m: {'endpoints': 8, 'worst_ps': 10} for m in ('max', 'min')}}
        receipt['minimum_period_review'][c] = {'log_sha256': c, 'passed': True, 'basis': 'clock min period and pulse checks reviewed'}
    return {'masters': [leaf]}, {'real_leaf': receipt}

def test_missing_and_mismatched_evidence_fail():
    m, r = fixture()
    assert g.gate(m, r)['passed']
    assert not g.gate(m, {})['passed']
    r['real_leaf']['libs']['ss'] = 'unrelated historical view'
    assert not g.gate(m, r)['passed']

def test_constraints_source_clock_and_coverage_are_independent_obligations():
    for mutate in (
        lambda r: r.update(original_constraints_verified=False),
        lambda r: r['routed_spec'].update(params={'N': 16}),
        lambda r: r['corners']['ss']['clocks_ps'].update(core=730),
        lambda r: r['corners']['ss']['coverage']['max'].update(unconstrained=1),
        lambda r: r['corners']['ff']['reg2reg']['min'].update(worst_ps=-0.1),
        lambda r: r['minimum_period_review']['ss'].update(log_sha256='unrelated report'),
    ):
        m, r = fixture()
        r = copy.deepcopy(r)
        mutate(r['real_leaf'])
        assert not g.gate(m, r)['passed']

def test_zero_etm_minperiod_does_not_prove_missing_internal_paths():
    m, r = fixture()
    for c in ('ss', 'ff'):
        r['real_leaf']['corners'][c]['reg2reg'] = {x: {'endpoints': 0, 'worst_ps': None} for x in ('max', 'min')}
        r['real_leaf']['corners'][c]['minimum_period_report'] = 'period_min = 0.00'
    assert not g.gate(m, r)['passed']
    # A measured all-arcs graph census independently proves there is no feedback
    # or internal sequential-to-sequential path in a one-stage relay.
    for c in ('ss', 'ff'):
        r['real_leaf']['corners'][c]['structural_reg2reg_pairs'] = 0
    assert not g.gate(m, r)['passed']
    r['real_leaf']['routed_spec']['sha256'] = 'actualsource'
    r['real_leaf']['no_internal_reg2reg_review'] = {c: {'passed': True, 'basis': 'source-bound one-stage relay reviewed with returned STA absence', 'log_sha256': c, 'source_spec_sha256': 'actualsource'} for c in ('ss', 'ff')}
    assert g.gate(m, r)['passed']
    # Faulty structural fanin census zero must NEVER override returned negative timing.
    r['real_leaf']['corners']['ss']['reg2reg']['max'] = {'endpoints': 8, 'worst_ps': -187.58}
    assert not g.gate(m, r)['passed']

def test_opensta_property_units_are_ps():
    log = 'OT_INTERNAL_CLOCK core 833.333008\nOT_INTERNAL_COVERAGE max 8 0 12.5\nOT_INTERNAL_STRUCTURAL_PAIRS 8\nOT_INTERNAL_REG2REG max 8 12.5\nOT_INTERNAL_DONE\n'
    r = g.parse(log)
    assert r['clocks_ps']['core'] == 833.333008
    assert r['coverage']['max']['worst_ps'] == 12.5
