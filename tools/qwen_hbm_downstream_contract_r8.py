#!/usr/bin/env python3
"""Source-owned downstream contracts and exact272-sector fixture; no RTL build.

Fixture contains demands and required interfaces, NEVER invented callbacks.
IRS retirement is a supported conditional edge, not a Qwen consumer provider.
Additive slot failure includes inherited occupancy and nonnegative via/PDN
unknowns: no empty service band or free retirement/reuse is assumed.
"""
from collections import Counter
from fractions import Fraction as F
import argparse,hashlib,json,math,re
from pathlib import Path
from qwen_hbm_controller_events_r1 import ROOT,pinned
from qwen_hbm_controller_calendar_r2 import BASE,PROGRAM,kv_rows,kv_read_rows

PIN='a4e647e327b1692259f32a658b84fe3db7e09c7b'
OBS='results/rtl/qwen_hbm_provider_observation_r5_20261002'
DIR='results/uarch/qwen_hbm_downstream_contract_20261002'
FAST=F(2500,3);SLOW=F(10000,9)
PATHS=[
 'rtl/hdc/kv/ot_hdc_hbm_model.sv','rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv',
 'rtl/hdc/hbm/ot_hdc_qwen_kv_pc_adapter.sv','rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv',
 'rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv','rtl/hdc/kv/ot_hdc_qwen_kv_system.sv',
 'rtl/abi3/ot_a3_issue_record_store.sv','rtl/abi3/ot_a3_event_scoreboard.sv',
 'rtl/abi3/ot_a3_microsequencer.sv','rtl/abi3/ot_a3_pkg.sv','rtl/lib/ot_async_fifo.sv',
 'tools/qwen_hbm_complete_common36.py','tools/qwen_hbm_complete_service_provider.py',
 'tools/qwen_o4_floorplan.py','configs/signoff/pdn_m7_m8_upper_grid.tcl',
 'configs/signoff/pdn_m7_m8_wide_upper_grid.tcl','configs/pdk/asap7_local_liberty_lock.json']

def sources():return {p:pinned(ROOT,PIN,p).decode() for p in PATHS}

def port_names(raw):
    # Restrict to the module header: comments do not count as implemented ports.
    raw=re.sub(r'//[^\n]*','',raw)
    header=raw[:raw.index(');')]
    return re.findall(r'\b(?:input|output)\s+(?:wire|reg)\s*(?:\[[^]]*\]\s*)?(\w+)',header)

def audit_sources():
    s=sources();paths={p:dict(commit=PIN,sha256=hashlib.sha256(v.encode()).hexdigest()) for p,v in s.items()}
    assertions=[
      ('controller_no_WR_completion','rtl/hdc/kv/ot_hdc_hbm_model.sv',lambda r:not any('done' in p or 'visible' in p for p in port_names(r))),
      ('PC_service_unready_pulse','rtl/hdc/hbm/ot_hdc_qwen_pc_service.sv',lambda r:'p_wr_done_v' in port_names(r) and not any('wr_done_rdy' in p or 'wr_done_ready' in p for p in port_names(r))),
      ('IRS_real_conditional_retirement','rtl/abi3/ot_a3_issue_record_store.sv',lambda r:'retire_serial <= serial[complete_slot];' in r and 'retire_valid <= 1\'b1;' in r),
      ('prototype_WR_accept_releases_buffer','rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv',lambda r:'WREQ: if (mem_w_ready)' in r),
      ('prototype_no_lease_retire_endpoint','rtl/hdc/kv/ot_hdc_qwen_kv_system.sv',lambda r:not any('lease' in p or 'retire' in p for p in port_names(r))),
      ('callback_consumer_is_supplied','tools/qwen_hbm_complete_common36.py',lambda r:'def consumer_result_retire(self,die,tag,epoch,result_visible_ps,dut_retire_ps)' in r),
      ('leased_consumers_are_supplied','tools/qwen_hbm_complete_service_provider.py',lambda r:"for instruction in (link['scores'], link['pv'])" in r and 'def retire(self, position, instruction, result_visible_ps, retire_ps)' in r)]
    for name,path,test in assertions:assert test(s[path]),name
    return dict(pins=paths,checks=[dict(rule=n,path=p,status='PASS_SOURCE_AUDIT_ONLY') for n,p,_ in assertions],
      endpoints=[
       dict(name='Common36',kind='Python_callback_validator',identity='sector/tag/logicalowner/transportepoch',missing='Actual allocation-epoch snapshot and result-visible/DUT-retire providers; callbacks are caller supplied.'),
       dict(name='RMW/write prototype',kind='Existing_RTL_unbound_prototype',identity='sector and payload, no accepted producer epoch or IRS serial',missing='Releases on mem_w_ready; no held-visible sector ownership/retirement. Do not adopt K-tail topology or one-edge parallel byte merge as the GPU instruction provider.'),
       dict(name='KV_READ/SCORES/PV',kind='Encoded_program_plus_callback_model',identity='writer10/read12/scores13/pv15, position1, layer0/die0',missing='No stitched epoch/address-bearing ready/valid lease-acquire or result-retire/lease-release interface.'),
       dict(name='ABI3_IRS',kind='Existing_generic_RTL',identity='slot5+serial32+event32, no KV address/generation',supported='Registered retirement one consumer-clock cycle after actual complete_valid hit.',missing='Qwen engine completion/result provider and persistent owner correlation into Common36/lease scoreboard.')],
      existing_retirement_is_Qwen_provider=False,sector_vs_opcode_retirement=dict(sector_credits_per_die=4,required_sector_completions=272,verdict='FAIL_CIRCULAR_WAIT_IF_SECTOR_CREDIT_USES_WHOLE_WRITER_OPCODE_RETIRE',reason='KV_WRITE10 cannot complete all272 sectors if its four active sector credits wait for the single whole-instruction retirement. A real addressed sector-store retirement endpoint is separately required; generic IRQ completion alone cannot create272 sector retirements.'))

def fixture():
    g=json.loads(pinned(ROOT,BASE,PROGRAM));op=g['instructions'][10]
    assert [g['instructions'][i]['opcode'] for i in (10,11,12,13,15)]==['KV_WRITE','KV_FENCE','KV_READ','SCORES','PV']
    rows=kv_rows(g,op,1);prefix=kv_read_rows(g,op,1)
    assert len(rows)==272 and sum(r['partial'] for r in rows)==256
    records=[dict(writer=10,position=1,layer=0,die=op['attributes']['die'],**r,
                  request_epoch_source='REQUIRED_ACCEPTANCE_SNAPSHOT',physical_tag_source='REQUIRED_FINITE_COMMON36_ALLOCATION',IRS_correlation_source='REQUIRED_ALLOC_SLOT_SERIAL_CAPTURE',required_retirement_stages=['RMW_read_result_and_DUT_retire'] if r['partial'] else []) for r in rows]
    for r in records:r['required_retirement_stages']+=['fullAW_backing_visible','held_ACK_capture','forward_CDC','completion_bit_store','sector_consumer_result_and_DUT_retire','reverse_credit']
    return dict(schema='Actual_address_metadata_downstream_fixture_r8',status='REQUIREMENTS_ONLY_NO_FABRICATED_EVENT_TIMESTAMPS',program_pin=BASE+':'+PROGRAM,instruction_count=len(g['instructions']),writer=10,position=1,sector_count=272,partial_RMW_count=256,sectors_by_stack=dict(Counter(r['stack'] for r in rows)),sector_rows=records,KV_prefix_read_rows=prefix,
      directory_precondition='Position0 generation must be truly published and remain readable in same epoch; no synthetic prior-generation publication.',
      instruction_dependencies=[dict(id=i,opcode=g['instructions'][i]['opcode'],dependencies=g['instructions'][i]['dependencies'],provider_key=g['instructions'][i]['provider_key']) for i in (9,10,11,12,13,14,15,16)],
      required_final_events=['all272 completed reversecredit records','writer/fence actual result and retirement','KV_READ actual acquisition/retirement','SCORES result-visible+IRS-retire','PV result-visible+IRS-retire after EXP_SUM14','lease release then writer-context release'],
      supplied_retirement_events=[],supplied_lease_ACKs=[],encoded_payload=False)

class OwnedRetirementLedger:
    """Finite additive endpoint model. Every result/retire is an explicit input.

    This validates a proposed owner-correlator protocol. Passing this Python
    object never asserts that such an endpoint exists in the current source.
    """
    def __init__(self,rows):
        self.rows={r['ordinal']:r for r in rows};self.live={};self.bits=set();self.credited=set();self.leased=False;self.consumer_results={}
    def reserve(self,ordinal,slot,serial,producer_epoch,transport_epoch):
        if ordinal not in self.rows or ordinal in self.bits or ordinal in self.live:raise ValueError('exact descriptor/unique reservation')
        if len(self.live)>=4:return False
        if not 0<=slot<32 or not 0<=serial<1<<32 or not 0<=producer_epoch<1<<64 or not 0<=transport_epoch<1<<32:raise ValueError('identity aperture')
        if any((x['slot'],x['serial'])==(slot,serial) for x in self.live.values()):raise ValueError('IRS owner collision')
        self.live[ordinal]=dict(slot=slot,serial=serial,producer_epoch=producer_epoch,transport_epoch=transport_epoch,completed=False);return True
    def retire(self,ordinal,slot,serial,producer_epoch,transport_epoch,result_visible_ps,complete_ps,retire_ps,period):
        p=self.live[ordinal]
        if (slot,serial,producer_epoch,transport_epoch)!=(p['slot'],p['serial'],p['producer_epoch'],p['transport_epoch']):raise ValueError('captured owner/epoch/IRS identity')
        result,complete,retired,clock=map(F,(result_visible_ps,complete_ps,retire_ps,period))
        if clock<=0 or complete%clock or retired%clock or result>complete or retired<complete+clock:raise ValueError('actual visible/completion/registered IRS retirement')
        if p['completed']:raise ValueError('duplicate sector retirement')
        p.update(completed=True,retire_ps=retired);self.bits.add(ordinal)
    def reverse_credit(self,ordinal,now,period):
        p=self.live[ordinal];clock=F(period)
        if not p['completed'] or clock<=0 or F(now)<(p['retire_ps']//clock+3)*clock:raise ValueError('no invented reversecredit')
        del self.live[ordinal];self.credited.add(ordinal)
    def acquire_lease(self):
        if len(self.bits)!=272 or len(self.credited)!=272 or self.live:raise ValueError('all272 exact ownership retirements/reversecredits required')
        if self.leased:raise ValueError('duplicate lease')
        self.leased=True
    def consumer_result(self,name,instruction,result_visible_ps,complete_ps,retire_ps,period):
        # Mandatory caller event: no event is generated by a elapsed timer.
        if not self.leased or (name,instruction) not in [('SCORES',13),('PV',15)]:raise ValueError('actual matching leased consumer/instruction')
        result,complete,retired,clock=map(F,(result_visible_ps,complete_ps,retire_ps,period))
        if clock<=0 or result>complete or complete%clock or retired%clock or retired<complete+clock:raise ValueError('actual consumer visible/completion/IRS retirement')
        if name in self.consumer_results:raise ValueError('duplicate consumer retirement')
        self.consumer_results[name]=dict(result=result,retire=retired)
    def release_lease(self):
        if not self.leased or set(self.consumer_results)!={'SCORES','PV'}:raise ValueError('actual SCORES/PV result and retirement required')
        self.leased=False

def costs():
    r7=json.loads(pinned(ROOT,PIN,'results/uarch/qwen_hbm_resource_schedule_20261002/model_r7.json'))['physical']
    r=sources();q=r['tools/qwen_o4_floorplan.py']
    assert 'service_logic_um2=2 * 10e6' in q and 'LOGIC_UTIL = 0.50' in q
    inherited_per_stack=20.0/0.5/4
    owner_fields=dict(writer=11,position=21,die=1,stack=2,client=6,sector=34,ordinal=9,physical_tag=16,logical_tag=64,producer_epoch=64,transport_epoch=32,beat=5)
    owner=sum(owner_fields.values());IRS=dict(slot=5,serial=32,event_id=32)
    correlation=owner+sum(IRS.values())+3+1
    packet=owner+sum(IRS.values())+4+1+64+1
    lease=dict(writer=11,reader=11,scores=11,pv=11,position=21,layer=6,die=1,producer_epoch=64,transport_epoch=32,IRS_slots_and_serials=3*(5+32),flags=3,kind=3,visible_ps=64,valid=1)
    lease_width=sum(lease.values())
    # Independent owned-retirement channel: no subtraction from Common36
    # callback queues without a matched hardware replacement/width inventory.
    sector_retirement_bitmap_bits=2*272
    opcode_owner_contexts_per_die=4
    storage=sector_retirement_bitmap_bits+2*(4+opcode_owner_contexts_per_die)*correlation+2*(2*(4+1)+4)*packet+2*(4+1)*lease_width+8*22
    identity_compare=2*4*(owner+5+32)
    provider_area=(storage*.2916+identity_compare*.2)/.5/1e6
    # Explicit source-shaped max tree/comparator lower-order area proxy.
    # Timers retain full64 fields. Lowering ADD/clock/routing remains blocked.
    pc_count=8*32
    timer_ops=dict(ACT_max_nodes_per_PC=8,column_max_nodes_per_PC=6,FRFCFS_earliest_compare_nodes_per_PC=15,bank_row_equal_bits_per_PC=64,RAW_compare_bits_per_PC=4*34)
    timer_bit_eq=pc_count*((8+6)*64*2+15*64+64+4*34)
    timer_area=timer_bit_eq*.2/.5/1e6
    owned_shared_bundle=1160-216+packet+lease_width
    additive=r7['priced_subset_total_mm2_per_stack']+(provider_area+timer_area)/8
    combined=inherited_per_stack+additive;slot=r7['service_slot_area_mm2']
    profiles=[]
    for file in ('pdn_m7_m8_upper_grid.tcl','pdn_m7_m8_wide_upper_grid.tcl'):
        text=r['configs/signoff/'+file];stripes=[]
        for layer,width,pitch in re.findall(r'add_pdn_stripe .*?-layer \{(M\d+)\} -width \{([\d.]+)\}.*?-pitch \{([\d.]+)\}',text):
            stripes.append(dict(layer=layer,width_um=float(width),pair_pitch_um=float(pitch),metal_pair_fraction=2*float(width)/float(pitch)))
        profiles.append(dict(file='configs/signoff/'+file,stripes=stripes,scope='Configured signoff sizing grid only, not observed HBM service-band PDN. Do not relax50percent signal-share escrow.'))
    return dict(owner_fields=owner_fields,owner_bits=owner,IRS_fields=IRS,correlation_width=correlation,retirement_packet_bits=packet,lease_fields=lease,lease_packet_bits=lease_width,sector_owner_contexts_per_die=4,opcode_owner_contexts_per_die=opcode_owner_contexts_per_die,retire_FIFO_channels_per_die=2,retire_FIFO_depth_per_channel=4,reversecredit_FIFO_depth=4,lease_shared_FIFO_depth=4,sector_retirement_bitmap_bits=sector_retirement_bitmap_bits,additional_provider_FF_bits=storage,additional_provider_area_proxy_mm2=provider_area,timer_logic_inventory=timer_ops,timer_logic_bit_equivalents=timer_bit_eq,timer_compare_mux_proxy_mm2=timer_area,
      inherited_controller_fabric_reservation_mm2_per_stack=inherited_per_stack,priced_r7_subset_mm2_per_stack=r7['priced_subset_total_mm2_per_stack'],r8_additive_subset_mm2_per_stack=additive,total_retained_plus_additive_lower_bound_mm2_per_stack=combined,available_service_slot_mm2_per_stack=slot,area_overflow_lower_bound_mm2_per_stack=combined-slot,
      occupancy_overlap_credit=0,scope='Conservative additive to retained W5 fabric reservation. R7 bank/queue proxies cannot be subtracted from inherited reservation without a matched component inventory. Not a measured exact area.',
      slot_verdict='FAIL_RETAINED_INHERITED_OCCUPANCY_PLUS_ADDITIVE_COST',PDN_profiles=profiles,signal_share_reserved=0.5,
      candidate_overmacro_M4_to_upper_data_endpoint_vias_per_stack=32*(2*472+2*471),via_cost_contract='A_via_escape and PDN_grid_service_area must come from actual platform/cut/enclosure/net/pin geometry. Required_area >= known_additive +60352*A_via_escape +extra_PDN_area. Both are nonnegative, so current slot already fails without assigning either zero cost.',
      via_PDΝ_qualification='ABSENT_SERVICE_BAND_LAYOUT_AND_PLATFORM_GEOMETRY',failed_corridor=dict(raw_return_bits=15072,vertical_capacity=2696,all_stack_shared_bundle_bits=4*1160,owned_local_bundle_bits=owned_shared_bundle,owned_allstack_bundle_bits=4*owned_shared_bundle,direct_macro_escape_tracks=211.5072,pins_per_edge=793,verdict='FAIL_RETAINED_DIRECT_CORRIDOR_AND_PIN_ESCAPE'),
      timer_ADD_and_clock_logic='REQUIRED_IMPLEMENTATION_INVENTORY;64bit timer adders, fanout, clocktree/skew and SS/FF remain unclosed.',slot_fit=False)

def compose():
    a=audit_sources();f=fixture();c=costs()
    return dict(schema='Qwen_actual_downstream_endpoint_and_additive_contract_r8',status='SOURCE_ENDPOINTS_ABSENT_ADDITIVE_CONTRACT_PRICED_BEFORE_RTL',audit=a,fixture=dict(sector_count=f['sector_count'],partial_RMW_count=f['partial_RMW_count'],sectors_by_stack=f['sectors_by_stack'],descriptor_SHA256=hashlib.sha256(json.dumps(f['sector_rows'],sort_keys=True).encode()).hexdigest(),accepted_retirements=0,lease_ACKs=0),costs=c,
      additive_interfaces=[
       dict(name='accept_owner_capture',direction='controller/ingress -> owned map',required='Frozen fullAW34 address, exact encoded writer/position/ordinal, client/tag, producer64+transport32 at actual acceptance; no receiver stamping.'),
       dict(name='RF_result_visibility_completion',direction='conventional GPU RF/shared commit -> completion owner correlator',required='Actual addressed RMW merge/result visibility plus complete_slot; do not derive engine finish from HBM read take.'),
       dict(name='owned_opcode_IRS_retirement',direction='actual IRS retire -> Qwen result/lease correlator',required='Correlate actual slot5/serial32 with frozen instruction/generation before reuse; this is whole-opcode retirement, not automatic sector credit release.'),
       dict(name='owned_sector_store_retirement',direction='actual addressed completion-bit store -> held sector-retire endpoint',required='ADDITIVE missing conventional memory-tracker endpoint: reserve before store, actual completion-bit write/visibility, one registered retirement stage, immutable owned ready/valid output. Distinct from whole KV_WRITE opcode retirement; no event generated by this preparation.'),
       dict(name='fulladdress_WR_visible',direction='conventional HBM delayed commit -> held endpoint',required='Reserve BEFOREcommand/pop, commit after column+CWL+burst, held valid/ready with exact owner; legacy WRdone pulse cannot substitute.'),
       dict(name='publication_lease',direction='addressed completion directory <-> KVread/attention consumers',required='272 matching sector retirement+reversecredit entries; sameepoch prior/current generation acquisition; actual SCORES/PV result+IRS retirement; held lease release before writer reuse.')],
      source_supported_conditional_latencies=dict(IRS_complete_to_retire_consumer_edges=1,scoreboard_visible_store_serial_edges=1,CDC_destination_edges_per_direction=3),
      candidate_added_service=dict(sector_bit_store_serial_edges=1,sector_commit_to_owned_retire_serial_edges=1,sector_store_retire_pipeline_throughput_per_serial_edge=1,source_implementation_of_sector_retire_endpoint='ABSENT_ADDITIVE_CONTROL_CONTRACT_NOT_ACTUAL_ACK',owner_correlator_registered_capture_edges=1,held_packet_FIFO_accept_edges=1,retire_issue_arbitration_per_die='one/cycle,32IRSslots with at most4sector owners',retirement_flits_320_with_64_header=math.ceil((c['retirement_packet_bits']+64)/320),lease_flits_320_with_64_header=math.ceil((c['lease_packet_bits']+64)/320),retirement_NoC_flit_work_per_writer=272*math.ceil((c['retirement_packet_bits']+64)/320),retirement_NoC_lane_work_floor_FAST_ps=str(272*math.ceil((c['retirement_packet_bits']+64)/320)*FAST),scoreboard_stores_per_writer=272,scoreboard_work_floor_ps=str(272*SLOW),registered_sector_retirement_edges_work=272,store_retire_pipelining='Separate registered stages;272 stores and272 retirements overlap, do not serial-sum work floors.',RMW_serial_merge_edges_work=256*27,RMW_work_floor_ps=str(256*27*SLOW),phase_scope='Conditional structural candidate costs only; engine completion times, actual domain mapping and ready stalls must be supplied by the finite provider experiment.'),
      dependency_composition='sector credit release = reverseCDC(max(actual result visibility, actual IRS retirement, scoreboard visibility, owner FIFO/NoC readiness)); publication=max(all272 matching releases); reader=max(publication, prior-generation availability, actual lease acquisition); release=max(actual SCORES and PV visible+IRSretired)+heldlease service. Preserve EXP_SUM14 dependency for PV15. No sum of parallel work floors.',
      exact_experiment_input='Capture real engine complete/result and IRS alloc/retire signals with an accepted owner map, delayed HBM visibility, and actual lease/result endpoints. Current r5 source journal has none of these fields. Metadata fixture must not fill timestamps.',
      provider_PASS=False,RTL_admission=False,physical_admission=False,hardware_rate_credit=0,fullprogram_execution=False,checkpoint_payload=False)


def provider_ports():
    """Exact additive ready/valid ABI proposal; not implemented ports."""
    value={'channels': [{'capture': 'Actual request acceptance; producer epoch supplied by issuing owner, never receiver-stamped.', 'domain': 'controller', 'name': 'accept_owner', 'pins': {'owner': 265, 'ready': 1, 'valid': 1}}, {'capture': 'Actual conventional GPU RF/shared commit; owned opcode completion must refer to this result.', 'domain': 'consumer', 'name': 'result_commit', 'pins': {'IRS_serial': 32, 'IRS_slot': 5, 'owner': 265, 'ready': 1, 'result_visible_ps': 64, 'valid': 1}}, {'capture': 'Actual matching addressed bit-store visible handshake; producer held until ready.', 'domain': 'consumer', 'name': 'sector_store', 'pins': {'completion_bit': 1, 'owner': 265, 'ready': 1, 'valid': 1}}, {'capture': 'Additive finite memory-tracker registered retirement after actual store visibility, separate from whole-opcode IRS completion.', 'domain': 'consumer', 'name': 'sector_retire', 'pins': {'event': 404, 'ready': 1, 'valid': 1}}, {'capture': 'Snapshot actual IRS output; reserve capture at owner issue because source IRS output has no ready. Filter mapped ownership, no fabricated pulse.', 'domain': 'consumer', 'name': 'opcode_retire_capture', 'pins': {'event': 404, 'existing_IRS_fault': 1, 'existing_IRS_retire_valid': 1, 'existing_IRS_serial': 32, 'existing_IRS_slot': 5, 'held_ready': 1, 'held_valid': 1}}, {'capture': 'After272 sector retirement/reversecredit and true prior-generation availability.', 'domain': 'consumer', 'name': 'lease_acquire', 'pins': {'event': 350, 'ready': 1, 'valid': 1}}, {'capture': 'After actual SCORES and PV result-visible+IRS-retire snapshots and dependent operations.', 'domain': 'consumer', 'name': 'lease_release', 'pins': {'event': 350, 'ready': 1, 'valid': 1}}, {'capture': 'Finite4 FIFO, three destination edges plus explicit route/capture readiness; no release on ACK/store alone.', 'domain': 'consumer_to_controller', 'name': 'reversecredit', 'pins': {'event': 404, 'ready': 1, 'valid': 1}}], 'compile_GO': False, 'domains': {'consumer': {'actual_Qwen_IRS_domain_mapping': 'REQUIRED_PROVIDER_INPUT', 'candidate_period_ps': '10000/9'}, 'controller': {'actual_instantiation': 'source_r5only', 'candidate_period_ps': 1000}, 'hub': {'actual_stitched_endpoint': 'ABSENT', 'candidate_period_ps': '2500/3'}}, 'fields': {'IRS': {'event_id': 32, 'serial': 32, 'slot': 5}, 'event_width': 404, 'lease_width': 350, 'owner': {'beat': 5, 'client': 6, 'die': 1, 'logical_tag': 64, 'ordinal': 9, 'physical_tag': 16, 'position': 21, 'producer_epoch': 64, 'sector': 34, 'stack': 2, 'transport_epoch': 32, 'writer': 11}}, 'geometry': {'all_FIFO_control_instances': 8, 'capture_FIFO_depth_per_channel_per_die': 4, 'held_outputs_per_channel_per_die': 1, 'lease_shared_event_FIFO_per_die': 1, 'owned_opcode_contexts_per_die': 4, 'owned_sectors_per_die': 4, 'retire_channels_per_die': 2, 'reversecredit_FIFO_per_die': 1, 'source_IRS_is_pulse_capture_reserved_before_issue': True}, 'hardware_admission': False, 'source_endpoint_presence': False, 'status': 'ADDITIVE_INTERFACE_PROPOSAL_SOURCE_ENDPOINT_ABSENT_NO_RTL', 'unsupported_legacy_paths': ['Tag-only p_wr_done_v with no ready/epoch/address cannot carry these contracts.', 'KV adapter HAW32/PCS128 addr[6:0] selection differs from actual AW34 XOR PC map; no direct prototype capacity/identity transfer.']}
    c=costs()
    assert value["fields"]["event_width"]==c["retirement_packet_bits"]
    assert value["fields"]["lease_width"]==c["lease_packet_bits"]
    assert value["fields"]["owner"]==c["owner_fields"]
    return value

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();a.output_dir.mkdir(exist_ok=False)
    for name,record in [('model_r8.json',compose()),('fixture_metadata_r8.json',fixture()),('provider_ports_r8.json',provider_ports())]:
        with (a.output_dir/name).open('x') as out:json.dump(record,out,indent=2,sort_keys=True);out.write('\n')
