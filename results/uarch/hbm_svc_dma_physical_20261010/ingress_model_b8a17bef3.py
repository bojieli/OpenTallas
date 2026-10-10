"""Admission sizing for actual four-stack HBM DMA bandwidth, before wide RTL.

Source controller bandwidth is roof-limited: 3.8TB/s sustained, 4TB/s nominal.
The prior eight-lane vehicle's fraction of its own port peak is NOT HBM BW.
"""
from pathlib import Path
import hashlib,json,math,re

def wide_model(lanes=32, tag_bits=6, sectors_per_request=256, native_latency=104,
               request_hops=96, data_hops=96, credit_hops=96):
    root=Path(__file__).resolve().parents[1]
    stacks=4; pcs=32; hz=1.2e9
    sustained=3.8e12/hz;nominal=4e12/hz;target=.9*nominal
    peak=stacks*lanes*32
    write_commit=3;read_publication=5;cache_publication_overhead=2;seam_captures=2
    # Actual cache API allocates one sector/bank record per accepted edge.
    # Every 1..4-record burst must be fully allocated before native issue.
    allocation_cycles=4
    # Existing registered ot_secded encoder1/decoder2, to bind in successor.
    ingress_protection_cycles=3
    fill=(native_latency+request_hops+allocation_cycles+ingress_protection_cycles+
          write_commit+read_publication+cache_publication_overhead+data_hops+seam_captures)
    descriptor_cycles=sectors_per_request/lanes
    required_windows=math.ceil(fill/descriptor_cycles)
    tag_count=1<<tag_bits
    # Credit is reserved at read launch, before registered publication.
    rtt=read_publication+cache_publication_overhead+data_hops+credit_hops+seam_captures
    credits=1<<math.ceil(math.log2(rtt))
    lease_count=1<<math.ceil(math.log2(math.ceil(native_latency/4)+1))
    width=lanes*(256+2+tag_bits+8)+1+tag_bits+9+37+lanes+1
    height=math.ceil((8+(width/2)*.096+8)/.048)*.048
    macro='ot_sram_1r1w_256x256_m2_r2c2'
    lef=root/'physical/asap7_memory_macros_v2'/macro/(macro+'.lef')
    text=lef.read_text();mw,mh=map(float,re.search(r'SIZE\s+(\d+\.\d+)\s+BY\s+(\d+\.\d+)',text).groups())
    # Per-PC caching needs two 4-sector groups for a 256-sector descriptor.
    # Allow a third group for an unaligned descriptor. Each sector bank has
    # 128 payload +128 protected-sidecar rows:64 descriptors x3groups exceeds
    # one macro, hence BOTH rows/sidecars replicated (two macros per bank).
    groups=tag_count*math.ceil((sectors_per_request+3)/(pcs*4))
    macros_per_bank=math.ceil(groups/128)
    macro_count=stacks*pcs*4*macros_per_bank
    record=dict(schema=1,status='SIZED_WIDE_ADMISSION_NOT_IMPLEMENTED',
        bandwidth_basis='Owner calibration supplied20261010:3.8TB/s sustained95%4.0TB/s nominal; source table tools/hbm_accel_current_target_portmap.py also prices4stack4000GB/s',
        hz=hz,sustained_B_per_cycle=sustained,nominal_B_per_cycle=nominal,
        minimum_owner_90pct_nominal_B_per_cycle=target,
        old_8lane_component_peak_B_per_cycle=1024,old_port_fraction_of_sustained=1024/sustained,
        old_component_94p5085pct_fraction_of_sustained=(1024*.94508537)/sustained,
        stacks=stacks,pcs_per_stack=pcs,lanes_per_stack=lanes,port_peak_B_per_cycle=peak,
        required_controller_utilization_of_port_peak=target/peak,
        achievable_upper_bound_B_per_cycle=min(peak,sustained),
        actual_90pct_gate_possible_at_port_width=peak>=target,
        native_latency_validation_scenario_cycles=native_latency,
        native_latency_measured=False,
        native_outstanding_bursts_per_PC=lease_count,native_4sector_group_max=True,
        native_per_PC_one_sector_per_cycle_service_required=True,
        distributed_cache_required_allocator_instances=stacks*pcs,
        distributed_cache_allocation_sector_per_PC_cycle=1,
        distributed_cache_allocation_B_per_PC_cycle=32,
        distributed_cache_allocation_B_per_stack_cycle=pcs*32,
        distributed_cache_allocation_B_per_die_cycle=stacks*pcs*32,
        distributed_cache_fetch_sector_per_PC_cycle=2,
        distributed_cache_fetch_B_per_PC_cycle=64,
        distributed_cache_fetch_B_per_stack_cycle=pcs*64,
        distributed_cache_fetch_B_per_die_cycle=stacks*pcs*64,
        one_global_allocator_is_insufficient=True,
        native_response_ingress_before_II2_banks={
            'proposed_entries_per_bank':32,'banks_per_PC':4,'entries_per_PC':128,
            'payload_bits_per_entry':256,'planned_SECDED_bits_per_entry':32,
            'slot_index_epoch_fault_metadata_bits_per_entry':16,
            'planned_paired_metadata_bits_per_entry':32,
            'protected_storage_bits_per_PC':128*(256+32+32),
            'aggregate_four_stack_storage_bits':128*128*(256+32+32),
            'native_return_backpressure_allowed':False,
            'reserve_every_burst_beat_before_native_issue':True,
            'reservation_release_point':'queued_beat_dispatch_into_fixed_write_commit_pipeline',
            'worst_case_reserved_sectors_per_bank_with32_fourbeat_leases':32,
            'four_entries_per_bank_predecessor_admission':'FAIL:16beats total cannot hide104cycle native latency without inventing PHY return backpressure',
            'arrival_sector_per_PC_cycle':1,
            'per_bank_service_sector_per_cycle':.5,
            'balanced_per_bank_arrival_sector_per_cycle':.25,
            'finite_queue_BW_validation_required':True,
            'rationale':'direct CAM-to-bank selected response stalls at bankII2; bank-local elastic queues decouple OOO return bursts without changing raw roof or descriptor workload',
            'no_guarantee_for_arbitrarily_unbalanced_bank_streams':True},
        format_expansion={
            'FP32_U32':dict(multiplier=1,VM_Bcycle_required=target,minimum_sector_ports=math.ceil(target/32),proposed_physical_ports=128),
            'BF16':dict(multiplier=2,VM_Bcycle_required=2*target,minimum_sector_ports=math.ceil(2*target/32),proposed_physical_ports=256),
            'FP8E4M3_INT8':dict(multiplier=4,VM_Bcycle_required=4*target,minimum_sector_ports=math.ceil(4*target/32),proposed_physical_ports=512)},
        fixed_WP128_raw_Bcycle_roofs_by_format=dict(FP32_U32=4096,BF16=2048,FP8E4M3_INT8=1024),
        WP512_logical_write_bits_per_cycle=512*280,
        VM_physical_minimum_banks_single_write_per_cycle=512,
        VM_physical_minimum_banks_protected_II2=1024,
        VM512_protected_II2_raw_Bcycle_roof_FP8=512*32/2/4,
        VM512_protected_II2_fails_FP8_owner_gate=True,
        VM_physical_bank_II_must_be_measured=True,
        VM128bank_singleport_is_insufficient_for_FP8_or_BF16_owner_gate=True,
        format_conversion_location='beside512physicalVMbanks; raw272bitlane longlinks then4localdestination-sector writes; no unpriced expanded143360bit diebus',
        conversion_replica_count=128,
        replica_local_bank_fanout=4,
        VM_bank_depth_scaling_at_fixed_capacity='512physicalbanks eachquarterdepth of128bankdesign; SRAMinventory regenerated beforeRTL',
        supported_formats='0FP32/5U32,1BF16,2FP8E4M3,4INT8; FP4notimplementedinexistingDMAfront',
        initial_credits=credits,credit_RTT_cycles_budget=rtt,
        SRAM_write_commit_cycles=write_commit,
        SRAM_read_publication_cycles=read_publication,
        distributed_cache_publication_overhead_cycles=cache_publication_overhead,
        distributed_cache_visible_cycles=read_publication+cache_publication_overhead,
        native_burst_metadata_allocation_cycles_worst_case=allocation_cycles,
        native_burst_all_sector_records_reserved_before_issue=True,
        planned_ingress_SECDED_encoder_decoder_cycles=ingress_protection_cycles,
        ingress_protected_successor_implemented=False,
        interface_seam_capture_cycles=seam_captures,
        credit_reservation_point='cache_read_launch_before_registered_publication',
        source_to_first_data_fill_cycles_budget=fill,
        request_window_sectors=sectors_per_request,
        port_peak_descriptor_drain_cycles=descriptor_cycles,
        minimum_concurrent_descriptor_windows_to_hide_fill_at_peak=required_windows,
        tag_bits=tag_bits,tag_count_per_stack=tag_count,
        tagged_window_lead_cycles=tag_count*descriptor_cycles,
        tag_admission_pass=tag_count>=required_windows,
        dq_bits=1+tag_bits+9+37,dd_bits_per_lane=256+2+tag_bits+8,
        total_face_traffic_bits_per_stack=width,
        two_layer_face_pitch_um=.096,minimum_companion_height_um=height,
        proposed_companion_height_um=480,
        old_120um_gap_fit=False,
        geometry_gate='HOLD: 480um reservation expands occupied service-to-SM band; actual die must regenerate',
        raw_face_capacity_480um=int(2*(480-16)/.096),
        face_pin_raw_fit=width<=int(2*(480-16)/.096),
        sram_cache_groups_per_PC=groups,
        sram_macro=macro,sram_geometry_um=[mw,mh],sram_macros_per_bank=macros_per_bank,
        sram_macros_per_PC=4*macros_per_bank,sram_macros_four_stacks=macro_count,
        sram_macro_area_four_stacks_mm2=macro_count*mw*mh/1e6,
        sram_lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),
        sram_model='Eachbank128payload/128sidecarrows; bankII2 protectedread/write; registered publication5cycles',
        cache_bank_count_is_new_inventory=True,
        MACs_per_cycle=0,compute_intensity=0,
        physical_floorplan_fit=False,implemented_wire_relays=False,
        adoption_gate='Exact fullshape native/controller bandwidth >=3000Bcycle plus real expanded floorplan, SRAM/control/relay timing and format-expanded VM sink:512logical32Bwrite ports with provenII1, or1024interleaved physicalII2banks',
        exclusions='No assumption that4096Bportpeak is actualHBM bandwidth; no zero-hop credit or unpriced prefetch')
    return record
if __name__=='__main__':print(json.dumps(wide_model(),indent=2))
