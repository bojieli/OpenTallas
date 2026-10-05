"""Pre-RTL inventory of the bounded two-segment opt2 candidate, on top of PQ.

Physical costs are explicit inventory, never a routed closure or rate credit.
This does not allocate x memory, alter arithmetic or price the entire SM twice.
"""
def model(nc=8, sub=4, ds=3, dg=3, pio=2, rmax=4096, nout=4):
    rw = (rmax - 1).bit_length()
    # SEG and FP4 per physical issue slot; registered second context, counts,
    # combined mask inputs and two-entry enqueue controls. No new multiply.
    slots = 8 * 2
    second_context = (rw + 1) + 8 + 7 + 2 + (rw + 9)
    counts = 2 * (rw + 9)
    pair_request = 2 * 32 + 2 * 4 + 3 + 1
    # Three independent metadata bits: op parity, distinct reducer key override
    # is already SW=3 in tag; carry op-local row separately, reusing existing RW.
    # A full 3-bit key must be added to the tag if the old field remains local.
    added_tag_bits = 1 + 3
    distribution = added_tag_bits * (1 + sub * ds + sub * ((nc + 3)//4) + sub * nc)
    gather = added_tag_bits * nc * sub * (1 + dg)
    combine = added_tag_bits * nc * (1 + 7 * (sub - 1).bit_length())
    stack = nc * (4 * 7 * 1 + 1)  # parity travels on four stack metadata pipes
    output = nc * 0 + 1 * (1 + pio)  # one common row/op identity at boundary
    total = slots + second_context + counts + pair_request + distribution + gather + combine + stack + output
    return dict(schema='opentallas.dshbm.wavepack.prertl.v1', default_enabled=False,
                basis='PQ opt1, main e23dd61fb; only opt2 delta',
                registers=dict(slot=slots, second_context=second_context, counts=counts,
                               pair_request=pair_request, distribution=distribution,
                               gather=gather, combine=combine, stack=stack, output=output,
                               total_incremental_bits=total),
                ports=dict(weight_response_bits=1088, request_address_bits=32,
                           reqs_per_cycle=1, x_read_ports_per_leaf=1,
                           x_write_ports_per_leaf=1, added_memory_ports=0,
                           extra_boundary_metadata_bits=1),
                clock=dict(period_ps=833.333333, ss_uncertainty_ps=60, ff_uncertainty_ps=25,
                           additional_clock_sinks=total),
                mux=dict(pair_request_address_mux_bits=32,
                         cursor_context_mux_bits=rw+1+8+7+2,
                         per_line_format_select_fanout=sub,
                         metadata_replication=sub*nc,
                         new_arithmetic_macs=0),
                memory=dict(added_macros=0, existing_x_depth=128,
                            simultaneous_contexts='explicit disjoint installed spans, refused otherwise'),
                latency=dict(chunk_revisit_edges=8, added_arithmetic_edges=0,
                             setup_edges='must be measured with production opt1',
                             target_w2_pairs=3, issue_wave_reduction=3,
                             theoretical_issue_cycles_removed=192,
                             measured_composed_ar_gain=None, measured_composed_mtp_gain=None),
                physical=dict(ff_area_um2=None, loaded_clock_cap_ff=None, track_capacity=None,
                              slot_fit=None, ss_slack_ps=None, ff_slack_ps=None,
                              required='actual mapped delta and contextual SS/FF; no free fanout/clock credit'),
                production_interface_bound=False, engine_build_admitted=False, adoption=False)


def w2_tag16_model(nout=4):
    """Priced W2-only row concatenation; older widened-tag estimate is history."""
    descriptor_bits = 13 + 13 + 7 + 7 + 7 + 32 + 32 + 1 + 1
    # a_rows,total_rows,xb_A,xb_B,delta_x,op_A,op_B,bound,pack.
    held = nout * (descriptor_bits + 1 + 3 + 4) + 2 * 2 + 3
    nand2_allowance = 600  # compare/subtract/add, 32+7-bit mux, bounds; nonzero
    buffers = 6  # positive select/control fanout allowance, no free global net
    return dict(schema='opentallas.dshbm.wavepack.tag16_model.v2', default_enabled=False,
                scope='three homogeneous FP4 W2 pairs, each A/B rows2 G2 c8',
                tag=dict(row_bits=12, group_last_bits=1, reducer_slot_bits=3,
                         total_bits=16, extra_bits=0,
                         encoding='virtual_row=Arow or rowsA+Brow; slot=virtual_row mod8'),
                source_binding='Euclid pq_production_20261005 issuer absolute xa; packed caller only',
                arithmetic=dict(new_macs=0, added_arithmetic_edges=0, chunk_revisit_edges=8,
                                golden_order_changed=False),
                control=dict(descriptor_bits=descriptor_bits, max_outstanding=nout,
                             caller_held_ff_allowance=held, mapper_ff=0,
                             retire_bitmap_bits_per_descriptor=4,
                             nand2_equivalent_allowance=nand2_allowance, buffers=buffers,
                             x_delta_precomputed='(xbB-xbA) mod128; held with descriptor',
                             completion='four distinct actual rows; duplicate fault; last-row pulse alone does not release'),
                area=dict(ff_allowance_um2=held*0.37908,
                          combinational_allowance_um2=nand2_allowance*0.08748+buffers*0.10206,
                          cell_basis='uarch_model 0.37908 reset FF allowance/0.08748 NAND2/0.10206 BUF',
                          utilisation=0.5,
                          reserved_floorplan_um2=2*(held*0.37908+nand2_allowance*0.08748+buffers*0.10206),
                          actual_slot_fit=None),
                fanout=dict(x_select_sinks=7, result_op_select_sinks=32,
                            result_row_select_sinks=12, local_control_buffer_allowance=buffers),
                boundaries=dict(added_column_tag_bits=0, extra_memory_ports=0,
                                mapper_issue_inputs_bits=13+7+1,
                                mapper_result_inputs_bits=12+1,
                                restored_identity_output_bits=32+12+1+1+1+1,
                                added_external_identity_bits=32,
                                route_tracks_lower_bound=32,
                                physical_channel_capacity=None),
                latency=dict(issue_mapper_edges=0, result_mapper_edges=0,
                             existing_s1_capture_required=True,
                             added_selector_path_requires_ss_ff=True,
                             measured_incremental_gain=None),
                clocks=dict(period_ps=833.333333, ss_uncertainty_ps=60, ff_uncertainty_ps=25,
                            caller_additional_clock_sinks=held,
                            mapper_additional_clock_sinks=0,
                            loaded_clock_capacitance=None),
                component_source_admitted=True, physical_build_admitted=False, adoption=False)


def request_join_model(dq=4, pio=2):
    # Physical bases A/B32, line count24, PAIR+bound2; queue pointers/count;
    # request offset6 and remaining24. Response ring/tag logic is unchanged.
    entry = 32+32+24+2
    queue = dq*entry + 2*(dq-1).bit_length() + dq.bit_length()
    request = 24+6
    op_hook = 8*(pio+(2*pio+3))+8
    ff = queue+request+op_hook
    logic = 1100  # two32b address adders +32b mux +FIFO selectors/bounds/control
    return dict(schema='opentallas.dshbm.wavepack.request_join_model.v1',
                default_enabled=False, inherited_caller_ff=491,
                added_ff=ff, queue_ff=queue, request_cursor_ff=request,
                same_credit_op_hook_ff=op_hook, total_caller_and_join_ff=491+ff,
                ff_allowance_um2=ff*0.37908,
                nand2_equivalent_allowance=logic, buffer_allowance=8,
                combinational_allowance_um2=logic*0.08748+8*0.10206,
                reservation_um2=2*(ff*0.37908+logic*0.08748+8*0.10206),
                added_memory_ports=0, added_column_tag_bits=0, added_arithmetic_edges=0,
                pair_request_index='physical index={accepted_offset[5:3],accepted_offset[1:0]}; segment=offset[2]',
                reqs_per_cycle=1, response_tag_bits=10, response_payload_bits=1088,
                line_address_bits=32, descriptor_fifo_depth=dq,
                clock_period_ps=833.333333, ss_uncertainty_ps=60, ff_uncertainty_ps=25,
                clock_sinks=ff, loaded_clock_capacitance=None,
                selector_fanout=32, boundary_added_descriptor_bits=34,
                route_tracks_lower_bound=34, channel_capacity=None, slot_fit=None,
                component_source_admitted=True, physical_build_admitted=False,
                composed_gain=None, adoption=False)
