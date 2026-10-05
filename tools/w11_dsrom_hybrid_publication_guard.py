"""Source-bound software fill/visibility/lease contract; no actual provider credit."""
import argparse
import gzip
import json
import struct
from pathlib import Path
import w11_dsrom_stage_crom_union as U

HYBRID=('f1af146d6b40c2341a95da483d3650b878068e7c','results/quality/w16_engram_initializer_20261001/hybrid_topology.json')
PRODUCT=('60545ff45','results/uarch/w11_engram_product_source_20261001/L14.product.crom64-logical-slice.bin.gz')

def actual_binding_required():
    model,_=U.load(HYBRID)
    if model['hybrid']['actual_read_capture_ack_provider'] is None or model['hybrid']['current_adapter_EXT_input_connected'] is not True:
        raise ValueError('actual cache/ACK/provider absent; hardware publication prohibited')
    if model['hardware_admission'] is not True:
        raise ValueError('hybrid model not admitted')
    return True

def identity(rank,layer,reset_generation,lease):
    if type(rank) is not int or rank not in range(4) or type(layer) is not int or layer not in (1,14):
        raise ValueError('rank/logical-layer identity')
    if any(type(x) is not int or not 0<=x<2**32 for x in (reset_generation,lease)):
        raise ValueError('reset generation/lease identity')
    if layer==1: raise ValueError('L1 retained source absent; invalid coefficients cannot publish')
    model,mref=U.load(HYBRID);program,pref=U.load(U.PROGRAM);manifest,iref=U.load(U.MANIFEST,True)
    if dict(field_stage=layer,logical_layer=layer,rank=rank) not in model['topology']['dense_cache_owners']:
        raise ValueError('physical owner candidate identity')
    return dict(rank=rank,logical_layer=layer,field_stage=layer,reset_generation=reset_generation,
        lease=lease,slot=3,source_checkpoint_image_sha256=manifest['rank_images'][rank]['image_sha256'],
        program_sha256=program['ranks'][rank]['encoded_template_sha256'],
        hybrid_model_sha256=mref['decoded_sha256'],product_crom64_sha256='f2297940486c2604a7a4baf8887ed319c264f77cb10ccc3f164c16e01182f377',
        physical_image_sha256=None,actual_owner_provider=None)

def retained_vector(vector):
    if type(vector) is not int or vector not in range(20): raise ValueError('product vector identity')
    raw=gzip.decompress(U.read(*PRODUCT))
    if len(raw)!=20480*8 or U.sha(raw)!='f2297940486c2604a7a4baf8887ed319c264f77cb10ccc3f164c16e01182f377':
        raise ValueError('immutable product image identity')
    words=struct.unpack('<20480Q',raw)
    if any(w>>32 for w in words): raise ValueError('CROM64 high-half zero contract')
    return struct.pack('<1024I',*words[vector*1024:(vector+1)*1024])

def validate_fill(tag,vector,fp32_bits,state,*,owner_rank,owner_layer,owner_generation,owner_lease):
    expected=identity(owner_rank,owner_layer,owner_generation,owner_lease)
    if tag!=expected: raise ValueError('source/rank/layer/reset/image/program/lease tag mismatch')
    if fp32_bits!=retained_vector(vector): raise ValueError('actual fill bits/vector order mismatch')
    if type(state.get('mask')) is not int or state['mask']!=(1<<1024)-1:
        raise ValueError('complete 1024-lane mask required')
    keys=['init_done','fill_accepted','fill_done','backend_visible','consumer_read_captured','slot_drained','owning_credit_returned']
    if any(type(state.get(k)) is not bool for k in keys): raise ValueError('unknown/nonboolean completion or owning acknowledgement')
    if state['fill_accepted'] and not state['init_done']: raise ValueError('init/reset fence precedes acceptance')
    if state['fill_done'] and not state['fill_accepted']: raise ValueError('completion precedes acceptance')
    if state['backend_visible'] and not state['fill_done']: raise ValueError('visibility precedes write completion')
    if state['consumer_read_captured'] and not state['backend_visible']: raise ValueError('capture precedes visibility')
    if state['slot_drained'] and not state['consumer_read_captured']: raise ValueError('drain precedes capture')
    if state['owning_credit_returned'] and not state['slot_drained']: raise ValueError('owning credit precedes consumer drain')
    return dict(software_fill_accepted=state['fill_accepted'],software_value_visible=state['backend_visible'],
        software_consumer_read_allowed=state['backend_visible'],
        software_slot_reuse_allowed=state['owning_credit_returned'] and state['slot_drained'],
        actual_hardware_publication_allowed=False,actual_provider=None,
        packet_credit_alone_releases_consumer_slot=False,logical_product_global_range=[529280+vector*1024,529280+(vector+1)*1024],
        slot=3,vector=vector,FP32_bits_sha256=U.sha(fp32_bits))

def build():
    model,mref=U.load(HYBRID);program,pref=U.load(U.PROGRAM);manifest,iref=U.load(U.MANIFEST,True)
    sources=[]
    for rank in range(4):
        sources.append(dict(rank=rank,checkpoint_image_sha256=manifest['rank_images'][rank]['image_sha256'],
            original_program_sha256=program['ranks'][rank]['encoded_template_sha256']))
    return dict(schema='w11.hybrid-publication-guard.v1',source_pins=[mref,pref,iref],
        product_commit=PRODUCT[0],product_path=PRODUCT[1],
        product_vector_FP32_sha256=[U.sha(retained_vector(v)) for v in range(20)],rank_sources=sources,
        candidate_dense_owner_count=len(model['topology']['dense_cache_owners']),
        field_stage40_dense_CROM_words=model['topology']['field_stage40']['dense_CROM_cache_words'],
        headnorm_eight_heads_provider=model['topology']['head']['actual_norm_home_to_eight_heads_mapping'],
        source_L1_valid=False,L1_global_invalid_range=[508800,529280],
        gamma_words=10240,other_persistent_slots=[0,1,2],product_stream_slot=3,
        product_words_per_slot=1024,product_vectors_per_command=20,
        reset_init_visibility_and_owning_lease_fences_explicit=True,
        packet_credit_distinct_from_slot_release=True,actual_cache_module=None,
        actual_ack_provider=None,actual_physical_image_sha256=None,
        current_L0_L20_publication_credit=False,hardware_admission=False,image_admission=False,
        actual_TTFT=None,actual_warm_token_cycles=None,checkpoint_payload_reads=0,jobs_launched=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
    if out.exists(): raise ValueError('preserve previous evidence')
    out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
