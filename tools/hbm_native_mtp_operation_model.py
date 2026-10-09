"""Full native operation lowering, before implementation/physical admission."""
def model():
 return dict(schema='opentallas.hbm.native_mtp_operation.model.v1',default_enabled=False,
  macs_per_cycle=0,compute_intensity=0,memory_bytes_per_cycle={'template':8,'command_install_each_half':8},
  boundary_bits_per_cycle={'native_command_with_identity':277,'real32SM_launch':32+64+34+40+146,'real32SM_result':1024+96},
  routing_tracks_required=1639,channel_capacity='fresh nativeCPsouth slot/pin pricing pending',replicas_per_die=1,
  mux_cost='11-entry protectedPC table plus finite35-launch cursor; twoactual16SM CP halves',fanout='selected16SM masks perhalf',
  area={'template_bits':11*72,'captured_command_bits':5*72,'protected_CP_command_bits':2*2*72,'CP_replica_count':2},
  clock_mhz=1200,latency_cycles={'template_launch_install_and_CP_dispatch_upper':8,'command_capture':1,'native_completion_ack':1},
  fullshape_launch_counts={'VLAYER0_max6cols':24,'VLAYER_other_max6cols':18,'VHEAD_max6cols':12,'SEED_max6cols':6,'DSTAGE0_block5':35,'DSTAGE_other_block5':30,'DHEAD_block5':10,'MARKOV_one':1},
  composition='sum real perkernel cycles plus ordered dispatch overhead; sequential sourceexpansion does not claim verify weightreuse',
  obligations=['source-produced fullshape elevenkernel entry PCs/images','real32SM completion/result bindings','reset quiescence/persistentepoch','fullcontrollerstate protection','TTsetup/FFhold/DRC0; SS sensitivity'])
