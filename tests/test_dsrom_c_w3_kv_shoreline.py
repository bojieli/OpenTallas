import copy
import importlib.util
from pathlib import Path
import pytest

P=Path(__file__).resolve().parents[1]/'tools/dsrom_c_w3_kv_shoreline.py'
spec=importlib.util.spec_from_file_location('w3',P)
M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def fixture(tmp_path):
    source=tmp_path/'test_source'; source.write_text('synthetic test only')
    def row(die,layers,**extra):
        kinds=['head_state'] if die.startswith('head') else ['window_KV','row_gather']+(['index_scan'] if M.SCAN.intersection(layers) else [])
        c=dict(batch=216,state_bytes_per_user=1000,non_state_reserve_bytes=100,
               non_HBM_stage_us=1,controller_service_us=.1,
               transfers=[dict(kind=k,bytes_per_stage_service=1000,fixed_latency_us=1) for k in kinds])
        return dict(die=die,layers=layers,controller_pseudochannels_per_stack=16,
                    contexts={ctx:copy.deepcopy(c) for ctx in M.CONTEXTS},**extra)
    return dict(schema='DSROM_C_W2_W3_MAP_V1',kind='actual_W2_map',source_commit='a'*40,
                source_files=[dict(path=str(source),sha256=M.digest(source))],stages=73,ranks_per_stage=4,
                rank_dies=[row(f's{s}r{r}',[s] if s<43 else [],stage=s,rank=r) for s in range(73) for r in range(4)],
                head_dies=[row(f'head{i}',[]) for i in range(8)],head_bound_us={ctx:10 for ctx in M.CONTEXTS})


def run(m): return M.actual_map(m,20_250_000_000,1e12,10,12)


def test_provisional_capacity_has_no_adoption_or_latency_pass():
    r=M.run()
    assert r['provisional_allocation']['stacks_model_only']==420
    assert r['provisional_capacity'][0]['capacity']['headroom_bytes']==62_978_688
    assert r['gates']['batch216_capacity'] is None
    assert not r['adopted_420_stack_claim'] and not r['physical_launch_allowed']
    assert not r['non_scan_shoreline']['area_credit_applied']
    assert r['non_scan_shoreline']['freed_vs_four_historical_PHY_mm']==25.5
    assert r['non_scan_shoreline']['freed_vs_four_package_keepout_mm']==36


def test_exact_fixture_join_and_gate_model(tmp_path):
    r=run(fixture(tmp_path))
    assert r['total_stacks']==420 and all(r['gates'].values())
    assert r['allocation'][0]['controller_pseudochannels']==16
    assert r['allocation'][8]['controller_pseudochannels']==64


@pytest.mark.parametrize('mutation',['capacity','latency','busiest'])
def test_independent_failures_never_become_stack_adoption(tmp_path,mutation):
    m=fixture(tmp_path); c=m['rank_dies'][0]['contexts']['1048576']
    if mutation=='capacity': c['non_state_reserve_bytes']=21_000_000_000
    if mutation=='latency': c['transfers'][0]['bytes_per_stage_service']=2_000_000
    if mutation=='busiest': c['non_HBM_stage_us']=11
    key={'capacity':'batch216_capacity','latency':'one_stack_latency_bound','busiest':'busiest_stage'}[mutation]
    assert run(m)['gates'][key] is False


@pytest.mark.parametrize('mutation',['missing_die','duplicate_layer','missing_transfer','wrong_batch','stale_pin'])
def test_incomplete_or_stale_map_refused(tmp_path,mutation):
    m=fixture(tmp_path)
    if mutation=='missing_die': m['rank_dies'].pop()
    if mutation=='duplicate_layer': m['rank_dies'][4]['layers']=[0]
    if mutation=='missing_transfer': m['rank_dies'][0]['contexts']['1048576']['transfers'].pop()
    if mutation=='wrong_batch': m['rank_dies'][0]['contexts']['1048576']['batch']=1
    if mutation=='stale_pin': Path(m['source_files'][0]['path']).write_text('changed')
    with pytest.raises(ValueError): run(m)


def test_reserve_and_units_boundary():
    assert M.capacity(93_458_432,62_978_688,1,20_250_000_000)['fits']
    assert not M.capacity(93_458_432,62_978_689,1,20_250_000_000)['fits']
    with pytest.raises(ValueError): M.capacity(float('nan'),0,1,20_250_000_000)
