"""Compose selected minimum W11 write/publication stages, never select by default.

All clocks/stages/cell/slot costs are explicit joint-owner inputs. Source retirement
edges follow existing spine/adapter/core old-state sequencing, not a fullcore job.
"""
from pathlib import Path
import argparse,hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]
REQUIRED=('selection_id','provider_source','provider_sha256','write_clock_GHz','field_clock_GHz',
 'forward_CDC_edges','packet_route_edges','checked_old_stripe_read_edges',
 'decode_old_edges','merge_encode_edges','data_check_commit_edges',
 'checked_publication_edges','registered_receipt_edges','reverse_CDC_edges',
 'consumer_first_VM_request_after_GO_edges','consumer_clock_GHz',
 'last_root_return_ns','actual_consumer_deadline_ns','minimum_component_cell_mm2',
 'minimum_component_placement_mm2','minimum_component_slot_mm2',
 'metadata_codec_control_pipeline_bits','source_bank_reserved_before_GO',
 'partial_stripe_RMW_port_reserved','data_and_checks_matched_before_publication',
 'counted_reverse_identity_match','owners_agreed')
SOURCES=('rtl/dsrom_sys/s81_capture_parent/ot_v41_spine_w17w10.sv',
 'rtl/dsrom_sys/s81_capture_parent/ot_v41_rom_adapt.sv',
 'rtl/w17_runtime/hdc/v41x/ckvsel/ot_hdc_core_v41x.sv')

def retirement_edges(logical_done_before_return):
    # F means final reverse receipt captured AFTER rising edge. If logical
    # capture committed on F too, all_done sees new counts only on F+1.
    extra=0 if logical_done_before_return else 1
    return dict(logical_capture_drained=extra,spine_IDLE=1+extra,
      adapter_IDLE=2+extra,waiting_core_GO=3+extra,
      engine_samples_GO=4+extra,
      conditions='core already S_ISSUE, required waited bit set, all other gates ready; otherwise waiting latency remains additional, never zero.')

def compose(binding,source_root):
    missing=[k for k in REQUIRED if k not in binding or binding[k] is None]
    if missing:raise ValueError('Unbound selected inputs: '+','.join(missing))
    b=binding;r=Path(source_root);p=r/b['provider_source']
    if hashlib.sha256(p.read_bytes()).hexdigest()!=b['provider_sha256']:raise ValueError('Selected provider source drift')
    if b['owners_agreed']!=['Maxwell','Archimedes','Nash']:raise ValueError('Joint minimum-component selection not agreed')
    for k in ('source_bank_reserved_before_GO','partial_stripe_RMW_port_reserved',
              'data_and_checks_matched_before_publication','counted_reverse_identity_match'):
        if b[k] is not True:raise ValueError('Missing actual service obligation: '+k)
    for k in ('write_clock_GHz','field_clock_GHz','consumer_clock_GHz'):
        if type(b[k]) not in (int,float) or not math.isfinite(b[k]) or b[k]<=0:raise ValueError(k)
    stages=('forward_CDC_edges','packet_route_edges','checked_old_stripe_read_edges',
      'decode_old_edges','merge_encode_edges','data_check_commit_edges',
      'checked_publication_edges','registered_receipt_edges','reverse_CDC_edges',
      'consumer_first_VM_request_after_GO_edges')
    for k in stages:
        if type(b[k]) is not int or b[k]<1:raise ValueError('Nonzero selected source stage required: '+k)
    # Gear close and packing wait MUST be explicitly source-bound; no inherited
    # r3 0.9GHz or4:3 FIFO constant. Clocks determine whether that calendar applies.
    gear=b.get('gear_capture_to_launch_bound_ns')
    if type(gear) not in (int,float) or not math.isfinite(gear) or gear<=0:raise ValueError('Actual selected gear bound missing')
    # gear_capture_to_launch includes the selected forward CDC, so do not
    # count that stage twice. WQD4 contributes at most3 predecessor rows.
    if gear < b['forward_CDC_edges']/b['write_clock_GHz']:
        raise ValueError('Gear bound omits its selected forward CDC')
    bank=(sum(b[k] for k in stages[1:8])+3)/b['write_clock_GHz']
    reverse=b['reverse_CDC_edges']/b['field_clock_GHz']
    f=b['last_root_return_ns']+gear+bank+reverse
    chain=retirement_edges(b.get('logical_capture_done_before_reverse') is True)
    engine=f+chain['engine_samples_GO']/b['field_clock_GHz']
    read=engine+b['consumer_first_VM_request_after_GO_edges']/b['consumer_clock_GHz']
    slack=b['actual_consumer_deadline_ns']-read
    fit=b['minimum_component_placement_mm2']<=b['minimum_component_slot_mm2']
    return dict(schema='dsrom.s81.selected.minimum_stage_composition.v1',selection=b,
      source_sha256={n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in SOURCES},
      calendar=dict(last_root_ns=b['last_root_return_ns'],final_reverse_ns=f,
        WQD4_predecessor_wait_edges=3,forward_CDC_already_in_gear_bound=True,
        source_retirement_relative_edges=chain,consumer_engine_GO_sample_ns=engine,
        first_consumer_VM_request_bound_ns=read,consumer_deadline_slack_ns=slack),
      model_decision='FIT_AND_DEADLINE' if fit and slack>=0 else 'REJECT_FIT_OR_DEADLINE',
      minimum_component_fit=fit,deadline_met=slack>=0,
      area_scope='One actual selected VM service group + its ports/codec/publication/control, no wholearray build.',
      absolute_origin_binding_required=True,other_gate_stalls_not_priced_zero=True,
      setup_SS_ps=60,hold_FF_ps=25,SSFF_closure_claim=False,
      whole_token_rate=None,RTL_or_physical_adoption=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();x=compose(json.loads(a.binding.read_text()),a.source_root)
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'model.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    print(x['model_decision'])
