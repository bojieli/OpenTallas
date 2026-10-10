"""Pre-build capacity and latency of the HBM reset/fault control masters."""
import json

def model(ports=4, sources=16):
    # Two-stage synchronizers per asynchronous status, three-stage deassert
    # collars at each real region clock. Reset and fault handling do no MACs.
    sync_bits=2*(2+4+ports+2)
    release_bits=3*(4+ports+2)
    state_bits=4+32+32+32+sources
    bits=sync_bits+release_bits+state_bits
    return dict(schema='opentallas.hbm_control_robustness.model.v1', default_enabled=False,
      signoff=False, macs_per_cycle=0, compute_intensity=0, communication_intensity='control only',
      memory_bytes_per_cycle=0, boundary_bits_per_cycle=sources*2+4+ports+12,
      replicas=1, mux_cost='32-bit sticky cause OR; 32-bit saturating CE/UE counters',
      fanout='local synchronous release collars, no direct asynchronous status fanout',
      routing_tracks=sources*2+4+ports+12, channel_capacity_required_tracks=sources*2+4+ports+12,
      register_bits=bits, cell_area_floor_um2=round(bits*.37908,3),
      floorplan_slot=dict(width_um=100,height_um=100,utilization_target=.55,fit_is_physical_pending=True),
      boot_release_cycles={'status_sync':2,'stages':5,'region_release':3},
      token_latency_delta_cycles=0, fault_status_latency_cycles=1,
      clock=dict(stream_mhz=1200,aon_mhz='platform dependent; not token path',ss_setup_uncertainty_ps=60,ff_hold_uncertainty_ps=25),
      obligations=['SS/FF +15ps and DRC0 with real pins','Production vendor PLL lock and clocks','CDC reset release at each region clock','Fault end-to-end token-loop stop and host record'])

if __name__=='__main__': print(json.dumps(model(),indent=2))
