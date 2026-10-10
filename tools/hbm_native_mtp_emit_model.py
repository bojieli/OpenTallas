"""Finite native token output sink, modeled before RTL."""
def model(depth=8):
 return dict(schema='opentallas.hbm.native_mtp_emit.model.v1',default_enabled=False,macs_per_cycle=0,compute_intensity=0,
  memory_bytes_per_cycle={'queue_write':81/8,'queue_read':81/8},boundary_bits_per_cycle={'native_input':38,'host':82,'identity':44},
  routing_tracks_required=164,channel_capacity='fresh CPsouth pin inventory pending',replicas_per_die=1,
  mux_cost=f'{depth}:1 host queue mux',fanout='local eight-entry storage',area={'storage_bits':depth*81,'other_state_bits_upper':160},
  clock_mhz=1200,floorplan='fresh CPsouth, separately sized with guard',
  latency_cycles={'accepted_token_to_host_valid':1,'completion_after_last_host_pop':1},
  composition='native e_ready stops controller at full queue; final host completion waits all committed records drained',
  obligations=['actual host accept path','protected mutable state','TTsetup/FFhold/DRC0; SS sensitivity'])
