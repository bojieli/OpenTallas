"""Pre-build sizing of source-owned HBM service write completions."""
def model(stages=2):
 return dict(default_enabled=False,macs_per_cycle=0,memory_bytes_per_cycle=32,
  new_boundary_bits_per_cycle=2+16,replicas=4,
  added_source_register_bits=2*(8+stages+3),
  ledger_slots_per_pc=8,ledger_pc_count=32,ledger_owner_bits=512,
  routing_tracks_added=18,required_channel_capacity_added_tracks=18,
  floorplan_slot='existing svc WB collar; slot fit must be checked after synthesis',
  added_token_cycles_fault_free=0,added_ack_latency_cycles=2,
  mux_cost='owner2 follows exact WB data path; three independent Gray ACK queues',
  fanout='per-PC ledger readiness gates write issue only; ack counter updates localized',
  clock_period_ps=1024,physical_signoff=False)
