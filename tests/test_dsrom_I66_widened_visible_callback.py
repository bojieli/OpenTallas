import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_widened_visible_callback as M


def fields(user):
    return dict(generation=7,operation_sequence=9,owner_stage=1,packet_kind=2,
                packet_ordinal=3,payload_bits=576*63,rank=2,user=user,reserved=65535)


@pytest.mark.parametrize('user',[0,65535,65536,2**31,2**32-1])
def test_header144_keeps_user32_and_reserved16(user):
    assert M.decode(M.encode(fields(user)))==fields(user)
    assert M.encode(fields(user))!=M.encode(fields(user^65536))


def fixture():
    ctx=dict(stage=0,rank=0,expert=0,phase=10,key_word=2149580800,generation=7,user=65536,xversion=52,pc=66)
    pub=dict(context=ctx,row=128,physical_shard=1,address=1000,data=123,writer_kind='rom',writer_port=64)
    s=dict(parameters=dict(X_ROM=1,ROM_R=128,SUN=256,ROM_PHW=10,ROM_FBW=1632),edge=500,post_edge=500,pre_stage='preedge',post_stage='postNBA',sampled_writer_classes=list(M.WRITERS),
           reset_accepted=True,healthy=True,context=ctx,
           writes=[dict(kind='rom',port=64,address=1000,data=123)],post_VM={'1000':123})
    return s,pub


def test_concrete_local_visible_callback_no_runtime_credit():
    s,p=fixture();r=M.visible_callback(s,p)
    assert r['physical_shard']==1 and r['edge']==500
    assert not r['source_runtime_enrolled']


@pytest.mark.parametrize('bad',['same_value_competitor','alias','old_VM','stale','missing_writer_class','preNBA','wrong_edge','wrong_root','reset','unknown_writer'])
def test_false_owned_visibility_rejected(bad):
    s,p=fixture()
    if bad=='same_value_competitor':s['writes'].append(dict(kind='xb',port=0,address=1000,data=123))
    if bad=='alias':s['writes'][0]['address']+=2**19
    if bad=='old_VM':s['post_VM']['1000']=122
    if bad=='stale':s['context']=dict(s['context'],generation=8)
    if bad=='missing_writer_class':s['sampled_writer_classes'].pop()
    if bad=='preNBA':s['post_stage']='preedge'
    if bad=='wrong_edge':s['post_edge']+=1
    if bad=='wrong_root':p['writer_port']=63
    if bad=='reset':s['reset_accepted']=False
    if bad=='unknown_writer':s['writes'][0]['kind']='predicted_publish'
    with pytest.raises(ValueError):M.visible_callback(s,p)


def test_remote512_writepoint_does_not_qualify_lease_or_provider():
    s,p=fixture();s['writes']=[dict(kind='xa',port=0,address=a,data=123 if a==1000 else 0) for a in range(992,1008)]
    p['writer_kind']='xa';p['writer_port']=0
    assert not M.visible_callback(s,p)['remote_lease_qualified']


def test_source_plan_preserves_real_VM_semantics_and_unimplemented_provider():
    m=M.source_plan()
    assert m['candidate_header_bits']==144 and m['new_command_bits']==237
    assert m['native_callback']['no_hardware_write_reset_gate']
    assert not m['compiled_encoder_or_collector'] and not m['RTL_GO']


def test_unmasked_external_block_sample_cannot_drop_other15_words():
    s,p=fixture();s['writes'][0]['kind']='xa';s['writes'][0]['port']=0
    p['writer_kind']='xa';p['writer_port']=0
    with pytest.raises(ValueError,match='all16'):M.visible_callback(s,p)


def test_current_visibility_does_not_inherit_PHW6_or_bool_context():
    s,p=fixture();s['parameters']['ROM_PHW']=6
    with pytest.raises(ValueError):M.visible_callback(s,p)
    s,p=fixture();s['context']=dict(s['context'],stage=False)
    with pytest.raises(ValueError):M.visible_callback(s,p)
