#!/usr/bin/env python3
"""Pre-RTL sizing of the additive HBM fused-SU stream endpoint.

These are architectural bounds, never a measured or adoption verdict. Existing
FP engines retain their own arithmetic and storage; the wrapper adds transport,
transaction counters and a reservation handshake with the real VM writer.
"""
import json


def model():
    rows = []
    for kind, n, d, rd, core, baseline in (
        ("hc_norm", 1024, 5120, 0, 222, 487),
        ("q_norm", 256, 1280, 0, 196, None),
        ("kv_norm", 512, 512, 64, 191, None),
        ("swiglu", 1024, 1024, 0, 119, None),
        ("hc_post", 1024, 5120, 0, 43, None),
    ):
        nv = (d + n - 1) // n
        # hc_post groups process N/4 elements/beat and emit four rows.
        beats = (4 * d + n - 1) // n if kind == "hc_post" else nv
        gain_beats = nv if kind.endswith("norm") else 0
        events = nv * (2 + bool(rd)) if gain_beats else beats
        input_bits = (4*n if kind == "hc_norm" else
                      5*n//4 if kind == "hc_post" else
                      3*n if kind == "swiglu" else n) * 32
        # norm publishes y, optional ro, and quant payload as distinct events.
        payload_bits = n*32 + n*8 + (n//32)*10 + n*16 + 10
        config_bits = 512 + 128 + 32*3 + max(1, rd//2)*64
        endpoint_ff = 7*(4*n*32) + 8*(payload_bits+n*32) + config_bits + 137
        rows.append(dict(kind=kind, lanes=n, dimension=d, rope_tail=rd,
            replicas=1, input_beats=beats, cold_gain_load_beats=gain_beats,
            reserved_output_events=events if kind!="swiglu" else 2*events, BCAST=7, RET=8, RW=9, BW=9,
            clock_hz_target=1200000000, clock_qualified=False,
            existing_standalone_core_and_input_stream_cycles_ESTIMATE=core,
            warm_endpoint_cycles_ESTIMATE=core+15,
            core_estimate_basis="retained LM5/LA4 standalone; LM6/LA5 extra stages NOT yet measured",
            cold_endpoint_cycles_ESTIMATE=core+15+gain_beats+2,
            baseline_generic_cycles_at_900MHz=baseline,
            VM_read_bytes_per_edge=input_bits//8,
            CR_gain_read_bytes_per_edge=n*4 if gain_beats else 0,
            VM_output_boundary_bits_per_edge=payload_bits,
            quant_boundary_bits_per_edge=n*8+(n//32)*10+n*16,
            reservation_count_bits=16, output_queue_words=0,
            VM_adapter_descriptor_FF_bits_ESTIMATE=5*24+32+config_bits+3+16+2+8+8+2,
            VM_adapter_added_read_ports=0, VM_adapter_added_write_ports=0,
            memory_response_latency_edges=1,
            SwiGLU_partial32_quant_allowed=False,
            output_backpressure="whole command reservation before dispatch; real writer accepts every event",
            MACs_per_cycle_added=0, existing_engine_arithmetic_unchanged=True,
            compute_intensity="reuse selected engine; no added MACs",
            endpoint_register_bits_upper_bound_ESTIMATE=endpoint_ff,
            endpoint_DFF_area_upper_bound_um2_ESTIMATE=endpoint_ff*.2916,
            gain_storage_reused_from_norm=True,
            input_source_mux_clients=1, parent_output_mux_clients=4,
            parent_mux_area_um2=None, clock_fanout_cost_um2=None,
            route_tracks_required_lower_bound=input_bits+payload_bits,
            corridor_available_tracks=None, floorplan_slot_fit=None,
            serial_critical_path_measured_us=None, CDC_refresh_credit_cost_measured_us=None,
            composed_token_delta_us=None, composed_rate_gain_percent=None,
            physical_matching_context=None, SS60_FF25_qualified=False,
            adopted=False))
    return dict(schema="opentallas.hbm-su-fused.price.v1", default_enabled=False,
        scope="new command/stream endpoint, not a replacement die floorplan",
        primitive_owner="Nash", fusion_owner="Einstein", composition_owner="Maxwell",
        reference_HC_norm_occurrences_P1=81,
        HC_norm_only_optimistic_token_saving_us_ESTIMATE=81*(487/.9-244/1.2)/1000,
        reference_count_source="matched_reference fused.json: 80 HC pre + one head",
        tau="external composition owner default; runtime/compiler have no tau",
        hc_post_ML=5, hc_post_AL=4, norm_swiglu_LM=6, norm_swiglu_LA=5,
        clock_domain="same SU clock; no new CDC claimed; parent availability/CDC stays exposed",
        per_position_replicas=1, P6_measured=False, rows=rows,
        adoption_gate="actual exact1M + measured critical path + area/corridor + contextual SS60/FF25 + composed gain>=1%",
        unknowns_are_ESTIMATE=True)


def command_bridge_model():
    """Price the missing scalar producer/held command, before adding hardware.

    Existing VM has four N1024 read planes. The proposal reserves one plane's
    first 20 word lanes for config, and reuses it after capture. No extra port
    or payload CDC is assumed; actual parent arbiter is not yet identified.
    """
    records=[]
    for kind, words in (("hc_norm",4),("q_norm",0),("kv_norm",0),
                       ("swiglu",1),("hc_post",20)):
        held_bits=32+5*24+words*32+3*32+3+16+16+8
        records.append(dict(kind=kind,producer_VM_words=words,
            producer_VM_bytes=words*4,producer_read_bits_per_edge=words*32,
            producer_max_read_planes=1 if words else 0,new_memory_ports=0,
            read_request_edges=1 if words else 0,read_response_capture_edges=1 if words else 0,
            command_handoff_edges_ESTIMATE=1,
            added_edges_after_operand_availability_ESTIMATE=(2 if words else 0)+1,
            descriptor_and_scalar_hold_FF_bits_ESTIMATE=held_bits,
            descriptor_DFF_area_floor_um2_ESTIMATE=held_bits*.2916,
            arbiter_clients=2,read_address_mux_bits=4*1024*24,
            read_source_mux_bits=4*1024*2,read_enable_mux_bits=4*1024,
            write_address_mux_bits=1024*24,write_data_mux_bits=1024*32,
            write_enable_mux_bits=1024,read_return_demux_bits=4*1024*32,
            read_mux_area_um2=None,write_mux_area_um2=None,
            command_ready_fanout_cost_um2=None,clock_tree_cost_um2=None,
            boundary_min_payload_tracks=words*32,corridor_capacity=None,
            parent_slot_fit=None,wire_CDC_credit_refresh_exposure_measured_us=None,
            full_program_composed_delta_us=None,replicas=1,added_MACs_per_cycle=0,
            input_availability='actual source producer completes before command read; upstream not hidden',
            lease='exclusive VM ownership held until actual writes and producer/read debt drain',
            numerical_contract='raw VM bits; no scalar arithmetic/reassociation',
            physical_qualified=False,adopted=False))
    return dict(schema='opentallas.hbm-su-command-bridge.price.v1',default_enabled=False,
        actual_parent_issuer_arbiter_source=None,
        existing_execution_hook='dshbm_baseline_measure.cmd_su_run -> rtl_hdc_v41x_vec_campaign.run_program',
        existing_hook_scope='whole-program native bench plus CPU reference; not hardware issuer',
        concrete_blocker='shared VM issuer/arbiter lease transfer between VEC and fused path not identified',
        no_new_hardware_written=True,rows=records,estimates_not_results=True)


if __name__ == "__main__":
    print(json.dumps(model(), indent=2))
