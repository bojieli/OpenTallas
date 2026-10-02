#!/usr/bin/env python3
"""Single shared S58 allocator/packet/ECC contract, metadata only."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import dsrom_full_product_binding as B

CANDIDATE_PIN='c1b460ae0665909cd41b393ea037ebf58ce9f057'
CANDIDATE_PATH='results/uarch/dsrom_shared_complete_pair_candidate_r20_20261002/shared_candidate.json'

def secded_bits(payload):
    if not isinstance(payload,int) or isinstance(payload,bool) or payload<1:
        raise ValueError('positive integer payload bits')
    r=0
    while 2**r < payload+r+1:r+=1
    return r+1  # extended Hamming overall parity

def pinned(path,commit=B.PIN):
    raw=subprocess.check_output(['git','show',commit+':'+path],cwd=B.ROOT)
    return raw,dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest())

def build(demand):
    if demand['source_pins']!=B.source_pins():raise ValueError('emitter currency')
    B.F.validate_program(demand['functional_program'])
    raw,ref=pinned(CANDIDATE_PATH,CANDIDATE_PIN);candidate=json.loads(raw)
    if candidate['candidate_id']!=B.CANDIDATE:raise ValueError('shared candidate identity')
    source=[]
    for path in ['tools/rtl_v41_fullshape_layer_campaign.py','tools/rtl_v41_rom_array.py',
                 'tools/v41_die_images_w17w10.py','tools/v41_rom_ksplit_bankmap.py',
                 'tools/v41_fullshape_isa.py','rtl/v41rom/ot_v41_rom_elem_w10.sv',
                 'docs/ARCHITECTURE_ATLAS.html']:
        _,p=pinned(path);source.append(p)
    collectives=[]
    for stage in demand['functional_program']['stages']:
        for c in stage['collectives']:
            collectives.append(dict(c,layer=stage['layer'],
                node_id=f"L{stage['layer']}.I{c['instruction']}",
                rank_node_ids=[f"L{stage['layer']}.I{c['instruction']}.R{r}" for r in range(4)]))
    return {'schema':'opentallas.dsrom.shared-S58-owner-packet-ecc-contract.v1',
        'candidate_id':B.CANDIDATE,'candidate_source':ref,'source_pins':source,
        'demand_canonical_sha256':B.digest(demand),
        'budget':{'stages':58,'TP':4,'q_complete_pairs_per_die':2651,
                  'BF_complete_pairs_per_die':724,'total_complete_pairs_per_die':3375,
                  'logical_slots_per_pair':2,'physical4096_macros_per_pair':4,
                  'reservation_slots_per_die':6750,'reservation_macros_per_die':13500,
                  'scope':'reservation budget, not a BF floor or proof that compiled NP has no padding',
                  'corrected_capacity_verdict':'FAIL','corrected_deficit_mm2':2.4233123538459154},
        'ownership':{'physical_grain':'COMPLETE_NB2_PP1_PAIR',
            'semantic_grain':'allocator-established indivisible golden owner; complete pairs stay together',
            'logical_layers':40,'physical_ownership_groups':58,
            'no_layer_stage_equivalence':True,
            'default_dense_rule':'Keep each rank-local die_slices tensor and its dependent golden reduction together unless allocator emits a legal aligned golden-subtree split plus ordered partial publication/consumption.',
            'physical_address_formula':{'logical_leaf':'2*complete_pair+logical_slot (logical_slot0or1)','PP_bank':'logical_word_index & 1','physical_leaf':'2*logical_leaf+PP_bank =4*complete_pair+2*logical_slot+PP_bank','physical_4096_row':'logical_word_index >> 1','logical_word_range':[0,8191],'physical_row_range':[0,4095],'phase_base':'even PP issue-order base; sum of all colocated phase words/alignment <=8192 per logical leaf','mandatory_cfg_limits':'source NSEG8, class disjointness and per-round slot/FIFO demand; no truncation or overlap'},
            'row_region_rule':'Keep all row segments in the source return region until a source-bound inter-owner completion adapter exists; never combine arbitrary partials or round at a stage boundary.',
            'expert_rule':'All384 expert homes retained. Runtime ascending six EIDs dispatch to those homes; other378 are storage, not omitted capacity. w1/w3->activation->w2 and shared-expert path remain ordered.',
            'TP_rule':'Fixed rank0..3; wo_b column partial reduction stays ((r0+r1)+(r2+r3)) with original final BF16 rounding. No new TP or K reduction reassociation.',
            'builder_rule':'die_slices(L,rank,dict(SHIPPED,ratio=RATIO),range(384),L in ENGRAM) for stored views; FullLayerBuilder actual complete instructions, not only generic build_tp_layer for special layers; preserve source runtime actions.'},
        'stage_packet':{'scope':'compiler/model logical interface; no claim of existing encoded wire ABI',
            'identity_fields':['token_or_position_epoch','logical_layer','original_instruction_index','substage_owner','TP_rank','row_region','golden_segment_or_tree_node','producer_visibility_fence'],
            'identity_widths':'Bind to source provider/calendar; coll_seq8 alone cannot identify layer/position or relocated subtasks. No fabricated header bit cost.',
            'layer_boundary_payload':{'h_shape':[4,5120],'h_dtype':'BF16','h_bytes_per_rank':40960,
                'pre_shape':[4],'pre_dtype':'FP32','pre_bytes_per_rank':16,'packed_bytes_per_rank':40976,
                'existing_FP32_VM_bytes_per_rank':81936},
            'substage_payload':'Actual producer output slice/type from original descriptor; FP32 partials retain FP32, carry exact subtree/row/position tags. Do not charge whole-layer packet for every substage.',
            'input_acceptance':'producer last value and write-visible fence; receiver vector/source state and finite destination credits ready',
            'completion':'all required writes visible plus return/vector/collective/persistent-state consumers drained; END alone insufficient',
            'compiler_binding_keys':'L{layer}.I{original_instruction_index}.R{rank}; L{layer}.A{action_index}.R{rank}; L{layer}.fence.R{rank}',
            'manifest_fields':['owner_grain','provider','semantic_sha256','source_receipts','address_patches','native_ISA_provider_contract','calendar'],
            'calendar_fields':['domain','accept_cycles','complete_cycles','issue_interval_cycles','completion_dependencies','source_receipts'],
            'pricing':'Stage-hop wire/CDC/serialization/header and finite backlog attach to actual source->destination edges, separately from fixedTP4 collectives; no frequency credit from 10ns benches.'},
        'collective_interface':{'TP':4,'all_reduce':'FP32 ((r0+r1)+(r2+r3)); apply BF16 output rounding only when original coll_rnd requests it',
            'all_gather':'rank0 then rank1 then rank2 then rank3 concatenation',
            'topk':'score desc, global ID asc tie; ID=rank*source_dynamic_stride+localID; selected IDs written ascending; preserve original n/k/idbase/stride',
            'head_argmax':'full5120 K per contiguous32320 rows/rank; maximum FP32 logit, tie lowest global vocabulary ID, reject NaN; endpoint separate from legacy layer collective executor',
            'identity':'original layer/instruction/seq/rank plus position epoch; retain original coll_seq8, do not silently reinterpret it as a globally unique owner',
            'source_VM_words':'32bit; ALL_REDUCE n*4 bytes input/output perrank; ALL_GATHER n*4 input and n*16 output; TOPK n*8 input(score+id),k*4 output',
            'provider_obligations':['all-rank arrival readiness','finite input and output slots','write-visible ACK before dependent descriptor','unchanged golden rounding/tree','per-edge transport/CDC/service II/completion costs'],
            'actual_descriptor_count':len(collectives),'descriptors':collectives},
        'ECC':{'product_requirement':'Atlas ROM SECDED/CRC/BIST declaration remains a provider gate; historic raw field path does not satisfy it',
            'current_witness_mode':'none; cost0 for absent ECC hardware, protection credit0, not selected product policy',
            'word_formats':[{'format':fmt,'useful_bits':bits,'physical_bits':274,'spare_bits':274-bits,
                'SECDED_check_bits':secded_bits(bits),'minimum_protected_bits':bits+secded_bits(bits),
                'fits_raw_word_bit_budget':bits+secded_bits(bits)<=274,'actual_SECDED_provider':False}
                for fmt,bits in [('qFP4',272),('qFP8',264),('BF16',256)]],
            'allocator_reservation':'Explicit separate paired check-storage obligation:10checkbits per allocated qFP4 274bit ROM word. Protect all272 useful bits including both exponent bytes; preserve existing payload placement and do not assume use of two spare bits.',
            'parity_address_key':['physical_main_leaf_id','physical_4096_bank','row_address'],
            'cost_fields_required':['qFP4_allocated_and_required_padded_words','check_storage_bits=10*protected_qFP4_words','characterized_check_provider_or_full_macro_packing','check-read bits/cycle per simultaneous word port','encoder/decode/fault logic area','additional capture/decode latency and hold/clock costs'],
            'no_free_physical_side_macro':True,'no_macro_274_to_282_substitution':True,
            'FP8_BF16_note':'Bits fit extended-Hamming parity in spare columns, but existing emitter/consumer lacks encode/decode/fault binding; no protection or zero-latency qualification inferred.',
            'capacity_gate':'Add distinct check storage/control/routes cost exactly once after demonstrating whether historical field debit already contains an actual ECC provider. Failure or missing provider prevents selection; do not delete ECC to force fit.'},
        'adopt':False,'hardware_admission':False,'new_count_selected':False,'jobs_launched':0}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--demand',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    raw=a.demand.read_bytes();d=json.loads(gzip.decompress(raw) if a.demand.suffix=='.gz' else raw)
    result=build(d);a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
if __name__=='__main__':main()
