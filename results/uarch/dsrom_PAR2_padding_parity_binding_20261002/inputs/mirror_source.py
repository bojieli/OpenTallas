#!/usr/bin/env python3
"""Source-derived additive transport correction/readback of the one PAR2 map.

Old dcc64 screen and bindingr1 are immutable. This tool never creates link BW,
slack or physical-provider completion evidence; finite-calendar inputs must come
from the accepted source event calendar.
"""
from __future__ import annotations
import argparse,ast,collections,json,re,subprocess
from pathlib import Path
import dsrom_parallel_owner_binding as B
import dsrom_full_owner_compiler as C
import dsrom_native_weight_address_join as J
import dsrom_owner_cfg_interface_export as E
OUT=B.OUT
PIN=B.FIELD_COMMIT
SOURCES=['rtl/v41die/ot_v41_spine_w17w10.sv','rtl/v41die/ot_v41_pair_w17w10.sv',
         'rtl/v41die/ot_v41_retn_w17w10.sv','rtl/v41rom/ot_v41_ret.sv']


def width_expression(source,phw=10):
    text=re.search(r'parameter integer BW\s*=\s*([^\n]+)',source).group(1)
    tree=ast.parse(text.strip(),mode='eval')
    def value(n):
        if isinstance(n,ast.Expression):return value(n.body)
        if isinstance(n,ast.Constant) and type(n.value) is int:return n.value
        if isinstance(n,ast.Name) and n.id=='PHW':return phw
        if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Add):return value(n.left)+value(n.right)
        raise ValueError('unrecognized source BW expression')
    return value(tree)


def packet_bits(mode):
    if mode=='FULL':return 1632+49
    if mode=='ROOT':return 69+39
    if mode=='CFG':return 37
    raise ValueError('Only full bus source capture is bound; narrow reconstruction unimplemented')


def cfg_edges(cfg_go=0):
    # Literal nonblocking edge model of pair ld_run/ld_k/c_v/c_a/c_d.
    run=False;k=0;cv=False;ca=0;word=None;events=[]
    for edge in range(cfg_go+28):
        if cv:events.append(dict(edge=edge,element_cfg_capture_word=ca,ROM_word=word))
        oldrun=run;oldk=k;cv=oldrun;ca=oldk
        if oldrun:word=oldk
        if edge==cfg_go:run=True;k=0
        elif oldrun:
            k+=1
            if oldk==24:run=False
    if [x['ROM_word'] for x in events]!=list(range(25)):raise ValueError('loader pipeline')
    return dict(command_edge=cfg_go,ROM_read_edges=list(range(cfg_go+1,cfg_go+26)),
                element_cfg_capture=events,last_cfg_capture_edge=cfg_go+26,
                source_safe_GO_edge=cfg_go+27,
                actual_hard_ROM_CLKQ_ECC_capture_or_delivery_fence_qualified=False)


def readback(binding):
    """Independent polynomial compressed-run selector/conservation check.

Original immutable plan hash is the provenance; no weight words/checkpoint reads.
    """
    totals=collections.Counter();max_remote_rows=0;stage=collections.defaultdict(collections.Counter)
    keys=set();layer_experts=collections.defaultdict(set);choice_set=set();live={}
    rows=list(C.readrows(binding/'phase_shard_bindings.jsonl.gz'))
    if len(rows)!=46509:raise ValueError('phase count')
    for p in rows:
        identity=p['stage'],p['phase']
        if identity in keys or not 0<=p['phase']<1024:raise ValueError('phase identity')
        keys.add(identity);live[identity]=p
        if p['cfg_word_range']!=[p['phase']*25,(p['phase']+1)*25]:raise ValueError('cfg address')
        if p['alias'].startswith('exp'):layer_experts[p['layer']].add(int(p['alias'].split('.')[0][3:]))
        subs=p['shards']
        if [x['shard'] for x in subs]!=[0,1]:raise ValueError('shard list')
        ords=[i for s in subs for i in s['plan_ordinals']]
        if sorted(ords)!=list(range(len(ords))):raise ValueError('omitted/duplicate run ordinal')
        if sum(s['output_rows'] for s in subs)!=p['rows_per_rank']:raise ValueError('rows lost')
        if p['row_cross_shard_K_reductions']!=0:raise ValueError('cut ordered subtree')
        for s in subs:
            if (s['local_NP'],s['local_NBF'],s['R'])!=(2048,362,64):raise ValueError('physical source topology')
            for k in ('physical_weight_words','output_rows','ECC_local_bits','ECC_remote_bits'):
                totals[k]+=s[k];stage[p['stage']][k]+=s[k]
        max_remote_rows=max(max_remote_rows,subs[1]['output_rows'])
        totals['phases']+=1;totals['both_shards_active']+=int(all(s['output_rows'] for s in subs))
    if set(layer_experts)!=set(range(40)) or any(e!=set(range(384)) for e in layer_experts.values()):raise ValueError('full experts omitted')
    calls=list(C.readrows(binding/'native_shard_choices.jsonl.gz'))
    for b in calls:
        for q in b['phase_choices']:
            p=live[(q['stage'],q['phase'])]
            if (q['alias'],q['source_key_word'])!=(p['alias'],p['source_key_word']):raise ValueError('instruction provider owner')
            if q['required_shards']!=[s['shard'] for s in p['shards'] if s['output_rows']]:raise ValueError('admission mask')
            if q['remote_source_root_wire_bits']!=69*q['remote_rows']:raise ValueError('return packet debit')
            choice_set.add((q['stage'],q['phase']))
    if choice_set!=keys or len(calls)!=1149:raise ValueError('native provider closure')
    initial=json.loads((binding/'model.json').read_text())
    if dict(totals)!=initial['source_totals']:raise ValueError('source totals')
    for path,sha in initial['source_dependency_sha256'].items():
        if J.sha(B.ROOT/path)!=sha:raise ValueError('dependency hash '+path)
    return dict(all40_all384_PASS=True,phase_count=46509,native_call_count=len(calls),
                native_choice_count=sum(len(x['phase_choices']) for x in calls),source_totals=dict(totals),
                max_remote_final_rows_per_single_position_phase=max_remote_rows,
                conservative_full_phase_capture_bits_at108_per_packet=max_remote_rows*108,
                capture_bound_requires_positions_multiplier_and_original_consumer_delivery_fence=True,
                capture_is_not_qualified_FIFO_or_SSFF_area=True,
                encoded_totals_are_allocated_template_words_NOT_runtime_read_traffic=True,
                expert_return_order='Actual six selected IDs retain original producer/output order; PAR2 is row-sharding, not independent whole-expert stage ownership.',
                complexity='One46509phase and276909choice compressed-record scan; no enumeration of full-model weight payload or repacking.')


def local_replica_plan(field,provider):
    """ONE optional local sidecar mirror within charged PAR2 padding sites.

Keep original103 providers in shard0. Mirror each completepair into an unused
Q_ONLY shard1 pair; no matrix/HE/CROM relocation or NP change. No physical port
or ECC decoder is implied by legal storage addresses.
    """
    padding=set(field['padding_site_IDs']);active=set(field['weight_active_site_IDs'])
    bf=set(field['BF_DUAL_site_IDs'])
    if padding & active or padding | active!=set(range(4096)):raise ValueError('padding partition')
    available=sorted(p for p in padding if p//2048==1 and p not in bf)
    originals=provider['pairs']
    if any(p//2048!=0 or p not in active for p in originals):raise ValueError('original sidecar home')
    if len(set(originals))!=len(originals) or len(available)<len(originals):raise ValueError('local parity capacity')
    copies=available[:len(originals)]
    if set(copies)&active or len(set(copies))!=len(copies):raise ValueError('occupied replica provider')
    return dict(stage=provider['stage'],kind='ECC_FP4_LOCAL_MIRROR_OPTION_NOT_SELECTED',
                original_pairs=originals,mirror_pairs=copies,bits=provider['bits'],
                all_mirror_sites_Q_ONLY_and_original_padding=True,
                original_parity_source_unmodified=True,
                words_per_complete_pair=16384,useful_data_bits_per_word=256,
                sidecar_SECDED_bits_per_word=10,
                source_bijection='same linearbit -> original pidx/MB/parity/row/bit -> mirror pidx same MB/parity/row/bit; copy protected256+10 source word without changing code parity',
                extra_complete_pairs_used=len(copies),extra_weight_macro_instances=0,
                previously_charged_padding_macros_now_used=4*len(copies),
                remaining_shard1_padding_pairs=len(available)-len(copies),
                additional_local_ECC_decoder_read_router_capture_area_unpriced=True,
                actual_read_ports_or_SSFF_qualified=False)


def local_sidecar_address(plan,linear_bit,code_shard):
    if code_shard not in (0,1) or not 0<=linear_bit<plan['bits']:raise ValueError('local parity coordinate')
    pidx,within=divmod(linear_bit,4194304);word,bit=divmod(within,256)
    mb,a=divmod(word,8192)
    pair=(plan['original_pairs'] if code_shard==0 else plan['mirror_pairs'])[pidx]
    if pair//2048!=code_shard:raise ValueError('parity owner alias')
    return dict(**B.site(pair),mb=mb,parity=a%2,physical_row=a//2,data_bit=bit,
                source_original_pair=plan['original_pairs'][pidx],source_linear_bit=linear_bit,
                replica_selected_and_implemented=False)


def generate(binding,out):
    binding=binding.resolve();out=out.resolve()
    if out.exists():raise ValueError('fresh corrected record required')
    out.mkdir(parents=True)
    pins={}
    for p in SOURCES:
        raw=subprocess.check_output(['git','show',PIN+':'+p],cwd=B.ROOT)
        dest=out/Path(p).name;dest.write_bytes(raw);pins[p]=dict(commit=PIN,sha256=C.sha(raw),archive=str(dest.relative_to(B.ROOT)))
    spine=(out/'ot_v41_spine_w17w10.sv').read_text();pair=(out/'ot_v41_pair_w17w10.sv').read_text()
    if width_expression(spine)!=1632:raise ValueError('PHW10 source broadcast changed')
    for text in ('c_v <= ld_run;',"if (ld_k == 5'(CW - 1)) ld_run <= 1'b0;",'c_a <= ld_k;','go && act'):
        if text not in pair:raise ValueError('loader source')
    proof=readback(binding)
    field=json.loads(E.READBACK.read_text())['compiled_field']
    replicas=[local_replica_plan(field,p) for p in C.readrows(E.OUT/'export_r1/FP4_ECC_provider_directory.jsonl.gz')]
    boundary_checks=0
    for r in replicas:
        for i in range(len(r['original_pairs'])):
            start=i*4194304;stop=min(r['bits'],start+4194304)
            if start>=stop:continue
            for bit in (start,stop-1):
                a=local_sidecar_address(r,bit,0);b=local_sidecar_address(r,bit,1)
                if any(a[k]!=b[k] for k in ('mb','parity','physical_row','data_bit','source_original_pair','source_linear_bit')):raise ValueError('replica bit identity')
                boundary_checks+=1
    C.gzrows(out/'local_ECC_mirror_option.jsonl.gz',replicas)
    old=json.loads((binding/'model.json').read_text())
    negative=dict(verdict='FAIL_SOURCE_WIDTH_AND_EXPLICIT_BEAT_IDENTITY_IN_INITIAL_INTERFACE_SCREEN',
                  prior_model_sha256=J.sha(binding/'model.json'),
                  prior_source_full_bus_bits=old['finite_transport_contract']['activation_full_source_bus_bits'],
                  source_correct_full_bus_bits=1632,
                  reason='549xs +1067xb is1616data-only; cfg_go/PHW10/np/go/go_bf add16. Initial33bit phase/op header omitted16-bit streamed beat identity.',
                  numerical_allocation_and_source_plan_identity_unchanged=True,
                  original_records_preserved=True,no_RTL_measurement_or_performance_claim=True)
    (out/'initial_interface_screen_FAIL.json').write_text(json.dumps(negative,indent=2,sort_keys=True)+'\n')
    model=dict(schema='opentallas.dsrom.PAR2-source-transport-contract.v1',candidate=old['candidate'],
               binding_model_sha256=J.sha(binding/'model.json'),binding_directory=str(binding.relative_to(B.ROOT)),
               source_pins=pins,readback=proof,
               source_widths=dict(q_activation=549,BF_activation=1067,data_only=1616,
                                  cfg_GO_controls_at_PHW10=16,complete_broadcast=1632,
                                  PHW=10,source_root=69,remote_root_ports=64,
                                  full_bus_packet_proposal=packet_bits('FULL'),root_packet_proposal=packet_bits('ROOT'),
                                  CFG_command_packet_proposal=packet_bits('CFG')),
               header=dict(full_activation='stage6,rank2,shard1,phase10,era1,opseq13,beat16=49; preserve source cfg/go/np/positions and data fields',
                           root='stage6,rank2,shard1,phase10,era1,opseq13,rootindex6=39; source69 already includes globalrow16,pos3,data,valid,error',
                           cfg='stage6,rank2,shard1,phase10,era1,opseq13,np3,cfggo1=37; local arrays generate distinct25x48 words in parallel',
                           counter_reuse_or_new_allocation_must_be_priced=True,RTL_or_physical_packet_provider_implemented=False),
               source_cfg_edges=cfg_edges(),
               finite_transport_requirements=dict(
                   activation='Replay every actual valid cfg/go/xs/xb edge into remote common-phase field. FIFO ordering and source beat identity; cannot omit controls or lose beats. Clock crossing/link endpoint delay has positive priced cycles.',
                   admission='Two owner leases and actual both-shard cfg/input readiness; originalfieldbusy sums pairbusy ONLY and does not prove cfgloader/return/ECC queues drained.',
                   cfg='Source loader safeGO edge27 is simulation genericcmr contract;7hard4096x72macro depth-select, clkq, ECC and register capture need independent realprovider calendar. Add to remote cfg command path before GO.',
                   return_capture='64remote roots have no ready:6912packetbits can arrive per streamedge.64whole packet capture slots required for one simultaneous full burst; multi-edge held link bound must be priced separately.',
                   ECC='8178892800 remote sidecar DATA parity bits in full-model allocated per-rank templates, not measured traffic. Corrected compute needs protected sidecar-word decoder and original bit identity causally before result; derive per-event256+10word reads/coalescing from actual main-read schedule.',
                   HE_CROM='All80 original providers retain exact stage/globalpair/nativeword/lane coordinates. New shard routing includes HE bank ownership and CROM read request/return debts; existing adapters still unimplemented.',
                   finite_calendar='Use B.finite_calendar with actualedge events, bits including headers, explicit width/positive latency/slots. All channels on one link share FIFO. Originalconsumerdeadlines must come from source program events, not fitted sensitivity.',
                   no_loss='No added serialstages or TP4 levels; assert remote visible <= original consumer dependency deadline for cfg,input,ECC,roots,provider requests and rearm; propagate exposed stalls to descendants.',
                   delivered_source_edges_and_original_deadlines_bound=False,
                   source_target_clock_domains='stream1.2GHz; serial0.9GHz; SSsetup60ps/FFhold25ps unchanged. Calendar tick must be bound to source domain; no physical closure claim.'),
               local_parity_option=dict(
                   status='LEGAL_SYMBOLIC_STORAGE_OPTION_NOT_SELECTED_OR_PHYSICAL_PROVIDER_QUALIFIED',
                   same_candidate_NP2048_R64_NBF362_and_all_original_matrices_unchanged=True,
                   original58x103completeparitypairs_preserved=True,
                   new_mirrors_per_stage=103,all58_stage_mirror_pairs=sum(x['extra_complete_pairs_used'] for x in replicas),
                   TP4_total_mirror_pairs=4*sum(x['extra_complete_pairs_used'] for x in replicas),
                   extra_redundant_useful_parity_data_bits_per_rank=sum(x['bits'] for x in replicas),
                   extra_reserved_provider_capacity_bits_per_stage=103*4194304,
                   original_padding_shard0=337,original_padding_shard1=384,remaining_padding_shard1=281,
                   extra_macro_instance_count=0,already_charged_padding_macros_used_per_stage=412,
                   prospective_694p883_macro_body_screen_unchanged_but_new_adapters_UNPRICED=True,
                   local_parity_word_endpoint_boundaries_checked=boundary_checks,
                   conditional_cross_shard_parity_data_reads_after_local_copy=0,
                   precompute_qualification='Actual local protected256+10-word read/decoder/coalescer calendar before corresponding mainword compute; local address removes transport dependency, not the read/qualification latency.',
                   ECC_read_port_capacity_and_capture_or_adapter_SSFF_price_UNBOUND=True,
                   immutable_provider_copy_provenance_and_physical_ROM_init_NOT_QUALIFIED=True),
               minimal_adapter_state=dict(
                   mirrored_phase_key_bits_per_shard=1024*32,mirrored_phase_R0_policy_bits_per_shard=1024,
                   both_tables_repeated_on464_layerdies=True,
                   tables_exist_in_old_owner_and_no_full_double_area_credit=True,
                   additional_table_copy_bits_per_old_rank_owner=1024*33,
                   accepted_shard_lease_min_bits_per_logical_owner=2,
                   required_generation_identity='phase10,era1,opseq13 with all source/owner/delivery/causalvisibility debts fenced before wrap; source producer cancellation state17 remains distinct',
                   root_capture_one_full64packet_burst_bits=64*108,
                   ECC_remote_word_capture_and_coalescing_slots_unbound=True,
                   additional_accept_return_adapter_SSFF_area_unqualified=True,
                   source_R128_to_two_R64_wrapper_adaptation_REQUIRED=True),
               verdict='PASS_SYMBOLIC_SOURCE_BOUND_PAR2_MAP_PROVIDER_AND_TRANSPORT_CONTRACT_ONLY',
               build_admitted=False,rate_adopted=False,single_token_no_loss_proven=False,
               actual_provider_and_remote_event_calendar_qualified=False,
               next_cheapest_gate='Maxwell/Peirce deliver source accepted cfg/input/root/ECC/HE/CROM arrivaledges, originalconsumerdeadlines, finite link/CDC/capture params and causal fence identities for this exact PAR2; evaluate shared calendar before adapter RTL or physical build.')
    model['generator_sha256']=J.sha(Path(__file__))
    model['binding_artifact_sha256']={p.name:J.sha(p) for p in sorted(binding.iterdir()) if p.is_file()}
    (out/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(verdict=model['verdict'],readback=proof)))


def main():
    p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.binding,a.out)
if __name__=='__main__':main()
