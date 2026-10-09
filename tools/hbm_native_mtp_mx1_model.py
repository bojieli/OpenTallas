"""Owner-confirmed MX1 correction: drained reset, plain control flops."""
def model():
 return dict(schema='opentallas.hbm.native_mtp_mx1.model.v1',default_enabled=False,macs_per_cycle=0,
  compute_intensity=0,memory_bytes_per_cycle={'flop_PC_template_read':8,'CP_command_each_half':8,'host_queue_each_port':73/8},
  boundary_bits_per_cycle={'native_request':201+32+4+32,'native_completion_identity':32+4+32,'native_AM_result':18,'host_record':73},
  routing_tracks_required=1631,channel_capacity='Claude physicalintake sole route owner; actual pin geometry pending',replicas_per_die=1,
  mux_cost='11-entry plainflop PC table; finite35-launch cursor; two16SM CPs; eight-entry host FIFO',fanout='actual32SM launch/result ports',
  area={'backend_flop_bits':1168,'each_CP_flop_bits':483,'backend_total_flop_bits':2134,'host_payload_flop_bits':584,'control_ECC_bits':0,'control_mirrors':0,'reset_epoch_bits':0},
  latency_cycles={'ordered_control_overhead_per_launch':9,'native_AM_pin_capture':1,'native_completion_ack':1},
  reset='MX1 only: actual controller/backend/CP/results/hostqueue drained before coordinated reset, no job acceptance during reset',
  arithmetic='actual sourceordered sixop lowering; eleven production kernelimages remain explicit pending',
  protection='SRAM/HBM payload SECDED remains required; control storage here isflops and hasnone',
  obligations=['same-source minimum composedbench and mutant PASS','Claude approval and dedupedphys-intake before routing','real11kernel sourceimages/numerics','actual32SM drain/reset'])
