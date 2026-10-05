"""Boundary checks: replicated work, unknowns, units and direct-stream options."""
import importlib.util
from pathlib import Path
import json
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hbrom_power', ROOT/'tools/hbrom_power.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    candidate = {'candidate': {'tp':4},'tpot_us':1000,'service':{'w':{'active_tiles':2,'source_request_cycles_upper':10,'weight_bytes_per_cycle_active':8}},
                 'geometry':{'rom_mm2_per_die':2},'topology':{'logic_dies':4,'stages':['a'],'memory_inventory':{'hbm_stacks':4}}}
    inputs = {'dag':[{'kind':'weight','id':'w','format':'bf16','weight_bytes':64,'macs':32,'activation_bytes':16,'result_bytes':8}], 'macro':{'area_mm2':1}}
    tech = json.loads((ROOT/'configs/hardware/technology.json').read_text())
    scenarios = json.loads((ROOT/'configs/hardware/power_scenarios.json').read_text())
    kv = {'traffic':{'fullscan_index_B_per_token':100,'selected_CKV_HBM_B_if_fetch_every_compressed_layer':20,'window_cold_B_all_layers':4}}
    return candidate, inputs, tech, scenarios, kv


def test_replication_and_unknown_total():
    args = fixture()
    a = m.evaluate(*args)
    args[1]['dag'][0]['replicated'] = True
    b = m.evaluate(*args)
    assert b['workload']['useful_weight_bytes'] == 4*a['workload']['useful_weight_bytes']
    assert b['workload']['macs_by_format']['bf16'] == 128
    assert b['sensitivities'][0]['total_average_w'] is None
    assert b['peak_w'] is None
    assert b['unknown_addends']


def test_energy_units_and_staging():
    a = m.evaluate(*fixture())
    first, staged = a['sensitivities'][:2]
    assert first['priced_subtotal_average_w'] == pytest.approx(first['priced_subtotal_j_per_token']/0.001)
    assert staged['priced_subtotal_j_per_token'] > first['priced_subtotal_j_per_token']
    assert all(row['mandatory_G0_weight_ring'] for row in a['sensitivities'])
    assert first['terms_j']['mandatory_G0_weight_ring_write_read'] > 0
    assert not first['optional_extra_source_FIFO']
    assert staged['optional_extra_source_FIFO']
    assert first['applicability'] == 'lower_bound_not_actual_candidate_read_traffic'
    assert a['idle_sensitivity']['each_additional_W_per_logic_die_j_per_token'] == 0.004


def test_no_missing_hbm_inventory_and_zero_time():
    args=fixture()
    args[0]['topology']['memory_inventory']['hbm_stacks']=None
    with pytest.raises(ValueError):m.evaluate(*args)
    args=fixture()
    args[0]['tpot_us']=0
    with pytest.raises(ValueError):m.evaluate(*args)
