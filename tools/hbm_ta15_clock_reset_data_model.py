"""Before-build opt-in TA15 DATA reset-intent boundary, not PLL qualification."""


def model():
    periods = dict(stream=5/6, serial=10/9, hbm=1.024, link=5/6)
    return dict(schema='opentallas.uarch.hbm_ta15_clock_reset_data.v1',
        default_enable=False, MACs_per_cycle=0, compute_intensity=0,
        communication_intensity=0, memory_port_bytes_per_cycle=0,
        replica_count=1, replica_mux_demux_cost=0,
        boundary_bits_per_cycle=dict(clocks=5, intent=17, raw_lock=1,
            cold_POR=1, sequence_ready=1, reset_outputs=17, ready_AON=1),
        forward_FF_bits=51, return_FF_bits=34, registered_ready_FF_bits=1,
        boundary_FF_bits=86, sequencer_FF_bits=38, composed_FF_bits=124,
        boundary_FF_area_floor_um2=86*.2916,
        composed_FF_area_floor_um2=124*.2916,
        forward='Two positive-edge DATA sampling FFs then negative-edge reset output; boot intent never drives an asynchronous reset pin',
        return_path='Each actual reset output crosses through two AON DATA FFs; registered ready requires all returned levels and held AON sequence_ready',
        period_ns=periods,
        forward_latency_domain_cycles=dict(minimum=1.5, maximum=2.5),
        forward_maximum_ns={k:2.5*v for k,v in periods.items()},
        return_ready_maximum_AON_cycles=3,
        source_sequence_ready_to_ready_AON_cycles=1,
        cold_assertion='Asynchronous cold POR assertion only; source assertion network delay remains unmeasured',
        steady_state_added_data_cycles=0,
        latency_contribution='Boot/runtime intent response up to 2.5 destination cycles; qualified ready return up to 3 AON cycles. AON period, analog acquisition and metastability-tail probability are unresolved terms, not zero.',
        routing_tracks_needed=dict(clock=5, intent=17, cold_reset=1,
            lock=1, local_reset=17, return_status=17, source_ready=1),
        channel_capacity=None, floorplan_slot_fit=False,
        analog_PLL_area_um2=None, analog_PLL_power_W=None,
        analog_PLL_startup_ns=None, AON_period_ns=None,
        platform_contract_required=[
            'Cold POR release satisfies recovery/removal at first positive AND negative PLL edges and first AON edge; only startup contract, no runtime clock gating',
            'First forward and return DATA FF metastability tau/T0 and required system MTBF at actual destination clocks, data toggle rate, PVT, resolution path and load',
            'AON intents are held levels; brief pulses are unsupported',
            'PLL lock loss either asserts cold POR through qualified emergency source or leaves all clocks valid for maximum 2.5-cycle sampled assertion plus implementation delay',
            'Actual source slew, load, insertion, jitter, phase, sink recovery/removal and reset-tree obligations'
        ],
        STA_policy='No false paths, CDC timing waivers, invented phase or first-stage deterministic setup/hold claim. Retain first CDC failures and separately characterize asynchronous capture; downstream paths require ordinary SS/FF checks.',
        physical_closed=False, CDC_characterized=False, PLL_qualified=False)
