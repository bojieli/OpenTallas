#!/usr/bin/env python3
"""Pre-RTL sizing of the additive HBM fused-SU stream endpoint.

These are architectural bounds, never a measured or adoption verdict. Existing
FP engines retain their own arithmetic and storage; the wrapper adds transport,
transaction counters and a reservation handshake with the real VM writer.
"""
import json


def finite_native_parent_model():
    """Minimum installed DS20 borrower, with positive finite service pricing.

    Area is a conservative source construction, not installed slot credit.
    Timing ranges are exclusive/drained provider planning budgets, not measured
    successful-service guarantees or a new frequency claim.
    """
    import hashlib, math
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    codec_record = 'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json'
    cm = json.loads((root/codec_record).read_text())['SRAM_protection_candidate']
    stage_bits = 893952
    auxiliary = dict(control=144, scalar=720, program=704*8,
                     held_MREQ_response=720, prior_tag_kind_valid=2592, sector_caches=1656)
    ff = stage_bits+sum(auxiliary.values())
    # Parallel capture encoders are required by the native wide strobes.
    # Balanced encoder/decoder pairs deliberately overprice unused decoders.
    codec_pairs = 5120+2176+8+5+3
    mux_bits = 5*72*1023 + 72*2175
    clock_buffers = math.ceil((ff-1)/7)
    body = ff*.2916 + codec_pairs*cm['pair_cell_body_um2'] + mux_bits*.2 + ff*.2 + clock_buffers*.10206
    control_logic_allowance = .02*body
    placement = 2*(body+control_logic_allowance)/1e6
    pins = ['rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cluster20.sv',
            'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv',
            'rtl/gpu_sys/ot_gpu_mreq_cdc.sv', 'rtl/gpu_sys/ot_gpu_memsys.sv',
            'rtl/gpu_sys/ot_gpu_hbm_partition.sv', 'rtl/hdc/kv/ot_hdc_hbm_model.sv',
            'rtl/hdc/ot_hdc_cg.sv', 'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', codec_record]
    return dict(schema='hbm.su.finite-native-parent.minimum.v1', default_enabled=False,
        selected_parent=pins[0], selected_issuer=pins[1], namespace='cluster20_su / su_parent; Einstein sole RTL owner',
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in pins},
        command='original scheduled four-word L0.hc_post.attn; no rescheduling, new opcode or public completion ABI',
        N=1024, M=256, D=5120, native_ML=6, native_AL=5, fused_ML=5, fused_AL=4,
        program_capacity_words=8, scalar_capacity_words=20, frame_capacity=1,
        protected_stage_FF=stage_bits, auxiliary_FF=auxiliary, total_FF=ff,
        native_read_seats=5120, native_write_seats=2176,
        outstanding_provider_requests=1, existing_prior_tag_slots_per_client=32, installed_clients=4,
        provider=dict(request_bits=337,response_bits=273,sector_bytes=32,byte_address_bits=32,tag_bits=16,
            CDC_depth=8,NS=2,NPC=2,MEM_WORDS=2097152,USE_W2=0,
            memory_clock_ns=1,source_target_clock_ns=1/1.2,
            new_ports=0,borrow='SM0 only after actual accepted prior request/response drain and allSM/launch exclusion; Rawls arbitrates SU/W2, no simultaneous borrower'),
        namespace_bytes=dict(VM=0,KV=0x100000,CRlo=0x300000,CRhi=0x320000,WR=0x340000),
        minimum_component_address_coverage_bytes=4*1024*1024,
        engine_clock='ot_hdc_cg existing latch/ICG; hold native/fused engine AND scheduled issuer/read-response/write strobes together; backend/CDC remains live',
        codec=dict(source='rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',balanced_pairs=codec_pairs,
            body_mm2=codec_pairs*cm['pair_cell_body_um2']/1e6,
            encode_held_edges=2,decode_held_edges=3,select_edges=1,
            basis='source W6 construction plus retained minimum-group cone: encode905.013ps/decode1633.328ps incl60unc; assumed extra250ps local loading, no contextual qualification',
            encode_estimated_loaded_ps=1155.013,decode_estimated_loaded_ps=1883.328,
            UE_CE='hold/quarantine owned debt until repair; never release partial corrupted state'),
        protocol=dict(initial_snapshot_encode_edges=2, launch_capture_edges=1,
            selected_head_decode_edges=3, request_select_register_edges=2,
            response_capture_edges=1,response_encode_edges=2,matched_publication_release_edges=2,
            per_transaction_local_edges_estimate=10,
            provider_roundtrip_ns_planning_range=[45,500],
            range_basis='exclusive/drained source, CL12.5+REQ10+RSP10ns, ACT/PRE/turnaround/one350ns refresh plus positive CDC/controller allowance; not a guarantee under competing traffic or refused sinks',
            read_before_write='all owned frame reads before VM/KV/reducer writes, original priority retained',
            publication='actual tag/kind write ACK then same-address ordered readback; no engine done or request acceptance substitutes visibility'),
        worst_frame_service=dict(cache_hits_credited=0, read_MREQ=5120,write_MREQ=2176,publication_MREQ=2176,
            MREQ_transactions=9472,partial_write_internal_old_reads=2176,physical_sector_actions=11648,
            note='source maxima planning envelope, not actual simultaneous command traffic. Cache/address coalescing must be measured; internal partial-write RMW counted once, not extra public MREQ.',
            serialized_planning_us_range=[(11648*45+9472*10/1.2)/1000,(11648*500+9472*10/1.2)/1000]),
        area=dict(FF_body_mm2=ff*.2916/1e6,codec_body_mm2=codec_pairs*cm['pair_cell_body_um2']/1e6,
            mux_bits=mux_bits,mux_um2_per_bit_assumed=.2,feedback_mux_bits=ff,
            fanout8_clock_buffers_estimate=clock_buffers,buffer_um2_assumed=.10206,
            control_logic_allowance_mm2=control_logic_allowance/1e6,placement_at50pct_mm2=placement,
            required_minimum_component_outline_um=[2800,2400],component_envelope_mm2=6.72,
            estimate_fits_component_envelope=placement<=6.72,
            parent_home_reserved=False,slot_scope='required standalone minimum component envelope; NOT free space in Claude die floorplan',
            excludes='actual codec cut FF/hold repair beyond allowance, clock/PG/loaded long wires and installed parent placement'),
        boundary_payload_tracks_lower_bound=337+273,loaded_channel_fit=False,
        implementation_model_selected=True,component_RTL_implementation_permitted=True,
        physical_route_admitted=False,physical_clock_qualified=False,
        composed_token_gain_us=None,adopted=False,
        implementation_gate='retain finite capacities and positive cuts; real CP launch/borrower/publication, same original scheduled program and existing input image; contextual SS60/FF25 later, not a prerequisite to write opt-in candidate RTL')


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

    The native bench ABI requires four N1024 read planes. That is not an
    instantiated HBM memory provider. Scalar capture proposes reusing the
    first 20 lanes only if a provider can actually guarantee those ports.
    The mux estimate below does not price or qualify that missing provider.
    """
    records=[]
    for kind, words in (("hc_norm",4),("q_norm",0),("kv_norm",0),
                       ("swiglu",1),("hc_post",20)):
        held_bits=32+5*24+words*32+3*32+3+16+16+8
        records.append(dict(kind=kind,producer_VM_words=words,
            producer_VM_bytes=words*4,producer_read_bits_per_edge=words*32,
            producer_max_read_planes=1 if words else 0,new_memory_ports=0,
            new_memory_ports_scope='scalar capture reuse proposal only; provider unresolved',
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
        concrete_blocker='no selected finite HBM VM provider guarantees native/fused ports and actual write publication',
        enclosing_provider=provider_requirements(),
        no_new_hardware_written=True,rows=records,estimates_not_results=True)


def provider_requirements():
    """Actual N1024 native ABI maxima, not simultaneous traffic or SRAM cost.

    A 256-bit service's payload-only beat counts are lower bounds. They do
    not include addresses, bank conflicts, wire/CDC, credits or arbitration,
    and cannot satisfy the unstallable next-edge ABI without priced storage.
    """
    ports=[]
    for name, words, source_bits in (
            ('native_indirection_read',1024,0),
            ('native_operand_read',4096,2),
            ('native_VM_write',1024,0),
            ('native_KV_write',1024,0),
            ('native_reduction_VM_write',128,0)):
        ports.append(dict(name=name,max_words_per_edge=words,
            payload_bits_per_edge=words*32,payload_bytes_per_edge=words*4,
            address_bits_per_edge=words*24,enable_bits_per_edge=words,
            source_select_bits_per_edge=words*source_bits,
            payload_only_256bit_service_beats_lower_bound=(words*32+255)//256,
            maxima_not_assumed_simultaneous=True))
    storage=dict(VM=4*(1<<18),KV=4*(1<<19),CR=8*(1<<15),WR=2*(1<<16))
    return dict(native_source='rtl/hdc/v41x/ot_hdc_v41x_vec.sv',
        bench_source='rtl/test/tb_hdc_v41x_vec.sv',
        enclosing_owner='Euclid',selected_provider_source=None,
        provider_selection_owner='Claude',ports=ports,
        bench_logical_storage_bytes=storage,
        bench_logical_storage_total_bytes=sum(storage.values()),
        storage_scope='logical bench capacities; not an approved macro topology or new area',
        read_contract='fixed next-edge synchronous reply; no response-valid or request-ready',
        write_contract='unstallable writes; native cr_dseq/cr_rseq are pipeline events, not physical memory ACK',
        additional_parent_producer_ports='external X producer/capture must be bound and priced by enclosing owner',
        actual_provider_bank_topology=None,bank_conflict_or_buffer_cost=None,
        provider_area_mm2=None,provider_clock_cost=None,corridor_capacity=None,
        provider_min_max_timing=None,provider_CDC_credit_latency_us=None,
        actual_provider_publication_hook=None,composed_latency_delta_us=None,
        RTL_build_admitted=False,physical_qualified=False,adopted=False)


def finite_provider_tradeoff_model():
    """Compose Euclid's selected finite transport with actual provider costs.

    Payload floors cannot stand in for successful service bounds. The same
    original HC engine benchmark is used only as a scoped comparison, not a
    physically corrected baseline or a token-rate denominator.
    """
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    p = 'results/uarch/hbm_su_finite_provider_20261005/selection.json'
    selection = json.loads((root/p).read_text())
    stream = selection['alternatives'][1]
    rows = []
    for row in stream['rows']:
        rd = row['read_sectors_aligned_contiguous_optimistic']
        wr = row['write_sectors_aligned_contiguous_optimistic']
        floor = rd+wr
        rows.append(dict(kind=row['kind'], read_sectors_floor=rd,
            write_sectors_floor=wr, serial_sector_payload_floor_us=floor/1000,
            successful_service_upper_bound_us=None,
            explicit_latency_equation=(
                f'{rd}*T_read_roundtrip + {wr}*T_write_roundtrip + '
                'staging/pack_mux + read_drain + checked_publication + owner_handoff; '
                'engine overlap allowed only by accepted dependent-event calendar'),
            roundtrip_definition='each includes actual request CDC, accepted backend wait/service, matched response CDC and acceptance; do not add CDC again',
            native_and_fused_operand_response_compatibility=False,
            field_to_X_availability_time_us=None, physically_qualified=False))
    hc = rows[0]
    original = 487/.9/1000
    rf = finite_rf_provider_model()
    return dict(schema='opentallas.hbm-su-finite-provider.composition.v1',
        authoritative_provider_selection=p,
        selected_transport=selection['selected_transport_candidate'],
        source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest(),
            'rtl/gpu_sys/ot_gpu_mreq_cdc.sv':hashlib.sha256((root/'rtl/gpu_sys/ot_gpu_mreq_cdc.sv').read_bytes()).hexdigest()},
        rows=rows, original_HC_benchmark_us=original,
        HC_transport_floor_over_original_benchmark=hc['serial_sector_payload_floor_us']/original,
        HC_nonoverlapped_81_call_payload_floor_us=81*hc['serial_sector_payload_floor_us'],
        repeated_call_scope='conditional 81 serial HC calls only; not token delta or proof of current physical provider latency',
        decision='selected sector path is a functional-integration candidate, NOT an acceleration credit; pricing cannot use original fixed-wide bench as physical baseline',
        smallest_alternative='existing finite two-read RF with exclusive staged Q/KV working set; limited contiguous commands, not a replacement whole VM',
        alternative_source='rtl/gpu/ot_gpu_rf_service.sv',
        alternative_Q_KV_staged_service_us={r['kind']:r['provider_time_us_at_target_900MHz'] for r in rf['rows']},
        alternative_adapter_reservation_mm2_ESTIMATE=rf['shared_adapter_reservation_mm2_ESTIMATE'],
        alternative_RF_body_mm2=rf['macro_body_mm2'],
        alternative_macro_debit='retain installed RF body once if actually leased; dedicated replica adds 0.49812185088mm2 body before clock/PG/routes',
        alternative_remaining_costs='actual source staging load, CR address namespace, byte-aligned RMW, quant/KV destination, external clock crossings, loaded mux/FF hold and slot',
        selected_sector_staging_DFF_floor_mm2=stream['DFF_body_floor_um2_if_register_implementation']/1e6,
        selected_sector_staging_area_scope='largest fused input/output reserve incl sealed state; before mux/clock/PG/corridor; mutually exclusive command variants, not summed with RF proposal',
        existing_CDC_FIFO_payload_bits=8*(337+273),
        CDC_FIFO_debit='already installed in borrowed SM0 route; retain once, no new ports; outstanding limit1 cannot inherit FIFO throughput8',
        physical_SS_FF_acceptance=False, clock_hz_qualified=None,
        component_exactness_not_physical_qualification=True,
        composed_token_delta_us=None, headline_rate_gain_percent=None,
        adoption=False, RTL_build_admitted=False)


def finite_rf_provider_model():
    """One finite, GPU-style working-set candidate; not a wide VM claim.

    Only contiguous Q/KV norm commands are selected. Their operands are
    snapshotted before issuing the unchanged fixed-response fused wrapper.
    All unstallable outputs are reserved before GO. The enclosing adapter,
    source/namespace mapping and loaded register cuts are still to be built.
    """
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    macro_path = ('physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/'
                  'ot_sram_1r1w_128x256_m1_r2c2.json')
    macro = json.loads((root / macro_path).read_text())
    paths = ['rtl/gpu/ot_gpu_rf_service.sv',
             'rtl/gpu/ot_gpu_full_sm_service.sv',
             'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
             'rtl/hbm_accel/su/ot_hbm_accel_su_fused_vm.sv',
             'results/rtl/hbm_su_fused_20261005/command_bridge_provider_gap.json',
             macro_path, 'tools/uarch_model.py']
    rows = []
    for name, n, d, rd in [('q_norm', 256, 1280, 0),
                           ('kv_norm', 512, 512, 64)]:
        # Worst contiguous extent alignment: one extra RF vector per extent.
        # No indirection, arbitrary gather, scalar broadcast or coalescing credit.
        vectors_per_extent = (d + 127) // 128 + 1
        reads = vectors_per_extent  # two independent x/gain extents, two ports
        outputs = 1 + bool(rd)      # keep y and RoPE publications, no deadwrite credit
        writes = outputs * vectors_per_extent
        # Partial first/last vectors require checked ownership and RMW of old
        # untouched lanes using the same finite read port. No extra SRAM port.
        rmw_reads = 2 * outputs
        # Each transaction adds TWO explicit packing/selection register cuts.
        # Source-only II3/II2 is not a loaded 1.2 GHz guarantee.
        staged_read_edges = 5
        staged_write_edges = 4
        terms = dict(operand_snapshot=(reads * staged_read_edges),
                     output_boundary_RMW=(rmw_reads * staged_read_edges),
                     mirrored_output_publication=(writes * staged_write_edges),
                     snapshot_read_drain_fence=1, command_handoff=1,
                     final_ACK_and_owner_publication_fence=1)
        quant_bits = d * (8 + 16) + ((d + 31)//32)*10
        snapshot_bits = 2*d*32
        output_bits = outputs*d*32
        # Dedicated quant reserve is NOT a physical KV/reduction destination.
        payload_bits = snapshot_bits + output_bits + quant_bits
        transfer_ff = 2*(8192+4096)  # two proposed packing cuts each way
        metadata_ff = 1024  # explicit conservative reservation, issuer identity extra
        ff = payload_bits + transfer_ff + metadata_ff
        # Positive feedback/selector allowance; not mapped cell/timing evidence.
        enable_mux_gate_eq = 4*payload_bits
        snapshot_select_gate_eq = 3*2*n*32*((d+n-1)//n-1)
        packing_mux_gate_eq = 3*4096*(n//128-1)
        gates = enable_mux_gate_eq + snapshot_select_gate_eq + packing_mux_gate_eq
        cell_floor = ff*.2916 + gates*.08748
        edges = sum(terms.values())
        rows.append(dict(kind=name, lanes=n, dimension=d, rope_tail=rd,
            RF_read_transactions=reads, output_partial_vector_RMW_reads=rmw_reads,
            RF_write_transactions=writes, source_read_II_edges=3,
            source_write_II_edges=2, candidate_staged_read_edges=5,
            candidate_staged_write_edges=4, staged_terms_edges=terms,
            conservative_serial_provider_edges=edges,
            provider_time_us_at_target_900MHz=edges/.9/1000,
            working_set_RF_vectors=(2+outputs)*vectors_per_extent,
            working_set_capacity_fits_512_vectors=True,
            input_snapshot_FF_bits=snapshot_bits,
            full_output_reservation_FF_bits=output_bits,
            separate_quant_reservation_FF_bits=quant_bits,
            proposed_packing_cuts_FF_bits=transfer_ff,
            control_FF_reservation_bits=metadata_ff,
            total_added_FF_bits=ff, logic_NAND2_equivalents_ESTIMATE=gates,
            adapter_cell_floor_mm2_ESTIMATE=cell_floor/1e6,
            adapter_50pct_reservation_mm2_ESTIMATE=2*cell_floor/1e6,
            internal_snapshot_bits_per_edge=n*32,
            snapshot_gain_and_data_are_separate=True,
            full_program_composed_delta_us=None,
            KV_reduction_publication_time_us=None, source_load_store_time_us=None,
            actual_same_clock_binding=False, loaded_cuts_qualified=False))
    return dict(schema='opentallas.hbm-su-finite-rf.price.v1',
        selection='one existing GPU RF service, exclusive Q/KV norm working set',
        owners=dict(model='Maxwell', RTL='Euclid', programs='Einstein'),
        source_sha256={p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
        selected_provider='rtl/gpu/ot_gpu_rf_service.sv',
        real_caller='rtl/gpu/ot_gpu_full_sm_service.sv:u_rf',
        transfer=dict(read_ports=2, words_per_read_port=128,
                      read_bytes_per_transaction=1024, write_bytes_per_transaction=512,
                      operand_return_bits=8192, write_bits=4096,
                      read_address_bits=18, write_address_bits=9,
                      payload_boundary_tracks_lower_bound=12288,
                      capacity_outstanding_transactions=1,
                      reads_and_writes_mutually_exclusive=True,
                      source_read_response_edges=1, source_write_ACK_edges=0,
                      ACK_scope='both macro copies write at acceptance; ACK consumed next edge, reuse later',
                      source_read_II_edges=3, source_write_II_edges=2),
        replicas_per_selected_provider=1, logical_RF_bytes=262144,
        physical_operand_copies=2, macros_per_provider=128,
        macro_body_mm2=128*macro['area']['macro_area_um2']/1e6,
        macro_body_debit='existing leased RF: retain inherited body once; new dedicated replica adds full body',
        macro_timing_calibrated_only=macro['claim_boundary'],
        macro_SS_clkQ_ps=macro['timing']['ss']['clk_to_q_ps'],
        macro_FF_clkQ_ps=macro['timing']['ff']['clk_to_q_ps'],
        macro_clock_cap_SS_fF=128*macro['timing']['ss']['clk_cap_ff'],
        target_local_clock_hz=900000000, target_clock_not_qualified=True,
        mux_and_route_cuts='two positive register cuts per RF transaction, counted once in rows; loaded timing unknown',
        CDC='RF, snapshot and fused endpoint proposed same SU clock; outer SM/HBM domain crossings not bound',
        external_CDC_us=None, installed_RF_replica_available=None,
        clock_reset_route_PG_area_mm2=None, physical_slot_fit=None,
        initialization_and_transfer='actual source bits loaded through finite ports before snapshot; load/store and CR namespace adapter are not free',
        minimum_RTL_step='Euclid: default-off whole-command host RF lease after existing SIMD/host debt drain; operand snapshot and complete output reservation; finite packing/RMW and held mirrored ACK publication',
        caller_lease_gap='full_sm_service reserves RF for each SIMD operation, not an entire host fused command; competing host/SIMD work must be excluded by the new command lease',
        shared_adapter_reservation_mm2_ESTIMATE=max(r['adapter_50pct_reservation_mm2_ESTIMATE'] for r in rows),
        shared_adapter_area_rule='one Q/KV adapter sized to max row, not sum; incremental buffers are distinct from inherited fused endpoint registers',
        lease='drain competing readers/writers before snapshot; retain through all mirrored ACKs, read drain, quant destination publication and owner fence',
        no_native_full_width_provider=True, MACs_per_cycle_added=0,
        bench_3538944_bytes_not_replicated=True, rows=rows,
        not_supported=['native VI/gather interface', 'HC norm/post full command',
                       'KV/reduction destination publication', 'external X producer capture'],
        exact_adapter_implemented=False, RTL_build_admitted=False,
        SS60_FF25_qualified=False, adopted=False, headline_gain_percent=None)


if __name__ == "__main__":
    print(json.dumps(model(), indent=2))
