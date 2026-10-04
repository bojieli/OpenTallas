import importlib.util
from pathlib import Path
import shutil
import pytest
P=Path(__file__).resolve().parents[1]/'tools/hbm_ha9_service_composition.py'
s=importlib.util.spec_from_file_location('compose',P);M=importlib.util.module_from_spec(s);s.loader.exec_module(M)

def test_once_only_RF_and_distinct_bus_floors():
    r=M.compose()
    assert r['RF']['cell_plus_macro_mm2_per_SM']==pytest.approx(.5412902)
    assert r['RF']['cell_plus_macro_mm2_per_die_model']==pytest.approx(17.3212864)
    assert r['RF']['extra_W4_W6_area_debit_mm2']==0
    assert r['HA1']['simultaneous_all_port_track_floor']==361
    assert r['HA1']['ACK_visibility_completion_track_floor']==252
    assert not r['physical_launch_allowed']
    assert r['HA6']['replication_count'] is None

def test_bind_existing_S82_without_transfer_of_S73_claims():
    r=M.compose()['DS_KV']
    assert r['chosen_W2_stages']==82 and len(r['allocation'])==328
    assert r['total_stacks_provisional']==456
    assert r['return_contract']['RD']==64
    assert r['scan_homes_provisional'] and not r['adopted']
    assert r['capacity_batch216_1M'] is None

def test_stale_source_never_composes(tmp_path):
    b=tmp_path/'inputs';shutil.copytree(M.BASE,b)
    (b/'RF.sv').write_text('changed')
    with pytest.raises(ValueError):M.compose(b)

def test_channel_boundaries_and_no_escape_qualification():
    assert M.tracks(252,50.4,.1,.5)['fits']
    assert not M.tracks(253,50.4,.1,.5)['fits']
    assert not M.tracks(252,50.4,.1,.5)['obstruction_escape_and_loaded_timing_qualified']
    with pytest.raises(ValueError):M.tracks(252,0,.1,.5)
