import gzip,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_pc10_engine_r44 as m
from ds_hbm_bound_engine_r43 import bound_tiled_class
from h3_ds_connected_provider_r37 import peer
from h3_ds_checkpoint_provider_r30 import Provider
from hbm_bound_event_journal_r30 import JournalBudget
from ds_hbm_storage_home_binding_r41 import bind_storage

@pytest.fixture(scope='module')
def artifacts(tmp_path_factory):
    def load(p):return json.loads(gzip.decompress(p.read_bytes()))
    original_path=ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
    original=load(original_path)
    D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs'
    manifest=load(D/'prefix_input_manifest.json.gz')
    native,homes,_,_=bind_storage(original,load(D/'actual_DeepSeek_homes.json.gz')['homes'],manifest)
    path=tmp_path_factory.mktemp('bound')/'native.json.gz'
    path.write_bytes(gzip.compress(json.dumps(native,sort_keys=True).encode(),mtime=0))
    return original,native,homes,manifest,path,original_path

@pytest.fixture
def engine(artifacts,tmp_path):
    original,native,homes,manifest,path,op=artifacts
    p=object.__new__(Provider);p.native=native;p.homes=homes;p.manifest=manifest
    p.generation=manifest['generation'];p.revision=manifest['checkpoint_revision'];p.locations={}
    p.journal_budget=JournalBudget(tmp_path/'journal',131072)
    R=ROOT/'results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz'
    from ds_hbm_source_prefix_r43 import driver_class
    e=m.engine_class(driver_class(),finite_pc10=True)(native,json.loads(gzip.decompress(R.read_bytes())),p,p.revision,p.generation,homes,native_artifact_path=path,original_native_artifact_path=op,dispatch_artifact_path=R)
    yield e,p
    p.journal_budget.db.close()


def test_opt_in_full_constructor_preserves40groups_and_exact_calendar_source(engine):
    e,p=engine
    assert len(e.groups.plan.parents)==40 and e.retired==set()
    assert e.groups.endpoint.lineage=='R41_full_source_regeneration'
    assert e.groups.calendar_continuation.run.__func__ is peer('h4_c0_ds_tiled_continuation').TiledContinuation.run
    assert e.groups.calendar_continuation.__dict__ is e.groups.bound.__dict__
    assert e.groups.endpoint.provider is p and e.groups.shared.memories=={}
    assert p.journal_budget.db.execute('select count(*) from event').fetchone()[0]==0

@pytest.mark.parametrize('case',['not_retired','absent_producer','identity','result','completed'])
def test_refusal_before_any_mutable_provider_effect(engine,case):
    e,p=engine;g=e.groups
    identity=g.endpoint.identity(0);view=g.plan.parents[10]['writes'][0]['native_result_binding']
    if case!='not_retired':e.retired.update(range(10))  # metadata refusal control only; no producer data
    if case=='identity':identity=dict(identity,generation=2)
    if case=='result':view={}
    if case=='completed':g.completed.add((10,0,p.generation))
    before=set(g.completed)
    with pytest.raises(ValueError):g.run(10,0,generation=p.generation,identity=identity,source_store_view=view)
    assert g.completed==before and p.locations=={} and g.shared.memories=={}
    assert p.journal_budget.db.execute('select count(*) from event').fetchone()[0]==0


def test_default_keeps_reference_unchanged():
    class Prefix:pass
    assert m.engine_class(Prefix).__name__=='Engine'
    assert not hasattr(m.engine_class(Prefix),'pc10_endpoint_scope')
    with pytest.raises(ValueError,match='port-bound'):m.engine_class(Prefix,finite_pc10=True,physical_backend=True)
    with pytest.raises(ValueError,match='boolean'):m.engine_class(Prefix,finite_pc10=1)


def test_resource_counts_and_primitive_pins():
    x=m.resource_model()
    assert x['sector32_transactions']==1769472
    assert x['scratch64_commands']==884736 and x['shared_reserved_bytes']==201326592
    assert x['shared_payload_bytes']==56623104 and x['RF_source_payload_bytes']==25165824
    assert not x['hardware_admitted'] and x['physical_primitive_endpoint_latency'] is None
    assert set(m.primitive_sources())=={'bounded_native','arithmetic_helpers'}
