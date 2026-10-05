import sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_i64_codec_calendar_r22 as B

@pytest.fixture(scope='module')
def result():return B.join()

def test_source_match_full_graph_and_all_wide_symbols(result):
    m,ps,events=result
    assert m['source_match'] and m['affected_PCs']==144 and m['split64_symbols']==432
    assert len(ps)==144 and m['proof']['events']==108441
    assert m['proof']['dependency_edges']==356675
    assert m['proof']['status']=='PASS_FINITE_INTERVAL_PROOF'
    assert m['source_primitive_counts_unchanged'] and m['source_scratch_homes_unchanged']

def test_highword_traffic_not_hidden_and_all_added_terms_positive(result):
    m,ps,events=result
    assert m['traffic']['highword_read_sectors']==3704832
    assert m['traffic']['highword_write_sectors']==3704832
    assert m['capacity']['upper32_sidecar_bytes_per_rank']==1572864
    assert m['added_software_ticks']>0
    assert not any(m['no_admission'].values())
    def walk(nodes):
        for n in nodes:
            if n['kind']=='loop':yield from walk(n['body'])
            else:yield n
    affected=[n for p in ps.values() for n in walk(p['primitive_tree']) if 'split64_provider_bindings' in n]
    assert affected
    assert all(all(v>0 for v in n['stage_cycles'].values()) for n in affected)
    assert all(n['split64_intervals']['no_timer_publication'] for n in affected)

def case():
    d,m=B.inputs();k=next(iter(d['native_programs']));pc,rank=d['program_pc_rank'][k];homes={h['symbol']:h for h in d['wide_homes'] if (h['pc'],h['rank'])==(pc,rank)};costs=dict(m['endpoint_cycles']['values']);costs['I64_codec_split_join']=32
    return d['native_programs'][k],homes,costs

def test_missing_or_zero_codec_cost_rejected():
    p,h,c=case();c['I64_codec_split_join']=0
    with pytest.raises(ValueError):B.augment(p,h,c)

def test_aliasing_highword_provider_rejected():
    p,h,c=case();a=next(iter(h.values()));a['highword_base']=a['base']
    with pytest.raises(ValueError):B.augment(p,h,c)

def test_model_does_not_mutate_source_program_or_homes():
    p,h,c=case();before=copy.deepcopy(p);homes=copy.deepcopy(h)
    new,t=B.augment(p,h,c)
    assert p==before and h==homes and new['duration']>p['duration']
