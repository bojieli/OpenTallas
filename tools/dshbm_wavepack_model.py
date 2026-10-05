"""Pre-RTL inventory of the bounded two-segment opt2 candidate, on top of PQ.

Physical costs are explicit inventory, never a routed closure or rate credit.
This does not allocate x memory, alter arithmetic or price the entire SM twice.
"""
def production_adapter_model():
    """One finite DS20 MREQ adapter; existing PQ bench is not production IO."""
    import hashlib, json, math
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    cost='results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json'
    codec=json.loads((root/cost).read_text())['SRAM_protection_candidate']
    counts=dict(packet_slots=32*1512, restored_rows=14*432, xbeat=2304,
                configuration=4160, control=576)
    ff=sum(counts.values()); assert ff==61472
    pairs=21+6+4+1
    mux_bits=1512*31+432*13+337
    buf=math.ceil((ff-1)/7)
    body=ff*.2916+ff*.2+mux_bits*.2+pairs*codec['pair_cell_body_um2']+buf*.10206
    area=2*body*1.02/1e6
    paths=['rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
           'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv',
           'rtl/gpu_sys/ot_gpu_mreq_cdc.sv','rtl/gpu_sys/ot_gpu_memsys.sv',
           'rtl/gpu_sys/ot_gpu_hbm_partition.sv','rtl/hdc/kv/ot_hdc_hbm_model.sv',
           'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',cost]
    return dict(schema='dshbm.wavepack.production-adapter.minimum.v1',default_enabled=False,
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
        RTL_owner='Erdos production adapter; Rawls sole enclosing top/mux',
        actual_launch='CP20 launch_v0/launch_pc32/token17/pos20; job32/gen4 captured only db_v&&db_rdy',
        loader='existing64-bit loader; compiler must bind original linked W2PC and nonoverlapping installed weight/X/result extents; no reserved guessed opcode/addresses',
        packet_capacity=32,packet_raw_bits=1280,packet_check_bits=160,packet_metadata_bits=72,
        restored_row_capacity=14,restored_NC=8,one_xbeat_bits=2048,one_xbeat_capacity=1,
        descriptor_capacity=4,descriptor_words64=16,protected_FF=counts,total_FF=ff,
        provider=dict(route='borrowed SM0 LSU -> existingAW3 CDC -> memsys',
            request_bits=337,response_bits=273,sector_bits=256,sector_bytes=32,tag_bits=16,
            outstanding_requests=1,added_ports=0,memory_clock_ns=1,source_clock_target_ns=1/1.2,
            NS=2,NPC=2,MEM_WORDS=2097152,USE_W2=0,
            exclusion='Actual all old accepted requests/responses drained before borrow; mutually exclusive with Einstein SU; no req_ready tie or acceptance-as-publication'),
        packet_service=dict(useful_bytes=136,sector_actions=5,physical_bytes=160,padding_bytes=24,
            padding_fraction_of_useful=24/136,
            response_to_caller_edges=1,assembly_to_xwrite_edges=1,descriptor_validation_edges=1,
            encode_held_edges=2,decode_held_edges=3,
            minimum_packet_local_edges=8,
            provider_roundtrip_ns_planning_range=[45,500],
            occupied_packet_ns_planning_range=[5*45+8/1.2,5*500+8/1.2],
            planning_assumptions='same exclusive/drained provider source as finiteSU; actual request-to-response may stall on CDC/backend/refresh/held sinks; range is not a measured guarantee',
            stripe_capture='reserve whole packet before request, collect5actualsectors, validate owner and decode held W6 state before exposing1088bits once',
            X='source A/B bytes fetched through real provider before xwrite/start; no cached bench XB as installed memory authority',
            publication='real restored row address -> actual writeACK -> same-address readback before sm_done; CPLtoken is never taken from W2 data'),
        component_cost=dict(body_FF_mm2=ff*.2916/1e6,codec_pairs=pairs,
            codec_body_mm2=pairs*codec['pair_cell_body_um2']/1e6,
            codec_timing_basis='retained W6 encode905.013ps/decode1633.328ps incl60unc, positive250ps local loading estimate:2encode/3decode held targetedges; not II1 or contextual signoff',
            mux_bits=mux_bits,mux_um2_per_bit_assumed=.2,feedback_mux_bits=ff,
            fanout8_clock_buffers_estimate=buf,buffer_um2_assumed=.10206,
            placement_at50pct_mm2=area,required_component_outline_um=[400,400],component_envelope_mm2=.16,
            estimate_fits_component_envelope=area<=.16,parent_home_reserved=False,
            original_mapped_W2_body_um2=845.7129,original_mapped_W2_FF=1364,
            original_clock_load_fF=645.941909,
            original_W2_debit_separate_once=True,
            exclusions='actual codec cut FF/extra hold repair/long routes/PG/loaded CTS; envelope not die-space containment'),
        boundary_tracks_lower_bound=337+273,loaded_channel_fit=False,
        measured_609_to425_scope='retained logical PQ fixture only, NOT production fetched-packet latency',
        actual_production_exposed_packet_count=None,composed_production_gain_us=None,
        one_percent_threshold_established_for_production=False,
        selection='existing DS20 singleSM0 LSU correctness-only production integration; Rawls14:15 decision',
        production_rate_binding='REJECT_SINGLE_MREQ_ACCELERATION_CREDIT',
        production_traffic_floor=dict(useful_weights_bytes=32640,sector_weights_bytes=38400,
            X_bytes=55296,write_readback_bytes=896,total_bytes=94592,
            minimum_sector_edges=2956,source_memory_clock_ns=1,minimum_us=2.956,
            excludes='latency/arbitration/CDC/codec; different provider from retained609->425'),
        source_implementation_model_selected=True,component_RTL_implementation_permitted=True,
        physical_route_admitted=False,physical_clock_qualified=False,adopted=False,
        next='Rawls binds exact original installed image/PC/span map; Erdos implements finite adapter under these seats/cuts; actual same-provider production baseline/candidate gate decides benefit, no modeled gain transfer')

def w2_parent_source_model(fixture):
    """Price the proposed DS20 single-MREQ installation BEFORE engine RTL.

    This rejects treating the component's 1088-bit procedural return source
    as a physical 256-bit DS20 client. It is not a new memory architecture or
    a composition edit; Maxwell owns canonical integration of this inventory.
    """
    ds=[fixture['composite_descriptors'][k] for k in fixture['w2_groups']]
    weight_lines=sum(d[4] for d in ds)
    rows=sum(d[0] for d in ds)
    # Actual joint P1 XMAP source uses groups[0,4] for FP4 and [0] for FP8.
    x_beats=sum(((d[7] if d[6] else 0)+(d[13] if d[10] else 0))*(2 if d[3]==2 else 1) for d in ds)
    weight_bytes=weight_lines*136
    padded_weight_bytes=weight_lines*5*32
    x_bytes=x_beats*256
    publication_bytes=rows*32*2  # full NC8 write plus positive readback
    request_edges=(padded_weight_bytes+x_bytes+publication_bytes)//32
    inventory=dict(weight_assembly=32*(1280+160+72),
                   publication=14*6*72,x_beat=32*72,
                   frozen_configuration=4*(1024+16),frame_control=8*72)
    ff=sum(inventory.values())
    # Positive bounds for selectors/protection/control; not mapped closure.
    nand2=3*1280*32+3*432*14+3*1024*4+12000
    buffers=128
    area=ff*.37908+nand2*.08748+buffers*.10206
    return dict(schema='opentallas.ds20.w2.parent_source_model.v1',
        default_enabled=False,existing_provider='SM0 LSU -> mreq_cdc -> memsys_adapter/xbar/L2/HBM',
        request_bits=337,response_bits=273,request_data_bytes=32,
        provider_clock_ps=1000,stream_clock_ps=833.333333,
        ss_uncertainty_ps=60,ff_uncertainty_ps=25,
        new_memory_ports=0,provider_requests_per_edge=1,arithmetic_macs_added=0,
        component_logical_weight_lines=weight_lines,restored_rows=rows,
        useful_weight_bytes=weight_bytes,padded_weight_bytes=padded_weight_bytes,
        weight_sectors=padded_weight_bytes//32,x_beats=x_beats,x_read_bytes=x_bytes,
        publication_write_readback_bytes=publication_bytes,
        total_provider_request_edges_floor=request_edges,
        total_provider_service_us_floor=request_edges*.001,
        useful_weight_only_us_floor=weight_bytes/32*.001,
        padded_weight_only_us_floor=padded_weight_bytes/32*.001,
        source_ff_inventory=inventory,total_storage_bits_allowance=ff,
        nand2_equivalent_allowance=nand2,buffer_allowance=buffers,
        cell_area_allowance_um2=area,reservation_at_50pct_um2=2*area,
        clock_pin_cap_ff_proxy=ff*.5,loaded_clock_cap_ff=None,
        weight_selector_inputs=32,weight_payload_mux_bits=1280,
        internal_weight_boundary_bits=1088,internal_x_boundary_bits=2048,
        added_response_capture_edges=1,added_x_write_edges=1,
        descriptor_validation_edges_min=1,publication='matched write ACK plus actual readback; no acceptance-as-completion',
        source_image_bound=False,parent_slot_fit=None,channel_capacity=None,
        composer_owner='Maxwell',canonical_composed_latency=None,
        engine_build_admitted=False,physical_build_admitted=False,adopted=False,
        verdict='REJECTED_SINGLE_MREQ_RATE_BINDING',
        rejected_binding_not_numeric_verdict=True,
        original_opt2_component_result_unchanged=True,
        required_next_selection='Existing native stream/formatter source and actual compiled DS20 W2 spans, with Maxwell canonical model pricing; no new memory architecture implied',
        reason='Weight traffic alone exceeds old 425/609-cycle procedural provider intervals; installed-source/actual-provider composition must replace that credit, not inherit it')


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
    request = 24+6+32+32+1+1+1+1  # active A/B bases, PAIR/bound/active/fault
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


def result_join_model(nctx=11, rw=12):
    # Public start acceptance can enqueue CHD7 posted +NOUT4 outstanding.
    bits = nctx*(32+32+rw+1+1+1) + 2*(nctx-1).bit_length() + nctx.bit_length() + rw+1+4+1
    extra = max(0,bits-491)
    return dict(schema='opentallas.dshbm.wavepack.result_join_model.v1',
                default_enabled=False, posted_contexts=7, outstanding_contexts=4,
                queue_depth=nctx, actual_ff=bits, inherited_reservation_ff=491,
                additional_ff=extra, additional_ff_allowance_um2=extra*0.37908,
                nand2_equivalent_allowance=600, buffer_allowance=6,
                boundary_op_identity_bits=32, payload_registers_added=0,
                extra_memory_ports=0, extra_column_tag_bits=0, added_edges=0,
                physical_build_admitted=False, component_source_admitted=True,
                closure_policy='SS60/FF25, unchanged 833.333333ps',
                measured_gain=None, adoption=False)
