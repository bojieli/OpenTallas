"""Additive native checked-CPRESULT producer boundary, before build/route."""
def model():
 return dict(schema='opentallas.hbm.native_mtp_cp_result.model.v1',default_enabled=False,
  macs_per_cycle=0,compute_intensity=0,memory_bytes_per_cycle={'checked_result_input':17/8},
  boundary_bits_per_cycle={'new_cp_result':18,'cp_to_native_facade':197,'native_to_cp_facade':517},
  routing_tracks_required=732,channel_capacity='new native197/517 physicalmaster pending',replicas_per_die=1,
  mux_cost='elaboration-selected argmax producer; no token→logit conversion',fanout='one nativecontroller accept observation',
  area={'added_input_pin_registers':18,'local_argmax':'inactive when EXTERNAL_AM=1; no measured area saving credited','floorplan':'candidate native466.56x200.88 requires actualnewclosure'},
  clock_mhz=1200,added_latency_cycles={'checkedCPRESULT_pin_capture':1},
  composition='each realCPhead/Markov result enters nativecontroller1cycle after pin; command done independently waits allresult rows',
  obligations=['actualowned CPRESULT only','no simultaneous rawlogit producer','new197/517facade/pins','TTsetup/FFhold/DRC0; SS sensitivity'])
