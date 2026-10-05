import gzip
import hashlib
import json
from pathlib import Path
import sys

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_retention_physical_allocation as S


@pytest.fixture(scope='module')
def model():
    return S.R.obj(S.OUT/'model-r1.json')


@pytest.fixture(scope='module')
def allocation():
    return json.loads(gzip.decompress((S.ROOT/S.OUT/'successor-allocation-r1.json.gz').read_bytes()))


def test_successor_conserves_replaced_source_owners_and_prices_inversions(model,allocation):
    assert len(allocation['removed_old_control_FFs'])==32
    rows=model['source_cells']
    assert len({r['instance'] for r in rows})==85
    assert sum(r['role']=='mask' for r in rows)==80
    assert sum(r['role']=='bank_strobe' for r in rows)==5
    assert model['new_FFs']==53 and model['total_metadata_FFs']==90
    assert model['restoring_INV_cells']==85
    assert model['nominal_retention_cell_area_um2']==pytest.approx(23.80914)
    assert model['mask_selector_distribution_buffers']==480
    assert model['conservative_reserved_area_um2']<125000
    assert len({r['restoring_INV'] for r in rows})==85
    for r in rows:
        assert allocation['added_primitive_cells'][r['restoring_INV']]['type']==S.INV
        assert r['QN_wire_length_um']>0
        assert r['restoring_INV_input_cap_fF']['ss']>0


def test_exact_source_reset_ownership_and_finite_placement(model,allocation):
    rows=model['source_cells'];coords=allocation['nominal_node_coordinates_um']
    assert {r['reset_index'] for r in rows}==set(range(5,90))
    incoming={(e['sink'],e['pin']):e for e in allocation['wire_edges']}
    for r in rows:
        x,y=r['position_um']
        assert 0<=x<=357.696 and 0<=y<=1360.8
        assert x<coords[r['macro']][0]
        n,p=r['instance'],'RESETN'
        e=incoming[n,p]
        while e['driver'].startswith('retention_'):
            assert 0<e['length_um']<=128
            e=incoming[e['driver'],'A']
        assert e['driver']==f"u_tile.u_logic.g_distribution.u_tree.g_reset_leaf[{r['reset_index']//8}].u_buf"
        assert (r['instance'],'CLK') in incoming


def test_fresh_endpoint_timing_has_explicit_unbalanced_clock_failure(model):
    for corner,r in model['timing_preflight'].items():
        assert r['clock_sinks']==102352 and r['reset_sinks']==56683
        assert r['clock_pin_cap_fF']>45072 if corner=='ss' else r['clock_pin_cap_fF']>52451
        assert r['clock_span_ps']>r['clock_skew_target_ps']==20
        assert r['balanced_CTS'] is False and r['clock_skew_demand_failed'] is True
        assert r['baseline_timing_transferred'] is False
        assert r['source_ff_reset_bounds_recomputed'] is True
        assert r['contextual_SSFF'] is False
        assert r['max_BUF_load_fF']<=46.08
    assert model['status']=='FAIL_NOMINAL_CLOCK_BALANCE_NOT_BUILD_ADMITTED'
    assert model['balanced_clock_required_before_build_admission'] is True


def test_binary_initialization_is_explicit_contract_not_Z_equivalence(model,allocation):
    assert model['driven_binary_initialization_contract']['stored_Z'].startswith('FAIL_RETAINED')
    assert allocation['semantic_data_graph_qualified'] is False
    assert model['source_map_admission'] is False and model['hardware_adoption'] is False
    assert model['numerical_or_map_runs']==0 and model['PnR'] is False
    assert 'No edge3guarantee' in model['startup']
    assert model['selected_corridor_um']==96.768 and model['complete_cell_ceiling_um2']==125000
    assert any('60/25' in p for p in model['prerequisites'])


def test_source_and_artifact_manifests(model):
    base=S.ROOT/S.OUT
    for name,d in json.loads((base/'sourcepins-r1.json').read_text())['sha256'].items():
        assert hashlib.sha256((S.ROOT/name).read_bytes()).hexdigest()==d,name
    for name,d in json.loads((base/'artifact-sha256-r1.json').read_text()).items():
        assert hashlib.sha256((base/name).read_bytes()).hexdigest()==d,name
    assert hashlib.sha256((base/'successor-allocation-r1.json.gz').read_bytes()).hexdigest()==model['allocation_sha256']
