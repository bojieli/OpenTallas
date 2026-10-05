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
