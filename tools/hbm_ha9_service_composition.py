#!/usr/bin/env python3
"""Once-only service body and port composition; no physical launch or rate credit."""
import argparse
import hashlib
import json
import math
import re
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/hbm_ha9_service_composition_20261003/inputs'


def tracks(signals, width_um, pitch_um, signal_share):
    if type(signals) is not int or signals<1 or not all(math.isfinite(x) and x>0 for x in (width_um,pitch_um,signal_share)) or signal_share>1:
        raise ValueError('source-bound channel quantities required')
    available=int((Decimal(str(width_um))/Decimal(str(pitch_um))*Decimal(str(signal_share))).to_integral_value(rounding=ROUND_FLOOR))
    return dict(required_tracks=signals,available_tracks=available,fits=signals<=available,
                status='MODEL_SINGLE_LAYER_ONLY',obstruction_escape_and_loaded_timing_qualified=False)


def bind_partition(stage, model):
    rows=stage['rank_dies']; n=model['provisional_S']
    if {(r['stage'],r['rank']) for r in rows}!={(s,r) for s in range(n) for r in range(4)} or len(rows)!=n*4:
        raise ValueError('chosen W2 partition incomplete')
    scans=set(stage['scan_service_homes'].values())
    if not scans.issubset(set(range(n))): raise ValueError('scan home outside chosen partition')
    allocation=[dict(die=r['die_id'],stage=r['stage'],rank=r['rank'],stacks=4 if r['stage'] in scans else 1) for r in rows]
    return dict(chosen_W2_stages=n,return_contract=model['selected_return'],
                allocation=allocation,head_stacks_provisional=8*4,
                total_stacks_provisional=sum(x['stacks'] for x in allocation)+8*4,
                provider_homes=stage['provider_homes'],layer_matrix_stages=stage['layer_matrix_stages'],
                scan_homes_provisional=stage['scan_home_is_provisional_not_source_service_binding'],
                capacity_batch216_1M=None,latency_and_busiest_stage=None,
                delta_adopted_dies=0,adopted=False,
                next='W2/Claude bind actual KV owner, reserve and gathered-row/scan delivery inventory to these existing homes; no new stage sweep')


def compose(base=BASE):
    def load(name): return json.loads((base/name).read_text())
    origins=load('origins.json')
    for name,pin in origins.items():
        if hashlib.sha256((base/name).read_bytes()).hexdigest()!=pin['sha256']:
            raise ValueError('frozen actual source changed: '+name)
    rf=load('RF_service_home.json')['RF_current']; ha1=load('HA1.json'); ha6=load('HA6.json'); ha8=load('HA8.json')
    binding=load('HA8_current_source_binding.json')
    if not binding['exact_forwarded_installer_match'] or binding['actual_source_sha256']!=ha8['installer_source_sha256']:
        raise ValueError('HA8 forwarded installer differs from actual frozen current source')
    header=(base/'RF.sv').read_text().split(');',1)[0]
    if not re.search(r'\[4095:0\]\s+rsp_a,\s*rsp_b',header) or not re.search(r'\[4095:0\]\s+wr_data',header):
        raise ValueError('actual RF port closure changed; recompose, never retain old widths')
    if rf['mapped_RF_macro_count']!=128: raise ValueError('complete RF128 mapping required')
    RF_body=rf['mapped_RF_macro_area_mm2']+rf['mapped_stdcell_area_mm2']
    buses={k:v['bits_per_cycle'] for k,v in ha1['ports'].items()}
    return dict(schema='HBM_HA9_SERVICE_COMPOSITION_V1',status='SOURCE_MODEL_INCOMPLETE_NOT_ADOPTED',
                input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.iterdir() if p.is_file()},
                source_origins=origins,
                RF=dict(basis='OWNER_REPORTED_ACTUAL_MAPPED_BODY; raw mapping verifier remains Hubble/Goodall',
                        source='a76916ad639c37e62b4ddbdef661240b509cae21',
                        unique_component='RF128_W4_W6_FMAX_FMIN_context',macro_count_per_SM=128,
                        macro_area_mm2_per_SM=rf['mapped_RF_macro_area_mm2'],
                        stdcell_area_mm2_per_SM=rf['mapped_stdcell_area_mm2'],
                        cell_plus_macro_mm2_per_SM=RF_body,replicas_per_die_model=32,
                        cell_plus_macro_mm2_per_die_model=32*RF_body,
                        extra_W4_W6_area_debit_mm2=0,
                        read_payload_bits_per_cycle=8192,write_payload_bits_per_cycle=4096,
                        local_payload_track_floor=12288,
                        PDN_halo_channel_and_clock_area=None,SS_FF_qualified=False),
                HA1=dict(source_status=ha1['status'],port_bits=buses,
                         simultaneous_all_port_track_floor=sum(buses.values()),
                         ACK_visibility_completion_track_floor=buses['W4_accepted_common_ACK']+buses['W6_accepted_visibility']+buses['scheduler_completion'],
                         new_storage_mm2_per_die_proxy=ha1['storage_cell_um2_per_die']/1e6,
                         complete_added_service_area_mm2=None,available_tracks=None,
                         mux=ha1['table'],latency=ha1['latency']),
                HA6=dict(retained_FIFO_ports=ha6['ports'],
                         actual_parent_FIFO_installed=ha6['parent_FIFO_instantiation_found'],
                         conditional_service_contract=ha6['qualified_service_contract'],
                         replication_count=None,composed_clock_CDC_area_mm2=None,
                         actual_HA6_caller_crossing_inventory=None,
                         serial_1p091GHz_adopted=False),
                HA8=dict(forwarded_native_engine=ha8['selected_native_engine'],
                         actual_frozen_installer_binding=binding,
                         native_engine_installed=ha8['native_engine_installed'],
                         current_installer_source_sha256=ha8['installer_source_sha256'],
                         RF_body_paid_once=True,SRAM_residency_bank_port_selection=None,
                         native_engine_track_and_clock_join=None,adopted=False),
                DS_KV=bind_partition(load('W2_stage_map.json'),load('W2_model.json')),
                physical_launch_allowed=False,added_cycles_adopted=0,
                gate='Actual caller/replica/port and PG/clock/OBS channel joins, function and measured composed performance precede P&R')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(compose(),f,indent=2,sort_keys=True);f.write('\n')
