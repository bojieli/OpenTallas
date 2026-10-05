import importlib.util,gzip,json
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('descriptor',Path(__file__).resolve().parents[1]/'tools/w17_compact_descriptor_price.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@pytest.fixture(scope='module')
def model():return m.build()

def test_owner_lookup_tables_preserve_entire_actual_candidate(model):
    c=json.loads(gzip.decompress(m.blob(m.PINS['candidate'])))
    for t in model['owner_lookup']['tables']:
        assert t['padding_value']==0 and t['padding_entries']==128
        for e,word in enumerate(t['entries']):
            o=c['owners'][m.owner_index(t['layer'],e)]
            assert word>>15==1 and (word>>9)&63==o['stage'] and word&511==o['slot']
    for l,e in ((40,0),(0,384),(-1,0),(0,-1)):
        with pytest.raises(ValueError):m.owner_index(l,e)

def test_descriptor_overflow_and_explicit_new_service(model):
    f=model['dense_existing_failures'];assert f['full_stage_appended_stream_words']==76384
    assert f['first_stream_base_overflow']==dict(slot=292,family='w2',stream_base=65568,phase_index=878)
    assert f['rejected_stream_bases']==145
    assert model['template_storage']['spine_stream_template_words']==224
    s=model['service_candidate'];assert s['one_expert_three_family_cfg_plus_stream_cycles']==323
    assert s['cfg_load_cycles']==27 and s['perpair_parallel_affine_precompute_cycles']==6
    assert s['fullstage_cfg_bits_per_cycle_including_reserved_BF_clear']==4773*48
    assert not model['interface_change']['existing_PHW6_compatible']
    assert not model['physical_admission'] and not model['engine_RTL_build_ready']
    assert s['actual_complete_stage_cycles'] is None and s['root_stop_cycles'] is None

def test_affine_address_intermediates_never_need_truncation(model):
    c=json.loads(gzip.decompress(m.blob(m.PINS['candidate'])))
    prefix={}
    for family in ('w1','w3','w2'):
        for p in c['templates'][family]['pairs']:
            pair=p['pair'];stride=c['pair_stride'][str(pair)]
            base=340*stride+prefix.get(pair,0)
            assert base+(p['logical_words_per_mate']-1)<8192
            assert base<1<<model['affine_address_generation']['product_and_base_bits']
            prefix[pair]=prefix.get(pair,0)+p['logical_words_per_mate']
    assert all(prefix[int(pair)]==stride for pair,stride in c['pair_stride'].items())
