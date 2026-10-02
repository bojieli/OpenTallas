import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import dsrom_selector_station_parent_binding as M

@pytest.fixture(scope='module')
def model():
    return M.build()

def test_exact_default_off_parameter_only_inverse(model):
    raw, _ = M.load(); original = raw['ot_v41_field_w17w10.sv'].decode()
    proposed = M.propose_field(original)
    for flag in M.FLAGS:
        assert f'parameter integer {flag} = 0,' in proposed
        assert f'.{flag}({flag})' in proposed
        assert flag not in original
    assert model['caller']['exact_inverse_source_gate']
    assert not model['caller']['actual_current_field_configuration_join']
    assert not model['caller']['elaborated_or_numerically_qualified']
    assert model['caller']['added_register_edges'] == 0

def test_selected_source_receipt_configuration(model):
    assert model['caller']['measured_element'] == {f:1 for f in M.FLAGS}
    assert model['caller']['historical_pair_defaults'] == {f:0 for f in M.FLAGS}
    assert model['caller']['all_pair_sites_forwarded']

def test_changed_caller_is_not_silently_repatched():
    raw, _ = M.load(); text = raw['ot_v41_field_w17w10.sv'].decode()
    with pytest.raises(ValueError): M.propose_field(M.propose_field(text))
    with pytest.raises(ValueError): M.propose_field(text.replace('.PHW(PHW),', '.PHW(6),'))

def test_no_extra_capture_edge_from_unadmitted_intrinsic(model):
    h = model['historical_intrinsic']
    assert h['two_edge_capture_remaining_ps'] == pytest.approx(767.5732666666668)
    assert h['remaining_409p969_not_admitted']
    assert h['slew_diagnostic_still_open']
    assert not h['extra_capture_edge_selected']

def test_cap_domain_no_extrapolation():
    raw, _ = M.load(); b = json.loads(raw['SS_driver_cells.json'])['cell_bodies']['BUFx4_ASAP7_75t_R']
    with pytest.raises(ValueError): M.lut(b,'cell_rise',321,11.52)
    with pytest.raises(ValueError): M.lut(b,'cell_rise',80,185)

def test_finite_registered_delay_and_slew_domain(model):
    s = model['station']
    assert s['BUF_per_registered_segment'] == 5
    assert s['total_stage_upper_ps'] < s['clock_period_ps']
    assert s['next_BUFFER_count_stage_ps'] > s['clock_period_ps']
    assert s['DFF_SS_output_slew_ps'] <= 160
    assert s['FF_hold_margin_before_extra_reserved_hold_buffer_ps'] > 40
    assert s['source_R_kohm_per_um'] == .031287
    assert s['source_C_fF_per_um'] == .178475
    assert s['propagated_slew_or_wire_not_admitted']

def test_whole_transport_width_and_drain_price(model):
    t = model['transport']
    assert t['segments_each_direction'] == 46
    assert t['sink_segments'] == 13
    assert t['intermediate_FF_bits'] == 214806
    assert t['per_call_additional_cycles'] == 102
    assert t['nine_call_cycles'] == 918
    assert t['nine_call_us'] == .765
    assert t['six_position_verification_us'] == 4.59
    assert t['MTP_drafter_commit_rollback_unbound']

def test_clock_hold_and_repeater_floors_not_only_FFs(model):
    a = model['area']; t = model['transport']
    assert a['full_station_cell_floor_mm2_at50pct'] > 3*a['FF_only_mm2_at50pct']
    assert t['clock_tree']['cells'] == 4995
    assert t['data_BUF_cells'] == 1105645
    assert t['reserved_hold_BUF_cells'] == 214806
    assert a['FF_only_old_0p052811676_replaced_not_added']
    assert not a['actual_station_row_placement']
    assert a['clock_routes_PG_pinaccess_and_detours_unpriced']

def test_no_admission_transfer(model):
    a = model['admission']
    assert not a['full_context_PR_admitted']
    assert not a['selector_station_PR_admitted']
    assert a['fulltoken_not_required_for_local_characterization']
    assert model['jobs_launched'] == 0

def test_exact_frozen_inputs():
    raw, origins = M.load()
    for n,b in raw.items(): assert hashlib.sha256(b).hexdigest() == origins[n]['sha256']

def test_source_station_coordinates_conserve_data_bits(tmp_path,model):
    out = tmp_path/'trial'; M.emit(out)
    r = json.loads((out/'station_request.json').read_text())
    assert r['source_aligned_data_station_bits'] == r['expected'] == 189450
    records = [json.loads(v) for v in gzip.decompress((out/'preferred_source_stations.jsonl.gz').read_bytes()).splitlines()]
    assert len({(v['pin'],v['station']) for v in records}) == 189450
    assert all(v['pin'] not in ('clock','reset') for v in records)
    assert all(v['row_snapped_preferred_DBU'][0]%54 == 0 and v['row_snapped_preferred_DBU'][1]%270 == 0 for v in records)
    assert not any(v['actual_cell_placement'] for v in records)

def test_generator_refuses_overwrite(tmp_path):
    with pytest.raises(FileExistsError): M.emit(tmp_path)

def test_nonfinite_clock_tree():
    with pytest.raises(ValueError): M.tree_count(100,10,10)
    assert M.tree_count(100,.5,10)['cells'] == 11
