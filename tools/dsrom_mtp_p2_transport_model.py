"""Exact P2 expert-return budget; individual FP32 rows retain golden id order."""
import math


def model():
    rank_width = 5120//4
    expert_bytes = rank_width*4
    flits = math.ceil(expert_bytes/64)
    return dict(
        schema='opentallas.dsrom.mtp-p2-transport.v1', adopted=False,
        source='tools/hdc_golden_v41.py dspark expert sum; released width5120 TP4',
        arithmetic='FP32 zero then each expert FP32 output in sorted expert-id order, then shared FP32, then BF16',
        shape=dict(rows_parallel=5, ranks=4, packages=20, stages=3,
                   selected_experts_per_row=3, rank_output_values=rank_width),
        MACs_per_cycle_unchanged=True, compute_intensity_unchanged=True,
        ports=dict(UCIe_bits_per_cycle=512, UCIe_bytes_per_cycle=64,
                   primary_request_BF16_vector_bytes=5120*2,
                   per_expert_return_FP32_bytes=expert_bytes,
                   per_expert_return_flits=flits),
        boundaries=dict(individual_expert_payload_bits_per_cycle=512,
                        identity_header_bits='actual transaction, position and expert-id format required'),
        replicas=dict(A_die=20, B_die=20, UCIe_pairs=20),
        mux_demux_fanout=dict(A_sorted_expert_merge_inputs=3,
                             B_return_selection_inputs=3,
                             A_adder_order='must stall until next golden expert arrives; no B pre-sum'),
        storage=dict(A_individual_expert_row_bytes_upper=3*expert_bytes,
                     B_pending_expert_row_bytes_upper=3*expert_bytes,
                     pair_row_buffer_bytes_upper=6*expert_bytes,
                     array_row_buffer_bytes_upper=20*6*expert_bytes,
                     actual_minimum_FIFO_implementation_required=True),
        routing=dict(tracks=512, channel_capacity=None),
        area=dict(buffer_macro_inventory=None, finite_merge_cell_area=None,
                  floorplan_slot_fit=False),
        stages=[dict(stage=0, B_experts=0, B_return_flits=0),
                dict(stage=1, B_experts=3, B_return_flits=3*flits),
                dict(stage=2, B_experts_range=[0,3], B_return_flits_upper=3*flits)],
        latency=dict(clock_GHz=1.2, old_summed_return_flits=flits,
                     stage1_additional_return_flits=2*flits,
                     stage2_additional_return_flits_upper=2*flits,
                     stage1_extra_serialization_us=2*flits/1200,
                     stage2_extra_serialization_us_upper=2*flits/1200,
                     critical_row_extra_serialization_us_upper=4*flits/1200,
                     multiply_by_5_parallel_rows=False,
                     headers_endpoint_credit_and_ordering_stalls_unmeasured=True,
                     historical_P2_point2us_budget_qualified=False),
        qualification='model-before-build; full-shape output ordering and finite transport gates required')


def rootpipe_model():
    """P2 rb4 sizing, written before RTL; route remains generic-IO pathfinding."""
    return dict(schema='opentallas.mtp-p2-rootpipe.v1', adopted=False,
                parent='b9e5dd224', MACs_per_cycle=0, FP32_add_lanes=16,
                arithmetic_order='+0,E0,E1,E2; unchanged FP32 rounding',
                ports_bytes_per_cycle=dict(ingress=128, output=64, SRAM_read=96, SRAM_write=96),
                boundary_bits_per_cycle=dict(ingress=1208, output=594),
                replicas=dict(accumulator_decode_stage=1, output_groups=19),
                added_storage_bits=512+3+594+19+3,
                mux_demux_fanout=dict(output_data_mux_levels=0, output_enable_fanout_max=32,
                                      output_ready_pin_fanout=2),
                routing=dict(data_tracks=512, existing_channel_tracks=548, added_external_wires=0),
                area=dict(outline_um=[560,460], added_FF_envelope_um2=1131*.6,
                          slot_fit='same 12 SRAM grid; synthesis/floorplan must confirm'),
                latency=dict(parent_cycles=5954, added_decode_cycles=240,
                             predicted_cycles_lower=6194, output_release_bubble_cycles=1,
                             output_station_capacity=1, pipeline_cycles_per_drain_word=1,
                             worst_increment_cycles=320, upper_cycles=6274),
                qualification='exact transaction bench and mutants; TT setup/FF hold/DRC gate required')
