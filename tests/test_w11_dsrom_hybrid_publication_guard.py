import copy
import pytest
import w11_dsrom_hybrid_publication_guard as G

def state():
    return dict(mask=(1<<1024)-1,init_done=True,fill_accepted=True,fill_done=True,backend_visible=True,
        consumer_read_captured=True,slot_drained=True,owning_credit_returned=True)

def check(tag=None,s=None,bits=None,vector=0):
    return G.validate_fill(G.identity(0,14,7,9) if tag is None else tag,vector,
        G.retained_vector(vector) if bits is None else bits,state() if s is None else s,
        owner_rank=0,owner_layer=14,owner_generation=7,owner_lease=9)

def test_source_bound_visible_consumed_and_owning_credit_are_distinct():
    s=state();s.update(fill_done=False,backend_visible=False,consumer_read_captured=False,slot_drained=False,owning_credit_returned=False)
    r=check(s=s);assert r['software_fill_accepted'] and not r['software_value_visible'] and not r['software_slot_reuse_allowed']
    s.update(fill_done=True,backend_visible=True)
    r=check(s=s);assert r['software_consumer_read_allowed'] and not r['software_slot_reuse_allowed']
    s.update(consumer_read_captured=True,slot_drained=True)
    assert not check(s=s)['software_slot_reuse_allowed']
    s['owning_credit_returned']=True
    assert check(s=s)['software_slot_reuse_allowed'] and not check(s=s)['actual_hardware_publication_allowed']

@pytest.mark.parametrize('field',['rank','logical_layer','reset_generation','lease','source_checkpoint_image_sha256','program_sha256','slot'])
def test_stale_or_wrong_owner_identity_rejected(field):
    t=G.identity(0,14,7,9);t[field]='wrong'
    with pytest.raises(ValueError,match='tag mismatch'):check(tag=t)

@pytest.mark.parametrize('field',['init_done','fill_accepted','fill_done','backend_visible','consumer_read_captured','slot_drained','owning_credit_returned'])
@pytest.mark.parametrize('unknown',[None,1,'X'])
def test_unknown_completion_never_publishes_or_releases(field,unknown):
    s=state();s[field]=unknown
    with pytest.raises(ValueError,match='unknown/nonboolean'):check(s=s)

def test_mask_bits_and_vector_order_failures():
    s=state();s['mask']^=1
    with pytest.raises(ValueError,match='mask'):check(s=s)
    b=bytearray(G.retained_vector(0));b[0]^=1
    with pytest.raises(ValueError,match='bits/vector'):check(bits=bytes(b))
    with pytest.raises(ValueError,match='bits/vector'):check(bits=G.retained_vector(1))

def test_l1_and_actual_uninstantiated_provider_block_publication():
    with pytest.raises(ValueError,match='L1 retained'):G.identity(0,1,7,9)
    with pytest.raises(ValueError,match='provider absent'):G.actual_binding_required()
    r=G.build();assert r['candidate_dense_owner_count']==160 and r['field_stage40_dense_CROM_words']==0
    assert not r['hardware_admission'] and not r['current_L0_L20_publication_credit']
    assert r['actual_warm_token_cycles'] is None and r['headnorm_eight_heads_provider'] is None

def test_credit_cannot_skip_visibility_capture_or_drain():
    for field in ['init_done','fill_accepted','fill_done','backend_visible','consumer_read_captured','slot_drained']:
        s=state();s[field]=False
        with pytest.raises(ValueError):check(s=s)
