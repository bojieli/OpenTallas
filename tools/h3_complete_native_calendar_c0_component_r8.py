#!/usr/bin/env python3
"""Source-sized W5 C0 component, actual W2/W6 contracts, prospective costs only."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h3_complete_native_calendar_20261002/c0_command_r8'
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def require(x,message):
    if not x:raise ValueError(message)
def register_fields(path):
    # Counters declared integer are control iteration, not stored RTL arrays.
    data=path.read_text();out={}
    for width,names in re.findall(r'\breg\s*(\[[^\]]+\])?\s*([^;]+);',data):
        bits=1
        if width:
            hi,lo=map(int,width.strip('[]').split(':'));bits=hi-lo+1
        for item in names.split(','):
            match=re.fullmatch(r'\s*(\w+)\s*(?:\[(\d+):(\d+)\])?\s*',item)
            require(match is not None,'literal stored field '+item)
            name,hi,lo=match.groups();out[name]=bits*((int(lo)-int(hi)+1) if hi else 1)
    return out
def model():
    manifest=json.loads((BASE/'input_manifest.json').read_text())
    for name,row in manifest.items():
        raw=(BASE/'inputs'/name).read_bytes()
        require(len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'pin '+name)
    old=json.loads((BASE/'inputs/Ampere_model.json').read_text());current=json.loads((BASE/'inputs/Ampere_W2_W6_reconcile.json').read_text())
    proposed=json.loads((BASE/'model_before_RTL.json').read_text())
    C0=ROOT/'rtl/gpu/hbm_w5_c0_candidate/ot_hbm_w5_c0_command.sv';adapter=ROOT/'rtl/gpu/hbm_w5_c0_candidate/ot_hbm_w5_w2_pc_adapter.sv'
    fields=register_fields(C0);fields.pop('demand_legal') # Combinational legality predicate, not a retained FF.
    aside=register_fields(adapter)
    require(fields['meta']==128*92 and fields['backend']==128*16 and fields['data_q']==4096 and fields['remaining_context']==1024,'whole64fragment dimensions')
    require(current['W2']['raw_bits_per_PC']==4781 and current['W2']['protected_bits_per_PC']==9144,'selected W2')
    require(current['W6']['raw_bits_per_SM']==71 and current['W6']['protected_bits_per_SM']==144,'selected W6')
    staging=old['models']['DeepSeek']['staging']
    require(staging['useful_bytes_per_SM']==139264 and staging['physical_bytes_per_SM']==163840,'DS source staging')
    x=proposed.copy();x.update(schema='C0_CONNECTED_SOURCE_MODEL_R8',source_manifest_sha256=hashlib.sha256((BASE/'input_manifest.json').read_bytes()).hexdigest(),
        source_files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [C0,adapter]},
        actual_source_interfaces=dict(W2_commit=manifest['ot_hdc_qwen_pc_exact_completion.sv']['commit'],W6_commit=manifest['ot_gpu_rf_visibility_fence_w6.sv']['commit'],W4_commit=manifest['W4_RF_service.sv']['commit']),
        raw_C0_register_fields=fields,raw_C0_register_bits_per_SM=sum(fields.values()),raw_C0_register_bits_32SM=32*sum(fields.values()),
        raw_adapter_fields=aside,raw_return_carrier_bits_per_PC=sum(aside.values()),raw_return_carrier_bits_128PC=128*sum(aside.values()),
        assumed_C0_storage_64to72_protection_bits_per_SM=sum(math.ceil(n/64)*72 for n in fields.values()),
        gross_local_storage_proxy_50pct_mm2=32*sum(math.ceil(n/64)*72 for n in fields.values())*.42282*2/1e6,
        capture_decoder_correction_not_implemented=True,adapter_storage_proxy_50pct_mm2=128*math.ceil(sum(aside.values())/64)*72*.42282*2/1e6,
        gross_proxy_not_net_addition=True,matched_R14_meta92_W4_parent55_native_privatekey_and_budget_debits='UNKNOWN; do not debit or add gross to parent bridge',
        W2_selected=current['W2'],W6_selected=current['W6'],W2_W6_once_only={name:{'W2':row['W2_once_only'],'W6':row['W6_once_only_replacement']} for name,row in current['models'].items()},
        legacy_RF_visibility51_is_not_selected_W6=True,DS_staging_source=staging,
        retained_PHY=old['models']['DeepSeek']['shoreline']['retained_PHY_interface_bits'],selected_PHY=old['models']['DeepSeek']['shoreline']['selected_controller_required_bits'],
        PHY_component_binding='one32Bsector only: localAW31,LEN5=1,BEAT4=0; selected LEN6/BEAT5 narrowing is lossless for these constants, bulk bursts not supported',
        address_extent='source r17: byte<81000000000,32Baligned, full31local-sector asserted by extent; never truncate wider physical addresses',
        actual_RF_ACK='c4c794 fullwidth ack_owner46+ack_slot9+ack_identity_fault, held ack_ready; aggregate only after all8 validated both-copy writes, no synthetic identity on bareACK',
        namespace='allocation_tag32/gen4/source_byte39 accepted explicitly; native_owner64/gen64 remain in retained private mapping, no cast into originaltag32',
        context_admission=json.loads((BASE/'context_admission_port_model_r1.json').read_text()),
        actual_global_G0_or_caller_directory=False,
        canonical_bridge_owner='Popper35b5; Dewey local prototype preserved, not canonical implementation',
        prototype_source_contract_differences=['one aggregate commandparent55 vs Popper perframe owner anchor ABI; adapter must reconcile before any use','same opaque producer_gen4 required within command; opaque tuple straddling wrap needs canonical source allocator rule','whole refill frames only; no destination-writeback snapshot/visibility implementation'],
        upper_waits='Installed endpoint/consumer/reverse/allcopy upper bounds unknown; no always-ready credit',
        local_serial_command_lower_edges=dict(MAX64_local_edge_floor=128*6+64+8*3+19+128,sector_allocation_W2select_accept_positiveendpoint_restore_capture_edges=6,source_stageACK_edges=64,source_W4_accept_plus_bothcopyACK_capture_edges=24,W6_edges=19,retained_reverse_accepts=128),
        minimum_single_token_contribution='N(source-bound full64fragment commands)*(1003 local-edge floor + actualR14/W10 forward/return/reverse and contention/CDC/producer-drain terms). Actual command count/routing join unavailable, no scalar whole-token price.',
        local_floor_is_prospective_not_clock_measured=True,whole_token_ns=None,
        selectors=dict(response_owner_ways=128,response_compare_bits=108,request_duplicate_owner_ways=128,request_duplicate_owner_bits=46,backend_duplicate_ways=128,backend_duplicate_bits=18,reverse_mux_ways=128,reverse_mux_payload_bits=108,RF_output_bits=4096,local_credit_count_ways=128,local_credit_count_bits=8),
        clock_paths='single local service clock;128way identity/capacity/alias checks and1024bit plan capture need actual synthesis/pipeline; target1.2GHz prospective only; W6 ECC decode/encode latency not physically measured',
        fanout_and_tracks='32SM demand and128PC return carriers; exact combined physical cuts/PG/CTS unbound, no W15wide-slot rate transfer',
        unsupported_semantics=['partial last512Bframe/oldtail merge','KV FP8 codec and actual KV caller body','DS96 nativePC/rank/home mapping','actual native G0 all-gang reservation/DAG binds','global originaltag32/gen4 allocator and source shared leases','full16 R14 backend echo/quarantine installation','source current scoped allcopy/CDC/reset abort producer','C0 mutable metadata protection and contextual SSFF'],
        numerical_or_physical_credit=False)
    return x
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    raw=canonical(model());out=BASE/'composed_model_r2.json'
    if args.verify:require(out.read_bytes()==raw,'byteexact current component model')
    else:
        require(not out.exists() or out.read_bytes()==raw,'historical record overwrite refused');out.write_bytes(raw)
    print('PASS current source model; actual W2/W6 interface component, production G0/allcopy/whole-token UNKNOWN')
if __name__=='__main__':main()
