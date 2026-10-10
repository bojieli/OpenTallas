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
if __name__=='__main__': print(json.dumps(model(),indent=2))
