import gzip
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_pc01_witness_inventory_r70 as inventory

def test_structural_root_key_not_embedded_key(tmp_path):
    p=tmp_path/'native.gz'
    with gzip.open(p,'wt') as f:
        json.dump({'nested':{'instructions':[{'pc':999}]},'instructions':[{'pc':0},{'pc':1},{'pc':2}]},f)
    assert inventory.first_instructions(p,2)==[{'pc':0},{'pc':1}]

def test_truncated_native_refuses(tmp_path):
    p=tmp_path/'native.gz'
    with gzip.open(p,'wt') as f:f.write('{"instructions":[{"pc":0}')
    with pytest.raises(ValueError):inventory.first_instructions(p,2)

def test_source_identity_census_replays_without_observed_claim():
    result=inventory.model(ROOT)
    frozen=json.loads((ROOT/'results/uarch/ds_hbm_restore_lifetime_r70_20261003/witness_identity_census.json').read_text())
    assert result==frozen
    assert result['boundary_seen_keys']=={'PC0':384,'PC1':576}
    assert not result['actual_observations'] and not result['complete_source_phase_bounds']
    assert not result['remote_GO']
