import gzip,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_unconsumed_retirement_r45 as m


def test_exact_full_native_orphan_has_no_consumer_or_manifest_reference():
    O=ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
    D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/prefix_input_manifest.json.gz'
    n=json.loads(gzip.decompress(O.read_bytes()));manifest=json.loads(gzip.decompress(D.read_bytes()))
    homes=json.loads(gzip.decompress((ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs/actual_DeepSeek_homes.json.gz').read_bytes()))['homes']
    p=m.retirement_plan(n,manifest,homes)
    assert 'DeepSeek.8.o.65' in p[8]
    assert 'DeepSeek.8.o_own.66' not in p[8]
    assert 'DeepSeek.9.zpart.67' not in p[9]

@pytest.mark.parametrize('where',['reads','provider','future_source','manifest'])
def test_any_explicit_or_unknown_version_reference_prevents_release(where):
    n={'instructions':[dict(pc=0,writes=[{'version':'out','home_indices':[0]}],source_outputs=[{'version':'out','home_indices':[0]}])]}
    manifest={}
    if where=='manifest':manifest={'future_reader':'out'}
    else:n['instructions'].append(dict(pc=1,writes=[],**{where:['out']}))
    assert m.retirement_plan(n,manifest,[dict(version='out',birth_pc=0,retire_pc=0)])[0]==[]


def protocol_fixture(*,fail=False,leased=False):
    order=[];op=dict(pc=8,rank_bindings=[dict(rank=0)],writes=[{'version':'unused','home_indices':[0]}],source_outputs=[{'version':'unused','home_indices':[0]}])
    class Provider:
        manifest={}
        witness=SimpleNamespace(failed=False,seen={(8,'unused',0,1,'data')})
        rf={};state={}
        def _leased(self,v):return leased
        locations={'unused':'held'}
        def release_version(self,v,g):
            order.append('release')
            if leased:raise ValueError('version still leased')
            self.locations.pop(v)
    class Base:
        def __init__(self):
            self.native={'instructions':[op]};self.homes=[dict(version='unused',birth_pc=8,retire_pc=8)];self.provider=Provider();self.retired=set();self.last_use={}
            self.generation=1;self.journal=[]
        def execute_operation(self,op):
            order.append('producer')
            if fail:raise ValueError('reverse debt')
            self.retired.add(op['pc']);order.append('producer_retired')
    return m.retirement_class(Base)(),op,order


def test_release_follows_actual_base_terminal():
    e,op,order=protocol_fixture();e.execute_operation(op)
    assert order==['producer','producer_retired','release']
    assert e.provider.locations=={} and e.unconsumed_retired=={(8,'unused')}


def test_producer_refusal_retains_output_and_no_release():
    e,op,order=protocol_fixture(fail=True)
    with pytest.raises(ValueError,match='reverse debt'):e.execute_operation(op)
    assert order==['producer'] and e.provider.locations=={'unused':'held'} and e.journal==[]


def test_live_lease_refusal_retains_output_and_no_retirement_record():
    e,op,order=protocol_fixture(leased=True)
    with pytest.raises(ValueError,match='still leased'):e.execute_operation(op)
    assert e.provider.locations=={'unused':'held'} and e.unconsumed_retired==set() and e.journal==[]

@pytest.mark.parametrize('gate',['witness','home','debt'])
def test_missing_witness_retire_edge_or_owner_drain_refuses_release(gate):
    e,op,order=protocol_fixture()
    if gate=='witness':e.provider.witness=SimpleNamespace(failed=False,seen=set())
    if gate=='home':
        e.homes[0]['retire_pc']=9
        e.unconsumed_plan=m.retirement_plan(e.native,e.provider.manifest,e.homes)
        e.execute_operation(op)
        assert 'release' not in order and e.provider.locations=={'unused':'held'}
        return
    if gate=='debt':e.provider.rf={0:SimpleNamespace(live={'owned':1},queue=[],calendar=[],resident=0)}
    with pytest.raises(ValueError):e.execute_operation(op)
    assert 'release' not in order and e.provider.locations=={'unused':'held'}
