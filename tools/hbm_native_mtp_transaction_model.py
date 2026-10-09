"""Pre-build full native MTP command ownership model; no arithmetic claim."""
def model():
 return dict(schema='opentallas.hbm.native_mtp_transaction.model.v1',default_enabled=False,
  macs_per_cycle=0,compute_intensity=0,memory_bytes_per_cycle={'command_register':201/8},
  boundary_bits_per_cycle={'native_mtp_to_cp':517,'cp_to_native_mtp':179,'backend_owned_command':201+32+4+32+8+2,'backend_completion':32+4+32+8+3},
  routing_tracks_required=1075,channel_capacity='fresh CP south boundary pin inventory pending',
  replicas_per_die=1,mux_cost='one201-bit command plus owner registers; no per-SM replication',
  fanout='one backend request owner; command list passed intact',
  area={'register_bits_upper':600,'floorplan':'fresh CP south master; original CP master unchanged'},
  clock_mhz=1200,added_latency_cycles={'native_command_accept':0,'tagged_completion_to_native_done':1},
  token_latency='one completion acknowledgement cycle per native command; actual40-layer command count measured by native controller gate',
  resource_fit='600 register bits analytical bound; actual synthesis/slot fit pending',
  obligations=['actual operation descriptor backend bind','finite e_ready token sink','persistent external epoch and reset quiescence','mutable state protection','TTsetup/FFhold/DRC0; SS sensitivity'])
