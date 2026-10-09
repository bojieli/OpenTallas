"""Before-build sizing of real boot quiescence and reset-release commit."""

def model():
    return dict(schema='opentallas.hbm_quiescent_reset.v1',adopted=False,default_enabled=False,
      mechanism='Stop four real domain clocks; observe held-low acknowledgments; commit17 resetlevels; wait2AON edges; permit three-falling-edge safe restart; sample actual gate-active before ready.',
      periods_ns=dict(aon_provisional=3,stream=5/6,serial=10/9,hbm=1.024,link=5/6),
      replicas=dict(AON_controller=1,domain_gate=4,endpoint_resets=17),
      compute=dict(MACs_per_cycle=0,memory_bytes_per_cycle=0),
      state_bits=dict(sequencer_status_and_state=38,commit_and_pending=34,
        quiet_ack_meta_sync=8,phase=2,guard_counter=2,permit=1,fault=1,
        falling_edge_gates=12,total=98),
      FF_area_floor_um2=98*.2916,extra_FF_vs91=7,extra_FF_area_floor_um2=7*.2916,
      standalone_controller_slot_um=[100.224,99.36],
      gate_slot_um_per_domain=[25.92,25.92],
      tracks=dict(desired_reset=17,actual_reset=17,quiet_ack=4,permit=4,raw_qualification=1),
      boot_latency=dict(stop_max_root_edges=3,quiet_observation_AON_edges=2,
        commit_guard_AON_edges=2,start_root_falling_edges=3,active_observation_AON_edges=2,
        minimum_reset_release_to_first_destination_edge_ns={k:6+2.5*p for k,p in
          dict(stream=5/6,serial=10/9,hbm=1.024,link=5/6).items()}),
      latency_composition='Paid on reset-intent changes during boot or fault/requalification only; ordinary token pipeline adds0cycles. BIST/provider/PLL acquisition remains external and unmeasured.',
      protection='Raw POR/PLL-reset/lock/fatal qualification immediately asserts all endpoint resets; asynchronous deassert is permitted only after actual clock-low acknowledgment. Clock producer gates use three retained falling-edge FFs without asynchronous reset pins.',
      physical='Controller and gate candidates need review and standalone characterization; whole-die CTS, gate first-stage metastability, source jitter and actual reset pin recovery/removal are unqualified. No timing exceptions or constant acknowledgments.',
      actual_source_requirements=['Always-running actual PLL roots once locked',
        'Literal gate quiet acknowledgment iff its real output is held low',
        'Consumer reset deassert only under that held-low interval',
        'First root request/ack synchronizer technology metastability qualification',
        'Actual startup quiet interval and post-reset recovery/removal at every endpoint'])
