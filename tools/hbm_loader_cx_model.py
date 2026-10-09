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
