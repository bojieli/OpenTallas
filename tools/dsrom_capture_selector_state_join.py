#!/usr/bin/env python3
"""One frozen R49 allocation and full selector state census, no fit admission."""
import argparse, hashlib, json
from pathlib import Path
import dsrom_capture_home_r49 as H
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_selector_state_join_20261002'
def inputs():
    out={}
    for r in json.loads((BASE/'inputs/origins.json').read_text()):
        raw=(BASE/'inputs'/(r['name']+'.json')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']: raise ValueError('Frozen source drift')
        out[r['name']]=json.loads(raw)
    return out

def reconcile(core,transport,review,cells,home):
    c=core['shapes'][0]; t=transport['fixed']
    if c['state_bits']!=698354 or c['added_state_bits_vs_original']!=127140: raise ValueError('Core census changed')
    if t['data_FF']+t['valid_ASR']!=review['transport_total_FF']: raise ValueError('Transport census disagreement')
    if t['data_FF']!=475954 or t['valid_ASR']!=226: raise ValueError('Transport source changed')
    if not transport['cost']['old_station_replaced_not_added']: raise ValueError('Duplicate station charge')
    if t['transport_cycles_per_call']!=226 or t['service_increment_per_call']!=142: raise ValueError('Cycle contract drift')
    if home['geometry_raw_common_overlap_free'] is not True: raise ValueError('R49 overlap retained')
    pins=cells['source_cell_facts'];hq='DFFHQNx1_ASAP7_75t_R';asr='DFFASRHQNx1_ASAP7_75t_R'
    loads={corner:{'transport_CLK_fF':t['data_FF']*pins[hq][corner]['pins']['CLK']['cap_fF']+t['valid_ASR']*pins[asr][corner]['pins']['CLK']['cap_fF'],
      'transport_RESETN_fF':t['valid_ASR']*pins[asr][corner]['pins']['RESETN']['cap_fF'],
      'transport_SETN_fF':t['valid_ASR']*pins[asr][corner]['pins']['SETN']['cap_fF']} for corner in ('SS','FF')}
    return dict(schema='DS_CAPTURE_SELECTOR_DISTINCT_STATE_JOIN_1',candidate=home['candidate'],
      core=dict(full_bits=c['state_bits'],original_bits=c['state_bits']-c['added_state_bits_vs_original'],net_added_bits=c['added_state_bits_vs_original'],net_delta_is_already_inside_full_bits=True,source_50pct_reservation_mm2=c['area']['proposed_source_50pct_proxy_core_mm2'],physical_clock_RESETN_master_split=None),
      transport=dict(data_HQ=t['data_FF'],present_ASR=t['valid_ASR'],full_bits=t['data_FF']+t['valid_ASR'],INV=t['INV'],repeater_BUF=t['data_repeater_BUF'],terminal_BUF=t['terminal_BUF'],clock_BUF_floor=t['clock_BUF_floor'],present_TIEHI=review['transport_present_ties'],source_50pct_reservation_mm2=transport['cost']['station_reservation_mm2_at50pct'],terminal_delta_already_inside_station_mm2=transport['cost']['reserve_delta_mm2_at50pct'],old_station_replaced=True,clock_tree_is_floor_not_routed=True),
      disjoint_core_and_transport_bits=c['state_bits']+t['data_FF']+t['valid_ASR'],incorrect_extra127140_recharge_rejected=True,
      selector_core_plus_station_reservation_mm2=c['area']['proposed_source_50pct_proxy_core_mm2']+transport['cost']['station_reservation_mm2_at50pct'],
      transport_pin_demand=loads,core_pin_loads_and_added_token_loads_not_zero=True,
      capture_home=dict(raw=home['per_shard_raw_homes'],common_bbox_DBU=home['corrected_common_bbox_DBU'],gap_um=home['actual_raw_common_gap_um'],common_owner_shard=None,common_full_cell_requirement_mm2=home['area']['common_required_mm2'],common_reservation_mm2=home['area']['reduced_common_reserved_mm2'],no_crossdie_combinational576mux=True),
      costs_already_inside_whole_screen=True,whole_screen_unchanged_mm2=home['area']['whole_reticle_screen_unchanged_mm2'],
      additional_cycles_from_census=0,selector_service_cycles=142,selector_transport_cycles=226,nine_call_increment_cycles=9*(142+226),
      selector_core_legal_cells_sites_and_PG=None,station_legal_cells_sites_and_clock_reset_PG=None,
      actual_accepted_consumer_deadline=None,actual_capture_gather_to_consumer_latency=None,
      complete_legal_allocation=False,contextual_PR_admitted=False,fulltoken_qualified=False,new_jobs=[],
      retained_failed_capture_cut=True,source_CDC_and_common_controller_unselected=True)

def build():
    d=inputs();return reconcile(d['core'],d['transport'],d['review'],d['cells'],H.build())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
