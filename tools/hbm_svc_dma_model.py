"""Source-derived DMA service sizing; unmeasured physical facts remain explicit holds."""
import importlib.util
import math
from pathlib import Path

def svc_dma_model(initial_credits=256, window=2048):
    root = Path(__file__).resolve().parents[1]
    src=root/'physical/hbm_accel_die_views/svc/gen_svc_seg.py'
    spec=importlib.util.spec_from_file_location('svc_dma_geometry',src)
    g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    families={}
    for family in ('SW','SE'):
        pl=g.plan_family(family)
        # Actual committed port centers. Front location/route is not yet assigned.
        origin=pl['U']['e']; distances=[abs(origin[0]-pl['U'][f'pc{p}'][0])+abs(origin[1]-pl['U'][f'pc{p}'][1]) for p in range(32)]
        hops=[g.ceil_hops(d)+2 for d in distances] # both pin capture obligations
        internal_rtt=2*max(hops)+2 # sender+consumer credit capture
        max_existing=max(sum(v['bits'] for k,v in pl['face'].items() if k[0]==cut) for cut in range(len(pl['cuts'])))
        added=8*270+51+1+8
        capacity=int((pl['H']-4)/g.PITCH)*2
        families[family]=dict(physical_source=str(src.relative_to(root)),stack_service_um=[pl['W'],pl['H']],
            descriptor_origin_um=origin,pc_xy_um=[pl['U'][f'pc{p}'] for p in range(32)],
            manhattan_pc_to_service_endpoint_um=distances,hop_um=g.HOP,local_request_or_response_cycles=hops,
            minimum_internal_credit_roundtrip_cycles=internal_rtt,
            credits4_utilization_upper_bound=min(1,4/internal_rtt),credits8_utilization_upper_bound=min(1,8/internal_rtt),
            endpoint_front_roundtrip_cycles=None,
            initial_credits=initial_credits,remaining_front_roundtrip_budget_cycles=initial_credits-internal_rtt,
            existing_cross_face_bits_max=max_existing,added_cross_face_bits=added,
            total_cross_face_bits_bound=max_existing+added,two_layer_raw_capacity_tracks=capacity,
            raw_face_fit=max_existing+added<=capacity,
            route_track_fit='HOLD: power/keepouts and actual new pins not assigned',
            latency_to_first_sector_lower_bound_cycles=max(hops)+2,
            fixed_window_latency_cycles=math.ceil(256/8),
            sustained_payload_bytes_per_cycle_per_stack=256)
    storage=window*(256+1+4+8+1)+(window//256)*(37+9+4)+32*16*26
    return dict(schema=1,verdict='SIZED_NOT_PHYSICALLY_QUALIFIED',macs_per_cycle=0,
        compute_intensity=0,communication_intensity_payload_fraction=256/270,
        stacks=4,pcs_per_stack=32,lanes_per_stack=8,payload_bytes_per_cycle=1024,
        request_bits_per_stack_per_cycle=51,response_bits_per_stack_per_cycle=2160,
        credit_bits_per_stack_per_cycle=8,native_max_contiguous_same_pc_sectors=4,
        native_outstanding_bursts_per_pc=16,
        native_response_latency_sweep_cycles=[54,104],
        latency_basis='SourceT_RCD19;54/104areexplicit conservative validation scenarios, not measuredPHYtiming',
        pc_map='s[6:2] XOR s[11:7] XOR s[16:12]; s=byte_address[34:5]',
        reorder_sector_window=window,descriptor_queue_depth=window//256,storage_bits_per_stack=storage,
        area_assumed_flop_um2_per_bit=2.0,storage_only_area_um2=2*storage,
        area_status='HOLD: storage estimate excludes mux/control/relay and existing service cell usage',
        multiplexer_cost='8 lanes, each selects 32 PC sector responses; local partition required',
        fanout='descriptor distributed to32 PC controllers; reset and ready local registered',
        families=families,
        adoption_gate='Exact RTL + sustained >=90%BW including physical relay credits + fit + in-context timing',
        qualification='256 credits provisional; pin helper composed148/184cycleRTT, no fullrateclaim until physicallyreserved')

if __name__=='__main__':
    import json
    print(json.dumps(svc_dma_model(),indent=2))
