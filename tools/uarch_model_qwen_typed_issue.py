"""Actual SROW-to-PHY issue metadata, sized before RTL; no inferred class alias."""
def model():
    entries=4;packet=330;state=entries*packet+32*19+32+2+2+3+3+1
    return dict(schema='opentallas.qwen-typed-native-issue.v1',default_off=True,
      macs_per_cycle=0,replicas=128,state_bits=state,
      cell_area_bound_um2=state*.2916+1800,slot_um=[96.768,96.768],
      memory_ports=[dict(name='plain_typed_pending_flop_fifo',depth=entries,
        write_bytes_cycle=packet/8,read_bytes_cycle=packet/8)],
      boundary_bits_per_cycle=dict(request=331,native_static_cmd=31,
      PHY_issue=331,row_command=28,column_command=13),
      replicas_cost=dict(read_mux='4:1 x330bit',write_demux='4entry enables',
      physical_open_rows='32 x19bit actual ACT-row capture, one plain copy',
      fanout='localPC controller+PHY only',control_mirrors=0),
      flow=dict(prepaid_entries=4,release='one actual static col issue, not request acceptance',
      physical_capacity='provider reserves actualPHY request/return capacity before enqueue',
      descriptor_fence='queue empty AND provider actual return/write visibility drain'),
      latency=dict(added_edges_vs_native_ctrl_outputs=0,
      controller_static_input_edges=2,hclk_period_ps=1024,
      interface_timing='co-located comparison/readmux must physically close; no STA claim'),
      remaining=['typed producer phase wire boundary',
      'actuallogicalm_p2l walker/GO instead implicitnativeRD',
      'runtimefullsector write staging plus truepairedvisibility',
      '32PC shared row-slot TDM/nativePHY endpoint composition'])
