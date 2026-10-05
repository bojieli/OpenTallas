import copy,importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('resource_r2',ROOT/'tools/w17_owner_progress_resource_r2.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.fixture
def events():
    return json.loads((ROOT/'results/uarch/w17_owner_progress_resource_r2_20261002/model.json').read_text())['writer_calendar']['events']
def test_source_writer_calendar_valid(events):m.validate_writer(events)
@pytest.mark.parametrize('mutant',['duplicate_ACK','wrong_owner','early_ACK','scale_mask','address_alias'])
def test_actual_writer_contract_mutants_fail(events,mutant):
    e=copy.deepcopy(events)
    if mutant=='duplicate_ACK':e.append(next(x.copy() for x in e if x['kind']=='write_ack'))
    if mutant=='wrong_owner':next(x for x in e if x['kind']=='write_ack')['tag']^=1<<16
    if mutant=='early_ACK':next(x for x in e if x['kind']=='write_ack')['cycle']-=1
    if mutant=='scale_mask':next(x for x in e if x['kind']=='request' and x['strobe']!=4294967295)['strobe']=0
    if mutant=='address_alias':next(x for x in e if x['kind']=='request')['address']%=264320-2000
    with pytest.raises(ValueError):m.validate_writer(e)
def test_budget_is_not_old_known_impossible_cap():
    x=m.build();b=x['new_bounded_budget_proposal'];p=x['measured_profile']
    assert b['shared_compile_seconds']>p['frontend_wall_seconds']+p['baseline_CXX_seconds']
    assert b['generated_aggregate_bytes']>p['generated_bytes']
    assert b['shared_compile_seconds']+b['runtime_cases']*b['runtime_seconds_each']+b['reserve_seconds']==b['whole_seconds']
    assert b['fresh_GO_required'] and not b['auto_retry']
    assert x['new_builds']==0 and not x['physical_visibility']
