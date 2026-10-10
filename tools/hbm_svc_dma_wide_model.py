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
    fill=native_latency+request_hops+data_hops+5+2
    descriptor_cycles=sectors_per_request/lanes
    required_windows=math.ceil(fill/descriptor_cycles)
    tag_count=1<<tag_bits
    rtt=data_hops+credit_hops+2
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
        initial_credits=credits,credit_RTT_cycles_budget=rtt,
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
        adoption_gate='Exact fullshape native/controller bandwidth >=3000Bcycle plus real expanded floorplan, SRAM/control/relay timing and VM128bank write consumption',
        exclusions='No assumption that4096Bportpeak is actualHBM bandwidth; no zero-hop credit or unpriced prefetch')
    return record
if __name__=='__main__':print(json.dumps(wide_model(),indent=2))
