"""Owner-selected native command state; no control mirrors or IDs."""
def model():
    state=30+1+1+4+3+32+1+3+1
    return dict(schema='opentallas.qwen-native-cmd-plain.v1',default_off=True,
      macs_per_cycle=0,replicas=128,state_bits=state,cell_area_bound_um2=state*.2916+800,
      memory_ports=[],boundary_bits_per_cycle=dict(cmd=33,read_credit=3,
      descriptor=31,write=11,actual_retirement_fences=3),
      flow=dict(native_cmd_entries=8,pending_descriptor=1,pending_GO=1,
      descriptor_replacement='actual window retirement AND write/transport drain'),
      replicas_cost=dict(control_copies=1,comparators='legal descriptor count0..1024,orphanGO,duplicatecredit',
      read_mux='oneDESC/GO/WR command selector',fanout='localPC nativeFIFO only'),
      slot_um=[96.768,96.768],latency=dict(command_capture_hclk_edges=1,
      read_credit_capture_hclk_edges=1,hclk_period_ps=1024),
      remaining=['actualcore descriptor mailbox and drain binding','typed extraECCphysicalaccess scheduling'])
