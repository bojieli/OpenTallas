import gzip
import hashlib
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_local_subtree_context as N
import uarch_model_qwen_local_context as U

@pytest.fixture(scope='module')
def model():return N.R.obj(N.OUT/'model-r1.json')

def test_source_endpoints_and_old_failure_remain_separate(model):
    assert model['successor_clock_sinks']==102352
    assert model['successor_reset_sinks']==56683
    assert model['provider_clock_FFs']==2
    assert model['historical_global_lower_bound_um2']==pytest.approx(157385.58875971477)
    assert model['historical_global_fit'] is False
    assert model['global_equalization_chain_duplicated'] is False
    assert model['additional_maps']==model['numerical_runs']==0

def test_actual_full_cell_and_field_composition(model):
    assert model['complete_cell_area_um2']==pytest.approx(sum(model['area_terms_um2'].values()))
    field=model['tilefield']
    assert field['tiles']==1536
    assert field['complete_cell_area_mm2']==pytest.approx(model['complete_cell_area_um2']*1536/1e6)
    assert field['selected_field_area_mm2']==pytest.approx(747.6521730048)
    assert field['field_clock_ports']==102352*1536
    assert field['field_reset_pins']==56683*1536
    assert field['provider_extra_clock_FFs']==3072
    assert field['die_clock_reset_spine_and_other_domains_priced'] is False

def test_finite_loads_and_source_owned_reset_counts(model):
    for r in model['timing'].values():
        for s in r['scenarios']:
            assert s['reset_FF_sinks']==56683
            assert s['max_BUF_load_fF']<=46.08
            assert s['startup_not_admitted_if_any_reset_or_source_gate_fails'] is True
    assert model['period_ps']==pytest.approx(833.3333333333334)
    assert model['SS_setup_uncertainty_ps']==60 and model['FF_hold_uncertainty_ps']==25
    assert model['source_map_admission'] is False and model['PnR'] is False

def test_local_geometric_balance_load_inversion_and_metadata_ownership(model):
    base=N.R.ROOT/N.OUT
    g=json.loads(gzip.decompress((base/'local-subtree-allocation-r1.json.gz').read_bytes()))
    assert len(g['source_clock_sinks'])==102353
    assert len(g['reset_direct_sinks'])==56593 and len(g['metadata_reset_sinks'])==90
    assert all(0<e['length_um']<=128+1e-8 for e in g['wire_edges'])
    assert max(r['sinks'] for r in g['local_group_ledger'])<600
    assert len(g['local_balance_ledger'])==model['source_groups']
    for r in g['local_balance_ledger']:
        assert r['SS_requested_delay_ps']==pytest.approx(r['SS_inverted_delay_ps'],abs=1e-6)
    assert U.qwen_rom_local_context_price()['hardware_admission'] is False

def test_hash_manifests_and_production_calendar_scope(model):
    base=N.R.ROOT/N.OUT
    for name,d in json.loads((base/'sourcepins-r1.json').read_text())['sha256'].items():
        assert hashlib.sha256((N.R.ROOT/name).read_bytes()).hexdigest()==d,name
    for name,d in json.loads((base/'artifact-sha256-r1.json').read_text()).items():
        assert hashlib.sha256((base/name).read_bytes()).hexdigest()==d,name
    assert model['persistent_KV']['cold_calendar_role']=='reference only, not selected production'
    assert model['source_reachable_binary_init_proof'] is False
