"""Actual owner83 control API/emitter scaffold tied to the admitted b41 model.

No engine emission or runtime grants until joint port/cut/latency enrollment.
This module defines typed event matching and old-state transition guards. It is
not a hardware authority or a substitute for instantiated publication controls.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
MODEL='results/uarch/dsrom_s81_w11_publication_control_20261004/model.json'
TEMPLATE='tools/templates/dsrom_s81_w11_publication_control_pkg.sv.in'
NB,RC,K,WQD=2,6,4,4

@dataclass(frozen=True)
class Owner83:
    identity:int
    group:int
    bank:int
    slot:int
    row:int
    mask:int
    def packed(self):
        fields=((self.identity,57),(self.group,7),(self.bank,1),
                (self.slot,2),(self.row,8),(self.mask,8))
        bits=offset=0
        for value,width in fields:
            if type(value) is not int or not 0<=value<1<<width:
                raise ValueError('Owner83 field bounds')
            bits|=value<<offset;offset+=width
        if not self.mask:raise ValueError('Zero mask cannot own publication')
        return bits

@dataclass(frozen=True)
class CopyEvent:
    owner:Owner83
    copy:int
    qualified:bool
    init_operation:bool
    checked_bad:bool=False


def capture_copy_events(held,old_seen,events,*,init_operation):
    """Match actual qualified old-owner events atomically, before any release.

    Returns a mask or refuses the whole event batch. No partial publication on
    an edge containing a malformed/duplicate/poison event. Qualification must
    originate at real data+check commit or checked-readback ports, never timers.
    """
    held.packed()
    if type(init_operation) is not bool:raise ValueError('Explicit operation namespace required')
    if type(old_seen) is not int or not 0<=old_seen<1<<RC:raise ValueError('Copy mask bounds')
    seen=old_seen
    for event in events:
        if event.init_operation is not init_operation:raise ValueError('Wrong initializer/field event namespace')
        if event.qualified is not True:raise ValueError('Unqualified copy event')
        event.owner.packed()
        if event.owner!=held or type(event.copy) is not int or not 0<=event.copy<RC:
            raise ValueError('Wrong full owner83/group/copy')
        bit=1<<event.copy
        if seen&bit:raise ValueError('Duplicate actual copy terminal')
        if event.checked_bad:raise ValueError('Checked publication poison')
        seen|=bit
    return seen


def publication_complete(commit_seen,verified_seen):
    return commit_seen==(1<<RC)-1 and verified_seen==(1<<RC)-1


def capture_count_return(held,returned,*,actual_captured_return,count_sent,
                         init_operation,returned_init_operation):
    held.packed();returned.packed()
    if type(init_operation) is not bool or returned_init_operation is not init_operation:
        raise ValueError('Wrong returned initializer/field namespace')
    if actual_captured_return is not True or count_sent is not True or returned!=held:
        raise ValueError('Count return lacks captured old fullowner83 debt')
    # Eligibility only; actual coded state clears in the future engine at the
    # qualified transition. No lease deletion or host grant is performed here.
    return 'BANK_COLLECT' if init_operation else 'BANK_RETIRED'

# Each predicate is an actual named port/old-state guard. No numerical waits
# and no implicit read credit. Provider states can be held for arbitrary cycles.
TRANSITIONS=(
 ('BANK_EMPTY','BANK_INITIALIZE','captured_atomic_reservation AND authoritative_cold_empty_row_owner'),
 ('BANK_INITIALIZE','BANK_WRITE_REQUEST','fullstripe_zero_image_raw_W6_encode_captured AND leased_data_check_write_ports'),
 ('BANK_EMPTY','BANK_COLLECT','captured_reservation AND retained_initialized_image_owner'),
 ('BANK_COLLECT','BANK_READ_REQUEST','received_eq_expected AND actual_input_finished AND leased_read_ports AND old_image_initialized'),
 ('BANK_READ_REQUEST','BANK_READ_RETURN','actual_RMW_read_accept(owner83)'),
 ('BANK_READ_RETURN','BANK_CHECK_OLD','matched_all6_data_check_read_returns(owner83)'),
 ('BANK_CHECK_OLD','BANK_ENCODE_MERGE','all6_raw_W6_checked_old_images_equal AND no_UE'),
 ('BANK_ENCODE_MERGE','BANK_WRITE_REQUEST','actual_raw_W6_encode_output_captured(owner83)'),
 ('BANK_WRITE_REQUEST','BANK_ALL_COPY_COMMIT','actual_data_check_write_accept(owner83)'),
 ('BANK_ALL_COPY_COMMIT','BANK_VERIFY_REQUEST','commit_seen_eq_6_after_atomic_fullowner_match'),
 ('BANK_VERIFY_REQUEST','BANK_ALL_COPY_VERIFY','actual_all6_readback_port_accept(owner83)'),
 ('BANK_ALL_COPY_VERIFY','BANK_COUNT_HELD','commit_seen_eq_6 AND verified_seen_eq_6 AND old_image_match'),
 ('BANK_COUNT_HELD','BANK_COUNT_RETURN','actual_count_packet_capture(owner83,root_ids,counts)'),
 ('BANK_COUNT_RETURN','BANK_COLLECT','init_kind AND matched_initialization_allcopy_return; mark_initialized_only; received_mask_stays_zero'),
 ('BANK_COUNT_RETURN','BANK_RETIRED','field_kind AND positive_return_capture_matches_old_owner83'),
 ('BANK_RETIRED','BANK_EMPTY','actual_phase_allcopy_retirement AND no_external_debt'))

# Inputs needed to emit the actual sequential engine, not inferred by this API.
PRICED_BINDING_KEYS=('macro_check_port_binding','raw_W6_cut_binding',
 'bank_service_II_edges','bank_pipeline_capacity_rows',
 'write_clock_domain','publication_clock_domain','receipt_return_clock_domain',
 'phase_initialization_owner','input_finished_owner','all6_checked_publication_owner',
 'count_return_seat_owner','control_pipeline_bits','minimum_slot_and_route_cost',
 'service_and_consumer_latency','model_agreement',
 'cold_initializer_write_ports','initialized_row_owner_storage',
 'init_kind_sideband_and_coded_state_cost','cold_startup_service_edges')


def emission_contract(source_root):
    root=Path(source_root);p=root/MODEL;model=json.loads(p.read_text())
    target=model['target']
    if any(target[n]!=v for n,v in (('NB',NB),('RC',RC),('K',K),('WQD',WQD),('RDREG',1))):
        raise ValueError('Admitted W11 group geometry differs')
    if model['records']['active_RMW']['raw']!=100 or model['records']['held_count_receipt']['raw']!=104:
        raise ValueError('Owner83/counted receipt layout differs')
    for path,sha in model['source_pins'].items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=sha:
            raise ValueError('Admitted source drift: '+path)
    return {'model_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
      'owner_bits':83,'copy_mask_bits':6,'coded_receipt_bits':144,
      'event_owner_bits':83,'event_operation_kind_sideband_bits':1,
      'initialization':{'owner83_unchanged':True,'separate_init_kind_bit':True,
        'priced_base_receipt_raw_bits':104,'prepared_init_typed_receipt_raw_bits':105,
        'coded_receipt_bits_unchanged':144,
        'active_RMW_raw_bits_base':100,'init_kind_active_RMW_raw_bits':101,
        'active_RMW_coded_bits_unchanged':144,
        'stored_header_active1_go0_means_initializing':True,
        'row_initialized_uses_existing_three_bit_row_state':True,
        'bank_state_uses_existing_four_bit_bank_state':True,
        'cold_image':'scheduled full256 data +32 raw W6 checks per reservedrow/all6copies, no constructorzero',
        'initialization_not_input_publication':True,
        'unused_lane_input_leases_prohibited':True,
        'physical_whole_row_must_have_no_live_existing_value_owner':True,
        'field_GO_requires_all_reserved_rows_initialized_and_allcopy_returned':True,
        'startup_edges':'actualencode +writegrant +all6commit +readback/check +qualifiedinitreturn perrow; selectedports/cuts required; no fixed/free bound'},
      'transitions':TRANSITIONS,'priced_binding_keys':PRICED_BINDING_KEYS,
      'engine_emission_available':False,'hardware_authority':False}


def emit_interface(source_root,out):
    """Emit types only; does not emit an engine, model record or build command."""
    emission_contract(source_root)
    data=(ROOT/TEMPLATE).read_text()
    out=Path(out)
    with out.open('x') as f:f.write(data)
    return out


def require_engine_binding(binding):
    missing=[key for key in PRICED_BINDING_KEYS if key not in binding or binding[key] is None]
    if missing:raise ValueError('Unpriced control engine binding: '+','.join(missing))
    raise NotImplementedError('Engine emission remains closed until joint cuts are installed; interface/event scaffold only')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--interface-out',type=Path,required=True);a=p.parse_args()
    print(emit_interface(a.source_root,a.interface_out))
