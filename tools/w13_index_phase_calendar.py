"""Finite phase leases and RF/shared event audit; no invented physical callbacks."""
from collections import Counter
import hashlib,json,subprocess
from pathlib import Path
CORE={'FADD':7,'FMUL':7,'IADD':7,'FCMP':7,'SHFL':5}
REQUIRED=('raw_decode_consumer_done','packer_scratch_consumer_done','decoded_store_visible','old_generation_return_drained','score_scratch_first_store')



def register_versions(events,source_events):
    """Source-assigned result identities, physical allocation and unread lifetimes."""
    errors=[];writers={};consumers=[];seen_results=set()
    for e in events:
        src=source_events.get(e['id'],{})
        operands=src.get('operand_register_bindings');results=src.get('result_register_bindings')
        if not isinstance(operands,list) or not isinstance(results,list):
            errors.append('source_operand_result_identity_unbound:'+str(e['id']));continue
        if e.get('operand_register_bindings')!=operands or e.get('result_register_bindings')!=results:
            errors.append('callback_operand_result_identity_mismatch:'+str(e['id']))
        rr=e['RF_register_reads'];rw=e['RF_register_writes']
        if [o.get('register') for o in operands]!=rr or [o.get('register') for o in results]!=rw:
            errors.append('source_register_allocation_mismatch:'+str(e['id']));continue
        scope=(e['sm'],e['partition'],e['warp_slot'])
        for index,o in enumerate(operands):
            if o.get('operand_index')!=index or not isinstance(o.get('result_id'),str) or not o['result_id']:
                errors.append('source_operand_identity_invalid:'+str(e['id']));continue
            producer=o.get('producer_event')
            if not isinstance(producer,str):errors.append('source_operand_producer_unbound:'+str(e['id']));continue
            if not producer.startswith('phase_input:') and producer not in src['dependencies']:
                errors.append('operand_producer_missing_source_edge:'+str(e['id']))
            consumers.append((scope+(o['register'],),e['RF_read_tick'],producer,o['result_id'],e['id']))
        for o in results:
            result=o.get('result_id')
            identity=(e['id'],result)
            if not isinstance(result,str) or not result or identity in seen_results:
                errors.append('source_result_identity_invalid:'+str(e['id']));continue
            seen_results.add(identity)
            writers.setdefault(scope+(o['register'],),[]).append((e['writeback_tick'],e['id'],result))
    for key,history in writers.items():
        history.sort(key=lambda x:(x[0] if type(x[0]) is int else -1,x[1]))
        for previous,current in zip(history,history[1:]):
            if type(previous[0]) is not int or type(current[0]) is not int:continue
            if previous[0]==current[0]:errors.append('register_version_write_collision')
            unread=[r for k,r,p,v,c in consumers if k==key and (p,v)==previous[1:] and type(r) is int]
            if unread and current[0]<=max(unread):errors.append('register_overwrite_before_last_consumer:'+previous[1])
    for key,read,producer,version,consumer in consumers:
        if type(read) is not int:continue
        history=[w for w in writers.get(key,[]) if type(w[0]) is int and w[0]<=read]
        if producer.startswith('phase_input:'):
            if history:errors.append('phase_input_register_version_overwritten:'+consumer)
        elif not history or history[-1][1:]!=(producer,version):
            errors.append('stale_register_version:'+consumer)
    return errors

def audit(events,leases,source_events):
    errors=register_versions(events,source_events);reads=Counter();writes=Counter();bankread=Counter();bankwrite=Counter();ready={e['id']:e['writeback_tick'] for e in events};seen=set();shared_read_addresses=set();shared_write_addresses=set()
    if not events:errors.append('ordinary_runtime_events_missing')
    for e in events:
        eid=e['id'];src=source_events.get(eid)
        if eid in seen:errors.append('duplicate_event:'+str(eid))
        seen.add(eid)
        if src is None or src['op']!=e['op'] or src['dependencies']!=e['dependencies']:
            errors.append('authoritative_source_event_mismatch:'+str(eid));continue
        sm,part,warp=e['sm'],e['partition'],e['warp_slot']
        if not(0<=sm<32 and 0<=part<4 and 0<=warp<8):errors.append('finite_residency_aperture')
        r,i,f=e['RF_read_tick'],e['issue_tick'],e['writeback_tick']
        if any(type(t) is not int or t<0 or t%4 for t in [r,i,f]):errors.append('missing_or_invalid_serial_ticks');continue
        rr=e['RF_register_reads'];rw=e['RF_register_writes']
        if len(rr)>2 or len(rw)>1 or any(type(v) is not int or not 0<=v<32 for v in rr+rw):errors.append('RF_2R1W_register_aperture')
        for o in src.get('operand_register_bindings',[]):
            if str(o.get('producer_event','')).startswith('phase_input:'):
                entry=e.get('phase_entry_RF_visible_ticks',{}).get(str(o['register']))
                if type(entry) is not int or entry<0 or entry>r:errors.append('phase_input_RF_visibility_unbound')
        reads[sm,part,r]+=len(rr);writes[sm,part,f]+=len(rw)
        if reads[sm,part,r]>2 or writes[sm,part,f]>1:errors.append('RF_port_collision')
        if rr and i<r+8:errors.append('RF_two_cycle_import_missing')
        if e['op'] not in CORE:errors.append('unqualified_opcode:'+e['op'])
        elif f<i+4*CORE[e['op']]:errors.append('core_latency_missing')
        for dep in src['dependencies']:
            if dep not in ready or type(ready[dep]) is not int or ready[dep]>r:errors.append('operand_dependency_before_visible')
        for v in rw:ready[sm,part,warp,v]=f
        ready[eid]=f
        for direction,counter in [('read',bankread),('write',bankwrite)]:
            words=e.get('shared_'+direction+'_words',[])
            if words:
                tick=e.get('shared_service_tick')
                if type(tick) is not int or tick<0 or tick%4:errors.append('shared_service_tick_unbound');continue
                if any(type(w) is not int or not 0<=w<16384 for w in words):errors.append('shared_word_aperture');continue
                if direction=='read' and tick+8>f:errors.append('shared_read_RF_visible_before_import')
                if direction=='write' and tick<r+8:errors.append('shared_store_before_operand_import')
                if len(set(words))!=len(words):errors.append('broadcast_provider_not_qualified')
                for word in words:
                    address=(sm,tick,word)
                    current=shared_read_addresses if direction=='read' else shared_write_addresses
                    other=shared_write_addresses if direction=='read' else shared_read_addresses
                    if address in other:errors.append('same_address_shared_RW_order_unbound')
                    current.add(address)
                    counter[sm,tick,word%32]+=1
                    if counter[sm,tick,word%32]>1:errors.append('shared_bank_'+direction+'_collision')
                if len(words)>32:errors.append('shared_128B_capacity')
                if direction=='write' and e.get('shared_store_visible_tick')!=tick:errors.append('shared_store_visibility_unbound')
        if rw and e.get('RF_write_copy_count')!=2:errors.append('physical_RF_readcopy_write_missing')
    if seen!=set(source_events):errors.append('actual_executed_source_event_coverage_unbound')
    for l in leases:
        if any(type(l.get(k)) is not int or l[k]<0 for k in REQUIRED):errors.append('phase_alias_boundary_unbound');continue
        if l['score_scratch_first_store']<max(l[k] for k in REQUIRED[:-1]):errors.append('score_alias_before_consumers_drained')
        required=['payload_WR_visible','descriptor_WR_visible','reverse_CDC_ack','read_lease_acquired','consumer_done','credit_return']
        if any(type(l.get(k)) is not int or l[k]<0 for k in required):errors.append('physical_publication_lease_ACK_unbound');continue
        if not(l['payload_WR_visible']<=l['descriptor_WR_visible']<=l['reverse_CDC_ack']<=l['read_lease_acquired']<=l['consumer_done']<=l['credit_return']):errors.append('publication_lease_event_order')
        if l.get('physical_provider_source_pin') is None:errors.append('physical_provider_source_unbound')
    if not leases:errors.append('actual_phase_leases_missing')
    return {'issues':sorted(set(errors)),'candidate_event_constraints_pass':not errors,
      'physical_admission':False,'hardware_launch':False,'rate_credit':0,
      'scope':'event validation only; exact arithmetic/branch replay, source provider and contextual SSFF additionally required'}


def intake():
    p='results/rtl/deepseek_hbm_complete_20261001/index-tagged-producer-consumer-gate-r2.json'
    b=subprocess.check_output(['git','show','e5d9ad00a:'+p]);d=json.loads(b)
    result=audit(d.get('physical_ordinary_events',[]),d.get('physical_phase_leases',[]),{})
    result.update(schema='w13.index-phase-calendar-intake.v2',actual_software_evidence={'git':'e5d9ad00a','path':p,'sha256':hashlib.sha256(b).hexdigest()},
      source_defined_tick_units='3.6GHz commonticks;serial4,fast3; never CPUwall->ticks',
      software_row_events=d.get('actual_software_row_events'),ordinary_executed_manifest_pin=None,actual_branch_operand_replay=None,
      joint_lifetime_pin='ba0699538:results/physical_abi3/asap7/gpu/w13_index_f32_consumer_ports_20261001/joint_lifetime_r1.json',
      common36client_allocator_ACK_CDC_drain=None,unknown_opcode_latency=None,
      failed_history='e1d6e4c4f register readiness did not bind exact producer versions; FAIL_MODEL_VALIDATOR_STALE_REGISTER_VERSION',
      failed_receipt_preserved='33b08907d:results/physical_abi3/asap7/gpu/w13_index_f32_consumer_ports_20261001/phase_calendar_intake_r1.json')
    return result

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(intake(),indent=2)+'\n')
