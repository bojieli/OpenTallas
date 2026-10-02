import copy
import hashlib
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h3_deepseek_full_token_driver as D
import h3_deepseek_complete_native as N


def allocation():return {'AW':27,'bytes':33554432,'base':33554432,'occupied_extents':[{'base':0,'bytes':33554432}]}

@pytest.mark.parametrize('change',[{'AW':34},{'bytes':33554431},{'base':1},{'base':1<<27},{'occupied_extents':None},{'occupied_extents':[{'base':33554432,'bytes':32}]}])
def test_noalias_aw27_workspace_refuses_unbound_or_wrapping(change):
    with pytest.raises(ValueError):D.workspace_extent({**allocation(),**change})


def test_exact_checkpoint_revision_rejected_before_primitive_execution():
    spec={'shape':[2],'dtype':'U32'};binding={'kind':'immutable_weight_provider','logical_tensor':'layer.weight'}
    view={'field':'weight_codes','kind':binding['kind'],'rank':0,'generation':3,'provenance_certified':True,'logical_tensor':binding['logical_tensor'],'revision':'wrong','data':np.ones(2,np.uint32)}
    with pytest.raises(ValueError,match='checkpoint revision'):D.validate_view('weight_codes',view,binding,spec,0,3,'exact_revision')
    view['revision']='exact_revision';assert D.validate_view('weight_codes',view,binding,spec,0,3,'exact_revision') is view['data']


def fixture():
    b=N.Builder();x=b.load('x',(2,));b.output('out',b.op('FMUL',x,b.const(.5)));p=b.finish();p['family']='driver_protocol_control'
    binding={'kind':'versioned_operand','version':'x_v0','native_address_view':'owned2'}
    op={'pc':0,'family':p['family'],'dependencies':[],'reads':[{'version':'x_v0'}],'rank_bindings':[{'rank':0,'template':'t','buffer_programs':[]}],'provider_bindings':{'t':{'x':binding}},'writes':[{'version':'y_v1','home_indices':[0],'native_result_binding':{'result':'out'}}]}
    return {'instructions':[op],'templates':{'t':p}}, {'PC_dispatch':[{'pc':0,'family':p['family']}]},[{'version':'y_v1','rank_group':[0]}]


class ProtocolControlProvider:
    # This is a lifecycle control, explicitly NOT a checkpoint/causal-provider
    # qualification. Actual full-token plugin remains mandatory and separate.
    def __init__(self):self.log=[];self.output=None;self.mutant=None
    def workspace(self,rank):return allocation()
    def read_views(self,op,owned,generation):
        return {'x':{'field':'x','rank':0,'generation':generation,'kind':'versioned_operand','provenance_certified':True,'version':'x_v0','view_contract':'owned2','data':np.asarray([2.,4.],np.float32)}}
    def scratch_memory(self,owner,extent):
        m=N.PersistentMemory(credits=1);m.workspace_extent=extent;return m
    def publish(self,identity,fields,view):
        self.output=fields['data'].copy();self.log.append('publish')
        r={'identity':identity,'payload_sha256':{k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in fields.items()},'events':[{'identity':identity,'event':event,'sequence':i} for i,event in enumerate(['software_backing_visible','consumer_accept','validated_reverse_grant'])],'pending_obligations':0}
        if self.mutant=='held':r['pending_obligations']=1
        if self.mutant=='stale':r['identity']={**identity,'generation':identity['generation']-1}
        if self.mutant=='payload':r['payload_sha256']['data']='bad'
        if self.mutant=='early':r['events'][0]['event']='logical_WR_ACK'
        return r
    def release_views(self,*args):self.log.append('release_views')
    def retire_operation(self,pc,generation):
        self.log.append('retire');return {'PC':pc,'generation':generation,'pending_obligations':0,'source_consumers_released':True}
    def release_version(self,*args):self.log.append('release_version')
    def drain(self,generation):return {'generation':generation,'pending_obligations':0,'live_consumers':0}


def test_driver_executes_primitive_then_publication_and_last_consumer_retirement():
    provider=ProtocolControlProvider();native,dispatch,homes=fixture()
    r=D.TokenDriver(native,dispatch,provider,'revision',3,homes).run()
    assert np.array_equal(provider.output,np.asarray([1.,2.],np.float32))
    assert provider.log==['publish','release_views','retire','release_version']
    assert r['PCs_retired']==1 and not r['physical_visibility_qualified']

@pytest.mark.parametrize('mutant',['held','stale','payload','early'])
def test_actual_publication_contract_failure_does_not_retire_source_or_release_inputs(mutant):
    provider=ProtocolControlProvider();provider.mutant=mutant;native,dispatch,homes=fixture()
    driver=D.TokenDriver(native,dispatch,provider,'revision',3,homes)
    with pytest.raises(ValueError):driver.run()
    assert not driver.retired and provider.log==['publish']


def test_changed_dependency_and_home_identity_cannot_retire():
    provider=ProtocolControlProvider();native,dispatch,homes=fixture();native['instructions'][0]['dependencies']=[7]
    with pytest.raises(ValueError,match='dependency'):D.TokenDriver(native,dispatch,provider,'revision',3,homes).run()
    native['instructions'][0]['dependencies']=[];homes[0]['version']='other_version'
    with pytest.raises(ValueError,match='home/version'):D.TokenDriver(native,dispatch,provider,'revision',3,homes).run()


def test_full_source_driver_pins_and_scope_no_payload_or_operator_callbacks():
    native,dispatch,homes=D.load_programs()
    assert len(native['instructions'])==2213 and len(native['coverage']['families'])==30
    assert len(homes)==286114 and dispatch['automatic_scalar_fallback_templates']==0
    text=(ROOT/'tools/h3_deepseek_full_token_driver.py').read_text()
    assert 'h3_deepseek_streaming_linear' in text and 'hdc_golden' not in text


def test_collective_buffers_have_distinct_scratch_owners_and_publications():
    p=N.recipe('all_gather',{'n':2,'ranks':2},{});p['family']='all_gather'
    binding={'parts':{'kind':'versioned_operand','version':'a0','native_address_view':'owned_masks'},'ownership_mask':{'kind':'explicit_auxiliary_provider','identity_from_versions':['a0','b0']}}
    op={'pc':0,'family':'all_gather','dependencies':[],'reads':[{'version':'a0'},{'version':'b0'}],'rank_bindings':[{'rank':0,'template':'t','buffer_programs':[{'template':'t','read_version':'a0','write_version':'a1'},{'template':'t','read_version':'b0','write_version':'b1'}]}],'provider_bindings':{'t':binding},'writes':[{'version':v,'home_indices':[i],'native_result_binding':{'result':'out'}} for i,v in enumerate(['a1','b1'])]}
    class P(ProtocolControlProvider):
        def __init__(self):super().__init__();self.owners=[];self.outputs=[]
        def read_views(self,op,owned,generation):
            result={}
            for src,dst,factor in [('a0','a1',1),('b0','b1',10)]:
                common={'rank':0,'generation':generation,'provenance_certified':True}
                result[dst]={'parts':{**common,'field':'parts','kind':'versioned_operand','version':src,'view_contract':'owned_masks','data':np.diag(np.asarray([1,2],np.float32)*factor)},'ownership_mask':{**common,'field':'ownership_mask','kind':'explicit_auxiliary_provider','source_binding':{'kind':'explicit_auxiliary_provider','identity_from_versions':[src]},'data':np.eye(2,dtype=np.uint32)}}
            return result
        def scratch_memory(self,owner,extent):self.owners.append(owner);return super().scratch_memory(owner,extent)
        def publish(self,identity,fields,view):self.outputs.append(fields['data'].copy());return super().publish(identity,fields,view)
    provider=P();homes=[{'version':v,'rank_group':[0]} for v in ['a1','b1']]
    r=D.TokenDriver({'instructions':[op],'templates':{'t':p}},{'PC_dispatch':[{'pc':0,'family':'all_gather'}]},provider,'revision',3,homes).run()
    assert provider.owners[0]!=provider.owners[1]
    assert np.array_equal(provider.outputs[0],np.asarray([1,2],np.float32))
    assert np.array_equal(provider.outputs[1],np.asarray([10,20],np.float32))
    assert r['PCs_retired']==1
