"""Before-build model: loader core on a real external clock, finite CDC faces."""
def model(nd=2, aw=3):
    widths=[12,36,1,12,32,12,36,1,12,32,64,67,64,72,2,75,67,75,73,2]+[337,273]*nd
    return dict(schema='opentallas.loader_cx.v1',default_enabled=False,adopted=False,
      source_core='ot_hfd_loader_host_m unchanged',ND=nd,ADDR_W=32,
      scope='Historical full loader envelope structural alternative; not selected ND1/ADDR37 native facade',
      clocks_ns=dict(host=5/6,memory=5/6,core=5/3),
      actual_clock_requirement='External real PLL/clock-distribution core clock; no latch gate, generated divider or timing-only slowdown',
      MACs_per_cycle=0,replicas=dict(core=1,channels=len(widths)),
      FIFO_depth=1<<aw,payload_bits=sum(widths)*(1<<aw),
      pointer_and_sync_bits_upper=len(widths)*12*(aw+1),
      FIFO_DFF_area_floor_um2=sum(widths)*(1<<aw)*.2916,
      boundary_bits_per_cycle=dict(core_payload_sum=sum(widths),native_request=337*nd,native_response=273*nd),
      mux_demux='Same finite Gray-pointer channels as approved divider adapter; no new arbitration or replicas',
      memory_bytes_per_core_cycle=32*nd,per_die_payload_GBps=32/(5/3),
      tracks=dict(extra_clock_pins=1,host_memory_channels='existing faces; exact pin load and slot must be measured'),
      area='Existing loader slot retained as candidate; full mapped core plus channel storage fit requires measured synthesis',
      latency=dict(channel_visibility_destination_edges='2..3',round_trip_slow_edges='4..6 plus core service',steady_token_cycles=0),
      arithmetic='Unchanged pipelined CRC folds and data path; transaction-stream/CSR golden comparison mandatory',
      mutable_storage_protection='Inherited FIFO/loader source only; no reliability qualification inferred',
      physical='Standalone pathfinding pending actual clock source, loaded pin budgets and corner timing; no exceptions added')


def reset_partition_model(nd=2):
    m=model(nd=nd)
    m['schema']='opentallas.loader_cx_local_reset.v1'
    m['reset_partition']=dict(local_release_buckets_per_loader=5,replicas=5*nd,
      storage_bits=5*nd,area_floor_um2=5*nd*.2916,
      source_fanout='Existing per-engine reset synchronizer drives three host and two memory local release leaves instead of the engine endpoint reset pin cloud',
      endpoint_fanout='One actual retained local leaf per independent sequential process; leaf clock and endpoint clock identical',
      release_added_destination_cycles=1,release_latency_max_ns=5/3,
      steady_token_cycles=0,transactions='Source channel FIFOs remain finite and hold descriptors until locally reset control accepts; no payload or numerical changes',
      required_mapping='Preserve distinct ot_hfd_loader_reset_leaf instances; inspect mapped leaf clocks/reset endpoint groups before physical adoption',
      physical='Placement/fanout measured path required; added reset FF is not itself signoff')
    return m
