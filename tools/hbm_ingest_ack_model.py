"""Functional accepted-order ACK prefix, sized before successor RTL."""
def model():
 npc,depth,sources=32,8,3
 window=npc*depth
 return dict(schema='opentallas.hbm-ingest-ordered-ack.v1',npc=npc,per_pc_depth=depth,sources=sources,
  source_bits=2,ordinal_bits=8,source_fifo_bits=window*10,pc_pointer_count_bits=npc*10,
  completion_bits=sources*window,source_counter_bits=sources*(8+8+9),storage_bits=3723,
  area_lower_bound_um2=3723*0.37908,macs_per_cycle=0,issue_bytes_per_cycle=32,
  accepted_writes_per_cycle=1,retire_per_source_per_cycle=1,
  boundary_bits=149,replicas_per_die=4,mux_count=3,mux_inputs=256,
  routing_tracks_required=149,routing_capacity_tracks=None,slot_fit=None,
  physical_status='pending source-matched component gate and consuming service placement, no new standalone route requested',
  latency=dict(in_order_ack_added_cycles=0,out_of_order_ack_prefix_wait_max_cycles=255,
   extra_state='source FIFO ordinal and completed-prefix flags only; no leases/apertures/ECC/parity/mirrors'),
  rate_credit=0,adopted=False)
