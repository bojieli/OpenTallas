#!/usr/bin/env python3
"""User-authorized no-ECC weight-ROM source flow; originals unchanged.
Original PP bank captures + i3 valid/tags deliver directly to block-dot lanes.
No parity/decoder/mirror/exception debt, global ECC seats, or added ACK protocol.
Local source-control accepted CE model is conditional on supplied READY slices;
parent owns actual upstream phase/cfg/activation/root edges and absolute deadline.
"""
from __future__ import annotations
import argparse,ast,collections,hashlib,itertools,json
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_native_weight_address_join as J
import dsrom_owner_cfg_interface_export as E
import dsrom_parallel_transport_contract as T
ROOT=C.ROOT;OUT=ROOT/'results/uarch/dsrom_PAR2_no_ECC_source_baseline_20261002';INPUT=OUT/'inputs'

def source_pair():
    tree=ast.parse((INPUT/'source_pair_calendar.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='pair_issue')
    scope=dict(S=C.S,collections=collections,LAT=8)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<unchanged source pair_issue ONLY>','exec'),scope)
    return scope['pair_issue']

def stream_inputs(m):
    # Reuse parent offered waveform as explicit conditional READY pairinputs,
    # not an upstream accepted-event claim or new cfg/VM/root generator.
    load=collections.Counter();units=collections.defaultdict(set)
    for si,pair,first,n,stride,start,w in m['plans']:
        e,size=m['segments'][si];u0,u1=C.S.unit_range(m['format'],e,size)
        for q,lo in enumerate(range(u0,u1,8)):
            us=list(range(lo,min(u1,lo+8)));units[q].update(us)
            load[pair,q]+=n*sum(len(C.S.unit_halves(m['format'],e,size,u)) for u in us)
    beats=[]
    for q,us in sorted(units.items()):
        us=sorted(us);length=max(8,len(us),max(v for (p,qq),v in load.items() if qq==q));slots={i*length//len(us):u for i,u in enumerate(us)}
        for b in range(8):
            for slot in range(length):
                u=slots.get(slot)
                if u is None:beats.append(0)
                else:
                    valid=sum(1<<h for h in (0,1) if 2*u+h<m['K']//256)
                    beats.append(1|u<<1|b<<9|valid<<12)
    return beats

class NoECCSourceFlow:
    """Finite native PP pipeline ownership; metadata-only, no payload injection.
    Outstanding tags reside in original i1/i2x/i3 stages, main data in original
    cap0/cap1 perMB. Source i2_v/lane sample is local retirement; no new ACKwire.
    """
    def __init__(self,owner):
        self.owner=tuple(owner);self.pending={};self.last_bank_issue={};self.bank_capture={};self.next_word=collections.defaultdict(int);self.last_edge=-1;self.peak=0;self.accepts=0;self.captures=0;self.consumes=0
    def step(self,event):
        edge=event['edge'];rid=tuple(event['request_id']);kind=event['kind']
        if type(edge) is not int or edge<self.last_edge:raise ValueError('ordered source edges')
        self.last_edge=edge
        if tuple(event['owner_context'])!=self.owner:raise ValueError('source owner/generation binding')
        addr=event['main_word_address'];pair,word=rid;bank=(pair,addr['PP'])
        if addr['local_pair']!=pair or addr['PP'] not in (0,1) or addr['MBs']!=[0,1] or type(addr['row']) is not int or not 0<=addr['row']<4096:raise ValueError('actual NB2/PP1 bank/address')
        if kind=='main_CE_accept':
            if rid in self.pending or edge-self.last_bank_issue.get(bank,-100)<2:raise ValueError('duplicate/read bank everyotheredge source pp_block')
            if word!=self.next_word[pair]:raise ValueError('original source word/reduction order')
            self.next_word[pair]+=1;self.last_bank_issue[bank]=edge
            self.pending[rid]=dict(accept=edge,address=addr.copy(),capture=None)
            self.accepts+=1;self.peak=max(self.peak,len(self.pending));return
        p=self.pending[rid]
        if p['address']!=addr:raise ValueError('word/address changed under native capture ownership')
        if kind=='bank_capture':
            if edge!=p['accept']+2 or p['capture'] is not None:raise ValueError('actual cap0/cap1 enabled issue+2 capture')
            old=self.bank_capture.get(bank)
            if old is not None and old in self.pending:raise ValueError('overwrite unconsumed native bank capture')
            p['capture']=edge;self.bank_capture[bank]=rid;self.captures+=1
        elif kind=='lane_consumer_sample':
            if p['capture'] is None or edge!=p['accept']+3 or self.bank_capture.get(bank)!=rid:raise ValueError('i3valid+selectedbank+tag consumer at issue+3')
            self.consumes+=1;del self.pending[rid]
        else:raise ValueError('no ECC/sidecar/check/wait/extraACK events in noECC baseline')
    def report(self):return dict(main_CE_pair_requests=self.accepts,main_MB_reads=2*self.accepts,matching_pair_captures=self.captures,source_lane_pair_consumers=self.consumes,maximum_boundary_obligations_including_sameedge_departure=self.peak,drained=not self.pending,new_global_ECC_request_seats=0,new_owner_ACK_wire=False)

def case(m,p):
    beats=stream_inputs(m);fn=source_pair();requests=[];pair_receipts=[]
    for si,g,first,n,stride,start,w in m['plans']:
        if g//2048!=1:continue
        e,size=m['segments'][si]
        ps=[dict(fmt=m['format'],e0=e,elems=size,row=first+i*stride,mi=0,seg=si,nseg=len(m['segments']),base=start,tensor=m['tensor']) for i in range(n)]
        issues,receipt=fn(ps,beats,positions=1,bf=False,XF=4)
        if receipt['overflow']:raise ValueError('conditional sourceFIFO failure preserved; no fit')
        if len(issues)!=n*w or C.phase_cfg(m,g)[16]>>6!=start:raise ValueError('source phase/config/read conservation')
        pair_receipts.append(dict(global_pair=g,peak_XFIFO=receipt['peak_XFIFO'],words=len(issues),last_issue=receipt['last_issue']))
        for wi,(edge,i,u,b,h,pos,slot) in enumerate(issues):
            a=start+wi
            requests.append(dict(request_id=[g%2048,wi],owner_context=[m['stage'],0,1,p['phase'],p['source_key_word'],0,0],source_word_slot=slot,source_global_pair=g,source_row_tags=[2*ps[i]['row'],2*ps[i]['row']+1],source_ordered_K_segment=si,source_activation_unit=u,source_activation_block=b,
              main_word_address=dict(local_pair=g%2048,PP=a%2,row=a//2,MBs=[0,1]),source_CE_accept_edge=edge,source_bank_capture_edge=edge+2,source_lane_consumer_edge=edge+3,source_acceptance_scope='CONDITIONAL_READY_PAIR_INPUT_SOURCE_MODEL_NOT_UPSTREAM_RTL_TRACE'))
    events=[]
    for r in requests:
        for kind,key in [('main_CE_accept','source_CE_accept_edge'),('bank_capture','source_bank_capture_edge'),('lane_consumer_sample','source_lane_consumer_edge')]:
            events.append(dict(kind=kind,edge=r[key],request_id=r['request_id'],owner_context=r['owner_context'],main_word_address=r['main_word_address']))
    flow=NoECCSourceFlow(requests[0]['owner_context'])
    # Capture/consume scheduling mirrors simultaneous source posedges; a
    # physical bank cannot overwrite before priorword was sampled atN+3.
    priority={'main_CE_accept':0,'bank_capture':1,'lane_consumer_sample':2}
    postedge_peak=0
    for edge,group in itertools.groupby(sorted(events,key=lambda e:(e['edge'],priority[e['kind']],e['request_id'])),key=lambda e:e['edge']):
        for event in group:flow.step(event)
        postedge_peak=max(postedge_peak,len(flow.pending))
    summary=flow.report();summary['maximum_registered_native_pipeline_tags_after_edge']=postedge_peak
    summary['boundary_obligations_are_NOT_extra_hardware_slots']=True
    if not summary['drained'] or summary['main_CE_pair_requests']!=len(requests):raise ValueError('native sourceflow debt conservation')
    return requests,dict(layer=m['layer'],alias=m['alias'],stage=m['stage'],phase=p['phase'],source_key_word=p['source_key_word'],K=m['K'],rows_per_rank=m['rows'],pair_receipts=pair_receipts,source_flow=summary,first_CE=min(r['source_CE_accept_edge'] for r in requests),last_CE=max(r['source_CE_accept_edge'] for r in requests),last_lane_consumer=max(r['source_lane_consumer_edge'] for r in requests),added_ECC_or_global_seat_cycles=0,actual_parent_cfg_VM_accepted_absolute_origin_bound=False)

def removal_census():
    providers=list(C.readrows(E.OUT/'export_r1/FP4_ECC_provider_directory.jsonl.gz'));field=json.loads(E.READBACK.read_text())['compiled_field'];rows=[]
    for p in providers:
        mirror=T.local_replica_plan(field,p)
        # Their immutable original allocation remains preserved. This record
        # deactivates provider demand/reservations; no silent reallocation.
        rows.append(dict(stage=p['stage'],original_ECC_only_reserved_pairs=len(p['pairs']),original_global_site_IDs=p['pairs'],mirror_Q_ONLY_padding_pairs=len(mirror['mirror_pairs']),mirror_global_site_IDs=mirror['mirror_pairs'],original_sidecar_data_bits=p['bits'],mirror_duplicate_data_bits=p['bits'],original_role_weight_macros=4*len(p['pairs']),mirror_role_weight_macros=4*len(mirror['mirror_pairs']),removed_request_and_initialization_demand=True))
    if len(rows)!=58 or any(r['original_ECC_only_reserved_pairs']!=103 or r['mirror_Q_ONLY_padding_pairs']!=103 for r in rows):raise ValueError('coordinated source provider census')
    return rows,dict(stages=58,TP_ranks=4,shards_per_rank=2,original_sidecar_data_bits_per_rank=sum(p['bits'] for p in providers),duplicate_mirror_bits_per_rank=sum(p['bits'] for p in providers),reserved_sidecar_capacity_bits_per_rank=sum(p['protected_data_capacity_bits'] for p in providers),original_role_macros_all58xTP4=sum(r['original_role_weight_macros'] for r in rows)*4,mirror_role_macros_all58xTP4=sum(r['mirror_role_weight_macros'] for r in rows)*4,
       current_compiled_NP_per_die=2048,current_weight_macros_per_die=8192,current_compiled_macro_charge_UNCHANGED_until_coordinated_source_inventory_change=True,physical_macro_count_area_credit_currently_taken=0,new_depth_or_partition_sweep=False,main274macro_and_nativecap274_retained=True,HE_CROM_dense_BF_head_norm_capacity_and_provider_ownership_NOT_removed=True)

def generate(out):
    if out.exists():raise ValueError('fresh immutable output required')
    receipts=json.loads((INPUT/'receipts.json').read_text())
    for r in receipts:
        if J.sha(INPUT/r['archive'])!=r['sha256']:raise ValueError('source hash')
    phases={p['matrix_journal_ordinal']:p for p in C.readrows(J.PHASES)};out.mkdir(parents=True);cases=[]
    for i,m in enumerate(C.readrows(J.JOURNAL)):
        if i>12:break
        if i not in (10,11,12):continue
        requests,summary=case(m,phases[i]);C.gzrows(out/(m['alias'].replace('.','_')+'_source_reads.jsonl.gz'),requests);cases.append(summary)
    rows,census=removal_census();C.gzrows(out/'removed_provider_roles.jsonl.gz',rows)
    old=ROOT/'results/uarch/dsrom_PAR2_parity_requests_adapter_20261002/inputs/padding_binding.json';area=json.loads(old.read_text())['area']
    model=dict(schema='opentallas.dsrom.PAR2.noECC-native-source-flow.v1',policy='USER_AUTHORIZED_NO_ECC_WEIGHT_ROM_QWEN_AND_DS; this artifact is DS-only, no Qwen qualification transfer.',source_pins=receipts,generator_sha256=J.sha(Path(__file__)),source_cases=cases,
      source_flow=dict(geometry='fixed4096 NB2 PP1; compiledNP2048/shard; no new architecture selection',main_physical_carrier_bits=274,main_payload_consumed_bits=272,upper2_bits_NOT_required_as_ECC=True,paired_main_carrier_bits=548,native_perpair_capture_bits=2*2*274,native_tag_valid_alignment='i1->i2x->i3; original TW tags/position/bank preserved',main_read_to_capture_cycles=2,main_read_to_lane_consumer_cycles=3,source_local_retirement='actual i2_v/lane sample of bank-selected word; implicit localconsumption, no inventedexternalACK wire.',source_predicate='w_run && f_cnt!=0 && !hazard && !pp_block && !(BP!=0 && bp_hold!=0)',source_no_arbitrary_global_128_or512_ECC_seat_constraint=True,field_root_writer_owner_response_debts_and_fault_drain_NOT_removed=True),
      removed_dependencies=['FP4 sidecar read/capture/gather','main orraw ECCclean check wait','correction/exception queue','mirrorcopy initialization/visibility debt','global ECC capture/request slot admission','new ECC nonce/decoder-return tags'],
      source_removed_dependency_cycles='Each read returns to originalsourcecaptureN+2 and laneconsumeN+3; no fixedwholephase gain inferred from oldconditionalECCcalendar or rootendpoint.',
      source_fault_scope='No correction/detection/retry requirement for weight ROM under userdecision. Existing arithmetic/XFIFO/control fault paths and source/provenance/ownership/address/tag correctness remain.',
      removal_census=census,
      prospective_area_removal=dict(parity_added_logic_allowance_removed_mm2=area['total_incremental_allowance_mm2'],old_screen_mm2=area['with_existing_clearances_screen_mm2'],screen_without_parity_logic_before_coordinated_clearance_removal_mm2=area['with_existing_clearances_screen_mm2']-area['total_incremental_allowance_mm2'],clearance_debits_NOT_subtracted_pending_Arch_binding_mm2=area['prior_macro_clearance_debits_retained_mm2'],named_components=area['named_logic_allowance_mm2'],no_duplicate_decoder_floor_subtraction=True,old_proposed_exclusive_ECC_state_removed_bits=area['state_bits'],old_additional_candidate_ECC_state_10202plus668_not_new_noECC_state=True,conditional512seat_proposal_NOT_carried_or_credited_as_instantiated=True,existing_native_bank_captures_and_i1_i2x_i3_tags_retained=True,physical_SSFF_context_fit_UNQUALIFIED=True),
      result='PASS_CONDITIONAL_NATIVE_SOURCE_CAPTURE_CONSUMER_FLOW_AND_NO_ECC_ROLE_CENSUS',actual_upstream_fullphase_acceptance_and_root_ACK_provider_UNBOUND=True,physical_macro_area_credit_taken=0,no_token_loss_proven=False,RTL_builds=0,physical_GO=False,
      dependencies={str(p.relative_to(ROOT)):J.sha(p) for p in [J.JOURNAL,J.PHASES,E.READBACK,E.OUT/'export_r1/FP4_ECC_provider_directory.jsonl.gz',Path(C.__file__),Path(J.__file__),Path(E.__file__),Path(T.__file__),old]})
    (out/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n');print(json.dumps(dict(result=model['result'],cases=[dict(alias=c['alias'],flow=c['source_flow'],last_lane_consumer=c['last_lane_consumer']) for c in cases],census=census)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);generate(p.parse_args().out)
