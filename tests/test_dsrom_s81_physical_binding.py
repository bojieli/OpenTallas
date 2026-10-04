import copy
import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/dsrom_s81_physical_binding.py'
s=importlib.util.spec_from_file_location('binding',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

@pytest.fixture
def data(): return m.load_inputs()

def test_canonical_identity(data): m.validate(data)

@pytest.mark.parametrize('key,value',[('stages',82),('TP',8),('BF_dual_pairs',512),('padding_pairs',1),('ROM_ECC',True),('physical_ROM4096_per_layer_die',9552)])
def test_wrong_selected_inventory(data,key,value):
    data['inventory'][key]=value
    with pytest.raises(ValueError):m.validate(data)

def test_missing_unary(data):
    data['return_connectivity']['nodes']=[x for x in data['return_connectivity']['nodes'] if not x['unilateral']]
    with pytest.raises(ValueError,match='unary'):m.validate(data)

def test_root_removal(data):
    data['return_connectivity']['roots'][0]['removed']=True
    with pytest.raises(ValueError,match='root'):m.validate(data)

def test_wrong_BF_address(data):
    data['stage_map']['BF_site_IDs'][1]+=1
    with pytest.raises(ValueError,match='BF'):m.validate(data)

def test_rank_alias(data):
    data['stage_map']['rank_dies'][1]['rank']=0
    with pytest.raises(ValueError,match='rank'):m.validate(data)

def test_no_empty_side_credit(data):
    data['return_model']['removed_empty_side_storage_credit_bits']=64
    with pytest.raises(ValueError,match='credit'):m.validate(data)

def test_area_and_proposal_separate(data):
    b=m.budget(data)
    assert b['source_inventory_baseline_screen_mm2']==pytest.approx(841.6802584058436)
    assert b['Ampere_proposal']['area_mm2']==843.5278
    assert b['Ampere_proposal']['margin_percent']==pytest.approx(1.6867365967)
    assert b['Ampere_proposal']['increment_over_strict_baseline_mm2']==pytest.approx(1.8475415941564)
    assert not b['Ampere_proposal']['implemented']
    assert not b['original_2_19_percent_unspent']

def test_indexer_copy_conflict(tmp_path):
    import gzip,json
    p=tmp_path/'metadata.gz'
    with gzip.open(p,'wt') as f:f.write(json.dumps({'stage':0,'tensor':'layers.2.attn.indexer.wk.weight','rank_slices':[{'rows':[0,32]},{'rows':[32,64]}]})+'\n')
    with pytest.raises(ValueError,match='replicated'):m.census(p)

def test_source_pin_change(tmp_path):
    import json
    (tmp_path/'inputs').mkdir();(tmp_path/'inputs/source_binding.json').write_text(json.dumps({'local_sha256':{'x.json':'bad'}}));(tmp_path/'inputs/x.json').write_text('{}')
    with pytest.raises(ValueError,match='changed input'):m.load_inputs(tmp_path)
