"""W16 exact-boundary and refusal tests (no RTL build or product projection)."""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('w16', ROOT / 'tools/w16_measured_calibration.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def token_inputs():
    return [w.read(p) for p in (w.TP2, w.ERRATA, w.VERIFY)] + [w.sha(w.TP2)]


def test_exact_token_scope_and_stage_accounting():
    got = w.validate_tp2(*token_inputs())
    assert got['total_cycles'] == 151557
    assert got['token'] == 50994
    assert got['stage_span_cycles'] + got['outside_stage_span_cycles'] == 151557
    assert got['measured_collective_service_cycles'] is None


@pytest.mark.parametrize('key,value', [('tp',4), ('su_width',1024), ('smin',7),
                                     ('smax',10), ('tree_cut',7),
                                     ('collective_lat_cycles',339),
                                     ('su_reducer_time_levels',6), ('groups_per_die',5120)])
def test_refuses_each_mismatched_runtime_parameter(key, value):
    args = token_inputs()
    args[0]['design_point'][key] = value
    with pytest.raises(w.Refusal, match='configuration mismatch'):
        w.validate_tp2(*args)


@pytest.mark.parametrize('mutation', ['cycles','binary','token','layer','coverage'])
def test_refuses_corrupt_token_identity_or_exactness(mutation):
    args = token_inputs()
    if mutation == 'cycles':
        args[0]['total_cycles'] += 1
    elif mutation == 'binary':
        args[0]['binary_sha256'] = '0'*64
    elif mutation == 'token':
        args[0]['rtl_token'] += 1
    elif mutation == 'layer':
        args[0]['layer_x_checks']['L35_die1_x']['mismatches'] = 1
    else:
        del args[0]['layer_x_checks']['L35_die1_x']
    with pytest.raises(w.Refusal):
        w.validate_tp2(*args)


def test_explicit_reducer_parameters_and_unsupported_full_token():
    c = w.supported_qwen_components(w.CONFIG)
    assert c['reducer_tail_cycles'] == 66
    assert c['matched'] == {'su_width':64, 'red_lv':7}
    assert c['full_token_model_cycles'] is None
    cfg = dict(w.CONFIG, su_reducer_time_levels=6)
    assert w.supported_qwen_components(cfg)['reducer_tail_cycles'] == 62
    with pytest.raises(w.Refusal, match='unsupported mappings'):
        w.refuse_product_transfer('TP2', 'TP2', c['unsupported'])


@pytest.mark.parametrize('scope', ['W11 reduced','W17 field','TP4 partial','TP2 token'])
def test_refuses_raw_ratio_or_cross_configuration_product_transfer(scope):
    with pytest.raises(w.Refusal, match='scope cannot transfer'):
        w.refuse_product_transfer(scope, 'product headline')


def test_reduced_failure_preserved_and_attribution_conserved():
    r, a = w.read(w.REDUCED), w.read(w.ATTR)
    got = w.validate_reduced(r, a)
    assert got['overall_verdict'] == 'fail'
    assert got['cycle_difference'] == 54545
    assert got['product_price'] is None and not got['adopt']
    a['su_issue_attributed_intervals_by_region']['attn'] += 1
    with pytest.raises(w.Refusal, match='attribution inconsistent'):
        w.validate_reduced(r, a)
    r['status'] = 'pass'
    with pytest.raises(w.Refusal, match='overall FAIL'):
        w.validate_reduced(r, w.read(w.ATTR))


def test_qcnam_mandatory_core_failure_excludes_gain_despite_pending_finalizer():
    q = w.read(w.QC)
    got = w.qc_eligibility(q)
    assert got['stability'] == 'FAIL'
    assert not got['eligible_gain'] and not got['adopt']
    assert not got['full_gate_complete'] and got['full_verdict'] is None
    q['definitive_core_failure'] = False
    with pytest.raises(w.Refusal, match='mandatory QC-NAM'):
        w.qc_eligibility(q)


def test_pin_drift_refused_before_model_execution(tmp_path):
    p = tmp_path / 'input.json'
    p.write_text('{}')
    receipt = {'pins':{'input.json':w.sha('input.json',tmp_path)}}
    p.write_text('{"changed":true}')
    with pytest.raises(w.Refusal, match='pin drift'):
        w.check(receipt, tmp_path)


def test_historical_pins_report_drift_without_rebinding(tmp_path):
    p = tmp_path / 'source.py'
    p.write_text('new')
    old = {'source_sha256':{'source.py':'a'*64, 'absent.py':'b'*64}}
    got = w.source_binding(old, tmp_path)
    assert got['source.py']['recorded_sha256'] == 'a'*64
    assert not got['source.py']['matches_current']
    assert got['absent.py']['current_sha256'] is None
    assert old['source_sha256']['source.py'] == 'a'*64


def capacity_inputs():
    return [w.read(p) for p in (w.CAPACITY,w.CAPACITY_PIN,w.W19_PROGRAM,w.W19_FLOORPLAN)]


def test_compact_rejected_and_padded_derived_from_actual_record_counts():
    got = w.w19_capacity(*capacity_inputs())
    assert got['layout_scope'] == 'REJECTED_COMPACT_136B_CANDIDATE'
    assert got['compact_candidate']['rejected'] and not got['compact_candidate']['adopt']
    assert got['required_sector_address_bits'] == 26
    padded = got['padded_baseline']
    assert padded['all_rank_records'] == 3042050048
    assert sum(map(sum,padded['rank_stack_records'])) == padded['all_rank_records']
    assert padded['all_rank_sm_image_bytes'] == 778764812288
    assert padded['max_resident_stack_bytes'] == 2597703680
    assert padded['required_sector_address_bits'] == 27
    assert not padded['address_fit'] and padded['measured_service_ns'] is None
    assert not got['modulo_credit'] and not got['reload_credit']
    assert got['schedule']['incremental_ns_token_assumed'] == 340000
    assert got['schedule']['measured_ns_token'] is None
    assert not got['schedule']['priced_in_headline']
    assert set(got['non_sm_capacity']) == {'norm_and_HC_constants','embedding','Engram','KV','index'}


@pytest.mark.parametrize('mutation', ['sum','aperture','adoption','schedule','program'])
def test_refuses_malformed_capacity_or_free_schedule_credit(mutation):
    args = capacity_inputs()
    if mutation == 'sum':
        args[0]['rank_stack_bytes'][0][0] += 32
    elif mutation == 'aperture':
        args[0]['static_resident_address_fit'] = True
    elif mutation == 'adoption':
        args[0]['schedule_budget']['enabled_default'] = True
    elif mutation == 'schedule':
        args[0]['schedule_budget']['incremental_ns_token_vs_one_fetch_per_layer'] = 0
    else:
        op = next(o for l in args[2]['layers'] for o in l['ops'] if o['kind']=='mv')
        op['rows'][0][1] += 32
    with pytest.raises(w.Refusal):
        w.w19_capacity(*args)


def test_record_geometry_minimal_case_counts_padding_per_segment():
    op = {'kind':'mv','w':'dense.weight','fmt':'fp8','k':32,'rows':[[0,1] for _ in range(96)]}
    floor = {'quadrants':{str(s):list(range(8*s,8*s+8)) for s in range(4)}}
    counts, compact = w.resident_records({'layers':[{'ops':[op]}]}, floor)
    assert counts[0] == [8,0,0,0]
    assert compact[0] == [1152,0,0,0] # ceil(8*136/128)*128, not8*256
    op['w'] = [0,'w1']
    counts, compact = w.resident_records({'layers':[{'ops':[op]}]}, floor)
    assert counts[0] == [8*384,0,0,0]
    assert compact[0] == [1152*384,0,0,0]
