"""Sized before RTL: registered control/store faces for actual static endpoint."""
def model():
 return dict(payload_bits=545,sequence_bits=16,wire_bits=612,transport_frame_bits=613,
  storage_banks=4,storage_leaf_bits=141,native_sram_bits=64*512,
  state_capture_flops_per_bank=154,controller_launch_flops=577,
  controller_command_delay_edges=2,read_to_tx_edges=5,rx_edges=1,
  read_edge='n: launch; n+1: capture; n+2: macro read; n+3: store dout; n+4: q_pin; n+5: TX',
  sram_write_edge='n+3 from reservation; native captured write bypass retained',
  transport_acceptance='A(j)=17+floor(613*j/487); read A-6; write A-10',
  transport_receive='capture23+lastwordindex; publish24+lastwordindex',
  bits_per_cycle_per_store_boundary=154,channel_capacity_tracks=None,
  logical_flit_face_peak_bytes_per_cycle=545/8,
  actual_transport_application_bytes_per_cycle=(512/8)*(487/613),
  actual_transport_including_metadata_bytes_per_cycle=(545/8)*(487/613),macs_per_cycle=0,replicas=4,
  controller_clock_sinks_upper_bound=4000,state_clock_sinks_upper_bound=1000,
  area_slot_fit='native64x512 unchanged; leaf outline/physical path proof pending',
  slot_reuse='samephysical64 slots; nativeownershipguard delayed2 withcommands',
  status='SIZED; added2TXedges fullypriced; no physical qualification yet')
if __name__=='__main__':
 import json
 print(json.dumps(model(),indent=2))
