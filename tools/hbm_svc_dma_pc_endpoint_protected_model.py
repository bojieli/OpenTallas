#!/usr/bin/env python3
"""Protected one-PC endpoint sizing, committed before its new RTL.
Canonical source contract: stream commits 25909776a and f0596a3bd.
"""
import argparse,json
from pathlib import Path

def model():
 depth=256; contexts=4; macro=172.824*41.064
 fifo_bits=depth*2*(31+8) # paired metadata and selected-row identity
 pending=128; cam=32*26*2; active_groups=256*2
 context_bits=contexts*(2*31+2*1024+2*8)
 # Pending/FIFO/context pointers, allocation index, counters, credits and sticky
 # status are priced conservatively here, then replaced by mapped inventory.
 paired_control_budget=512; dd_bits=272*2
 ingress_payload=4*32*(256+32+2*16)
 ingress_pub=4*(2*256+2*18+2)
 protected_register_floor=fifo_bits+pending+cam+active_groups+context_bits+paired_control_budget+dd_bits
 ff_area_per_bit=0.35 # planning floor, not a library measurement
 cache_area=71455.30368
 return dict(schema=1,status='PRE_RTL_SIZED_NOT_PHYSICALLY_ADMITTED',
 canonical_contract_commits=['25909776a','f0596a3bd'],enable_default=0,
 instances=128,MACs_per_cycle=0,compute_intensity=0,
 command_ABI='capture one paired64 pending command; caller holds valid and all fields stable; cmd_rdy only physical native issue',
 command_FIFO_entries=depth,command_FIFO_primary_bits=31,command_FIFO_row_identity_bits=8,
 command_FIFO_paired_storage_bits=fifo_bits,pending_paired_bits=pending,
 command_FIFO_selected_implementation='FF; no ninth SRAM fits existing vertical column',
 command_SRAM_alternative=dict(macros=1,area_um2=macro,protected_row_bits=144,
  layout='31metadata+complement31+row8+complement8 padded128, two64 SECDED words',
  codec_encoder_cycles=1,codec_decoder_cycles=2,
  latency='macro registered address/capture and codec boundary must be measured',
  column_height_um=513.576,slot_height_um=480,admission='HOLD geometry; no invented rotation'),
 FF_FIFO_alternative=dict(storage_floor_area_um2=fifo_bits*ff_area_per_bit,
  mux='256to1x39 protected head selection, 39-bit paired write decoding; actual area and pin fit required'),
 native_CAM_entries=32,native_CAM_primary_bits=26,native_CAM_paired_bits=cam,
 native_CAM_fields='valid1/tag17/len4/seen4; allocation epoch carried inside tag, duplicate/OOB/unknown dropped and faulted',
 active_group_paired_bits=active_groups,
 group_recycle_contract='block group until final DD emission; native lease and cache debt cannot wrap epoch',
 cache_banks=4,cache_actual_macros=8,cache_area_um2=cache_area,
 cache_group_issue_II=2,cache_visible_cycles=7,cache_transfer_cycles=8,
 allocator_max_cycles=4,allocator_sector_per_PC_cycle=1,
 serializer_contexts=contexts,serializer_context_protected_bits=context_bits,
 serializer_protection='paired payload and metadata with failclosed data publication; no uninitialized contexts publish',
 DD_register_protected_bits=dd_bits,paired_control_planning_bits=paired_control_budget,
 endpoint_register_storage_planning_bits=protected_register_floor,
 endpoint_register_area_floor_um2=protected_register_floor*ff_area_per_bit,
 ingress_storage_bits=ingress_payload+ingress_pub,
 ingress_latency_cycles=5,ingress_reserved_entries_per_bank=32,
 return_backpressure=False,reservation='wholeburst reservation on native issue edge before any return; released only actual bank write',
 memory_port_bytes_per_cycle=dict(native_in=32,cache_write=32,cache_fourbank_read_peak=64,DD=32),
 boundary_bits_per_cycle=dict(command=64,native_request=58,native_response=278,DD=272,cache_bundle=1028),
 approximate_signal_tracks=dict(external_boundary=672,cache_bundle=1028),
 track_capacity='actual metal/pin inventory required, no assumed corridor capacity',
 minimum_context_capacity_sectors=16,credit_initial=256,credit_RTT_budget=194,
 sustained_sector_per_PC_cycle=min(1,2,1),die_B_per_cycle=4096,
 latency_composition=dict(request_relay=96,pending_capture=1,allocation=4,native_validation=104,
  ingress=5,bank_commit=3,cache_visible=7,cache_transfer=1,serializer_capture=1,DD_register=1,
  data_relay=96,seam_captures=2),
 first_DD_planning_cycles=321,native104_is_validation_scenario_not_measured=True,
 finite_queue_analysis='four cache and four serializer contexts overlap; serializer II1; 256 output FIFO covers192 groups; 32 leases cover128 native beats; ingress 32 per bank reserved',
 slot_um=[265,480],slot_area_um2=265*480,
 planned_cache_plus_endpoint_register_floor_um2=cache_area+protected_register_floor*ff_area_per_bit,
 area_exclusions=['ingress actual mapping','mux/decode/combinational logic','clock/hold/routing'],
 physical_admission='HOLD until complete endpoint mapping, distinct protection cells, real pins and slot fit',
 exact_gate='one PC actual eight SRAM models; arbitrary native tags/partial groups/reuse/credits/backpressure and invalid command mutants')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 with a.output.open('x') as f:json.dump(model(),f,indent=2);f.write('\n')
 print(json.dumps(model(),indent=2))
