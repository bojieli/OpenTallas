"""Before-build digital boundary sizing; analog PLL remains unqualified."""
DFF_UM2 = 0.2916

def hbm_ta15_clock_boundary_model(link_ports=9, stages=3):
    """TA15 analog PLL contract and per-endpoint digital reset-release sizing.

    Before-build analytical sizing only: analog area/startup and parent clock
    insertion are missing obligations, not zero-cost timing assumptions.
    """
    if link_ports < 1 or stages < 2:
        raise ValueError('positive link count and at least two release stages required')
    collars = 4 + link_ports + 4
    periods = dict(stream=5/6, serial=10/9, hbm=1.024, link=5/6)
    return dict(schema='opentallas.uarch.hbm_ta15_clock_boundary.v1',
        MACs_per_cycle=0, compute_intensity=0, communication_intensity=0,
        memory_port_bytes_per_cycle=0, replica_count=1,
        boundary_bits_per_cycle=dict(reference_clocks=1, generated_clocks=4,
            reset_intents=link_ports+8, lock_status=1, endpoint_resets=collars),
        reset_collar_count=collars, state_FF_bits=collars*stages,
        FF_area_floor_um2=collars*stages*DFF_UM2,
        replica_mux_demux_cost=0, per_collar_assert_inputs=3,
        period_ns=periods, reset_release_edges=stages,
        release_time_ns={k:stages*v for k,v in periods.items()},
        steady_state_added_data_cycles=0,
        latency_contribution='Three destination edges after each qualified boot intent; no decode data stages. Analog lock-acquisition and boot sequencer latency remain explicit unknown terms.',
        routing_tracks_needed=dict(clocks=5, status=1,
            reset_intents=link_ports+8, endpoint_resets=collars),
        channel_capacity=None, floorplan_slot_fit=False,
        analog_PLL_area_um2=None, analog_PLL_power_W=None,
        analog_PLL_lock_acquisition_ns=None, source_jitter_ps=None,
        clock_insertion_and_skew_ps=None,
        protection='POR, raw lock loss, or sequencer intent loss asynchronously assert destination reset; release uses three real destination edges. Existing AON sequencer owns boot ordering.',
        physical_closed=False, analog_PLL_qualified=False,
        adoption='Digital boundary candidate only; vendor characterized macro, real parent CTS/reset recovery/removal, and endpoint pin binding required')


