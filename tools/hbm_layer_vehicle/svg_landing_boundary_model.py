"""Opt-in native landing pin boundary, committed before RTL. No timing claim."""
def model():
    return dict(schema="opentallas.svg-landing-boundary.v1", opt_in_default=False,
      roots=["hbm_clk", "stream_clk"], reset_release_edges_per_root=2,
      elastic_ingress=dict(slots=2,bits=855,storage="two-slot ring plus one pin-capture register; below 2kb",
        ready_rule="ready_next=(reserved+push-pop)<2; push=in_v&&registered_ready",
        invariant="registered_ready == (reserved<2) after every active edge; 0<=reserved<=2; reserved=queued+pin_pending",
        stalled_release="full queue bubbles one edge when core first drains; no loss, no SM credits",
        sustained="one word/HBM edge when core ready; FIFO/SM schedule unchanged"),
      added_latency=dict(ingress_min_HBM_edges=2,ingress_max_when_core_stalled="unbounded by protocol; bounded by producer obeying ready",
        reserve_stream_edges=1, stop_stream_edges=1, read_stream_edges=2,
        complete_stream_edges=0,
        complete_explanation="old combin completion sampled at edge E; new pin register publishes immediately after same E",
        fault_stream_edges=1,overflow_HBM_edges=1,
        schedule="reserve/stop one stream edge earlier; read requests two stream edges earlier; HBM prefetch two HBM edges earlier plus CDC phase rounding"),
      fanout=dict(segment_bits=16,segments=18,kept_hierarchical_pointer_copies=True,
        mapped_audit_required=True),
      qualification="Analytical admission proof only; actual macro bench and mutations required; inherited core fanout still needs mapped audit")
