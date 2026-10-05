#!/usr/bin/env python3
"""Source-bound caller allocation proposal; reference invariants are not RTL receipts."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
BASE=Path(__file__).resolve().parent
PIN='20aa303ae9608582667f734122070ca6fe6bb5f75023a062b4057585e2f4b204'
def require(c,m):
 if not c:raise ValueError(m)
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
class TupleAllocator:
    """Five C0-client banks; KV5 preserves its existing producer tag instead.

    Client assignment is an explicit input from the missing production directory.
    A36-bit counter is not a truncation of native owner64/generation64. It assigns
    a new hardware child tag32/gen4 while native identity remains in parent context.
    """
    def __init__(self):self.next=[0]*5;self.held={};self.fault=False
    def reserve(self,client,parent_reference,source_identity):
        require(not self.fault and type(client)is int and 0<=client<5,'actual C0 client binding required; KV5 not reassigned')
        require(client not in self.held,'one frozen proposal per actual client allocator port')
        require(type(parent_reference)is int and 0<=parent_reference<2**32,'parent handle32')
        require(set(source_identity)=={'native_owner64','native_generation64','program_PC','rank','SM'},'retain full native source identity')
        for f in ['native_owner64','native_generation64']:require(type(source_identity[f])is int and 0<=source_identity[f]<2**64,'native64 never truncated')
        require(self.next[client]<2**36,'full tuple reuse needs actual all-copy fence, no silent wrap')
        n=self.next[client];self.held[client]=dict(client=client,tag32=n&0xffffffff,gen4=n>>32,parent_reference32=parent_reference,native=dict(source_identity));return dict(self.held[client])
    def accept(self,client,accepted):
        require(not self.fault and client in self.held and self.held[client]==accepted,'only actual matched W2 acceptance advances tuple')
        self.next[client]+=1;return self.held.pop(client)
    def reset(self):
        # No source fence implementation is fabricated. Reinitialization is not
        # a runtime reset operation and cannot clear accepted/potentially stale debt.
        raise ValueError('runtime reset/rearm requires actual provider/consumer/reverse/CDC quiescence binding')

def outputs():
    manifest=(BASE/'manifest.json').read_bytes();require(hashlib.sha256(manifest).hexdigest()==PIN,'manifest pin');m=json.loads(manifest);src={}
    for r in m:
        p=BASE/r['archive'];b=p.read_bytes();require(len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'source pin');src[Path(r['archive']).name]=b
    q=json.loads(gzip.decompress(src['Qwen_tiled.json.gz']));d=json.loads(gzip.decompress(src['program_final.json.gz']))
    programs={}
    for name,ops,expected in [('Qwen',q['operations'],1737),('DeepSeek',d['instructions'],2213)]:
        require(len(ops)==expected and [o['pc'] for o in ops]==list(range(expected)),'actual complete program PC inventory')
        programs[name]=dict(PCs=len(ops),program_PC_bits=(len(ops)-1).bit_length(),families=len({o.get('opcode',o.get('family')) for o in ops}),dynamic_child_transaction_count=None,actual_hardware_acceptances=None)
    a=json.loads(src['atomic_owner_contract.json']);require(a['provider_fragment_credit']==1 and a['max_provider_fragments_per_command']==64 and a['installed_bindings']==[],'native source contract')
    require('byte_address=base' in src['h4_c0_provider_movement.py'].decode() and 'base+64' in src['h4_c0_provider_movement.py'].decode(),'aligned64B movement')
    require('input wire [4095:0] wr_data' in src['ot_gpu_rf_service.sv'].decode(),'RF full-frame source')
    # Symbolic reference checks ONLY; these are not real accepted source requests.
    alloc=TupleAllocator();native=dict(native_owner64=2**64-1,native_generation64=2**64-1,program_PC=1736,rank=0,SM=0)
    first=alloc.reserve(0,123,native);require(first['native']==native,'full64 retained')
    require(alloc.held[0]==first and alloc.next[0]==0,'held stall does not consume tag')
    alloc.accept(0,first);require(alloc.next[0]==1,'advance on matched acceptance')
    alloc.next[0]=2**32-1;tail=alloc.reserve(0,124,native);require(tail['tag32']==2**32-1 and tail['gen4']==0,'tag boundary');alloc.accept(0,tail)
    carry=alloc.reserve(0,124,native);require(carry['tag32']==0 and carry['gen4']==1 and carry['native']==native,'source36 tuple extends, not native64 truncation');alloc.accept(0,carry)
    alloc.next[0]=2**36
    for action in [lambda:alloc.reserve(0,124,native),lambda:alloc.reserve(5,124,native),alloc.reset]:
        try:action()
        except ValueError:pass
        else:raise ValueError('unsafe wrap/KV override/reset accepted')
    frame_bytes,fragment_bytes,sector_bytes=512,64,32
    sectors=frame_bytes//sector_bytes;fragments=frame_bytes//fragment_bytes
    require(sectors==16 and fragments==8,'source frame dimensions')
    # With credit1 held until full-frame ACK, occupancy reaches64B then blocks;
    # no transition can produce the remaining448B required by full-frame write.
    blocked_bytes=a['provider_fragment_credit']*fragment_bytes;require(blocked_bytes<frame_bytes,'source lifetime join hazard')
    parent_fields=dict(parent_reference32=32,parent_capture55=55,sector_issued=16,sector_captured=16,sector_reverse=16,phase=3,valid=1)
    child_fields=dict(tag32=32,source_gen4=4,physical_PC7=7,client3=3,direction=1,RFslot9=9,parent_reference32=32,sector34=34,byte_mask32=32,backend_token16=16,phase3=3,valid=1)
    parent_raw=sum(parent_fields.values());child_raw=sum(child_fields.values());require(parent_raw==139 and child_raw==174,'explicit field sums')
    prot=lambda bits:math.ceil(bits/64)*72
    raw=32*parent_raw+32*16*child_raw+5*36+32
    protected=32*prot(parent_raw)+32*16*prot(child_raw)+5*prot(36)+prot(32)
    max_frames=a['max_provider_fragments_per_command']//fragments
    max_sectors=a['max_provider_fragments_per_command']*fragment_bytes//sector_bytes
    require(max_frames==8 and max_sectors==128,'source command lifetime envelope')
    conservative_raw=32*max_frames*parent_raw+32*max_sectors*child_raw+5*36+32
    conservative_protected=32*max_frames*prot(parent_raw)+32*max_sectors*prot(child_raw)+5*prot(36)+prot(32)
    price=json.loads(src['W2_pricing_model.json'])['full_wrapper_variant']
    flop_restore=price['cell_body_um2_by_section']['storage_QN_restore']/price['state_bits_per_PC']
    nand=price['protected_storage']['ECC_logic_body_um2_ASSUMED']/price['protected_storage']['ECC_logic_two_input_gate_equivalents_ASSUMED']
    words=conservative_protected//72
    storage_logic_lower=(conservative_protected*flop_restore+words*768*nand)/.5/1e6
    report=dict(verdict='FAIL_ACTUAL_NATIVE_CALLER_BINDING',scope='ONE allocator/retained mapping proposal sized against actual source contracts; no RTL/model adoption',enabled_default=False,program_inventory=programs,
        native_source_owner_bits=64,native_source_generation_bits=64,native_key_to_hardware_tag_is_private_mapping_not_truncation=True,
        proposed_C0_child_allocator=dict(banks=5,directory_mapping=None,one_accept_per_bank_per_edge=True,counter_bits_each=36,tag32='counter low32',producer_gen4='counter high4',whole_tuple_wrap='refuse until actual all-copy fence; no implemented fence in this model',held_request_stable=True,increment_only_on_W2_accept=True,actual_producer=None),
        KV5=dict(occupied=True,original32_preserved=True,producer_gen4_source=None,not_reassigned_to_C0=True),
        parent_reference=dict(bits=32,one_global_allocator_port_per_die_edge_PROPOSED=True,full_source_ticket_retained_in_existing_parent_context=True,existing_context_binding_proved=False,counter_wrap_requires_actual_fence=True,requester32way_arbiter_and_loaded_mux_unpriced=True),
        source_fragment_join=dict(fragment_credit=1,max_fragments_per_command=64,fragment_bytes=64,RF_full_write_bytes=512,sector_bytes=32,
          proposed_one_RF_frame_staging_perSM_min_fragment_tickets=fragments,retained_sector_identities_perSM_min=sectors,
          if_credit1_release_waits_full_RF_ACK_blocked_at_bytes=blocked_bytes,remaining_frame_bytes=frame_bytes-blocked_bytes,
          credit1_source_does_not_prove_8fragment_admission=True,
          required_owner_join='Popper/Dewey must bind real source-valid fragment capture/continued admission vs deferred physical reverse; full frame ACK and all-copy release stay mandatory. No phase is invented from software return.',
          source_whole_command_max_RF_frame_equivalents=max_frames,source_whole_command_max_sector_children=max_sectors,
          frame_early_reverse_release_proof=None,
          upper_bound_for_non_RF_endpoints=None),
        allocator_mapping_state_inputs=dict(parent_rows=32,parent_fields=parent_fields,child_rows_one_frame32SM=512,child_fields=child_fields,
          raw_bits_gross_lower=raw,protected_bits_gross_lower=protected,
          conservative_whole_command_hold_frame_rows32SM=32*max_frames,
          conservative_whole_command_hold_child_rows32SM=32*max_sectors,
          conservative_whole_command_gross_raw_bits=conservative_raw,conservative_whole_command_gross_protected_bits=conservative_protected,
          candidate_scope='single conservative whole-command envelope until real early child/frame release is proved; one-frame values are lower bounds only',
          one_active4096bit_assembler_perSM_reused_after_exact_commonACK=True,
          full_frame_record_and_child_identity_hold_through_C0_consumer_reverse=True,
          actual_parent_directory_storage_binding=None,protection_model='F0planning64->72 per concatenated row; actual field-specific correction/hold state not priced',
          full_native_private_context_RF_data_and_command_latch_recharge=False,
          parent55_W4_and_childmeta92_R14_overlap_requires_once_only_debit=True,net_bits_after_overlap=None,
          additional_RF4096_assembler_bits_already_in_connector_receipt=131072,
          allowed_flop_and_restore_um2_per_bit=flop_restore,allowed_NAND_equivalent_um2=nand,
          protection_768gateeq_per64to72word_ASSUMED=True,
          conservative_FF_plus_planning_protection_only50pct_mm2=storage_logic_lower,
          area_is_not_complete_gross_and_not_net=True,
          selectors_update_logic_clock_reset_routes_slot_area=None,actual_clock=None,
          source_widths_and_proposal_capacities_are_not_allocated_ports=True),
        ports=dict(C0_client_counter_accept_read_modify_write_each_bank=1,parent_allocations_per_die_edge_proposed=1,child_metadata_allocate_per_bank=1,return_and_reverse_update_ports=None,atomic_allocate_retire_priority='must be jointly specified and priced before implementation'),
        latency=dict(allocator_registered_assignment_min_edges=1,fold_into_Nash_selection_not_proved=True,native_C0_22ticks_preserved_once=True,source_W2_L1_and_R1412CORE_retained=True,all_copy_reuse_wait=None,full_service_bound=None),
        source_observed_runtime_scope=json.loads(src['Qwen_actual_runtime_demand_join.json'])['actual_KV_payload_lifecycle_observation_scope'],
        reference_checks=['complete actual1737/2213 PC inventory','full native64 retained','held proposal stable/no counter advance under stall','tag32 carry to independentgen4','whole36 wrap refusal','KV5 directory overwrite refusal','runtime reset refusal','source credit1/full512B frame join hazard','field/state sums'],reference_is_source_payload_qualification=False,
        unresolved=['actual accepted native command/tag/client emitter and installed rank/SM map','parent reference to complete native/version/home/lease record binding','fragment capture/admission/reverse causality within whole source program','KV source generation producer','actual fence/reset/rearm producer and positive continuous wrap waits','once-only state overlap, update ports, protection and physical slot/clock/route'],component_NC6_gate_is_separate_and_not_blocked_by_this_inventory=True,hardware_admitted=False,build_allowed=False)
    return canonical(report)
def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args();raw=outputs()
    if a.verify:require((BASE/'allocator.json').read_bytes()==raw,'byte exact allocator inventory')
    else:require(a.output is not None and not a.output.exists(),'fresh output');a.output.write_bytes(raw)
    print('PASS source inventory and symbolic allocator checks; FAIL_ACTUAL_NATIVE_CALLER_BINDING retained')
if __name__=='__main__':main()
