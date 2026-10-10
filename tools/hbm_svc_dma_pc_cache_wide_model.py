#!/usr/bin/env python3
"""Model-first protected four-bank PC cache with four fetch contexts."""
import json

def model():
    return {'scope':'onePC distributed protected cache, opt-in successor',
            'banks':4,'real_SRAM_macros':8,'groups_per_bank':256,
            'group_mapping':'{slot6, ordinal2}; ordinal=(srcsector>>7)-(descriptorbase>>7); bank=srcsector[1:0]',
            'payload_bytes':32768,'conservative_native_groups':192,
            'allocation_record':'2statebits(absent/native_debt/writing/ready)+epoch1, each with stored complement',
            'protected_metadata_FF_bits':6144,
            'fetch_contexts':4,'fetch_bundle_bits':1024,'publication_payload_FF_bits':4096,
            'bank_read_II':2,'bank_write_II':2,'cache_group_issue_II':2,
            'bank_first_visible_cycles':5,'bank_first_transfer_cycles':6,
            'cache_first_visible_cycles_budget':7,
            'throughput_sectors_per_pc_cycle':2,'required_sectors_per_pc_cycle':1,
            'peak_payload_bytes_per_pc_cycle':64,'peak_payload_GBps_at1p2GHz':76.8,
            'macs_per_cycle':0,'compute_intensity_MACs_per_byte':0,
            'communication_intensity_macro_bytes_per_payload_byte':2,
            'boundaries_bits_per_cycle_peak':{'allocate':32,'return':269,'fetch':15,'bundle':1030},
            'tracks_budget_required':1346,'channel265um_two_layers_pitch0p064_tracks':8281,
            'fanout':'PC-local metadata; four independent registered bank ports, no central reference memory',
            'replication':'four hardened banks, two macros/bank; local4context publication and priority muxes',
            'controller_area_reservation_um2':2000,
            'metadata_FF_only_area_floor_um2':6144*0.37908,
            'data_FF_only_area_floor_um2':4096*0.2916,
            'controller_area_budget_um2':5500,
            'controller_reservation_verdict':'FAIL_lower_bound_exceeds2000 even without publication or gates',
            'total_pc_area_budget_um2':63027.94704+5500,
            'pc_slot_um':[265,480],'slot_utilization_budget':(63027.94704+5500)/(265*480),
            'finite_flow':'four allocated fetchcontexts; per-bank oldest requested context issues; publications match oldest issued context; inorder bundle retirement',
            'epoch_contract':'ret_epoch preserved from native allocation through response; never reuse group/bank until native/write debt and issued/completed read publications drained; epoch toggles on reuse; 1bit safe only under this no-wrap contract',
            'stale_response':'reject absent, wrongepoch, duplicate(no native debt), or damagedmetadata before bank write',
            'early_fetch':'hold request until allocation/readiness of matching epoch; no oldepoch read',
            'single_user_token':'bank5visible + cachecapture/publication budget2 fill + 2*(N-1) group issue cycles, stalls composed by caller',
            'physical_scope':'mapped controller area and actual pinfit pending; no route claim'}

if __name__=='__main__': print(json.dumps(model(),indent=2))
