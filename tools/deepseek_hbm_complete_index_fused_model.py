"""Source-bound finite FP4 proof and unadmitted fused shared-service estimate.

No checkpoint reads, RTL, physical timing or whole-token latency qualification.
"""
import hashlib,json
from pathlib import Path
import numpy as np
import deepseek_hbm_complete_index_fused as F
import deepseek_hbm_complete_index_token_demand as T
ROOT=Path(__file__).resolve().parents[1]

def lattice_proof():
    # Actual index producer is E2M1 x UE8M0, not E4M3 x UE8M0.
    # Its normalized grid consists of these half-integer values after clip6.
    codes=np.array([0,.5,1,1.5,2,3,4,6,-0.,-.5,-1,-1.5,-2,-3,-4,-6],np.float64)
    checked=finite=exceptional=0
    for exponent in range(-126,127):
        with np.errstate(over='ignore'):
            before=(codes*np.exp2(exponent)).astype(np.float32)
            decoded=F.C.V.to_bf16(before)
        mask=np.isfinite(decoded);checked+=len(codes);finite+=int(mask.sum());exceptional+=int((~mask).sum())
        # Includes BF16 subnormals at exponent-126 and finite scale253.
        assert np.array_equal(decoded[mask],codes[mask]*np.exp2(exponent))
        assert np.all(decoded.view(np.uint32)[mask]&0xffff==0)
    return {'actual_producer':'hdc_golden_v41.qdq_fp4_e8m0, block32',
        'guard':'actual decoded query AND all returned key bits finite; producer version/source binding also required',
        'not_arbitrary_F32_domain':True,'normalized_codes':codes.tolist(),
        'scale_exponents':[-126,126],'scale_byte_range':[1,253],
        'finite_decoded_code_scale_pairs':finite,'excluded_actual_decoded_nonfinite_pairs':exceptional,
        'enumerated_pairs':checked,
        'derivation':[
            'amax floor6*2^-126 and finite F32 amax with rounded inv6 produce scale exponent -126..126. Exceptional producer e128/e129 is handled by continuation.',
            'clip6 and _round_grid(min_exp0,mant_bits1) produce half-integer E2M1 codes. Finite BF16 decode is exact on this grid, including subnormal2^-127 and finite scale253; overflow pairs are detected from decoded bits.',
            'Each value=u*2^(e-1), signed integer |u|<=12. Every product has integer coefficient at most144; every ordered partial of32 terms has absolute coefficient at most4608 (<2^13).',
            'Common dyadic product scale exponent is e_q+e_k-2 in[-254,250]. Nonzero products/partials are normal FP64, with magnitude below2^263 and at most13 significant bits. FP64 products, adds and FMA all exact irrespective grouping.',
            'Thus pinned full-shape BLAS block equals exact integer dot followed by one F32 RNE and source+0 canonicalization. Integer32 accumulation cannot overflow. No golden reassociation rounding is removed.',
            'F32 block overflow remains possible and is retained. Ordered four blocks plus four+0 pads, BF16, MAX signedzero/NaN policy, weighted multiply and chunk8/head tree execute explicit pinned IEEE wrappers. Finite inputs do not imply finite intermediates or weights.',
            'The suggested E4M3 bound229376 and partial bound32*229376^2<2^41 is a conservative different-producer argument, not the domain accepted by this E2M1 decoder. No E4M3 admission is claimed.'],
        'integer_max_partial':4608,'FP64_significand_bits':53,
        'full_hardware_producer_provenance_and_guard_epoch_qualified':False}

def model():
    q=np.ones((32,128),np.float32);keys=np.ones((2,128),np.float32);weights=np.ones(32,np.float32)
    prepared=F.prepare_query(q);_,receipt=F.scores(q,keys,weights,5456,True,prepared)
    def metrics(programs):
        return {'full_warp_slot_bytes':sum(p.metrics['shared_requested_bytes'] for p in programs),
                'shared_warp_issues':sum(p.metrics['shared_warp_issues'] for p in programs)}
    _,kg=F.classified(keys)
    parts={'query_bit_guard_once':metrics(prepared.query_classification),
        'query_decoder_once':metrics(prepared.query_decoders),
        'key_bit_guard_each_local2':metrics(kg),
        'key_masked_decoder_each_local2':metrics([F.decode_owned(keys[:,:32])[2] for _ in range(4)]),
        'fused_shader_each_local2':metrics([receipt['fused_kernel']])}
    # Explicit shared-interface obligations. Conservative full-slot accounting;
    # byte counters for masked STORE are slots, not measured active bytes.
    additions={'query_transpose_once':(32768,256),'query_scale_STORE_once':(512,4),
        'weights_refill_once':(256,2),'zero_word_init_once':(4,1),
        'key_scale_STORE_each_local2':(512,4),'head_to_ABI_each_local2':(16,3),
        'ABI_padding_each_local2':(120,1),'ABI_widen_each_local2':(384,3)}
    prefill=sum(v['shared_warp_issues'] for k,v in parts.items() if k.endswith('once'))+sum(v[1] for k,v in additions.items() if k.endswith('once'))
    steady=sum(v['shared_warp_issues'] for k,v in parts.items() if not k.endswith('once'))+sum(v[1] for k,v in additions.items() if not k.endswith('once'))
    # Each SM holds two keys. Fullquery cache uses actual decoded bits and units.
    regions={'query_raw_pitch33':16896,'query_units_pitch33':16896,'query_scales':512,
        'keys_raw2':1024,'keys_units4blocks_pitch33':1056,'key_scales':32,
        'weights':128,'query_guard_flags':512,'query_guard_collector_pingpong':128,
        'key_guard_flags':32,'key_guard_collector_pingpong':128,
        'ABI_input32':128,'ABI_output32':256,'zero':4,'epoch_and_dispatch_metadata_candidate':256}
    cursor=0;layout=[]
    for name,size in regions.items():
        cursor=(cursor+255)//256*256;layout.append({'region':name,'offset':cursor,'bytes':size});cursor+=size
    inventory=T.inventory();invocations=sum(x['ranks'][0]['SM0_two_key_invocations'] for x in inventory)
    return {'schema':'w19 finite fused unadmitted candidate r2','proof':lattice_proof(),
        'source_pins':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
            Path(__file__),ROOT/'tools/deepseek_hbm_complete_index_fused.py',ROOT/'tools/deepseek_hbm_complete_index.py',
            ROOT/'tools/w19_index32_integer_kernel.py',ROOT/'tools/hdc_golden_v41.py',ROOT/'tools/hdc_golden.py',
            ROOT/'tools/deepseek_hbm_complete_index_blas.py',ROOT/'tools/deepseek_hbm_complete_index_codec.py',
            ROOT/'tools/deepseek_hbm_complete_index_token_demand.py']},
        'resource_profile':T.resources(),'executed_local2_parts':parts,
        'additional_shared_obligations':{k:{'full_warp_slot_bytes':v[0],'shared_warp_issues':v[1]} for k,v in additions.items()},
        'query_prefill_shared_issues_per_SM_per_index_call':prefill,
        'finite_steady_shared_issues_per_SM_local2':steady,
        'source_index_calls':len(inventory),'SM0_local2_invocations_all8calls':invocations,
        'finite_SM0_shared_issue_count_known_obligations':len(inventory)*prefill+invocations*steady,
        'previous_cold_local2_shared_issues':2574,
        'comparison_is_issue_demand_only_NOT_token_rate_or_physical_cycles':True,
        'candidate_nonalias_256aligned_shared_regions':layout,'candidate_extent_bytes':cursor,
        'candidate_extent_fits_64KiB':cursor<=65536,
        'fallback':'unchanged source_sized_scores ordinary exceptional continuation, plus actual guards; no CPU FP64 oracle',
        'unpriced_mandatory_gates':['producer-version lattice provenance or typed membership validation',
            'guard flag bank maps, collector staging/visibility and global-local dispatch coherence',
            'kernel launch/branch issue, RF version allocation/ports and exact opcode II including compare wrappers',
            'key ingress/output gather, finite controller writes/ACK and provider hazards',
            'fallback live overlap and drain, shared layouts for every kernel phase',
            'Boyle full whole-token graph/lifetime/port join and physical clock qualification'],
        'source_fixture_only_opcode_counts':dict(receipt['fused_kernel'].counts),
        'software_cache_authority':{'kind':'factory-owned identity/weakref registry, source pins, monotonic epoch, explicit release and trusted content digest',
            'query_bytes_hashed_each_invocation':16384,'decoded_cache_bytes_hashed_each_finite_invocation':16896,
            'authority_check_GPU_instructions_cycles_and_ports':None,
            'old_r1_cache_authority_rejected':True,'known_945_issues_exclude_authority_cost_NOT_admission':True},
        'actual_token_rate':None,'hardware_admitted':False,'adopted':False,'RTL_written':False}

if __name__=='__main__':print(json.dumps(model(),indent=2,sort_keys=True))
