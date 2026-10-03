#!/usr/bin/env python3
"""One PAR2 symbolic binding of immutable622 plans; no repack, RTL or rate credit.

The calendar consumes actual source-edge events and explicit finite link/provider
parameters. Interface widths are never inferred to be link bandwidths.
"""
from __future__ import annotations
import argparse, collections, json, math, subprocess, sys
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_owner_cfg_interface_export as E
import dsrom_owner_provider_first as P
import dsrom_native_weight_address_join as J
ROOT=C.ROOT
OUT=ROOT/'results/uarch/dsrom_parallel_owner_binding_20261002'
CANDIDATE_COMMIT='dcc64cc119fa4e3b8069e90de54f456dea169882'
CANDIDATE_PATH='results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002/model-r4.json'
FIELD_COMMIT=E.PARENT
FIELD_PATH='rtl/v41die/ot_v41_field_w17w10.sv'
GLOBAL_BF=frozenset(i*4096//724 for i in range(724))


def site(g):
    if type(g) is not int or not 0<=g<4096:raise ValueError('compiled global site')
    s,p=divmod(g,2048)
    return dict(global_site=g,shard=s,local_site=p,global_return_region=g//32,
                local_return_region=p//32)


def coordinate(a):
    return {**a,**site(a['pair']), 'pair_is_original_global_site':True,
            'local_provider_pair':a['pair']%2048}


def address(m,phase,rank,row,k,ecc=None):
    a=coordinate(J.physical_address(m,phase,rank,row,k,ecc))
    if m['format']=='fp4':
        for key in ('ECC_extra_sidecar_first_bit','ECC_extra_sidecar_last_bit'):
            a[key]=coordinate(a[key]);a[key]['remote_from_code_owner']=a[key]['shard']!=a['shard']
    return a


def cfg_word(m,shard,local_pair,word):
    if shard not in (0,1) or type(local_pair) is not int or not 0<=local_pair<2048:raise ValueError('local cfg site')
    # Never rewrite global row/segment tags in the48-bit payload.
    return E.config_word(m,shard*2048+local_pair,word)


def provider_address(p,alias,row,col=0):return coordinate(P.provider_tensor_address(p,alias,row,col))


def ecc_runs(provider,start,length,code_shard):
    """Exact protected256-bit sidecar span; pair boundary4194304 data bits."""
    if start<0 or length<0 or start+length>provider['bits']:raise ValueError('sidecar span')
    out=[];end=start+length
    while start<end:
        pi=start//(16384*256);stop=min(end,(pi+1)*16384*256)
        a=site(provider['pairs'][pi])
        out.append(dict(**a,linear_bit_range=[start,stop],data_bits=stop-start,
                        remote_from_code_owner=a['shard']!=code_shard))
        start=stop
    return out


def bind_phase(m,p,ecc):
    if (m['layer'],m['alias'],m['stage'])!=(p['layer'],p['alias'],p['stage']):raise ValueError('phase owner mismatch')
    if J.digest(m['plans'])!=p['payload_plan_sha256']:raise ValueError('immutable plan hash')
    subs=[dict(shard=s,local_NP=2048,local_NBF=362,R=64,plan_ordinals=[],
               physical_weight_words=0,output_rows=0,ECC_local_bits=0,ECC_remote_bits=0) for s in (0,1)]
    prefix=0
    for ordinal,run in enumerate(m['plans']):
        si,g,first,n,stride,start,w=run;a=site(g);d=subs[a['shard']]
        if stride!=128 or first%128!=a['global_return_region']:raise ValueError('ordered row/region mismatch')
        if start%2 or start+n*w>C.DEPTH:raise ValueError('physical capacity')
        if m['format']=='bf16' and g not in GLOBAL_BF:raise ValueError('BF physical site')
        d['plan_ordinals'].append(ordinal);d['physical_weight_words']+=2*n*w
        if si==0:d['output_rows']+=sum(min(2,m['rows']-2*(first+j*stride)) for j in range(n))
        if m['format']=='fp4':
            for x in ecc_runs(ecc,m['ecc_bit_base']+prefix,16*n*w,a['shard']):
                d['ECC_remote_bits' if x['remote_from_code_owner'] else 'ECC_local_bits']+=x['data_bits']
            prefix+=16*n*w
    if sum(s['output_rows'] for s in subs)!=m['rows']:raise ValueError('row conservation')
    if sum(s['physical_weight_words'] for s in subs)!=P.matrix_words(m):raise ValueError('capacity conservation')
    return dict(stage=p['stage'],phase=p['phase'],layer=p['layer'],alias=p['alias'],
                source_key_word=p['source_key_word'],matrix_journal_ordinal=p['matrix_journal_ordinal'],
                payload_plan_sha256=p['payload_plan_sha256'],format=m['format'],K=m['K'],
                rows_per_rank=m['rows'],rank_slices=m['rank_slices'],shards=subs,
                row_cross_shard_K_reductions=0,ordered_global_row_tags_unchanged=True,
                cfg_word_range=p['config_logical_word_range'],cfg_parallel_provider_reads_per_pair=25,
                source_LAT8_issue_condition_cycles=m['issue_cycles_LAT8_condition'])


def map_selection(binding,phases,ids=None):
    if not binding.get('address_bound'):raise ValueError('unbound native provider')
    choices=binding['phase_choices']
    if binding['selector_slot'] is not None:
        J.expert_ids(ids);choice=choices[ids[binding['selector_slot']]]
    else:
        if ids is not None:raise ValueError('nonindexed selection')
        choice=choices[0]
    p=phases[(choice['stage'],choice['phase'])]
    if p['source_key_word']!=choice['source_key_word'] or p['alias']!=choice['alias']:raise ValueError('selection owner')
    return dict(**choice,required_shards=[s['shard'] for s in p['shards'] if s['output_rows']],
                source_alias_and_predicate_unchanged=True)


def finite_calendar(events,*,width_bits,latency_cycles,slots):
    """FIFO whole-frame capture, finite store-and-forward, integer stream edges.

At arrival edge e a slot is reserved (source cannot be backpressured). Serialization
starts at max(e, previous finish), lasts ceil(framebits/width) intervals; visibility
edge is finish+latency. Slots release at that visibility edge before new arrivals.
Headers MUST be included in framebits. No implicit CDC/capture zero-cycle credit.
    """
    if any(type(v) is not int for v in (width_bits,latency_cycles,slots)) or width_bits<=0 or latency_cycles<1 or slots<=0:raise ValueError('finite link parameters')
    journal=[];busy=0;occupied=[];seen=set();peak=0
    for e in events:
        if any(type(e.get(k)) is not int for k in ('arrival_cycle','bits','original_deadline_cycle')) or e['arrival_cycle']<0 or e['bits']<=0:raise ValueError('source event')
        identity=tuple(e['identity'])
        if len(identity)!=8 or identity in seen:raise ValueError('duplicate or incomplete owner identity')
        # stage/rank/shard/phase/era/opseq/channel/beat, source-assigned, never alias.
        stage,rank,shard,phase,era,seq,channel,beat=identity
        if not (0<=stage<58 and 0<=rank<4 and shard in (0,1) and 0<=phase<1024 and era in (0,1) and 0<=seq<8192 and type(channel) is str and type(beat) is int and beat>=0):raise ValueError('owner identity bounds')
        if journal and e['arrival_cycle']<journal[-1]['arrival_cycle']:raise ValueError('unordered source events')
        seen.add(identity);occupied=[t for t in occupied if t>e['arrival_cycle']]
        if len(occupied)>=slots:raise ValueError('unbackpressured capture overflow')
        start=max(e['arrival_cycle'],busy);finish=start+math.ceil(e['bits']/width_bits);visible=finish+latency_cycles
        occupied.append(visible);peak=max(peak,len(occupied));busy=finish
        journal.append(dict(**e,serialization_start=start,serialization_finish=finish,visible_cycle=visible,
                            exposed_cycles=max(0,visible-e['original_deadline_cycle'])))
    return dict(journal=journal,peak_capture_slots=peak,terminal_visible_cycle=max(occupied,default=0),
                no_loss_on_supplied_fixed_source_calendar=all(x['exposed_cycles']==0 for x in journal),
                full_token_no_loss_proven=False,source_stalls_or_interacting_ports_require_composed_replay=True)


def generate(out):
    if out.exists():raise ValueError('new immutable directory required')
    out.mkdir(parents=True)
    raw=subprocess.check_output(['git','show',CANDIDATE_COMMIT+':'+CANDIDATE_PATH],cwd=ROOT)
    (out/'candidate_source.json').write_bytes(raw)
    candidate=json.loads(raw)['single_parallel_successor']
    if (candidate['local_compiled_NP'],candidate['local_NBF'],candidate['ordered_return_regions_per_shard'])!=(2048,362,64):raise ValueError('single coordinated candidate')
    rawfield=subprocess.check_output(['git','show',FIELD_COMMIT+':'+FIELD_PATH],cwd=ROOT)
    (out/'ot_v41_field_w17w10.sv').write_bytes(rawfield)
    for x in ('localparam integer NL = 2 * NP','localparam integer LS = L - LR','(i * NP) / NBF == p','nv[LS][g]'):
        if x not in rawfield.decode():raise ValueError('source field topology')
    phases=list(C.readrows(J.PHASES));ecc={p['stage']:p for p in C.readrows(E.OUT/'export_r1/FP4_ECC_provider_directory.jsonl.gz')}
    sums=collections.Counter();formats=collections.Counter();stage_totals=collections.defaultdict(collections.Counter)
    def rows():
        for ordinal,(m,p) in enumerate(zip(C.readrows(J.JOURNAL),phases,strict=True)):
            if p['matrix_journal_ordinal']!=ordinal:raise ValueError('ordinal')
            r=bind_phase(m,p,ecc[m['stage']]);sums['phases']+=1;formats[m['format']]+=1
            for s in r['shards']:
                for key in ('physical_weight_words','output_rows','ECC_local_bits','ECC_remote_bits'):sums[key]+=s[key];stage_totals[m['stage']][key]+=s[key]
            sums['both_shards_active']+=int(all(x['output_rows'] for x in r['shards']))
            yield r
    C.gzrows(out/'phase_shard_bindings.jsonl.gz',rows())
    if sums['phases']!=46509:raise ValueError('full model phase closure')
    mapped=list(C.readrows(out/'phase_shard_bindings.jsonl.gz'));index={(p['stage'],p['phase']):p for p in mapped}
    def natives():
        for b in C.readrows(J.D/'r3/node_bindings.jsonl.gz'):
            if not b.get('address_bound'):continue
            alternatives=[]
            for q in b['phase_choices']:
                p=index[(q['stage'],q['phase'])]
                if q['source_key_word']!=p['source_key_word'] or q['alias']!=p['alias']:raise ValueError('native binding')
                alternatives.append(dict(**q,required_shards=[s['shard'] for s in p['shards'] if s['output_rows']],
                                         remote_rows=p['shards'][1]['output_rows'],remote_source_root_wire_bits=69*p['shards'][1]['output_rows']))
            yield dict(node=b['node'],selector_slot=b['selector_slot'],phase_choices=alternatives,
                       native_admission_failures=b['native_admission_failures'],input_VM=b['consumer_X_FP32_VM_elements'],
                       output_base=b['consumer_output_base_elements'],output_format=b['output_format'])
    C.gzrows(out/'native_shard_choices.jsonl.gz',natives())
    provider_records=[]
    for p in list(C.readrows(E.OUT/'export_r1/immutable_provider_directory.jsonl.gz'))+list(ecc.values()):
        provider_records.append(dict(**p,complete_pair_shard_bindings=[site(g) for g in p['pairs']],
                                     source_provider_word_API_unchanged=True,physical_adapter_qualified=False))
    C.gzrows(out/'provider_shard_bindings.jsonl.gz',provider_records)
    oldbf={i*4096//724 for i in range(724)};newbf={i*2048//362 for i in range(362)}
    if any({g%2048 for g in oldbf if g//2048==s}!=newbf for s in (0,1)):raise ValueError('BF mask')
    native=list(C.readrows(out/'native_shard_choices.jsonl.gz'))
    allchoices=sum(len(x['phase_choices']) for x in native)
    model=dict(schema='opentallas.dsrom.PAR2-owner-binding.v1',candidate=candidate['candidate_id'],
        candidate_commit=CANDIDATE_COMMIT,candidate_model_sha256=C.sha((out/'candidate_source.json').read_bytes()),
        field_source_commit=FIELD_COMMIT,field_source_sha256=C.sha(rawfield),owner_commit=E.OWNER,
        source_totals=dict(sums),phase_formats=dict(formats),native_calls=len(native),native_expert_alternatives=allchoices,
        site_bijection=[site(g) for g in range(4096)],BF_mask_exact=True,
        compiled_shape=dict(NP=2048,NBF=362,R=64,PHW=10,RD=64,ROOTD=128,shards=2,stages=58,TP=4,
                            pair_leaves=2,source_region_leaf_count=64,source_region_tree_levels=6,
                            weight_macros_per_die=8192,cfg72_macros_per_die=14336,layer_dies=464),
        active_and_padding=candidate['actual_622_shard_site_census'],
        source_R128_wrapper_is_directly_compatible=False,
        return_adapter='Map local port j to original global port64*shard+j; retain16-bit GLOBAL row tags. Concatenate original port order, never sum roots from different rows. One row all K subtrees resides in one shard.',
        phases_and_cfg='PHW10 tables copied to both shards; pair words are selected by original global_site. Original25*48-bit config words, global row/segment tags unchanged.7hardcfg72 macros charged per ALL2048sites; no active-only discount.',
        q_on_BF='Source BF dual mask preserved, no newly qualified hardened dual-mode abstract. Storage counted once.',
        conservation='Bijection over ALL4096sites including721padding. All46509plans and original rows,K,code/scale/ECC addresses conserved symbolically. No repacking, omitted expert or payload reads.',
        provider_totals=dict(HE=sum(p['kind']=='HE' for p in provider_records),CROM=sum(p['kind']=='CROM' for p in provider_records),FP4_ECC=sum(p['kind']=='ECC_FP4_SIDECAR' for p in provider_records)),
        finite_transport_contract=dict(
            activation_full_source_bus_bits=1616,narrow_q_source_interface_bits=549,
            remote_roots=64,source_root_bits=69,source_simultaneous_remote_root_bits=4416,
            wire_widths_are_NOT_link_bandwidth=True,
            required_event_identity='stage6/rank2/shard1/phase10/era1/opseq13/channel/beat; full bounds before truncate, causal fence before sequence wrap',
            source_root_packet_proposal_bits=108,root_header_bits=39,
            source_full_activation_packet_proposal_bits=1649,activation_header_bits=33,
            header_format_is_unimplemented=True,
            cfg_parallel_reads_per_pair=25,cfg_command_latency='finite command transport + actual25read/capture/ECCdecoder calendar + all-selected-pair delivery fence; never25*2048words from one broadcast',
            admission='Reserve two shard leases for selected phase; same-edge fault suppresses all accept/issue, freeze mismatched cfg generation. No go until both required cfg/input fences; keep accepted debts through source/owner retirement and causal visibility.',
            ECC='Each code read must bind its original inline2 and sidecar8 parity bits before corrected compute/return; remote sidecar traffic and decoder cycles require actual accepted word/calendar, cannot subtract from weight issue time.',
            root_capture='No ready on actualfieldroot ports; finite capture sized to actual worst arrivals and held-link interval; overflow isFAIL, not backpressure credit.',
            evaluator_API='finite_calendar(source_edge_events,width_bits,latency_cycles>=1,slots); bits include headers, all ports sharing link calendar serialized. Overflow/alias fails closed.',
            actual_link_width_latency_slots_and_cfg_decoder_calendar_bound=False,
            actual_source_arrival_and_consumer_deadline_calendar_bound=False,
            no_token_loss_test='Every dependency consumer deadline >= remote input/config/root/ECC visible edge including shared-port serialization and CDC; recompute descendants on exposed stalls.'),
        physical_area_screen_mm2=candidate['conservative_priced_per_shard_mm2'],
        additional_link_capture_cfg_adapter_area_not_included=True,
        mode_dependency='1d8380224b0cc5b11364c4a20f8328d4998abdb0 sixphase R0 inputproof and dedicated head ordered-provider contract; native failing descriptors remain unqualified',
        verdict='PASS_SYMBOLIC_FULL_MODEL_PAR2_BINDING_TRANSPORT_AND_PROVIDER_TIMING_UNQUALIFIED',
        single_token_no_loss_proven=False,build_admitted=False,performance_adopted=False,physical_provider_qualified=False,
        next_gate='Maxwell/Peirce source-edge accepted cfg/input/root/sidecar events with fixed positive link params, finite slots and original consumer deadlines; run finite shared-resource calendar before defaultoff adapter RTL or physical build.',
        stage_encoded_totals={str(k):dict(v) for k,v in sorted(stage_totals.items())})
    deps=[Path(__file__),ROOT/'tools/dsrom_full_owner_compiler.py',ROOT/'tools/dsrom_owner_cfg_interface_export.py',ROOT/'tools/dsrom_owner_provider_first.py',ROOT/'tools/dsrom_native_weight_address_join.py',J.PHASES,J.JOURNAL,E.READBACK,J.D/'r3/node_bindings.jsonl.gz',E.OUT/'export_r1/immutable_provider_directory.jsonl.gz',E.OUT/'export_r1/FP4_ECC_provider_directory.jsonl.gz']
    deps += [Path(x.__file__).resolve() for x in list(sys.modules.values()) if getattr(x,'__file__',None) and Path(x.__file__).resolve().is_relative_to(ROOT/'tools')]
    model['source_dependency_sha256']={str(p.relative_to(ROOT)):J.sha(p) for p in sorted(set(deps))}
    (out/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(out=str(out),verdict=model['verdict'],totals=dict(sums))))


def main():
    a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args();generate(args.out)
if __name__=='__main__':main()
