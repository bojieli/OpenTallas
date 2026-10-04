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
 'counted_reverse_identity_match','owners_agreed',
 'bank_service_II_edges','bank_pipeline_capacity_rows','bank_service_rows_ahead_bound',
 'bank_service_source','bank_service_sha256','reverse_capture_clock_GHz',
 'retirement_clock_domains','retirement_clock_GHz','retirement_crossings')
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

RETIREMENT_STAGES=('reverse_capture','logical_capture','spine','adapter','core','engine')
RETIREMENT_HOPS=(('reverse_capture','logical_capture'),('logical_capture','spine'),
                 ('spine','adapter'),('adapter','core'),('core','engine'))

def retirement_time(binding,final_reverse_ns,chain,source_root):
    domains=binding['retirement_clock_domains'];clocks=binding['retirement_clock_GHz']
    crossings=binding['retirement_crossings'];root=Path(source_root)
    domain_rates={}
    for stage in RETIREMENT_STAGES:
        domain=domains.get(stage);rate=clocks.get(stage)
        if not isinstance(domain,str) or not domain or type(rate) not in (int,float) or not math.isfinite(rate) or rate<=0:
            raise ValueError('Unbound retirement clock/domain: '+stage)
        if domain in domain_rates and domain_rates[domain]!=rate:
            raise ValueError('Inconsistent clock for retirement domain: '+domain)
        domain_rates[domain]=rate
    if clocks['engine']!=binding['consumer_clock_GHz']:
        raise ValueError('Engine-to-consumer clock boundary needs a separate bound before composition')
    if clocks['reverse_capture']!=binding['reverse_capture_clock_GHz']:
        raise ValueError('Reverse receiver clock differs from retirement binding')
    times={'reverse_capture':final_reverse_ns}
    local_edges={'logical_capture':chain['logical_capture_drained'],
                 'spine':1,'adapter':1,'core':1,'engine':1}
    pins={}
    for src,dst in RETIREMENT_HOPS:
        key=src+'->'+dst;cross=crossings.get(key)
        if not isinstance(cross,dict):raise ValueError('Unbound retirement crossing: '+key)
        delay=cross.get('bound_ns')
        if type(delay) not in (int,float) or not math.isfinite(delay) or delay<0:
            raise ValueError('Invalid retirement crossing bound: '+key)
        if domains[src]!=domains[dst] and delay<=0:
            raise ValueError('Distinct retirement domains require CDC/phase bound: '+key)
        path=cross.get('source');sha=cross.get('sha256')
        if not isinstance(path,str) or hashlib.sha256((root/path).read_bytes()).hexdigest()!=sha:
            raise ValueError('Retirement crossing source missing/drifted: '+key)
        pins[path]=sha
        # Crossing bound covers transport/phase capture ONLY; the receiver's
        # old-state FSM transition follows at its own local clock, separately.
        times[dst]=times[src]+delay+local_edges[dst]/clocks[dst]
    return times,pins

def compose(binding,source_root):
    missing=[k for k in REQUIRED if k not in binding or binding[k] is None]
    if missing:raise ValueError('Unbound selected inputs: '+','.join(missing))
    b=binding;r=Path(source_root);p=r/b['provider_source']
    if hashlib.sha256(p.read_bytes()).hexdigest()!=b['provider_sha256']:raise ValueError('Selected provider source drift')
    if b['owners_agreed']!=['Maxwell','Archimedes','Nash']:raise ValueError('Joint minimum-component selection not agreed')
    for k in ('source_bank_reserved_before_GO','partial_stripe_RMW_port_reserved',
              'data_and_checks_matched_before_publication','counted_reverse_identity_match'):
        if b[k] is not True:raise ValueError('Missing actual service obligation: '+k)
    for k in ('write_clock_GHz','field_clock_GHz','consumer_clock_GHz','reverse_capture_clock_GHz'):
        if type(b[k]) not in (int,float) or not math.isfinite(b[k]) or b[k]<=0:raise ValueError(k)
    stages=('forward_CDC_edges','packet_route_edges','checked_old_stripe_read_edges',
      'decode_old_edges','merge_encode_edges','data_check_commit_edges',
      'checked_publication_edges','registered_receipt_edges','reverse_CDC_edges',
      'consumer_first_VM_request_after_GO_edges')
    for k in stages:
        if type(b[k]) is not int or b[k]<1:raise ValueError('Nonzero selected source stage required: '+k)
    for k in ('bank_service_II_edges','bank_pipeline_capacity_rows'):
        if type(b[k]) is not int or b[k]<1:raise ValueError('Positive selected bank service capacity required: '+k)
    ahead=b['bank_service_rows_ahead_bound']
    if type(ahead) is not int or ahead<0:raise ValueError('Bank occupancy bound missing')
    service_path=r/b['bank_service_source']
    if hashlib.sha256(service_path.read_bytes()).hexdigest()!=b['bank_service_sha256']:
        raise ValueError('Bank II/occupancy source drift')
    service_latency=sum(b[k] for k in stages[2:8])
    if b['bank_pipeline_capacity_rows']*b['bank_service_II_edges']<service_latency:
        raise ValueError('Selected bank II requires more retained pipeline row capacity')
    predecessor_wait=ahead*b['bank_service_II_edges']
    # Gear close and packing wait MUST be explicitly source-bound; no inherited
    # r3 0.9GHz or4:3 FIFO constant. Clocks determine whether that calendar applies.
    gear=b.get('gear_capture_to_launch_bound_ns')
    if type(gear) not in (int,float) or not math.isfinite(gear) or gear<=0:raise ValueError('Actual selected gear bound missing')
    # gear_capture_to_launch includes the selected forward CDC, so do not
    # count that stage twice. Occupancy includes queued AND in-flight row
    # owners; sequential RMW/codec arbitration must be reflected in selected II.
    if gear < b['forward_CDC_edges']/b['write_clock_GHz']:
        raise ValueError('Gear bound omits its selected forward CDC')
    bank=(sum(b[k] for k in stages[1:8])+predecessor_wait)/b['write_clock_GHz']
    reverse=b['reverse_CDC_edges']/b['reverse_capture_clock_GHz']
    f=b['last_root_return_ns']+gear+bank+reverse
    chain=retirement_edges(b.get('logical_capture_done_before_reverse') is True)
    retire_times,crossing_pins=retirement_time(b,f,chain,r)
    engine=retire_times['engine']
    read=engine+b['consumer_first_VM_request_after_GO_edges']/b['consumer_clock_GHz']
    slack=b['actual_consumer_deadline_ns']-read
    fit=b['minimum_component_placement_mm2']<=b['minimum_component_slot_mm2']
    return dict(schema='dsrom.s81.selected.minimum_stage_composition.v2',selection=b,
      source_sha256={**{n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in SOURCES},
        **crossing_pins,b['bank_service_source']:b['bank_service_sha256']},
      calendar=dict(last_root_ns=b['last_root_return_ns'],final_reverse_ns=f,
        bank_service_II_edges=b['bank_service_II_edges'],
        bank_pipeline_capacity_rows=b['bank_pipeline_capacity_rows'],
        bank_service_rows_ahead_bound=ahead,bank_predecessor_wait_edges=predecessor_wait,
        forward_CDC_already_in_gear_bound=True,
        retirement_stage_bound_ns=retire_times,
        source_retirement_relative_edges_scope='same-domain native sequence only; numeric timing uses separately bound domains/crossings',
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
