"""Prospective finite RF source-owner alternatives; no runtime grants or RTL.

Consumers are whole source operators, not RF fragments. Conservation bounds
are derived from the released recipe; positive producer/consumer/reverse
callbacks remain an enrollment obligation, never synthetic completion.
"""
import hashlib
import json
import math
from pathlib import Path
from collections import defaultdict
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
ROOT=Path(__file__).resolve().parents[2]
INGRESS='rtl/experimental/hbm_c0_connected_20261003/r5/ot_gpu_pc40_native_ingress_r5.sv'
CODEC='rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv'
CELLS='results/uarch/w2_nc6_mutable_protection_20261003/inputs/results/uarch/w2_pc_exact_completion_20261003/inputs/cell_prices.json'


def model(placement):
    p=placement
    facts=json.loads((ROOT/CELLS).read_text())['facts']
    ff=facts['DFFASRHQNx1_ASAP7_75t_R']['SS']
    by_sm=defaultdict(list)
    for h in p.rf.values():by_sm[h.rank*32+h.sm].append(h)
    peaks=[];page_peaks=[];first_last=[]
    for sm in range(64):
        homes=by_sm[sm]
        intervals=[];pages=[]
        for pc in range(1737):
            live=[h for h in homes if max(0,h.birth)<=pc<=h.retire]
            intervals.append(len(live));pages.append(sum(h.end-h.first for h in live))
        peaks.append(max(intervals));page_peaks.append(max(pages))
        first_last.append([min(h.first for h in homes),max(h.end for h in homes)])
    max_consumers=max(len(h.consumers) for h in p.rf.values())
    count_width=max(1,max_consumers.bit_length())
    # Native tag64 and native generation64 remain distinct from session64.
    # No equivalence is inferred to reduce context state.
    direct_fields=dict(valid=1,published=1,session=64,version=11,owner46=46,
        consumer_remaining=count_width,producer_visible=1,reverse_pending=1,fault=1,
        accepted_consumer_PC=11,accepted_consumer_tag=64,accepted_consumer_generation=64)
    native_fields=dict(existing_native_context_payload=181,session=64,version=11,
        RF_first=9,RF_length=7,consumer_remaining=count_width,reverse_pending=1,accepted_consumer_PC=11)
    seats=len(p.rf_slots)
    alternatives=[]
    for name,rows,fields in [('direct_physical_seats',seats,direct_fields),
                             ('extended_native_range_contexts',sum(peaks),native_fields)]:
        payload=sum(fields.values());cw=math.ceil(payload/44)
        max_local=max(p.owner_model()['rows_per_SM']) if name.startswith('direct') else max(peaks)
        compiled_rows=max_local*64
        protected=compiled_rows*cw*72
        alternatives.append(dict(name=name,rows=rows,compiled_rows=compiled_rows,padding_rows=compiled_rows-rows,
             physical_replica_policy='64 equal MAX_LOCAL endpoint tables; padding charged',
             row_fields=fields,payload_bits_per_row=payload,
             sealed_words_per_row=cw,protected_row_bits=protected,
             FF_body_area_mm2_floor=protected*ff['area_um2']/1e6,
             CLK_SS_cap_fF_floor=protected*ff['pins']['CLK']['cap_fF'],
             query_ports_per_SM=1,SM_count=64,
             query_boundary_bits=84,held_owner_boundary_bits=46,
             source_lookup_bits_per_edge_upper=84/3,owner_delivery_bits_per_edge_upper=46/3,
             internal_codec_capture_bits_per_query=cw*72,
             input_replica_fanout=max_local,selector_levels=(max_local-1).bit_length(),
             page_payload_routing_added=False,
             maximum_local_rows=max_local,
             query='direct RFslot indexing' if name.startswith('direct') else 'version/session equality and first<=slot<first+length CAM',
             compare_input_bits=75 if name.startswith('direct') else 84,
             data_output_bits=46,prospective_query_edges=3,
             outstanding_consumer_capacity_per_context=1,
             outstanding_consumer_policy='whole operator issuer enrollment must prove serialization; otherwise reprice',
             consumer_order='compiled ordered PCs, advance only on exact owned complete AND reverse; duplicates fault',
             positive_capture_or_mirror_ACK_to_publish_min_edges=1,
             final_consumer_and_reverse_to_retire_min_edges=1,
             initiation_interval_edges=3,capacity_stalls_may_extend=True,
             missing=['held request/response and repair contexts', 'loaded codec, selection and feedback timing',
                      'positive whole-operator retirement/reverse callbacks', 'source namespace issuer and wrap fence'],
             full_area_mm2=None,physical_admitted=False))
    source=(ROOT/INGRESS).read_text()
    if "rf_ack_slot==9'd38" not in source or 'source_lease_reserved' not in source:
        raise ValueError('existing native owner source changed')
    pins=[dict(path=x,sha256=hashlib.sha256((ROOT/x).read_bytes()).hexdigest()) for x in (INGRESS,CODEC,CELLS)]
    return dict(schema='canonical-qwen-finite-source-allocator-r1',provider_pin=p.pin,source_pins=pins,
        exact_RF_seats=seats,RF_homes=len(p.rf),peak_live_home_contexts_per_SM=peaks,
        peak_live_RF_pages_per_SM=page_peaks,RF_slot_ranges_per_SM=first_last,
        maximum_consumers_per_home=max_consumers,consumer_count_width=count_width,
        existing_native_context=dict(actual_instances=1,protected_context_bits=216,protected_data_bits=4608,
            source_RF_slot=38,general_source_owner=False,additional_runtime_lease_state_credit=0,
            reason='PC40 retained context assumes external source_lease_reserved; not a full RF lease allocator',
            payload_replicas_not_charged_to_lease_extension=True),
        alternatives=alternatives,selected=None,RTL_admitted=False,
        per_token_latency=dict(actual_callback_census_unknown=True,
            formula='sum of uncached owner queries *3 + positive publication/retirement edges + repair/credit stalls',
            native_lookup_reuse_requires='actual retained source owner covering every queried slot/version/session; not caller reservation',
            source_declaration_home_queries=sum(1+len(h.consumers) for h in p.rf.values()),
            source_declaration_page_queries=sum((h.end-h.first)*(1+len(h.consumers)) for h in p.rf.values()),
            declaration_census_is_actual_callback_trace=False),
        rank_PC_translation_qualified=False)


def freeze(out,source_root=None):
    p=SourcePlacement.released(source_root)
    raw=(json.dumps(model(p),sort_keys=True,indent=2)+'\n').encode()
    path=Path(out);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(raw)
    return hashlib.sha256(raw).hexdigest()

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',required=True);a.add_argument('--released-source-root')
    args=a.parse_args();print(freeze(args.out,args.released_source_root))
