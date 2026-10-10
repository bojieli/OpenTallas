"""Size one PC-local DMA endpoint before replacing the central CPU vehicle.

Each physical source lane belongs to one PC. Carried tag/index identifies the
destination; the front owns and prices its actual index-to-VM-bank router.
"""
import argparse,json,math
from pathlib import Path

def model():
    stacks=4;pcs=32;sector=32;windows=64;groups_per_window=3
    queue_depth=1<<math.ceil(math.log2(windows*groups_per_window))
    # slot6,ordinal2,indexbase8,frontendtag6,epoch1,len4,startbank2,
    # native-issued1/fetch-issued1. Paired mutable control metadata.
    command_bits=31
    return dict(schema=1,status='SIZED_PC_ENDPOINT_BEFORE_RTL',
        physical_lane_contract='onePCperphysicalDDlane; arbitrary carried descriptoridx, no idx%32 requirement',
        endpoint_instances_per_stack=pcs,endpoint_instances_per_die=stacks*pcs,
        native_PC_map='PC=(sector>>2 ^ sector>>7 ^ sector>>12)&31',
        inverse_PC_map='page=base_sector>>7+ordinal; sector=(page<<7)|(((PC^page^(page>>5))&31)<<2)|bank',
        native_tag17_contract='{allocation_epoch1,startbank2,group8,6zero}',
        group8_contract='{slot6,ordinal2}; ordinal=(sector>>7)-(descriptor_base_sector>>7)',
        tag_namespace='exclusiveDMAownerphaseonly; full17normal tags preserved under drain owner',
        command_queue_entries_per_PC=queue_depth,
        maximum_groups_per_PC_with64_unaligned256sector_windows=windows*groups_per_window,
        command_primary_bits_per_entry=command_bits,
        protected_command_storage_bits_per_PC=queue_depth*2*command_bits,
        protected_command_storage_bits_per_die=stacks*pcs*queue_depth*2*command_bits,
        command_queue_payload='group/idxbase/frontendtag/epoch/len/startbank and native/fetch issue state; no sector payload copy',
        required_independent_serial_allocator_instances=stacks*pcs,
        allocator_cycles_per_burst_max=4,allocator_sector_per_PC_cycle=1,
        allocator_B_per_stack_cycle=pcs*sector,allocator_B_per_die_cycle=stacks*pcs*sector,
        all_selected_bank_records_allocated_before_native_issue=True,
        native_leases_per_PC=32,native_latency_validation_cycles=104,
        native_latency_measured=False,
        native_ingress_bank_entries=32,native_ingress_banks_per_PC=4,
        every_native_burst_beat_reserved_before_issue=True,
        native_return_backpressure=False,
        cache_fetch_contexts=4,cache_group_sectors=4,
        cache_fetch_measured_group_II_cycles=2,
        cache_fetch_measured_visible_cycles=7,cache_fetch_measured_transfer_cycles=8,
        cache_B_per_PC_cycle=64,cache_B_per_stack_cycle=2048,cache_B_per_die_cycle=8192,
        serializer_sector_per_PC_cycle=1,serializer_B_per_stack_cycle=1024,
        serializer_B_per_die_cycle=4096,
        serializer_select_cost='one4to1x256bitlocalmux perPC; metadata accompanies bank-selected beat',
        serializer_payload_hold_bits_per_PC=1024,
        serializer_payload_SECDED_bits_per_PC=128,
        serializer_mutable_metadata_protection=True,
        source_32x32_payload_crossbar_required=False,
        front_index_router_cost_owner='native_burst front owner: actual mux/fanout/tracks and VM bank conflicts',
        credits_per_physical_PC_lane=256,
        model_MACs_per_cycle=0,compute_intensity=0,
        measured_cache_controller_area_um2_per_PC=8417.63178,
        measured_cache_plus_fourbanks_eightmacros_area_um2_per_PC=71445.57882,
        area_exclusions=['protected command queue/controller','protected nativeCAM uplift',
                         'protected ingress including finite decoder publications',
                         'serializer payload/control','clock/relay/hold/routing'],
        descriptor_replication_and_fanout='128independent PC-local command FIFOs, source group routing and per-stackTAG identity; no free shared allocator',
        physical_admission='HOLD actual complete endpoint mapping/pins/corridor/resources/SSFF required',
        exact_gate='minimumonePC plus frontfixedPC-lane routing gate; nativeOOOtags and perbankdelays, allgroupidx and finitequeues',
        adoption_gate='physical/source/front/VM composed actualroof and cold single-user latency, defaultoff until exactness and SSFF close')

def verify_inverse_map():
    # Exhaust representative page carries and every bank/PC. This independent
    # identity lets the endpoint derive descriptor index without a permutation.
    pages=[0,1,31,32,1023,1024,32767,32768,(1<<23)-1]
    for page in pages:
        for pc in range(32):
            for bank in range(4):
                s=(page<<7)|(((pc^page^(page>>5))&31)<<2)|bank
                assert ((s>>2)^(s>>7)^(s>>12))&31==pc
                assert s>>7==page and s&3==bank
    return len(pages)*32*4

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();record=model();record['inverse_PC_map_cases']=verify_inverse_map()
    with args.output.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
