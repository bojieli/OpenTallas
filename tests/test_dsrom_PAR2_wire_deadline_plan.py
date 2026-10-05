import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('wire',Path(__file__).parents[1]/'tools/dsrom_PAR2_wire_deadline_plan.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

def event(identity='a',ready=0,deadline=1,bits=108):
    return dict(identity=identity,ready=ready,deadline=deadline,bits=bits)

def test_source_conservation_and_no_qualification():
    m=M.build()
    assert m['root']['total_rows']==576
    assert m['root']['peak_proposed_payload_bits_per_edge']==6912
    assert m['cfg']['aggregate_payload_bits_per_shard']==2048*25*48
    assert m['wholephase_exposed_delta'] is None
    assert not m['RTL_build_admitted'] and not m['fulltoken_rate']

def test_registered_delivery_not_same_edge():
    r=M.shared_link([event()],108,1,1)[0]
    assert r['sample']==3 and r['exposed_edges']==2

def test_peer_domains_do_not_overlap_on_shared_link():
    r=M.shared_link([event('cfg'),event('root')],108,1,2)
    assert [x['sample'] for x in r]==[3,4]

def test_finite_lease_overflow():
    with pytest.raises(ValueError,match='overflow'):
        M.shared_link([event('a'),event('b')],108,1,1)

def test_same_edge_release_not_credit():
    with pytest.raises(ValueError,match='overflow'):
        M.shared_link([event('a'),event('b',ready=3,deadline=5)],108,1,1)

@pytest.mark.parametrize('bw,lat,cap',[(0,1,1),(108,0,1),(108,1,0)])
def test_missing_positive_provider_refused(bw,lat,cap):
    with pytest.raises(ValueError):M.shared_link([event()],bw,lat,cap)
