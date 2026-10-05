#!/usr/bin/env python3
"""Source-pinned default-off mode/lease model; no engine implementation or payload.

Resolves input-RNE eligibility only for proven BF16 producer sites, retains FP32
results and golden chunk8 ordering; head compute/provider remains dedicated.
"""
from __future__ import annotations
import argparse,copy,gzip,json,math
from pathlib import Path
import dsrom_native_weight_address_join as J
import dsrom_full_owner_compiler as C
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/dsrom_native_mode_contract_20261002'
COMPRESSORS=['L2.I24','L2.I25','L8.I24','L8.I25','L14.I34','L14.I35']


def bf_round_bits(x):
    return ((x>>16)+(((x>>15)&1)&bool((x&32767) or ((x>>16)&1))))&65535


def prove_input(demand,node_id):
    ns=[n for n in demand['nodes'] if n['scope']==next(n['scope'] for n in demand['nodes'] if n['id']==node_id) and n['kind']=='instruction']
    at=next(i for i,n in enumerate(ns) if n['id']==node_id);f=ns[at]['instruction']
    producers=[(i,n) for i,n in enumerate(ns[:at]) if 'XN' in n['instruction'].get('_writes',[])]
    if not producers:raise ValueError('missing XN producer')
    pi,p=producers[-1];g=p['instruction'];K=f['me_k']*(1<<f.get('me_split',0))
    if not(g.get('unit')==2 and g.get('rnd')==1 and g.get('dst')==1 and g.get('su_nout')==1 and g.get('su_nin')==K and g.get('o_base')==f['me_xbase'] and g.get('o_si')==1 and not g.get('pred',0)):
        raise ValueError('producer is not whole-vector unconditional BF16-RNE')
    end=g['o_base']+K
    for n in ns[pi+1:at]:
        z=n['instruction']
        if z.get('unit')==2 and z.get('dst')==1 and 'o_base' in z:
            a=z['o_base'];b=a+z.get('su_nin',0)*max(1,z.get('su_nout',1))
        elif z.get('unit')==3 and 'qe_obase' in z:a=z['qe_obase'];b=a+z.get('qe_nout',z.get('qe_nb',0)*32)
        elif z.get('unit')==1 and z.get('me_oen',0):a=z['me_obase']*16;b=a+z.get('me_nout',0)
        elif z.get('unit')==6 and 'coll_dst' in z:a=z['coll_dst'];b=a+z.get('coll_n',0)*4 # conservative TP gather extent
        else:continue
        if a<end and b>g['o_base']:raise ValueError('intervening XN writer '+n['id'])
    fence=next((n['id'] for n in ns[pi+1:at+1] if n['instruction'].get('wait',0)&2),None)
    if fence is None:raise ValueError('no actual SU retirement dependency')
    return {'consumer':node_id,'producer':p['id'],'producer_rnd':1,'VM_elements':[g['o_base'],end],
      'first_actual_SU_wait_fence':fence,'input_RNE_idempotent':True,'intervening_vector_writer':False,
      'physical_VM_delivery_visibility_and_same_generation_required':True,'logical_SU_idle_not_general_physical_visibility':True,
      'descriptor_round_bit_unchanged':f['me_round'],'result_format':'FP32','producer_VM_write_acceptance_calendar_bound':False}


def allowed_mode(node_id,proof,producer_visible,lease_valid,phase_authenticated):
    return node_id in COMPRESSORS and proof['consumer']==node_id and proof['input_RNE_idempotent'] and producer_visible and lease_valid and phase_authenticated


def valid_eid(x):return type(x) is int and 0<=x<384

def effective_key(base,stride,eid):
    if not valid_eid(eid) or stride!=4096 or not 0<=base<1<<30:raise ValueError('invalid expert identity')
    return base+eid*stride

class Admission:
    """One-descriptor proposed acceptance ledger; post-edge state, no timers.

    owner_accept is held-valid && owner_ready on the *actual* edge. Cancel/fault
    has same-edge priority over all new acceptance. Matching poison drains the
    accepted VM read. Stale replies cannot retire its matching outstanding debt.
    """
    def __init__(self):
        self.vm=0;self.owner=0;self.pending=False;self.fault=False;self.cancel=False;self.era=0;self.key=None
    def step(self,*,start=False,indexed=False,vm_accept=False,rsp=None,owner_ready=False,owner_retire=False,cancel=False,known_fault=False,base=1<<21):
        events=[];prior_pending=self.pending
        self.cancel|=cancel;self.fault|=known_fault
        if rsp is not None:
            era,eid,poison=rsp
            if not self.vm or era!=self.era:self.fault=True;events.append('stale_or_unsolicited_response_discarded_no_credit_retirement')
            else:
                self.vm=0;events.append('accepted_VM_terminal_retired')
                if poison or not valid_eid(eid):self.fault=True;events.append('poison_or_invalid_EID_fault_before_lookup')
                elif not(self.cancel or self.fault):self.key=effective_key(base,4096,eid);self.pending=True;events.append('valid_EID_key_ready')
        if owner_retire:
            if not self.owner:raise ValueError('unowned owner terminal')
            self.owner=0;events.append('accepted_owner_terminal_retired')
        if self.cancel or self.fault:self.pending=False
        elif prior_pending and owner_ready:
            if self.owner or self.vm:raise ValueError('overlapping owner credit')
            self.owner=1;self.pending=False;events.append('actual_owner_accept')
        if start and not(self.cancel or self.fault):
            if self.vm or self.owner or self.pending:raise ValueError('occupied adapter')
            if indexed:
                if vm_accept:self.vm=1;events.append('actual_VM_request_accept')
                else:events.append('VM_request_held_no_credit')
            else:self.pending=True;events.append('owner_request_pending')
        return {'events':events,'VM_credits':self.vm,'owner_credits':self.owner,'owner_valid':self.pending and not(self.fault or self.cancel),
          'local_cancel_ack':bool((self.fault or self.cancel) and self.vm==0),'all_accepted_owner_credits_drained':self.owner==0,
          'rearm_not_timer_based':True}
    def rearm(self,*,source_ack,owner_retired,delivery_fence,causal_visibility,provenance):
        if not all([source_ack,owner_retired,delivery_fence,causal_visibility,provenance]) or self.vm or self.owner or self.pending or not(self.cancel or self.fault):raise ValueError('rearm fence incomplete')
        self.era^=1;self.fault=self.cancel=False;self.pending=False


def argmax_pair(values):
    """Finite-FP32 comparison contract, exact tie on value -> lowest global ID."""
    if not values or any(not math.isfinite(x) for _,x in values):raise ValueError('empty/nonfinite head result')
    return max(values,key=lambda p:(p[1],-p[0]))


def head_address(rank,row,k):
    if not(0<=rank<4 and 0<=row<32320 and 0<=k<5120):raise ValueError('head tensor coordinate')
    absolute_row=rank*32320+row;word,lane=divmod(absolute_row*5120+k,16)
    # Existing dedicated closure reserves embed first, then head; no compute-site choice.
    head_pair_start=math.ceil(129280*5120/16/16384)
    offset,local=divmod(word,16384);mb,a=divmod(local,8192)
    return {'provider':'dedicated_global_storage','pair':head_pair_start+offset,'mb':mb,'parity':a%2,'physical_row':a//2,
      'bit_range':[lane*16,lane*16+16],'SECDED_bit_range':[256,266],'global_vocab_ID':absolute_row,
      'head_tensor_word':word,'head_tensor_row':absolute_row,'head_tensor_col':k,'native_ME_provider_adapter_implemented':False}


def model():
    demand=json.load(gzip.open(J.D/'inputs/demand-r5.json.gz','rt'))
    proofs=[prove_input(demand,n) for n in COMPRESSORS+['Lhead.I5']]
    for p in json.loads((D/'inputs/source_pins.json').read_text()):
        if J.sha(D/'inputs'/p['snapshot'])!=p['sha256']:raise ValueError('source pin')
    adapter=(D/'inputs/ot_v41_rom_adapt.sv').read_text();spine=(D/'inputs/ot_v41_spine_w17w10.sv').read_text();mv=(D/'inputs/ot_hdc_v41_matvec.sv').read_text()
    for text in ['m_round && !m_amax && !m_mmode','S_IDXW: begin key <= key + AW\'(vi_q) * stride','S_GO: if (s_ready)']:assert text in adapter
    assert 'bb[(rq_pos[0] ? KMAX : 0)' in spine and 's_fmt <= 2\'d1' in adapter
    assert 'top_idx < am_idx' in mv and '!(|tv)' in mv
    headwords=129280*5120//16;headpairs=math.ceil(headwords/16384);rankwords=headwords//4
    cost={'scope':'ADAPTER_INCREMENT_ONLY, excludes Peirce producer278/19+10 and cfg/ECC-owner ledgers',
      'new_FF_bits_per_adapter':6,'FF_all58x4_adapters':6*58*4,'new_FF_allocation':{'VM_outstanding':1,'owner_outstanding':1,'sticky_cancel':1,'alternating_era':1,'input_proof_latched':1,'dedicated_head_route_latched':1},
      'existing_sticky_fault_and3bitFSM_andregistered_go_reused_not_recharged':True,
      'phase_R0_policy_bits_per_stage_rank':1024,'uniform_policy_bits_all58x4':1024*58*4,
      'exact_phase_whitelist_entries':6,'policy_hard_macro_ports_ECC_not_qualified':True,
      'full32bit_EID_range_guard':'OR(vi_q[31:9])==0 && !(vi_q[8]&&vi_q[7]); do not truncate before compare',
      'six_EID_order_ledger_optional_increment_bits':13,'optional_ledger_allocation':'9previousID+3count+1valid if actual selector/generation completion cannot be reused; not required per indexed descriptor and not doublecounted',
      'healthy_added_compressor_cycles_if_producer_and_cfg_fences_already_satisfied':0,
      'healthy_added_index_cycles_if_guard_combinational_closes_SS_FF':0,
      'healthy_extra_inputscan_or_VMtraffic':0,'if_SS_FF_requires_guard_register_cycles_per_indexed_descriptor':1,
      'indexed_descriptors_per_token':720,'conditional_guard_register_total_cycles_no_overlap':720,
      'physical_area_tracks_fanout_adoption':False,
      'adapter_boundaries':{'phase':10,'word':5,'pair':12,'logical_cfg_addr':15,'VM_EID_response':32,'checked_EID':9,'expert_stride':30,'lease_era':1,'VM_response_credit_max':1,'owner_request_credit_max':1,'selected_owner_stage':6,'phase_input_proof':1,'input_proof_era':1,'owner_terminal_era':1},
      'fanout':'new fault/freeze admission gates local VM valid and actual owner valid; do not replicate to4096pairs without pricing clock/routes; phase whitelist adds no compared key bits but one authenticated policy output',
      'critical_event_formula':'owner_accept=max(validated index terminal or direct descriptor acceptance, producer VM visibility, phase-policy lease, selected owner ready); cfg_accept follows actual owner_accept; fieldgo=max(all25actual cfg-delivery fences, operand-visibility fence, authenticated phase policy); unchanged field/reduction/result calendar thereafter'}
    return {'schema':'opentallas.dsrom.native-mode-contract.v1','verdict':'PASS_SOURCE_SEMANTICS_AND_DEFAULT_OFF_IMPLEMENTATION_SPEC_NOT_RUNTIME_ADMISSION','opt_in_default':False,'proposed_parameter':'OPT_NATIVE_MODE_CONTRACT=0',
      'compressor_input_proofs':proofs[:6],'head_input_proof':proofs[6],
      'compressor_resolution':{'descriptor_me_round_stays0':True,'no_new_FP32_activation_multiplier':'Existing BF16 buffer rounding is idempotent on source-produced BF16 words. Do not generalize round0 to arbitrary FP32 inputs.',
       'FP32_projection_outputs_not_BF16':'keep s_fmt1; no to_bf16 on CP_KVL/CP_SCL, slot pooling max/exp/div/weighted terms retained until pooled final to_bf16',
       'accept_rule':'existing contiguity predicates && !amax && !mmode && (m_round || authenticated allowR0 phase with same-generation whole-vector BF16 producer delivery fence)',
       'phase_policy':'lookup key hit and unique phase before authorization; six exact phase/descriptor tuples, no blanket m_round removal',
       'golden_K_tree_unchanged':'chunk8 sequential from+0 each8products then padded power-of-two tree; K5120 =>640leaves padded1024; existing physicalfield numeric/order gate still required'},
      'dedicated_head':{'route':'Dedicated native ME/provider mode, never pretend a622field phase or remap the head into compressor whitelist','tensor':'head.weight','rows_global':129280,'rows_per_rank':32320,'K':5120,'TP':4,'descriptor_round0_and_amax1_and_oen1_retained':True,
       'weight_storage_words_global':headwords,'weight_storage_pairs_global':headpairs,'weight_storage_macros_global':headpairs*4,
       'ideal_pairs_per_rank_ceiling':math.ceil(rankwords/16384),'native_ME_WROM_port_layout_adapter_implemented':False,
       'storage_API':'head_address(rank,row,K): exact existing dedicated global head word after embed reservation -> complete4096pair/MB/parity/code/ECC coordinates; capacity charge already dedicated closure, no layer-field doublecharge',
       'activation':'all5120 XN words BF16 from exact head normalizer; round0 eligibility input only, output all32320 FP32 logits if oen1',
       'golden_order':'per row640 sequential8-term chunk leaves padded1024 then golden tree; no sums across TP ranks (rows sharded), no transfer from differently partitioned field subtree',
       'argmax':'compare finite FP32 values, exact ties choose smallest global vocab ID=rank*32320+localrow; +/-0 ties canonically equal; NaN/Inf poison/fault before final token publication',
       'existing_source_tree_price':{'W':16,'G':4,'NW':21,'MP':1,'NL':64,'levels':6,'registered_tree_bits':127*54,'tv_bits':7,'running_state_bits':86,'total_owned_source_argmax_bits':127*54+7+86,'increment_if_reused':0,
        'return_sample_to_best_update_edges':8,'idle_registered_edge_after_last_tv_retire':1,'terminal_rule':'wait for native idle containing tv and output writes, matching terminal and external delivery fence; ready=!active alone can clear prior best before final compare'},
       'global_collective':'four finite(value32,globalID32) pairs -> deterministic compare/tie tree, not arithmetic allreduce.256inputbits,64outputbits; at2registeredlevels latency>=2localcomparecycles plus actual link/CDC/acceptance calendar UNBOUND',
       'head_compute_placement_provider_ECC_and_full_latency_ready':False},
      'invalid_EID_and_cancel':{'guard':'check complete32bit vi_q range0..383 before stride multiply and lookup; phasehit must match ME/QE kind and own lease',
       'preserved_alias_negatives':{'EID512':'exp0.w1 base +512*4096 aliases exp0.w3 family','EID262144':'30bit multiply/add wraps to exp0.w1; fullwidth range check forbids'},
       'same_edge_priority':'knownfault/freeze/cancel blocks descriptor, VMrequest and owner acceptance before edge; invalid matching terminal faults before lookup/config/fieldgo',
       'owner_terminal_authentication':'owner_retire is only matching selected-stage/phase/era authenticated terminal; external Peirce ledger validates it, not an unauthenticated done pulse',
       'registered_go_edge':'source S_GO registers s_go at e, actual spine samples at e+1. Hold request/identity until actual valid&&ready; state transition or s_go assignment is not acceptance.',
       'local_cancel_ack':'newadmission frozen plus all matching accepted VM terminals drained/discarded; independent of selected-owner EMPTY/readiness',
       'accepted_owner_obligations':'VM terminal done or localACK cannot delete accepted cfg/ECC/field/writer/return credits; owner retire/delivery/causalvisibility/provenance remain mandatory',
       'onebit_era_legal_only_drained_wrap':'rearm after localACK+ownerretire+deliveryfence+causalvisibility+provenance and zero outstanding requests. Stale generation never retires matching debt; no timer/reset-everytoken substitute.',
       'response_refusal':'accept/discard matching good or poison return under cancel without downstream ready; permanently held provider reply keeps debt and blocks ACK, watchdog only reports',
       'native_source_guard_cancel_handshake_currently_implemented':False,'future_external_ports':['freeze/cancel','source_cancel_ack','VM_req_valid/ready','VM_rsp_valid/terminal/era','owner_req_valid/ready','owner_retire','delivery_fence','causal_visibility','provenance_lease']},
      'composition_cost':cost,
      'expert_spatial_split':{'candidate_owner':'Maxwell; no independent NP/stage/count chosen','retain_TP4_and_complete_expert_triples':True,
       'activation_XN_bits_per_rank':5120*32,'gate_up_local_BF16_in32_output_bits_per_rank_per_expert':2*576*32,
       'activation_TP_allgather_output_bits_per_rank_per_expert':2304*32,'w2_result_bits_per_rank_per_expert':1280*32,
       'six_selected_result_bits_per_rank':6*1280*32,'shared_result_bits_per_rank':1280*32,
       'if_all_six_out_of_order_results_buffered_bits_per_rank':6*1280*32,'row_stream_reorder_alternative':'6owner FIFO head/tag/credit records plus bounded row FIFOs, capacities/fault drain must be separately derived; cannot just sum arrival order',
       'golden_merge':'ascending six runtimeEIDs, weighted activation rounding before w2, each TP act gather, w2 BF16 result, sequential six experts then sharedlast; preserve full source collectives and rounding boundaries',
       'critical_formula':'Tparallel=max_i(Tbroadcast_i+Tcfg_i+Tw1w3_i+TweightedSiLU_i+TTPactgather_i+TcfgW2_i+Tw2_i+Treturn_i)+Torderedmerge_and_finalTPgather; prove <= current full conditional token calendar, not <= coldrefill alone',
       'implementability':'source QE front-end currently serial single-field dispatch; new parallel owners require actual multi-owner admission slots/credits and operands/results transport. Model capacity, fanout, muxes and links before claiming parallelism.',
       'dense_grain_constraint':'Engram layer projection currently3200 activepairs, so simply shrinking compiledNP below that cannot hold unchanged wholeoperator. Golden-aligned row ownership or ordered subtrees/provider routing needed; no bit loss or free partial template.',
       'config_ECC_headers':'reserve immutable HE/CROM/ECC first per new owner; all compiled padding/sites, PHW/keytables and stage service replication charged; head/embed separate and fully conserved','selected_result_header_min_bits_each':{'stage':6,'rank':2,'expertID':9,'slot':3,'row':11,'era':1,'good_poison_terminal':2},'selected_result_header_total_bits_each':34,'six_complete_result_reorder_headers_bits_per_rank':6*34,'row_striped_collective_demand':'6independent576/rank ->2304/rank TP allgathers still contend on same link/service; extra owners are not free extra TP bandwidth','single_token_no_loss_proved':False},
      'readiness':{'source_semantic_model_complete':True,'RTL_ready_before_provider_event_calendar':False,'physical_or_full_token_or_rate_credit':False,'payload_reads':0,'RTL_builds':0},
      'next_gate':'Maxwell selected-owner cfg/ECC/VM-visible event calendar + Peirce shared cancellation fence binding; bounded defaultoff copied-adapter correctness fixture for six round0 BF16 proofs, invalid/stale/held returns and head provider mode only after composition review. No original RTL edit.',
      'source_tool_sha256':J.sha(Path(__file__))}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output required')
    a.out.mkdir(parents=True);m=model();(a.out/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':m['verdict'],'BF16_proofs':7,'physical_admission':False}))
