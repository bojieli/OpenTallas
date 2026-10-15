"""Analytical actual small-group static VM transport, immutable prices untouched."""
def model():
    q, bridge = 32, 16
    q_ff, bridge_ff = 1312, 2620
    return dict(schema='opentallas.s81.static-vm-small-transport.v1',
        source='cd1242953', macs_per_cycle=0,
        bank_macros=128, logical_rows_512bit=16384, capacity_bytes=1048576,
        hierarchy=dict(slices=4,banks_per_slice=32,quarters_b4=q,bridges_b8=bridge,
                       fsr=4,write_scatter=4,return32=4,core_hard_children=188),
        core_clock_roots=dict(bank=128,quarter_request=32,quarter_response=32,
                              bridge_request=16,bridge_response=16,fsr=4,write_scatter=4,return32=4,total=236),
        relay_mapped_flops=q*q_ff+bridge*bridge_ff,
        relay_data_and_valid_flops=83712, relay_reset_release_flops=192,
        relay_mapped_cell_area_um2=q*441.71568+bridge*881.74008,
        relay_pin_bound_footprint_um2=q*129.6**2+bridge*172.8**2,
        maximum_mapped_relay_clock_root_sinks=1346,
        replica_mux_cost='no arbitration or data mux added; same two registered request and response stages; split shared reset synchronisers add96FF vs old groups',
        request_bits_per_bank=168,response_bits_per_bank=159,
        physical_read_row_ports=32,physical_write_row_ports=32,
        physical_peak_memory_bytes_per_stream_cycle_each_direction=2048,
        source_row_writes=53,
        schedule='compiler-fixed bank reservations and <=3samebank capture lanes; steady drain <=32rows/cycle, no ready/credit or variable delay',
        functional_ages=dict(read_pin=12,command_done_pin=6,returned_commit_observation_lane0=11,
                             raw_macro_visibility='not inferred from returnedcommit; separate actualw_ce witness and physical phase required'),
        geometry=dict(native_pin_pitch_um=.096,native_layers='M5 N/S, M4 W/E',
                      local_signal_bits_screened=83712,worst_local_signal_manhattan_um=486.3,
                      required_global_endpoint_distribution='UNPROVEN; real sourcepin/clock/cut and fixedhopcount join needed'),
        qualification='component numerical/fixed-age proof plus local pin geometry only; nativeCTS/TTFFDRC, global endpoint fanout and cap/edge packing OPEN',
        price_policy='immutable prices unchanged; no measured token-rate or full-die area claim')

if __name__=='__main__':
    import json
    print(json.dumps(model(),indent=2))


def write_scatter_pin_stage_model(write_pipeline=0):
    """Explicit source-pin calendar for the opt-in cb4 scatter input stage.

    Current production write-front version remains separately source-bound. These
    ages apply to its existing full-core P+11 commit observation; they do not
    adopt the independently developed P+6 write-front successor.
    """
    if write_pipeline not in (0, 1):
        raise ValueError("WSCATTER_PIPE must be 0 or 1")
    return dict(write_scatter_pipeline=write_pipeline,
                source_pin_to_returned_commit_edges=11+write_pipeline,
                source_pin_to_actual_SRAM_write_edges=9+write_pipeline,
                actual_SRAM_write_to_returned_commit_edges=2,
                added_write_visibility_edges=write_pipeline,
                write_ii_edges=1, replicas=16,
                source_added_pin_flops_per_scatter=1248*write_pipeline,
                source_added_pin_flops_total=16*1248*write_pipeline,
                measured_gate_sinks_baseline=1219, measured_gate_sinks_staged=2467,
                visibility_proofs=["results/rtl/s81_vm_master_reset_20261015/record.json",
                                   "results/rtl/s81_vm_scatter_pipe1_raw_20261015/record.json"],
                whole_token_cost=None,
                qualification="opt-in candidate; real128SRAM exact edges/mutants and current producer/compiler/physical joins required")
