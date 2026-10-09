"""Path-informed collective capture partitioning before RTL (-cx)."""
def model():
    n=4;word=546;slices=(word+31)//32
    added=(slices-5)*n*8+(slices*32-word)*n*2+n*slices*32
    return dict(schema='opentallas.qwen-collective-cx.v1',default_off=True,
      arithmetic='unchanged rank-order16lane binary32 ADD_LAT7 fold',macs_per_cycle=0,
      fp32_adds_per_cycle=48,memory_ports=[dict(read_bytes_per_cycle=n*word/8,
      write_bytes_per_cycle=n*word/8,depth=32)],
      boundary_bits_per_cycle=dict(local_in=546,source_return=2184,output=512,
      native_credit=5),replicas=1,slice_count=n*slices,slice_width_bits=32,
      registered_control_fanout_per_leaf=32,control_comparators=0,
      state_bits_added=added,estimated_added_cell_um2=added*.2916,
      slot_um=[760.32,760.32],old_reservation_mm2=3.6,
      new_frame_mm2=.76032**2,max_face_density_bits_um_layer=2188/(530*2),
      latency=dict(added_cycles_vs_PR2=0,added_cycles_vs_PR1=1,
      single_user_composition='existing PR2 per-word fill edge retained; no rate credit'),
      limiting_receipt='f5c360282 actual TT hv0→128bit hdk capture -340.69ps',
      constraints=['kept data+control leaves preserve32-bit capture boundaries after synthesis',
      'existing PR2 launch/consumer retiming and actual credits unchanged',
      'actual placement and TT/FF closure required; no clock or IO budget changes'])
