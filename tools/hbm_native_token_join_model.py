"""Model before implementation of the native two-half HBM AR token join."""
def model(qwen=False):
 tw=18 if qwen else 17; pw=20; hrw=37+tw+pw; halves=2; nsm=16
 return dict(schema='opentallas.hbm.native_token_join.model.v1', token_bits=tw,
  position_bits=pw, host_record_bits=hrw, replicas_per_die=1, cp_halves=halves,
  sm_count=halves*nsm, commands_per_half=256, command_bits=64,
  macs_per_cycle=0, compute_intensity=0, memory_bytes_per_cycle={'command_write':16,'host_record':hrw/8},
  boundary_bits_per_cycle={'host_record':hrw,'sm_launch':32+2*(32+tw+pw),'sm_completion':32*35,'producer_owner':2*(tw+pw+36)},
  mux_cost='two equal-token completion sources plus checked job/position/generation',
  fanout='16 launches per actual CP half; host record posted by owner die only',
  routing_tracks_required=hrw+32+2*(32+tw+pw)+32*35+2*(tw+pw+36),
  channel_capacity='pending actual CP boundary sheet',
  area={'command_storage_bits':2*256*64,'host_fifo_bits':8*hrw,'identity_bits':36,
        'floorplan_fit':'pending native CP/token-loop slot'},
  clock_mhz=1200, added_ar_latency_cycles=0,
  token_turnaround_cycles=4, mux_completion_latency_cycles=0,
  qualification='unqualified until real CP slot/budget, exact RTL gates, TT setup/FF hold/DRC0 and SS sensitivity',
  mtp_integration='separate native commit adapter required; no speculative claim')
