#!/usr/bin/env python3
"""Price fixed-depth opaque relay delay banks before building them."""
import argparse
import hashlib
import json
from pathlib import Path


def model(ledger_path):
    path=Path(ledger_path);ledger=json.loads(path.read_text())
    for row in ledger['rows']:
        if row['physical_bits'] != 64 or row['modeled_transport_station_count']+row['modeled_latency_only_station_count'] != row['balanced_cycles'] or row['balanced_cycles'] != 72:
            raise ValueError('ledger is not the full64bit balanced72cycle candidate')
    if sum(r['modeled_latency_only_station_count'] for r in ledger['rows']) != ledger['latency_only_station_count']:
        raise ValueError('ledger padding count mismatch')
    choices=[]
    for depth,side in ((8,32.4),(16,45.36),(32,64.8)):
        rows=[]
        for r in ledger['rows']:
            pads=r['modeled_latency_only_station_count'];banks,tail=divmod(pads,depth)
            rows.append(dict(bus=r['bus'],group=r['group'],bank_count=banks,
                remaining_single_cycle_stations=tail,transport_stations=r['modeled_transport_station_count'],
                unchanged_total_cycles=r['modeled_transport_station_count']+banks*depth+tail))
        banks=sum(r['bank_count'] for r in rows);tail=sum(r['remaining_single_cycle_stations'] for r in rows)
        old=ledger['latency_only_assumed_slot_area_um2'];new=banks*side*side+tail*400
        choices.append(dict(depth=depth,proposed_bank_um=[side,side],flop_bits_per_bank=64*depth,
            ordinary_ff_area_lower_um2=64*depth*.2916,
            ff_plus_one_mux_per_bit_proxy_um2=64*depth*(.2916+.30618),
            area_proxy_scope='RVT DFFHQNx1 and constructive3NAND2+INV mux; this is not an asynchronous reset mapping',
            cell_budget_um2_at_55pct=side*side*.55,
            bank_count=banks,remaining_single_cycle_stations=tail,
            latency_only_reserved_area_um2=new,prior_latency_only_reserved_area_um2=old,
            area_reservation_reduction_um2=old-new,
            transport_reserved_area_um2=ledger['transport_assumed_slot_area_um2'],
            proposed_total_station_area_um2=ledger['transport_assumed_slot_area_um2']+new,rows=rows))
    return dict(selected=False,status='MODEL_BEFORE_RTL_AND_PHYSICAL_BUILD',
        candidate_depth=8,word_bits=64,MACs_per_cycle=0,
        boundary_input_bits_per_cycle=64,boundary_output_bits_per_cycle=64,
        register_stage_read_bytes_per_cycle=8,register_stage_write_bytes_per_cycle=8,
        SRAM_ports=0,replicas=choices[0]['bank_count'],
        bank_latency_cycles=8,composed_balanced_path_cycles=72,
        added_path_cycles_vs_fixed_delay_stations=0,
        packet_contract='opaque64bit slice; production fullpacket protection remains mandatory; no encodedword width reduction',
        flow_contract='unconditional every-edge capture, no ready; async active-low cold reset zeros all stages; ENABLE default0',
        pin_tracks=dict(data_input=64,data_output=64,clock=1,reset=1,
            per_data_face_native_pitch_um=.048,reserved_pitch_um=.096,
            data_window_um=6.144,proposed_face_um=32.4),
        choices=choices,
        gates=['actual async-reset technology mapping and full-bank synthesis area',
            'all physical banks plus spatial hop stations placed jointly; no endpoint proximity assumed',
            'actual fixed pin shapes and SS/FF >=15ps with60/25ps uncertainty',
            'fullpacket end-to-end error protection and exact stage replacement',
            'new clock tree load and shared PDN/control/result track capacity'],
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),path]})

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ledger',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();r=model(a.ledger);p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r['choices'][0][k] for k in ('bank_count','remaining_single_cycle_stations','proposed_total_station_area_um2','area_reservation_reduction_um2')}))
