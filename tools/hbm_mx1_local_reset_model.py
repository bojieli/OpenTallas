"""Before-build sizing for opt-in MX1 local reset ownership; no rate credit."""
import json

def model():
    units=['level','jf','ef','cf','kf','bf','hf','df','mtp','out','argmax']
    return dict(schema='opentallas.mx1_local_reset.v1',source='96ee08233',models=['Qwen3-8B HBM','DeepSeek-V4.1 HBM'],replicas_per_die=1,
        MACs_per_cycle=0,compute_intensity=0,communication_intensity=0,
        memory_port_bytes_per_cycle=0,boundary_bits_added=0,routing_tracks_added=0,
        reset_units=units,reset_replica_flops=2*len(units),reset_pin_fanout_added=2*len(units),
        reset_mux_demux=0,reset_replica_area_upper_um2=2*len(units)*0.6,
        outline_um=[1399.656,701.976],measured_baseline_cell_area_um2=12911,
        candidate_area_upper_um2=12911+2*len(units)*0.6,
        slot_fit='same macro and outline; <=13.2um2 added standard cells before route measurement',
        latency_cycles_added=0,single_user_token_latency_ns_added=0,
        qualification='transaction exactness + reset lockstep + full-shape TT/FF/DRC; no timing credit until measured')
def face_tile_model():
    """Two bounded side tiles from actual pin coordinates, before changing RTL."""
    import pathlib,math,hashlib
    p=pathlib.Path(__file__).resolve().parents[1]/'physical/hbm_cp_mtp_native/collar_mx1/hfd_cmdproc_s_mtp_native_mx1/ports.json'
    ports=json.loads(p.read_text())['ports']
    side={}
    for name in ('cSE','t_su_SE','cSW','t_su_SW'):
        ys=[(q[3]+q[5])/2 for q in ports[name]['pins']]
        side[name]=dict(min_y_um=min(ys),max_y_um=max(ys),tile_cut_y_um=86.4,
            pins_per_tile=[sum(y<86.4 for y in ys),sum(y>=86.4 for y in ys)],
            max_clock_pin_distance_um=max(abs(y-(43.2 if y<86.4 else 129.6)) for y in ys))
    return dict(schema='opentallas.mx1_face_tiles.v1',source='96ee08233',models=['Qwen3-8B HBM','DeepSeek-V4.1 HBM'],
        ports_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),MACs_per_cycle=0,compute_intensity=0,
        communication_intensity=0,memory_port_bytes_per_cycle=0,new_boundary_bits_per_cycle=4,new_boundary_clock_tracks=4,
        hardened_elements_per_die=1,side_tile_count=4,additional_ffs=0,additional_lockup_ffs=0,
        tile_clock_pins=dict(cke0=[1399.56,43.2],cke1=[1399.56,129.6],ckw0=[0.096,43.2],ckw1=[0.096,129.6]),
        side_pin_ranges=side,max_side_tile_span_um=86.4,pin_flop_final_wire_target_um=12,
        source_latency_policy='each face leaf arrives at measured interior insertion; actual local clock network delay is added by STA',
        source_accounting='separate related generated face clocks; calibrate core_clk only; one die common phase, no asynchronous groups',
        local_clock_network_target_ps=130,cross_root_half_cycle_ps=416.5,
        conservative_data_budget_ps=416.5-150-60,
        crossing_obligation='retain physical source-root falling-edge lockups; measure actual launch/capture skew in TT/FF',
        clock_buffers_area_allowance_um2=64*0.3,outline_um=[1399.656,701.976],
        replica_mux_demux_cost=0,clock_fanout='partition E/W capture sinks by actual pin y; no clock mux remains after TILECLK constant elaboration',
        routing_tracks_required=4,routing_capacity='four dedicated M6 face contacts; every added contact checked for overlap against existing M6 pins',
        latency_cycles_added=0,single_user_token_latency_ns_added=0,qualification='full-shape route and exactness; no measured gain claimed')

if __name__=='__main__': print(json.dumps(model(),indent=2))
