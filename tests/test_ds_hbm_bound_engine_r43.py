import copy,gzip,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from ds_hbm_storage_home_binding_r41 import bind_storage
from ds_hbm_bound_engine_r43 import validate_lineage,bound_tiled_class,engine_class
from ds_hbm_source_prefix_r42 import driver_class
from h3_ds_checkpoint_provider_r30 import Provider
from hbm_bound_event_journal_r30 import JournalBudget
from h3_ds_connected_provider_r37 import peer
R=ROOT/'results/uarch/ds_hbm_bound_engine_r43_20261002'
D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002'
O=ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
def load(p):return json.loads(gzip.decompress(p.read_bytes()))
@pytest.fixture(scope='module')
def artifacts(tmp_path_factory):
    original=load(O);homes=load(D/'inputs/actual_DeepSeek_homes.json.gz')['homes'];m=load(D/'inputs/prefix_input_manifest.json.gz')
    native,homes,_,_=bind_storage(original,homes,m)
    path=tmp_path_factory.mktemp('bound-artifact')/'bound_native.json.gz'
    path.write_bytes(gzip.compress(json.dumps(native,sort_keys=True).encode(),mtime=0))
    return native,homes,m,path
@pytest.fixture
def owner(artifacts,tmp_path):
    native,homes,m,path=artifacts;p=object.__new__(Provider)
    p.native=native;p.homes=homes;p.manifest=m;p.generation=m['generation'];p.revision=m['checkpoint_revision'];p.journal_budget=JournalBudget(tmp_path/'journal',131072)
    yield p,path
    p.journal_budget.db.close()

def test_bound_engine_constructor_all40_group_contracts_no_execution(owner):
    p,path=owner;dispatch=load(R/'inputs/actual_dispatch_bcf.json.gz')
    engine=engine_class(driver_class())(p.native,dispatch,p,p.revision,p.generation,p.homes,native_artifact_path=path,dispatch_artifact_path=R/'inputs/actual_dispatch_bcf.json.gz',original_native_artifact_path=O)
    assert len(engine.groups.plan.parents)==40 and len(engine.allocations)==96
    assert engine.groups.lineage['only_home_indices_changed']
    assert engine.groups.bridge.source_sha==engine.groups.lineage['bound_native_content_sha256']
    assert engine.retired==set() and engine.groups.completed==set()
    assert p.journal_budget.db.execute('select count(*) from event').fetchone()[0]==0

@pytest.mark.parametrize('mutation',['unbound_path','bad_original','bad_bound','memory_home','memory_arithmetic','directory'])
def test_native_artifact_or_memory_mismatch_is_refused(owner,tmp_path,mutation):
    p,path=owner;original=O
    if mutation=='unbound_path':path=O
    if mutation=='bad_original':original=tmp_path/'wrong-original.gz';original.write_bytes(b'wrong')
    if mutation=='bad_bound':path=tmp_path/'wrong-bound.gz';path.write_bytes(b'wrong')
    if mutation in ('memory_home','memory_arithmetic'):
        p.native=copy.deepcopy(p.native)
        if mutation=='memory_home':p.native['instructions'][5]['writes'][-1]['home_indices']=[]
        else:p.native['templates'][next(iter(p.native['templates']))]['code'][0]['attrs']['dtype']='I64'
    if mutation=='directory':p.homes=copy.deepcopy(p.homes);p.homes[-1]['binding']['base']+=512
    with pytest.raises(ValueError):validate_lineage(p,original_native_artifact_path=original,bound_native_artifact_path=path)
    assert p.journal_budget.db.execute('select count(*) from event').fetchone()[0]==0

@pytest.mark.parametrize('field',['template','provider','writer','rank'])
def test_original_group_contract_checks_remain_mandatory(owner,monkeypatch,field):
    p,path=owner;module=peer('h4_c0_ds_tiled_continuation');old=module.GroupOperandTiles
    class Mutant(old):
        def __init__(self):
            super().__init__();self.parents=copy.deepcopy(self.parents);pc=next(iter(self.parents));row=self.parents[pc]
            if field=='template':row['new_template']='unapproved'
            if field=='provider':row['provider_bindings']={}
            if field=='writer':row['writes']=[]
            if field=='rank':row['actual_rank_template_bindings']=[]
    monkeypatch.setattr(module,'GroupOperandTiles',Mutant)
    with pytest.raises(ValueError,match='actual current'):bound_tiled_class()(p,native_artifact_path=path,original_native_artifact_path=O)
    assert p.journal_budget.db.execute('select count(*) from event').fetchone()[0]==0
