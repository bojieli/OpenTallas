"""Replace one complete selector slot in the current complete-frame PAR2 map."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import dsrom_noECC_complete_parent_map as P
import dsrom_PAR2_wire_deadline_plan as W

BASE=W.BASE


def build():
    model,field,macros,cfg,bands,services=P.build()
    src=BASE/'inputs/selector_aa745_model.json'
    selector=json.loads(src.read_text())
    full=selector['slot_proposal']['known_service_overlay']['revised_rectangles'][0]['area_mm2']
    old=model['selector']['single_full_slot_bbox_DBU']
    width=old[2]-old[0]
    height=math.ceil(full*1e12/width/2160)*2160
    box=[old[0],old[1],old[2],old[1]+height]
    preserved=[b for b in services if b['name']!='X_SEL_TOPK_STORE']+field+cfg+bands
    collisions=[b['name'] if 'name' in b else b.get('local_pair')
                for b in preserved if P.overlap(box,b['bbox_DBU'])]
    if collisions or box[3]>26000000 or box[2]>33000000:
        raise ValueError('complete selector overlaps preserved capacity or exceeds reticle')
    reserved=width*height/1e12
    old_reserved=model['selector']['reserved_rectangle_mm2']
    old_screen=model['area']['combined_noncontainment_policy_screen_mm2']
    state=model['selector']['state_already_priced_mm2']
    new_screen=old_screen-old_reserved+reserved
    model['selector'].update(single_full_slot_bbox_DBU=box,
        reserved_rectangle_mm2=reserved,full_proxy_mm2=full,
        only_additional_full_proxy_charge_mm2=reserved-state,
        state_bits=selector['shapes'][0]['state_bits'],
        old_complete_slot_replaced_not_added=True,
        old_storage_only_0p06177_not_additional_credit=True,
        prior_full_proxy_replaced_mm2=old_reserved,
        inherited_state_charge_is_candidateFF_plus_remaining_state=True,
        actual_mapped_fullslot_not_available=True)
    model['area'].update(combined_noncontainment_policy_screen_mm2=new_screen,
        remaining_before_unpriced_interfaces_mm2=858-new_screen,
        complete_selector_extra_charged_once_mm2=reserved-state,
        new_selector_vs_prior_complete_map_increment_mm2=reserved-old_reserved)
    model['selector_latency']=dict(
        added_stream_cycles_per_call=142,calls_per_position=9,
        added_stream_cycles_per_position=1278,
        conditional_ns_at_1p2GHz=1065,
        sixposition_verification_only_upper_no_overlap_cycles=7668,
        conditional_sixposition_ns=6390,
        drafter_and_commit_rollback_extra_unknown=True,
        source_count_not_actual_token_schedule=True,
        fulltoken_latency_credit=False)
    model['wire_deadline_plan']=W.build()
    model['source_selector']=dict(commit='aa745a879e20',path='results/uarch/topk_balanced_filter_successor_model_20261002/model.json',
                                 sha256=hashlib.sha256(src.read_bytes()).hexdigest())
    model['schema']='opentallas.dsrom.PAR2.complete-selector-wire-join.v1'
    model['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    model['geometry_G0']=dict(reservation_no_overlap=True,reticle_dimensions_um=[33000,26000],
        complete_q_BF_frame_inventory_preserved=True,compiled_pairs=2048,
        weight_macros=8192,cfg_macros=14336,
        actual_cell_row_channel_OBS_PDN_union_available=False,
        fullslot_SS_FF_clock_closure=False,physical_build_admitted=False)
    model['trace_plan']['owner_split']['execution_owner']='Nash/current sole wholephase source chain; no duplicate launch'
    model['trace_plan']['accepted_runtime_receipt_available']=False
    return model


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('immutable records')
    a.output.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
