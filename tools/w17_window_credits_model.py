#!/usr/bin/env python3
"""Source-only WINDOW credits model. No RTL execution, payload reads or token-rate pricing."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '4e38326d6f361bc85e660f48c59c355e2bb95274'
REPLAY_COMMIT = 'f6f4c00d7a6d85484bf20715b34079d0b66b98de'
CHIP = 'rtl/chip/'
PATHS = [CHIP+p+'.sv' for p in (
    'ot_chip_v41x_window_kv_prefetch', 'ot_chip_v41x_window_attn_source',
    'ot_chip_v41x_window_refill_schedule', 'ot_chip_v41x_window_stage4',
    'ot_chip_v41x_window_retention', 'ot_chip_v41x_window_stream',
    'ot_chip_v41x_attn_row_merge', 'ot_chip_v41x_attn_desc_lifecycle',
    'ot_chip_v41x_kv_reqmux', 'ot_chip_v41x_kv_rope_reqmux',
    'ot_chip_v41x_hbm_karb', 'ot_chip_v41x_hbm3e_phy')]
PATHS += ['rtl/chip/ckvsel/ot_chip_v41x_die.sv',
          'rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv',
          'rtl/test/tb_window_refill_credits.sv',
          'tools/rtl_v41x_window_refill_credits_gate.py',
          'results/rtl/v41x_window_refill_credits.json',
          'results/rtl/v41_window_retention_gate.json',
          'results/contracts/v41_window_retention_contract.json',
          'results/rtl/v41_l0_live_chain.json',
          'tools/uarch_model.py', 'docs/MICROARCH_MODEL.md']


def obj(path, commit=SOURCE):
    # Committed text only. Never open the protected live checkout or checkpoint payloads.
    return subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def row_span(credits, latency):
    """Closed form from first sector grant to scale response; constant *handshake* latency L>=1."""
    assert 1 <= credits <= 16 and latency >= 1
    if credits == 1:
        return 17*latency+16
    # C tickets are issued per wave. At full pending, a same-edge return cannot grant.
    waves, tail = divmod(15, credits)
    last_code_request = waves*max(credits, latency+1)+tail
    return last_code_request+2*latency+1


def tag_failure():
    # Source has EPOCH_W=TAGW-5=11; the composed mux permits only tag[13:0].
    failures = [e for e in range(1, 2048) if ((e << 5) >> 14) != 0]
    return dict(status='FAIL_COMPOSED_EPOCH_OWNER_BUDGET', applies='REFILL_CREDITS>1 FR_PIPE only; default1 and WC/WS sector tags unaffected', declared_epoch_bits=11,
                sector_bits=5, reserved_client_owner_bits=2, safe_epoch_bits=9,
                safe_epoch_values=[0,511], first_bad_epoch=failures[0],
                first_bad_sector=0, first_bad_client_tag_hex=hex(failures[0]<<5),
                failing_nonzero_epoch_count=len(failures),
                effect='kv_rope_reqmux w_req_v=0 and bad_tag=1; no HBM grant; sticky mux fault. This is admission rejection, not backend slowness.',
                first_full128_rows_from_reset_safe=True,
                first_bad_refill_row_since_reset=512,
                prior_wrap_fixture='tb_window_refill_credits directly sets epoch=0x7fe, then emits epoch0x7ff; its source-only connection omits the mux that rejects this tag.',
                reset='Epoch advances per fetched row and is reset only by rst_n. Row drain prevents stale returns, but does not prevent high owner-bit collision.')


def build():
    raw = {p:obj(p) for p in PATHS}
    pin = {p:digest(v) for p,v in raw.items()}
    text = {p:v.decode() for p,v in raw.items()}
    prior = json.loads(raw['results/rtl/v41x_window_refill_credits.json'])
    pin_checks = {p:pin[p] == h if p in pin else digest(obj(p)) == h
                  for p,h in prior['sources'].items()}
    assert all(pin_checks.values()), pin_checks
    pf = text[CHIP+'ot_chip_v41x_window_kv_prefetch.sv']
    mux = text[CHIP+'ot_chip_v41x_kv_rope_reqmux.sv']
    assert 'TAGW-5' in pf and 'refill_pending < REFILL_CREDITS' in pf
    assert 'refill_received[15:0] == 16\'hffff' in pf
    assert 'wt[TAGW-1:TAGW-2]' in mux
    replay_path = 'results/rtl/w17_bounded_idx_replay_20261001_attempt1/record.json'
    replay_raw = obj(replay_path, REPLAY_COMMIT)
    replay = json.loads(replay_raw)
    assert replay['verdict'] == 'PASS_BOUNDED_TIMING_EQUIVALENCE'
    assert replay['source_sha256']['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'] == pin['rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv']
    def pc(a): return ((a>>2)^(a>>7)^(a>>12))&31
    def bank(a): return ((((a>>12)^((a>>15)>>2))&7)<<2)|((a^(a>>15))&3)
    rows = [[0x40000+r*17+s for s in range(17)] for r in range(128)]
    counts = [sum(pc(a)==p for row in rows for a in row) for p in range(32)]
    assert counts == [68]*32
    code_pc_counts = [len({pc(a) for a in row[:16]}) for row in rows]
    pairs = {(pc(a),bank(a)) for row in rows for a in row}
    assert tag_failure()['first_bad_epoch'] == 512
    assert row_span(1,34) == 594 and row_span(8,34) == 111
    # Logical declared bits; dead branches and tied-off fields may prune. Not a synthesis result.
    storage = dict(
        prefetch=dict(row_provenance=128*(16+10+21+2), stage_provenance=128*(21+10+1),
                      scalar_control_payload_capture_and_stats=3+20+42+4+5+256+8+32+1+5+128,
                      refill_issued_received=34, refill_next_pending=10, refill_epoch=11,
                      legacy_stage_payload_declared_but_banked_branch_dead=128*4224),
        stage4=dict(payload=128*4224, provenance=128*(21+10+1),
                    bank_read_registers=4*(4224+1), first_header=1+1+10+21+4,
                    response_registers=1+10+21+4+4+4*4224+1),
        schedule=3+10+21+8+8+1+1+32+8,
        staged_sent=1,
        compat_merge=3+21+10+8+11+11+3+21+2+4+16960+1+1,
        ii1_stream=dict(data=4*16896, masks=4*4,
                        counters_headers=1+10+21+9+4*7+1+1),
        retention_wrapper=1+10+21+8+320+1+16+32+2*30,
        retention_controller=3+320+2*16,
        descriptor_lifecycle=3+2*16+10+4*21+4*30+2+1+2*11+1+1+4,
        win_service_generation=16,
        kv_rope_mux=4+1+2*32,
        karb_per_stack=32*(1+8+8)+3*32)
    prefetch_active = sum(v for k,v in storage['prefetch'].items() if not k.startswith('legacy_stage'))
    stage4_active = sum(storage['stage4'].values())
    active = prefetch_active+stage4_active+storage['schedule']+storage['staged_sent']+storage['compat_merge']
    retention_bits = storage['retention_wrapper']+storage['retention_controller']
    # Assumed areas reuse uarch constants; mux count is an explicitly partial data-path estimate.
    bitmux_stage = 4*4224*31 + 4*4224*3
    area_flops = active*0.2916/1e6
    area_mux = bitmux_stage*0.2/1e6
    constant_cases = []
    for L in (2,15,34,53,64):
        arms = {str(C):128*(row_span(C,L)+3) for C in (1,2,4,8,16)}
        constant_cases.append(dict(handshake_latency_cycles=L, schedule_refill_cycles=arms,
                                   saved_1_to_8=arms['1']-arms['8'],
                                   scope='Exact algebra for abstract constant-L always-ready service; NOT an idx_hbm measurement or bound at this L.'))
    historical = []
    for base, fast in zip(prior['cases'][:4], prior['cases'][4:]):
        historical.append(dict(latency_knob=base['latency'], queue_limit=base['queue_limit'],
            credit1_refill_cycles=[base['result']['refill0'],base['result']['refill1']],
            credit8_refill_cycles=[fast['result']['refill0'],fast['result']['refill1']],
            source='results/rtl/v41x_window_refill_credits.json', qualification='historical synthetic OOO controller gate only'))
    return dict(
        schema='opentallas.uarch.dsrom_window_credits_bounded.v1',
        revision=2, supersedes='model.json prose-PC-count correction only; previous FAIL tag-owner verdict preserved',
        verdict='MODEL_REVIEW_COMPLETE_CANDIDATE_NOT_COMPOSED_READY',
        source_commit=SOURCE, source_sha256=pin,
        model_source_sha256={p:digest((ROOT/p).read_bytes()) for p in ('tools/uarch_model.py','tools/w17_window_credits_model.py')},
        scope='Existing full-shape WINDOW source serialization lever; no new architecture. One128x17 refill, local layer term only. No builds, RTL edits, payload/checkpoint reads, headline, adoption or whole-token extrapolation.',
        prior_model_review=dict(complete_composed_block_model_found=False,
            unified_dedicated='tools/uarch_model.py DEDICATED.attention prices MAC/P-loader jobs; DEDICATED.idx_reader prices index throughput. Neither contains WINDOW_REFILL_CREDITS, tag-owner budget, scale barrier or per-row schedule.',
            reuse=['unchanged credits functional gate and all11 matching source pins',
                   'unchanged retention functional gate; narrower provisional contract is not actual824-bit control sizing',
                   'bounded credit1 backend event proof'],
            live_chain_status=json.loads(raw['results/rtl/v41_l0_live_chain.json'])['status'],
            live_chain_qualification='partial_not_executed/stale, no cycles or inherited exactness'),
        defaults=dict(WINDOW_REFILL_CREDITS=1, candidate=8, WINDOW_RETAIN_L0=0,
                      WINDOW_STREAM_II1=0,KARB_LOCAL=0,PIPE_OUT=0,PIPE_RSP=0,
                      POS_W=21,USER_W=10,HAW=30,client_TAGW=16,backend_TAGW=17,BANKED_STAGE=1),
        geometry=dict(rows=128,code_sectors_per_row=16,scale_sectors_per_row=1,
            reads=2176,HBM_bytes=128*17*32,stage_useful_bytes=128*528,
            scale_padding_bytes=128*16,row_pitch_bytes=544,stage_row_bits=4224,
            attention_beats=32,beat_bits=16960,mask_bits=4,
            address_formula='base + user*2176 + (absolute_row &127)*17 + sector',
            bounded_address_interval=[0x40000,0x40000+2176],NPC=32,
            pc_formula='((s>>2)^(s>>7)^(s>>12))&31',
            bank_formula='((((s>>12)^((s>>15)>>2))&7)<<2)|((s^(s>>15))&3)',
            all_address_dram_rows=[8],reads_per_pc=counts,unique_pc_bank_pairs=len(pairs),
            PCs_per_17_sector_row=sorted({len({pc(a) for a in row}) for row in rows}),
            PCs_per_16_code_sectors_histogram={str(n):code_pc_counts.count(n) for n in sorted(set(code_pc_counts))},
            hash_fold_collision_example=dict(slot=120,address_interval=[0x407f8,0x40809],code_PC_sequence=[pc(a) for a in rows[120][:16]],scale_PC=pc(rows[120][16])),
            max_sectors_same_pc_in_one_row=max(sum(pc(a)==p for a in row) for row in rows for p in range(32)),
            chronological_order='first+i for i0..127, then ring slot mapping. Fixed full-window trace physical slots0..127 only matches first aligned to128; do not import that cold trace for arbitrary first/region/user.'),
        finite_credit_contract=dict(valid_parameter_range=[1,16],global_not_per_PC=True,
            cap_code_requests_in_flight=8,issue_ports=1,return_ports=1,request_len=1,
            issued_bits=17,received_bits=17,next_bits=5,pending_bits=5,epoch_bits=11,
            new_payload_bits=0,extra_live_metadata_bits_vs_elaborated_credit1=55,
            guard='pending<C uses pre-edge state; full queue cannot reuse a returning credit until next edge. Valid grant+reply leaves pending unchanged.',
            tag='epoch11:sector5; issued/received one-hot dynamic bit checks, sector<=16, epoch equal, beat0, nonpoison. No row/user in tag: captured row/user valid only while one row active and old row drained.',
            scale_barrier='issue sector16 only if all16 received bits already1; last code reply cannot grant scale at same edge. Scale response publishes stage/user/absolute-row validity and IDLE.',
            row_drain='Scale issuance follows all code replies, so pending<=1 for scale. Valid scale response takes pending to0 before next row epoch. No inter-row issue overlap.',
            fault='Invalid reply/poison faults, suppresses new requests and publication. Replies always ready. Faulted outstanding reads require external drain before reset; no cancel/drain protocol is implemented.'),
        tag_owner_gate=tag_failure(),
        publish_order=dict(producer='blk_idx0..15 in order; each block code write then masked scale write, waits both wr_done. row_valid only on final block. 32 write sectors per new row; credits never overlap these writes.',
            prefetch='schedule SEND->WAIT once per row. pf_ok requires IDLE and exact stage user/absolute row. 128 rows must finish before ISSUE.',
            stage='Four banks indexed row[1:0],32slots each. Fill writes one sector to one bank; scale writes128bits. Absolute21-bit row plus10-bit user and validity at each slot.',
            replay='stage4 has independent1R/1W per bank, first bank-read registers then rotation registers. Compat merge reserves one four-row request and one beat; 32full chronological beats. No producer writes/prime while source busy.',
            no_sink_stall_replay_edges='Let M be actual merge-start handshake: compat full128 emits accepted beats M+4+4j, j0..31; merge_done rises M+128, schedule done rises M+129. STREAM_II1 emits M+4+j, merge_done rises M+35, schedule done rises M+36. These source equations assume valid stage and kv_ready continuously1; engine drain is still separate.',
            lifecycle='STAGE->READY only matching fresh generation; ARM->STREAM waits engine notidle; 32beat masks full; DRAIN completion waits engineidle. Storage done alone cannot arm retention.'),
        storage_logical_declared_bits=storage,
        storage_totals=dict(active_source_compat_upper_bits=active,
            stage4_payload_bits=128*4224,legacy_dead_payload_bits=128*4224,
            ii1_stream_bits=sum(storage['ii1_stream'].values()),
            ii1_increment_vs_compat_bits=sum(storage['ii1_stream'].values())-storage['compat_merge'],
            retention_increment_bits=retention_bits,
            excludes='die ancillary controls, external HBM capacity, engines and behavioral scheduler. Dead codec/q and tied-off compat branches may prune. No synthesized size claim.'),
        compute=dict(MACs_per_cycle=0,compute_intensity_MACs_per_HBM_byte=0,
                     communication_HBM_to_useful_stage_ratio=544/528,
                     communication_to_engine_bits_per_job=32*16960),
        ports=dict(HBM_client_read_Bpc_peak=32,sector_stage_write_Bpc_peak=32,
            scale_stage_write_Bpc=16,stage_read_Bpc_per_bank=528,stage_read_Bpc_total=4*528,
            attention_bytes_equivalent_per_beat=16960/8,
            producer_accept_payload_bits=256+8,producer_HBM_write_per_block_bytes=64,
            credit8_admission_not_rate='Eight tickets hide latency, not eight issues/returns per cycle. A full row cannot use the32PC peak; only2to5codePCs touched for thisregion, one host return selector.'),
        boundaries_bits=dict(request_per_stack_with_valid=1+30+4+16+1+256+32,
            response_per_stack_with_valid=1+16+4+256,
            total_bidirectional_per_stack_with_handshakes_write_done=620,
            four_stack_client_bus_total=4*620,
            backend_request_per_PC_with_valid=1+30+4+17+1+256+32,
            backend_response_per_PC_with_valid=1+17+4+256,
            backend32PC_bidirectional_with_handshakes_write_done=32*621,
            stage_fill=1+10+21+5+256+1,stage_invalidate=1+21,
            stage_request_with_ready=1+10+21+4+1,
            stage_response=1+10+21+4+4+16896+1,
            attention_with_mask_valid_ready=16960+4+1+1,
            schedule_prefetch=1+1+10+21,schedule_issue=1+1+10+21+8,
            retention_content_key_declared=320,retention_content_key_used=16+32+2+30+30+10+21+8),
        replicas_mux_demux_fanout=dict(source_replicas_per_active_die=1,stage_banks=4,slots_per_bank=32,
            HBM_stacks_existing=4,PCs_per_stack=32,window_targets_one_stack=True,
            stage_read_bit_2to1_mux_equivalents=4*4224*31,
            bank_rotation_bit_2to1_mux_equivalents=4*4224*3,
            return32to1_bit_2to1_mux_equivalents=31*(16+4+256),
            K_fanout='One340-bit client request bus feeds32per-PC2:1 muxes/address-match guards; grant/ready reduces back to one client. Return lowest-PC32:1 over276data/tag/beat bits, demux by backend owner bit then two client-owner bits.',
            refill_fanout='5-bit reply sector drives17issued/received selections, poison choice and one of16sector enables; 7-bit row slot splits2-bit bank/5-bit slot. 256fill bits reach4banks but only one writes. No added global bus for credits8.',
            retention_fanout='320-bit key equality in registered decision (149used bits, restzero); stage validity/source checks and one16-bit lifecycle generation. No new payload replication.'),
        clocks=dict(source_schedule_stage_mux_arbiter='same clk, same reset; no CDC/FIFO at these boundaries',
            backend_internal_CLK_PS=1000,phy_binding='CLK_PS forwarded to W only; u_k default1000',
            exactness_scope='Event-cycle model only; do not convert a replay bench wall-period into qualified frequency.',
            physical_target='Existing policy1.2GHz streaming and0.9GHz serial chains; controller SS/FF contextual timing and CDC to serial units not priced by this behavioral port. No clock/uncertainty change.',
            uncertainty_policy_ps=dict(setup=60,hold=25)),
        contention=dict(assumed_for_conditional_cost='No CKV/RoPE/index requests or pending responses; no writes; reset-origin closed banks; no fault; legal epoch; region sufficient; correct source handshakes.',
            actual_priorities='WINDOW priority over CKV, alternating KV/RoPE perstack, per-PC round-robin K/index. K responses lowestPC first, one perstack percycle; other ready K returns are held in backendRQD32.',
            backend='QD64/RQD32 perPC,FR-FCFS RW16/MAXSKIP16 and ACT/PRE/refresh state. Credit8 changes admissions, schedule/refpb3 queued-bank scores, row hits and return collisions. Do not divide credit1time by8.',
            interference_unbounded_without_contract=True,
            W_port='Separate behavioral timing group; physical K/W bandwidth interference not modeled.'),
        latency=dict(exact_parametric_constant_service_cases=constant_cases,
            definition='L=response handshake edge minus grant edge, >=1. Always-ready requester/return, identicalL per sector, no competitors/faults, rows initially unstaged. Abstract memory service, not HBM timing.',
            recurrence='For C>1: a_i=max(a_(i-1)+1,b_(i-C)+1) for codei>=C; firstC at consecutivecycles; b_i=a_i+L. Scale a16=max(b0..b15)+1, b16=a16+L. Credit1 FR/FR_DONE: a_(i+1)=b_i+1.',
            closed_form='d1=17L+16; dC=floor(15/C)*max(C,L+1)+(15%C)+2L+1 (C>1). For8,L>=7: d8=3L+9. d is firstgrant to scale-response span.',
            schedule_edges='Descriptor/source start S; firstrow prefetch atS+1, firstgrantS+2. Nextrow firstgrant=prior scale-response+3. Finalresponse B; schedule entersISSUE atB+1 and staged_v rises; lifecycle captures stage atB+2. refill_cycles=B-S+1=sum(row d)+384 for128rows.',
            actual_credit1_recurrence='For variable backend B(a,state), d1(row)=sum17response-delays+16FSMedges. Neither fixedL nor measured scalar+2padding is actual source FR/FR_DONE+1.',
            timed_credit8_exact_numeric_cycles=None,
            unresolved_timed_composition=['source grant versus backend admission through actual owner muxes',
                'queued reads and per-PC FR-FCFS/refresh at changed admission edges',
                'lowestPC return arbitration/backpressure with OOO replies',
                'source row barrier and actual schedule counter/start alignment'],
            backend_REQ_CL_BURST_RSP_ps=[10000,12500,1024,10000],
            minimum_read_response_delay_cycles=34,
            conditional_lower_bounds_schedule_refill_cycles=dict(credit1=128*(row_span(1,34)+3),credit8=128*(row_span(8,34)+3)),
            lower_bound_scope='REQ+CL+BURST+RSP floor only; extra ACT/refresh/return competition cannot make responses earlier. Not attainable proof or timing prediction.',
            finite_numeric_upper_bound=None,
            upper_bound_reason='No enumerated composed idx_hbm admission/refresh/return-state solution, and unspecified competitors/backpressure permit unbounded wait.'),
        previous_backend_proof=dict(commit=REPLAY_COMMIT,path=replay_path,record_sha256=digest(replay_raw),
            elapsed_cycles=125627,reads=2176,refreshes=35242,activations=2154,
            padding='fixed driver response+2 and perrow+3; actual prefetch response+1, nextrow+3, differenttags and transport. Do not transfer its number to composed source, credit8, PV or another layer.',
            measurement_scope='One fixed direct cold case at12300; TAGW16 vs actual17, patternMEM_WORDS1; no payload/capacity or clock qualification.'),
        prior_functional_evidence=dict(pin_checks=pin_checks,cases=historical,
            synthetic_service='qdue=cycle+latency+((cycle*7)%13)+1; registered response consumed nextedge; periodic request refusal cycle%7;8slots/last-ready-slotOOO; no idx_hbm.',
            prior_stream='STREAM_II1=1 in prior gate; actual default0. Its74two-jobstream_cycles cannot be imported into default compat drain.',
            poison_and_bad_tags=prior['fault_cases'],
            scope=prior['scope']),
        retention=dict(scope='Single-use exact same-content L0QK->PV, not across-token cache.',
            skipped_on_hit=dict(HBM_reads=2176,rows_refilled_by_IO=0,new_payload_bits=0),
            key='16formatversion +32content_epoch +2stack +30base +30count +10user +21first +8count =149bits zero-extended to320. No layer-id field; caller restricts operation to approvedL0 shape.',
            source_key_used_bits=16+32+2+30+30+10+21+8,
            admission='Complete QK engine+lifecycle AND storage drain; matching physical key; PVexactshape128rows; fresh nonzero generation; not generationwrap. Request consumes arm once, even a miss.',
            invalidations='accepted block/prime, regionconfig, retain_invalidate(t_start or badregion),fault,reset; external region writers require exclusion/coherency separately.',
            hit_control_edges='SourceacceptA capturespending and registered hit; schedule accepts response atA+1 ->ISSUE; staged_v rises afterA+1; lifecycle sees stage atA+2. refill_cycles=0, but request/dispatch/stage edges are notzero.',
            misses='ordinary row refill; BANKED_STAGE=1 refills even if stage tags remain. A newtoken t_start invalidates retention; no warmtoken saving credited.',
            engine_and_SU='Probability preload, softmax/SU and PV arithmetic still required. Drain requires all32acceptedbeats and engineidle.',
            prior_gate='results/rtl/v41_window_retention_gate.json syntheticproducer+descriptors+VMelapsedslots, no numericattention/full-layer/realsharedHBM adoption gate.'),
        area_routing=dict(basis='Logical declaration upper estimate using unifiedDFF0.2916um2 and ASSUMEDbitmux0.2um2; no synthesis, SRAM mapping, route or SS/FF claim.',
            source_flop_equivalent_mm2=area_flops,partial_stage_mux_mm2=area_mux,
            partial_source_cell_mm2=area_flops+area_mux,
            partial_source_footprint_at_50pct_util_mm2=2*(area_flops+area_mux),
            credit_metadata_increment_flop_mm2=55*0.2916/1e6,
            retention_metadata_increment_flop_mm2=retention_bits*0.2916/1e6,
            primary_adjacent_boundary_tracks=16937+16966,
            illustrative_channel=dict(width_um=64,signal_layers=4,pitch_um=0.08,capacity_tracks=3200,
                required_corridors=11,required_width_um_at_fullutil=(16937+16966)*0.08/4,
                qualification='ASSUMED both adjacent buses share one corridor concurrently; sum is a sensitivity, not a proved co-route. Capacity reused from unifiedGPUtransport; not actual WINDOW allocation or hub routing-layer PASS.'),
            actual_channel_capacity=None,actual_floorplan_slot_mm2=None,slot_fit='UNRESOLVED',
            delta_routing='Credits8 introduces no wider payload boundary; epoch/sector path and credit fanout still need contextual closure. STREAM_II1 has separate4beatbuffer cost and cannot be silently bundled.'),
        conditional_per_layer_critical_cost=dict(
            formula='producer_publish + refill_QK(C,QK_state) + QK_engine/replay_composed + serial_SU + (retention_hit? retention_dispatch:refill_PV(C,PV_state)) + PV_engine/replay_composed + descriptor/control. Charge overlap with max(engine,replay), not independent sums.',
            credit8_saving='[R1_QK-R8_QK] + (hit?0:[R1_PV-R8_PV]); each R from its own admission/time/bank state. R_PV need not equal R_QK.',
            retention_saving='R_PV(C,PV_state) minus added retention dispatch/control; one refill per eligible QK/PV pair only.',
            conversion='cycles times actual qualified domain period only after closure; no whole40multiplication or rate.',
            whole_token_cycles=None,per_user_rate_gain_pct=None,
            adoption_threshold='Cannot price>=1percent user-rate until this local cost is bound into the actual layer/tokencriticalDAG; no adoption in this record.'),
        readiness=dict(first128_epoch_domain='SOURCE_ADMISSIBLE_FROM_RESET',
            all_epoch_composed_tag_contract='FAIL',actual_credit8_timed_backend_equivalence='NOT_PROVED',
            actual_payload_capacity_numeric='NOT_QUALIFIED',physical_SS_FF_slot_and_routing='NOT_QUALIFIED',
            whole_layer_or_token='NOT_PRICED',adopted=False),
        next_cheapest_necessary_gate=dict(name='COMPOSED_TAG_ADMISSIBILITY_STATIC_GATE',
            run_in_this_task='Static integer counterexample recorded; no RTL bench/build run.',
            explicit_next='See standalone w17_window_epoch_contract.py: current1 safe; qualify legalfirst128 throughactualowner muxes+KARB+idx_hbm OOO/heldreturns. Retain epoch512FAIL;9bitwrap remains proposal pendingimplementation/drainqualification.',
            benchmark_or_build_requested_now=False))


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, help='new JSON path; never overwrite evidence')
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2)+'\n'
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(payload)
    print(payload, end='')


if __name__ == '__main__':
    main()
