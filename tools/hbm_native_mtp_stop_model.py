"""Pre-build model for a native stop-aware MTP controller successor."""
def model(tw=17):
 return dict(schema='opentallas.hbm.native_mtp_stop.model.v1',default_enabled=False,
  max_context_positions=1048576,position_bits=20,count_bits=21,forced_draft_address_bits=23,
  max_gamma=5,max_verify_columns=6,macs_per_cycle=0,compute_intensity=0,
  memory_bytes_per_cycle={'token_history_write':tw/8,'accepted_output':tw/8},
  boundary_bits_per_cycle={'token_output':tw+20+2,'token_history':tw+32+1,'commit':33},
  routing_tracks_required=2*tw+109,channel_capacity='nativeMTP slot/CP boundary requalification pending',
  replicas_per_die=1,mux_cost='selected accepted prefix token plus registered EOS and length decision',
  fanout='local controller; acceptance emitted prefix used by commit and next-pending token',
  area={'register_delta_upper_bits':160,'floorplan':'existing MTP466.56x200.88 slot requires new measured fit'},
  clock_mhz=1200,added_token_cycles={'each emitted token':1,'prefill output':1,'max verify batch':6},
  model_composition='add one output-ack cycle per emitted token; stalls priced from actual e_ready',
  correctness='stop-aware golden mirror required; historical generate_spec commits full accepted batch before slicing output',
  obligations=['actual hfd_mtp_x native20-bit port binding','finite accepted-output sink','TT setup/FF hold/DRC0; SS sensitivity','no stale speculative state beyond effective prefix'])
