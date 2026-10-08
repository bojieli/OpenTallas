#!/usr/bin/env python3
"""Candidate placement and real native-SMH parent-join boundary inventory."""
import json
import hashlib
from pathlib import Path
from hbm_sm_serial_protection_model import model as protection
from hbm_sm_descriptor_bridge_model import model as descriptor

def model():
    pinpath=Path(__file__).resolve().parents[1]/'results/physical/hbm_smh_actual_pin_readback_20261007/actual_top_pin_boxes.json'
    pins=json.loads(pinpath.read_text())
    groups={}
    for group,prefixes in dict(north_control=['start','start_ready','op_rows','op_c','op_g','op_gs','op_fmt','op_xb'],north_X=['xw_en','xw_addr','xw_grp','xw_data'],north_status=['busy','arrive','release_in','released'],south_descriptor=['d_valid','d_ready','d_base','d_lines'],south_fault=['fault']).items():
        members=[p for p in pins['pins'] if p['name'].split('[')[0] in prefixes]
        centers=[((b['rect_um'][0]+b['rect_um'][2])/2,(b['rect_um'][1]+b['rect_um'][3])/2) for p in members for b in p['boxes']]
        groups[group]=dict(bits=len(members),center_bbox_um=[min(p[0]for p in centers),min(p[1]for p in centers),max(p[0]for p in centers),max(p[1]for p in centers)],directions={p['name']:p['direction'] for p in members if '['not in p['name']})
    ports=dict(
      run=dict(to_owner=1+32+33+16,from_owner=1),
      program_read=dict(to_owner=1+1+32+32+1,from_owner=1+32+1),
      weight_allocation=dict(to_owner=1+1+16+32+1,from_owner=1+16+24+1),
      operand_stream=dict(to_owner=1+1+16+7+4+2048+1,from_owner=1+16+7+8+1),
      publication=dict(to_owner=1+16,from_owner=1),
      completion=dict(to_owner=1,from_owner=1+1),
      SM_local=dict(to_owner=1+1+1+1,from_owner=47+1+1+7+7+2048+1+32+24))
    return dict(status='candidate_floorplan_reservation_only',actual_pin_groups=groups,actual_pin_readback_sha256=hashlib.sha256(pinpath.read_bytes()).hexdigest(),actual_pin_source_odb_sha256=pins['odb_sha256'],actual_pin_scope=pins['scope'],owner=protection(),descriptor=descriptor(),ports=ports,
      program_bytes_per_record=40,X_fragment_bits=25216,X_beats_per_address=13,X_payload_peak_bytes_per_fast_edge=256,
      weight_service='existing native SMH req_v/req_addr32/req_tag10 and rsp_v/rsp_tag10/rsp_data1088 pass through unchanged; REQCR1 return semantics retained',
      result_service='existing native SMH rv/rrow12/rdata256 passed to real result owner; matching publication receipt required separately',
      release_service='external actual release_in to SMH; never echoed from arrive in production RTL',
      replicas=32,north_owner_reserved_grid_um=[256.176,129.6],south_descriptor_bay_candidate_um=[128,64],proposed_owner_footprint_um=[256,128],reserved_area_um2_per_owner=32768,
      total_reserved_area_mm2=32*32768/1e6,cell_budget_um2_at_55pct=32768*.55,
      reservation_basis='generous unqualified envelope; DMR flop-only1559.1852um2, actual cell-mapped comb area absent; reserve, do not assert fit',
      pin_plan='256um north/south edges accommodateactual X planned pin span202.464um within each256um edge. Other control ports use remaining faces. Actual BPin/pinstation/diechannel capacity remains unqualified.',
      FF_setup_clock='1.2GHz stream clock; protected combinational check remains timing-unqualified; no relaxed SDC assumed',
      replica_latency='local owner three-edge ingress plus existing nativeSMH PIO=2 and fixed X write/read relative margin; producer waits real arrive+publication before next record',
      added_join_register_bits=descriptor()['total_register_bits'],added_join_cycles_per_descriptor=descriptor()['added_vs_same_cycle_accept_edges'],
      open_gates=['legal north-south perimeter descriptor path','actual mapped cell area','registered verification boundary if required','program/operand/allocation/publication upstream owner wiring','fullnative parent exactness','physical slot/clock/SSFF'],selected=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
