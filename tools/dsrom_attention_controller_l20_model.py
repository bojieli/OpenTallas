#!/usr/bin/env python3
"""Git-only L20 selected-CKV composition and minimum finite service contract.

No payload, images, live jobs, RTL builds or physical tools are accessed. Existing
program/characterization failures remain immutable. Numeric service candidates
are explicitly conditional on source-selected providers and physical admission.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

REAL = '4e38326d6f361bc85e660f48c59c355e2bb95274'
BASE = 'e72abea5ae169d3167dddc89543013f0e6bb3a7a'
PRODUCT = 'ffb875bc8fca363fd6a86e63510045e363140e62'
LEASE = '2723dbc74a3f0b86e6a5f93b4e61743a4bd40e96'
RETURN = '6936feacb1a45a4d09bff36263af04379f3ca891'
JOINT = '030323d5f2d0b66c210f28cc4cf5e6498302c2fc'
PREFIX = 'results/rtl/w17_connected_token_preparation_20261001/'
SERVICE = 'rtl/chip/ot_chip_v41x_ckv_die_service.sv'
DIE = 'rtl/chip/ckvsel/ot_chip_v41x_die.sv'
CORE = 'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv'
MERGE = 'rtl/chip/ot_chip_v41x_ckv_stream_merge.sv'
PINS = {}
CACHE = {}


def read(commit, path):
    key = commit + ':' + path
    if key not in CACHE:
        raw = subprocess.check_output(['git', 'show', key])
        CACHE[key] = raw.decode()
        PINS[key] = dict(commit=commit, path=path, sha256=hashlib.sha256(raw).hexdigest())
    return CACHE[key]


def record(commit, path):
    return json.loads(read(commit, path))


def cite(path, needle):
    hits = [dict(line=i, text=s.strip()) for i, s in enumerate(read(REAL, path).splitlines(), 1) if needle in s]
    assert hits, (path, needle)
    return dict(pin=REAL + ':' + path, matches=hits)


def selected_calendar(first=126, count=128):
    """Scalar recurrence of MERGE two buffers, both primed before CKV phase.

    Old-state full prevents filling a buffer on its emission edge. Stage A
    completion becomes rdy two edges later. No arithmetic or payload emulation.
    Real engine ILV0 kv_ready holds until T rows; all ranks reserved at READY.
    """
    full = [True, True]
    rdy = [True, True]
    f = o = 0
    produced = 2
    cq = None
    emits = []
    for t in range(first, first + 2000):
        emit = rdy[o]
        fill = produced < count and not full[f]
        nf, nr = full[:], rdy[:]
        if cq is not None:
            nr[cq] = True
        if emit:
            nf[o] = nr[o] = False
            o ^= 1
            emits.append(t)
        cq = f if fill else None
        if fill:
            nf[f] = True
            f ^= 1
            produced += 1
        full, rdy = nf, nr
        if len(emits) == count:
            return emits
    raise AssertionError('Merger did not drain')


def build():
    prev = record(PRODUCT, 'results/uarch/dsrom_attention_controller_product_events_20261001/product_model.json')
    raw = read(PRODUCT, 'tools/dsrom_attention_controller_product_model.py')
    assert hashlib.sha256(raw.encode()).hexdigest() == prev['generator_sha256']
    env = dict(__name__='retained_model_only', __file__=str(Path(__file__).resolve()))
    exec(compile(raw, 'retained_product_model', 'exec'), env)
    # Adapt only the arrival calendar in memory; all controller recurrence code
    # is retained. Record this change explicitly, not as an unchanged model run.
    start = raw.index('def scheduler(')
    end = raw.index('\ndef adapter_envelope', start)
    src = raw[start:end]
    assert src.count('credit_count=64):') == 1
    src = src.replace('credit_count=64):', 'credit_count=64, row_calendar=None):')
    src = src.replace('row_available=first_row', 'row_available=row_calendar[0] if row_calendar else first_row')
    old = 'row_available=t+row_II;counts'
    assert src.count(old) == 1
    src = src.replace(old, 'row_available=(row_calendar[len(kv_load)] if len(kv_load)<len(row_calendar) else 100000) if row_calendar else t+row_II;counts')
    exec(compile(src, 'retained_control_with_bound_arrivals', 'exec'), env)
    merger_checks = 0
    for first in (1, 126, 1000):
        for count in (2, 8, 32, 128):
            times = selected_calendar(first, count)
            assert len(times) == count and times[0] == first
            assert all(b > a for a, b in zip(times, times[1:]))
            assert times[-1] <= first + 2*count
            merger_checks += 1
    window = [1 + 4*i for i in range(32)]
    selected = selected_calendar(window[-1] + 1)
    arrivals = window + selected
    a = env['scheduler'](640, row_calendar=arrivals)
    z = env['scheduler'](640, extra_cut=2, row_calendar=arrivals)
    assert a['KV_accept_cycles'] == arrivals
    assert a['QK_issue_cycles'] == z['QK_issue_cycles']
    assert a['PV_issue_events'] == z['PV_issue_events']
    assert a['Q_load_events'] == z['Q_load_events']
    assert a['P_load_events'] == z['P_load_events']
    for output in ('scores', 'PV'):
        assert [t+2 for t in a['outputs'][output]] == z['outputs'][output]
    assert z['adapter_A_RUN_completion_cycle'] - a['adapter_A_RUN_completion_cycle'] == 2
    assert a['counts'] == dict(Q_push=16, P_loader_pop=320, KV_accept=160, QK_issue=160, PV_issue=160, fill_issue=160)
    # Prove finite credit pricing is sensitive to a real admission parameter.
    neg = env['scheduler'](640, row_calendar=arrivals, credit_count=8)
    negcut = env['scheduler'](640, row_calendar=arrivals, credit_count=8, extra_cut=2)
    assert neg['QK_issue_cycles'] != negcut['QK_issue_cycles']
    qenv = env['adapter_envelope'](16*512, 16*40)
    penv = env['adapter_envelope'](16*640, 16*32)
    for e in (qenv, penv):
        e['post_joint_READY_runtime_cycles'] = e['go_to_job_acceptance_cycles'] + a['adapter_A_RUN_completion_cycle'] + e['run_complete_to_published_idle_cycles']
        e['with_common_cut_runtime_cycles'] = e['post_joint_READY_runtime_cycles'] + 2

    manifest = record('1895c0711', PREFIX + 'L0_cli_recovery_launch.json')
    paths = read(REAL, 'tools/w17_current_fastpp_l20_sources.txt').split()
    source_map = []
    # The source list contains RTL only (including an existing macro model).
    assert all(p.endswith(('.sv', '.v')) for p in paths)
    for p in paths:
        read(REAL, p)
        digest = PINS[REAL + ':' + p]['sha256']
        source_map.append(dict(path=p, sha256=digest, in_actual_L0_compile_manifest=p in manifest['source_sha256'],
                               same_as_actual_L0_compile_manifest=manifest['source_sha256'].get(p) == digest))
    for p in ('tools/w17_current_fastpp_die_rt.py', 'rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp'):
        read(REAL, p)
        assert PINS[REAL + ':' + p]['sha256'] == manifest['source_sha256'][p]
    lease = record(LEASE, PREFIX + 'ckv_publication_lease_model.json')
    returns = record(RETURN, PREFIX + 'ckv_prelease_return_contract.json')
    joint = record(JOINT, PREFIX + 'ckv_joint_boundary_contract.json')
    compatibility = []
    for contract, label in ((lease, 'lease'), (returns, 'prelease'), (joint, 'joint')):
        for oldpin in contract['source_pins'].values():
            if not isinstance(oldpin, dict) or 'path' not in oldpin:
                continue
            p = oldpin['path']
            read(oldpin['commit'], p)
            assert PINS[oldpin['commit'] + ':' + p]['sha256'] == oldpin['sha256']
            exists = bool(subprocess.check_output(['git', 'ls-tree', '--name-only', REAL, '--', p]).strip())
            if exists:
                read(REAL, p)
            compatibility.append(dict(contract=label, path=p, old_commit=oldpin['commit'],
                                       available_in_4e383=exists,
                                       hash_identical_to_4e383=exists and PINS[REAL + ':' + p]['sha256'] == oldpin['sha256'],
                                       authority='Requirements only; source equality does not transfer qualification'))
    bindpath = 'results/rtl/hdc_v41x_fullshape_1m_s20260930_l20_program_bind_rope_hbm.json'
    bind = record(REAL, bindpath)
    isa = 'tools/hdc_isa_v41.py'
    isa_env = dict(__name__='retained_ISA_only', __file__=str(Path(isa).resolve()))
    exec(compile(read(REAL, isa), isa, 'exec'), isa_env)
    hexpath = 'results/rtl/hdc_v41x_fullshape_l20_program.hex'
    words = [int(x, 16) for x in read(REAL, hexpath).splitlines()]
    assert len(words) == len(bind['instruction_trace']) == 144
    for word, ins in zip(words, bind['instruction_trace']):
        fields = {k: tuple(v) if isinstance(v, list) else v for k, v in ins['fields'].items()}
        assert word == isa_env['encode'](full_shape=True, **fields)
    trace = bind['instruction_trace']
    graph = env['program_dependencies'](bind)
    for node in graph:
        if node['pc'] in (55, 63):
            node['completion_duration_known'] = True
            node['completion_cost'] = qenv if node['pc'] == 55 else penv
            node['completion_scope'] = 'Conditional source-derived post joint READY; provider integration not admitted'
    evidence = record(BASE, 'results/rtl/v41x_ckv_selected_dma.json')
    pc21 = record(BASE, 'results/rtl/w17_current_fastpp_connection_20261001/PC21_L20/result.json')
    eligible = []
    for rec, label in ((evidence, 'standalone_selected_DMA'), (pc21, 'PC21_producer_control')):
        for p, digest in rec.get('source_pins', rec.get('pins', {})).items():
            if p.startswith('rtl/'):
                read(REAL, p)
                eligible.append(dict(gate=label, path=p, same_hash=PINS[REAL + ':' + p]['sha256'] == digest))

    citations = {
        'TOPK_ID_order': cite('rtl/chip/ot_coll_topk_merge.sv', 'global-id order'),
        'TOPK_histogram_drain': cite('rtl/chip/ot_coll_topk_merge.sv', 'row == nrow && !h0_v'),
        'TOPK_radix_binding': cite('rtl/chip/ot_w15_coll_dma.sv', '.DIG(TK_DIG)'),
        'TOPK_physical_width': cite(DIE, 'localparam integer CL_GW'),
        'encoder_completion': cite('rtl/chip/ot_chip_v41x_ckv_row_encoder.sv', "blk == 6'd31"),
        'opt_in_shape': cite(DIE, '.L0_ONLY(!CKV_SELECTED)'),
        'partial_stage_actual': cite(DIE, '.stage_rows(WINDOW_HBM_ATTENTION ? 11\'d128'),
        'partial_READY_guard': cite('rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv', 'stage_rows <'),
        'CKV_readiness_discarded': cite(DIE, '.rows_ready()'),
        'wrap_scope_actual': cite(DIE, '(!win_service_busy && window_prime_ready && !win_blk_v)'),
        'selected_start': cite(CORE, 'assign ckv_sel_v'),
        'own_QDQ_producer': cite(CORE, 'assign ckv_nw_we'),
        'write_release_on_grant': cite(SERVICE, 'wr_k == 4\'d8'),
        'writer_and_fetch_simultaneously': cite(SERVICE, 'go <= 1; f_job <= 1;'),
        'max_published_placeholder': cite(SERVICE, '.published_source_count(POS_W\'((1 << POS_W) - 1))'),
        'collector_unconditional_count_update': cite(SERVICE, 'npresent <= npresent +'),
        'collector_new_epoch_clear': cite(SERVICE, 'present <= 0; npresent <= 0; rel_on <= 0; tail <= 0;'),
        'ordered_collector': cite(SERVICE, 'present[32\'(rel) + i]'),
        'rank_globalID_check': cite(SERVICE, 'wgid[i*POS_W +: POS_W] != rd_gid'),
        'replay_QK_PV': cite(SERVICE, 'if (job_v && rel_ok)'),
        'merge_stage_latency': cite(MERGE, 'if (cq) rdy[cq_b]'),
        'merge_two_buffers': cite(MERGE, 'reg [4*16*265-1:0] beat0, beat1'),
        'C_write_rejected': cite('rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv', '!c_we[s]'),
        'C_write_forced_zero': cite('rtl/chip/ot_chip_v41x_kv_reqmux.sv', 'c_wr_done'),
        'actual_TOPK_support': cite(DIE, '.TOPK(FULL_SHAPE)'),
        'actual_TOPK_command': cite(DIE, 'core_coll_op == 2\'d3'),
        'dynamic_newblk': cite(CORE, 'dyn[db + FDYN_NEWBLK]'),
        'driver_link_calendar': cite('rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp', 'int CKV_LAT_U = 11'),
        'host_unconditional_ready': cite('rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp', 'd->ckv_ag_tx_ready = 1;'),
        'slot_PIPE1': cite('rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv', '.PIPE(1)'),
        'engine_KV_ready': cite('rtl/hdc/v41x/ot_hdc_v41x_attn.sv', 'assign kv_ready = act'),
    }
    # Listed source payload storage and explicitly bounded additional metadata, not a
    # full mapped cell census. No bitcell area is inferred from register area.
    storage = dict(window_stage_payload=128*4224, selected_collector_payload=512*2304,
                   CKV_DMA_slots_payload=64*2304, CKV_fetch_output_register=2304,
                   engine_staging_read_register=16960, selected_merger_beat_buffers=2*16960,
                   selected_merger_input_registers=4*4224+4*2304,
                   IDs_table=512*21, owned_rank_ID_list=512*(10+21),
                   own_capture_and_encoder_and_encoded_buffers=2*8192+2*2304,
                   engine_stage_payload=640*16*265, stationary_payload=64*3*16*32*16,
                   transposer_payload=64*2*32*8*18,
                   TOPK_candidate_key_and_ID_arrays=4*2048*64)
    staging_path = 'rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv'
    read(REAL, staging_path)
    macro_path = 'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.lef'
    lef = read(REAL, macro_path)
    size = re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)', lef)
    assert size
    width, height = map(float, size.groups())
    stage_abstract = dict(source=REAL+':'+macro_path, SRAM_MACRO_actual_default=0,
                         optional_source_branch_macros=4*17, depth_per_lane_used=160, macro_depth=256,
                         physical_capacity_bits=68*256*256, logical_payload_bits=640*16*265,
                         macro_outline_um=[width,height], source_abstract_area_um2=round(68*width*height,4),
                         qualification='Source LEF outline only; generated memory abstract, not measured engine floorplan or SSFF fit. No existing option changed.')
    topk_service = []
    for pc,n,k in ((47,512,512),(52,2048,2048)):
        nrow=4*n//64
        bound=4*(nrow+7)+nrow+10+math.ceil(k/64)
        topk_service.append(dict(pc=pc,N=4,candidates_per_rank=n,selected=k,P=64,PF=64,DIG=8,passes=4,
                                 histogram_rows_per_pass=nrow,filter_chunks=nrow,
                                 source_local_control_upper_cycles=bound,
                                 bound='After all gathered keys/IDs stored and go accepted, faultfree: four HIST(nrow+4)/PICK3 passes, FILTER nrow, conservative10pipeline/drain edges + outputgroups. DMA reserves4VMwrites/cycle; network/gather phase charged separately.',
                                 array_capacity_candidates=8192,array_payload_bits=524288))
    # Minimum generation/epoch reservation metadata, explicit chosen design,
    # always opt-in; existing present512 bitmap and IDs are not charged again.
    additions = dict(collector_epoch=16, descriptor_join_flags=8,
                     selection_and_producer_credit=2, row_identity=21+10+6+16,
                     row_write_visible_bitmap=9, row_write_owner=14,
                     DMA_slot_epoch=64*16, three_outgoing_row_skids=3*(2304+10+21+16+1),
                     collector_epoch_reservation_flags=512,
                     peer_credit_counters=3*10, controller_cut=141382)
    added_bits = sum(additions.values())
    # Proposed conservative logical links: full row delivered in 2 cycles on
    # board, 1 on UCIe, including generation. Existing host queue is not hardware.
    packet_bits = 2304+10+21+16
    routes = [dict(boundary='CKV owner to each of three peers', replicas=3, packet_bits=packet_bits,
                   bits_per_cycle_required_board=math.ceil(packet_bits/2), bits_per_cycle_required_UCIe=packet_bits,
                   row_service_board_cycles=2, row_service_UCIe_cycles=1,
                   maximum_rows_per_source=512, collector_seats_per_destination=512,
                   hardware_port='generation16 + rank10 + globalID21 + payload2304 + valid/ready/credit',
                   current_port='ag_tx_valid/ready; three ag_rx_valid lanes without ready or epoch',
                   location='four TP ranks; peer rank xor1 UCIe, other two board links; no measured controller coordinates'),
              dict(boundary='collector to selected merger', replicas=1, signal_tracks_lower_bound=4*2304+3+10,
                   peak_payload_Bpc=1152, conditional_sustained_payload_Bpc=576,
                   fanout='512-to-1 row mux for each of four 2304-bit read ports; 5 write sources require banked collision handling'),
              dict(boundary='WINDOW/CKV mux to attention staging', replicas=1, signal_tracks_lower_bound=16960+4+2,
                   peak_payload_Bpc=2120, fanout='two16960bit candidates; stage write enables64 groups',
                   location='hub edge to four attention row lanes'),
              dict(boundary='controller E to tile R0 uniform cut', replicas=64,
                   signal_tracks_lower_bound=64*(525+579)+35, bits_per_cycle=64*(525+579)+35,
                   fanout='64 replicated load/issue consumers, shared35bit result-tag path; no9537 serial factor',
                   location='real engine replicas; characterization stub origins are not real slots'),
              dict(boundary='reserved HBM return landing', replicas=4, guaranteed_candidate_bits_per_cycle_per_stack=256,
                   source_peak_B_return_bits_per_cycle_per_stack=32*256, aggregate_candidate_bits_per_cycle=1024,
                   existing_B_ROB_bytes_per_stack=131072, CKV_slot_bytes_per_die=18432)]
    read_cycles = math.ceil(returns['pricing']['read_service_candidate_envelope_ps']*3/2500)
    coarse = dict(prelease_frozen_queue_candidate_cycles=returns['pricing']['coarse_frozen_queue_candidate_pluslanding_cycles'],
                  own_nine_visible_writes_candidate_cycles=lease['numeric_pricing']['ninewrite_group_cycles_with_sampling_turnover_publish'],
                  selected_read_sectors_worst_owner_stack=512*9,
                  selected_read_candidate_cycles=512*9*read_cycles,
                  WINDOW_read_sectors=128*17, WINDOW_read_candidate_cycles=128*17*read_cycles,
                  peer_delivery_serial_tail_candidate_cycles=142+2*512+2,
                  read_candidate_cycles_per_sector=read_cycles,
                  QK_and_PV_post_READY_cycles=qenv['post_joint_READY_runtime_cycles']+penv['post_joint_READY_runtime_cycles'],
                  common_controller_cut_two_ops_cycles=4)
    coarse['phase_serial_candidate_total_cycles'] = sum(coarse[k] for k in (
        'prelease_frozen_queue_candidate_cycles','own_nine_visible_writes_candidate_cycles',
        'selected_read_candidate_cycles','WINDOW_read_candidate_cycles','peer_delivery_serial_tail_candidate_cycles',
        'QK_and_PV_post_READY_cycles','common_controller_cut_two_ops_cycles'))
    phases = [
        ('previous_epoch_retired', 'new_selection_ids', 'all C/P/W/backend/peer old jobs retired; new selection guard; no stale collector writes'),
        ('new_selection_ids', 'id_done', 'PC47 actual TOPK->PC53 trigger; 32 VM words, one512bit word/cycle plus clear/capture/quarter-close pipeline'),
        ('actual_PC38_QDQ4E', 'encoded_row', '16 accepted32element beats then32 encoder blocks; captured buffer retained through publication'),
        ('id_done+encoded_row', 'exclusive_lease', 'quiesce only new jobs; old posted replies retain landing reservations; old index already retired at collective waits, not rescanned'),
        ('exclusive_lease', 'row_published', '9 distinct actual burst-visible events, one W/C owner perstack; hold row/globalID/epoch; no column/accept substitute'),
        ('row_published', 'selected_gather', 'release new f_job; IDs bounded by real published rows; reserve512 rank seats and 3 copy hop credits'),
        ('selected_gather+WINDOW128_staged', 'joint_READY640', 'all512 present matching IDs andepoch, WINDOWuser/absolute rows valid, writer complete, nofault'),
        ('joint_READY640', 'PC55_QK', 'published SU idle afterPC54; descriptor generation stable; adapter A_LDX then Q push and QK issues'),
        ('PC55_QK', 'PC61_scale_max', 'wait1 actual ME idle afterall160scores+8PVoutputs+VMwrites, not score expectedcount alone'),
        ('PC61_scale_max', 'PC62_exp', 'SU idle wait2 and exact reducer/SFU order; no activation injector'),
        ('PC62_exp', 'PC63_PV', 'wait2 actual SU idle; same640row rank order replay with retained IDs/collector'),
        ('PC63_PV+PC64_DEN', 'PC65_divide', 'wait3 ME/SU both completed; no producer-perfect-service assumption'),
        ('PC65_divide', 'PC66_inverse_RoPE', 'actual SU idle, read-only RoPE hold retained'),
        ('PC66_inverse_RoPE', 'PC67_release+epoch_credit', 'release afterSUwait2; descriptor160beats DRAIN->IDLE + MEoutputs/writequiet + peerempty; returncredits only then')]
    missing = [
        dict(provider='L20 die joint_READY/retirement', existing='CKV_SELECTED variant and lifecycle L0_ONLY0 exist; READY accepts partial128 rows',
             required='Opt-in source-selected all512 present/epoch/globalIDs + WINDOW128 join, CKVfault into lifecycle, full C/writer/peer retirement at wrap; retain L0_ONLY1 source path',
             priced='512seats existing collector; newepoch/reservation/join ledger below'),
        dict(provider='actual produced own row publication', existing='PC38 QDQ4E mirror16blocks and exact encoder32blocks; C writes rejected, c_wr_done ignored',
             required='writable mux and held W/C owner; actual burst-visible backend, nine unique accepted ACKs then publish; hold producercredit until visible and consumercredit until finaldone',
             priced='2952cycle exclusive write candidate + backend8192FF/.0443039744mm2 and frontend .0004689648mm2 from lease; no duplicate payload buffer'),
        dict(provider='selection/index/GID mapping', existing='144ISA encodes; actual TOPK and NEWBLK now present although bind still says blocked',
             required='Provider source gate on actual X_IDX2/X_SEL1 ring + TOPK global stride; bind published_source_count to real corpus/currentproducedrow not max21bit constant; guarantee own row placement if using rankK-1 fastpath',
             priced='32VMread words + quarterclosures; IDs10752bits and own-list15872bits, fiveIDreadports; compile changedsource audit mandatory'),
        dict(provider='finite peer transport', existing='host unbounded deques/ready1,11/142cycles/boardII2; noRXready/generation',
             required='3 finite transmit skids, preallocated512rank seats/receiver, epoch qualification and real hop/reversecredit calendar; 2cycles/row demands1176payload+metadata bits/cycle on board',
             priced='3*2352bit skids;511previousrows cannot overwrite samecollector until finaldrain; worst512rows2cycle+142hop conditional'),
        dict(provider='backend finite timing', existing='finite QD64/RQD32 and reserved postedreceivers from returncontract; actual backend default clock1000ps',
             required='Exact1.2GHz forwarded clock, actual bank/queue/refresh/drain recurrence validates357cycle read and326cycle write candidates; old remainingproducer work bound by actual issue events',
             priced='3072landingcycles/stack;734237coarse frozenqueue candidate; no claim of finite current-source write/peer maximum'),
        dict(provider='physical context and product CDC', existing='runtime die/attention/CKV sharedclk; original b819 characterisation fails',
             required='Real4e383 engine64replica abstracts/endpoints/channel widths/directional M2-M5 pitches+occupancy and full slot census; serial SU0.9GHz to streaming1.2GHz CDC and reversecredit measured/sized',
             priced='commoncut141382FF/41226.9912um2 retained; other state/ports below, no area fit or wirelength inferred')]
    return dict(schema='opentallas.dsrom.controller.L20-source-composed-model.v1',
        verdict='L20_MINIMUM_OPT_IN_MODEL_SIZED_CURRENT_CONNECTED_SOURCE_NOT_BUILD_READY',
        model_review_ready=True, engine_RTL_build_ready=False, physical_admission=False, launch_allowed=False, adopt=False,
        original_failure=prev['original_failure'],
        source_binding=dict(real_commit=REAL, characterization_commit=prev['characterization_vs_real']['characterization_source'],
             actual_L0_manifest_source_count=145, manifest_and_census=prev['manifest_binding'],
             L20_source_list_pin=REAL+':tools/w17_current_fastpp_l20_sources.txt', L20_source_count=len(paths), sources=source_map,
             actual_L20_compile_measured=False, engine_params=prev['manifest_binding']['compile_params'],
             driver_flags=['--l20','-GX_IDX=2','-GX_SEL=1','-GIDX_RING=1','-GSUN=256','-GSUM=64','-DV41_ATT_CUT','-DV41_L20'],
             wrapper=dict(CKV_SELECTED=1,CKV_NSLOT=64,WINDOW_HBM_ATTENTION=1,K_MEM=1<<24),
             provenance='Existing variant of same source4e383; source availability does not mean current L0 manifest compiled L20 top. Source-pinned standalone model additions only.',
             contracts_source_compatibility=compatibility),
        source_finite_producers=dict(selection_TOPK=topk_service,
             ID_loader=dict(words=32,word_bits=512,read_Bpc=64,quarter_close_tokens=3,
                  conservative_post_trigger_cycles=42,condition='Reserved synchronous VMport, no new clr or epoch reset;32reads + clear/request/capture and three two-edge quarterclosures; no network/SU inference.'),
             own_encoder=dict(capture_beats=16,capture_Bpc=64,blocks=32,
                  last_capture_to_service_encoded_visible_cycles=34,condition='Own16 distinct32element beats, encoderidle; nextedge ld_v then32block iterations then service enc_done sample. Upstream QE service remains producer-bound.'),
             VM_consumer='G4 reads and writes per adapter clock after published SU idle; actual CROM/RoPE/SFU/reducer arrival and0.9GHz CDC remain separate dependencies, no golden activation service.',
             source_macro_branch=stage_abstract),
        program_provenance=dict(instructions=144, reencode_pass=True, ISA_pin=REAL+':'+isa, bind_pin=REAL+':'+bindpath,
             program_pin=REAL+':'+hexpath, current_program_sha256=PINS[REAL+':'+hexpath]['sha256'],
             retained_status=bind['status'], retained_blockers=bind['blockers'],
             added_provenance_correction='Actual L20 die source supports TOPKop2 and rank-aware NEWBLK; historical bind blocker remains immutable and current source gate still required. L0 stale bind hash resolved only by independent reencode in ffb875, original untouched.',
             issue_graph=graph, relevant_instructions=[i for i in trace if i['pc'] in (21,22,38,45,47,52,53,54,55,61,62,63,64,65,66,67)]),
        minimum_opt_in=dict(default_off=True, source_implementation_applied=False, retain_original_L0_only=True,
             dimensions=dict(WINDOW=128,selected=512,total_rows=640,heads=16,D=512,tiles=64,PWORDS=1,ILV=0,REPL=0,NSTAGE=1),
             row_order='absolute WINDOW rows pos-127..pos, then selected ranks0..511; duplicate/out-of-order/globalID mismatch faults. Rowindex128+rank is engine position; GID is not this local index.',
             owner_mapping='die=GID[5:4]; stack=GID[7:6]; local=((GID>>8)<<4)|GID[3:0]; sector=CKV_BASE+9*local+k',
             own_row='PC38 QE QDQ4E actual produced row; address>>9 suppliesglobalID. PC21/22 areWINDOW row writes, not selected own row. Do not inject SU/golden values.',
             selected_limits='Current source requires strictly increasing IDs and assumes own row if selected isrank511. Bind producer ordering and real published count; mask current own row out of HBM fetch only with exact tagmatch.',
             joint_READY='WINDOW128 valid + all512selected rank/GID/epoch seats present + ninevisibleownwrites + stableselection + faultfree; stage_rows640 prospective join; actual partial128 READY source retained as evidence',
             reuse='Replay same immutable collector for QK thenPV; two descriptor generations, same selectionepoch; release onlyafter both consumer episodes+finalSU/RoPE+peer/backendquiet',
             clock_domains='Actual runtime sharesclk; source-local zeroCDC only there. Productstreaming1.2GHz/serialSU0.9GHz uses3/4ticks at3600MHz and explicitCDC/returncredit.',
             phase_dependencies=[dict(producer=p,consumer=c,acceptance=g) for p,c,g in phases]),
        local_controller=dict(arrival_calendar=arrivals, baseline=a, common_two_cycle_cut=z,
             calendar_binding='WINDOW compatibilityII4 followedby exact two-buffer selectedMERGE scalar recurrence. Two buffers preprimed whileA_LDX; jointREADY guaranteesall ranks, actualILV0 engineKVready until640rows.',
             recurrence_provenance=dict(retained_tool=PRODUCT+':tools/dsrom_attention_controller_product_model.py',
                    retained_sha256=prev['generator_sha256'], adaptation='In-memory row arrival calendar only; unchanged accept/credit/bank/control recurrence'),
             QK_adapter=qenv,PV_adapter=penv,
             cut='Mandatory prospectivecommon2cycle E->R0 load/issue/tag alignment remains priced; diagnostic, no certifiedminimum or physicalclosure',
             cut_credits=dict(score_reserved=64,PV_reserved=64,score_debt=z['max_credit_debt']['score'],PV_debt=z['max_credit_debt']['PV'],
                    input_probability_skid_entries=0,added_cut_skid_entries=0,source_stationary_banks=3,GUARD_Q=20,GUARD_P=16,
                    issue_schedule_unchanged=True,completion_delta_per_job=2,
                    basis='All loads and reads shift together; guardRAW/WAR margins retained. Credit return from adapterregister, not perfectservice; both outputs drain before reuse.'),
             two_ops_counts={k:2*v for k,v in a['counts'].items()},
             critical_path_events=dict(controller_completion_joins_per_L20_rank=2,uniform_cut_two_joins_cycles=4,
                    uniform_cut_two_joins_common3600MHz_ticks=12,whole_graph=prev['actual_critical_dependency_counts']['whole_functional_graph'],
                    fanout_serial_multiplier=1, scope='Actual144ISA dependency joins bound; full40 hardware schedule not certified. No9537multiply.'),
             negative_credit_case=dict(credits=8,baseline=neg['adapter_A_RUN_completion_cycle'],cut=negcut['adapter_A_RUN_completion_cycle'],
                    changed_issues=True)),
        storage_bits_per_die=storage, storage_total_bits=sum(storage.values()),
        added_opt_in_register_budget=dict(fields=additions,total_bits=added_bits,DFF_cell_area_um2=round(added_bits*.2916,4),
             backend_provider_additional_register_bits=8192,
             frontend_owner_FF_already_counted=True,
             area_scope='Exact specified register-state subtotal using inherited .2916um2/FF. Excludes reset/clock/hold/buffers, combinational cell sizing and placement. Existing memory bits not priced as free or as FF area.'),
        combinational_budget=dict(collector_four_read_mux_bit_equivalents=4*(512-1)*2304,
             collector_five_write_candidates_bit_equivalents=512*2304*4,
             fetch_four_stack_64slot_request_mux_bit_equivalents=4*(64-1)*(30+10+1),
             selectedID_five_read_mux_bit_equivalents=5*(512-1)*21,
             selected_WINDOW_beat_mux_bits=16960, source_own_row_fanout_copies=3,
             inherited_mux_area_basis_um2_per_bit=.2,
             collector_four_read_naive_mux_area_um2=round(4*(512-1)*2304*.2,4),
             collector_five_candidate_naive_write_mux_area_um2=round(512*2304*4*.2,4),
             scope='Naive mux-equivalent pressure, not mapped area; banked macro implementation must price5writes/4reads and select paths. Prior gates do not certify these macros.'),
        ports_and_routes=routes,
        intensity=dict(peak_MACpc=32768,Q_input_Bpc=1024,P_input_Bpc=64,KV_peak_Bpc=2120,
             WINDOW_compat_Bpc=530,CKV_two_buffer_sustained_engine_Bpc=1060,VM_read_Bpc=16,VM_result_write_Bpc=256,
             selected_HBM_bytes=512*288,WINDOW_cold_HBM_bytes=128*17*32,own_write_bytes=288,
             useful_MACs_per_QK_or_PV=16*640*512,
             actual_MACs_per_controller_job=2*16*640*512,
             actual_MACs_two_controller_jobs=4*16*640*512,
             execution_scope='Current adapter invokes both QK andPV eachjob and discards the unusedhalf; exactcurrentcontroller issuecost retained, no assumedhalfengine.',QK_MAC_per_KV_logical_byte=(16*640*512)/(640*530),
             packed_boundary_bits_per_job=160*16960, runtime_att_to_bits=25690,runtime_att_from_bits=35938),
        finite_service_candidate=dict(numeric=coarse,lease=lease['numeric_pricing'],prelease=returns['pricing'],
             current_unconditional_finite_bound=False,
             logical_cycle_composition='This subtotal treats adapterports and backend as source-derived streaming ticks in the proposed1.2GHz contract. Existing runtime sameclk/defaultbackend1000ps is not a productclock qualification; product0.9GHz SU/CDC and VMport rate require explicit intake.',
             condition='Serialized finite work phases withreservedlanding/seats andexclusiveactualvisiblewriter; HBM326/357cycle candidates require actualrefresh/controller recurrence validation. This is a numerical service contract, not current-source maximum.',
             exclusions_priced_separately='PC38 producer/encoder prefix, selection/indexscan/TOPK/SU and RoPE durations, oldremainingproducerjobs, WINDOWwrites, CDC/route turnaround; serialcandidate is subtotal, never a full token bound.',
             existing_calibration_reused='ffb875 L0 timedprovider sensitivity retained, not rerun or transferred toL20 GID addresses/bankstate; source-bound persector candidate from existing lease/return contracts'),
        exact_build_readiness_prerequisites=missing, source_citations=citations,
        prior_source_correctness=dict(gate_hash_comparisons=eligible, retained_DMA_scope=evidence['scope'],
             retained_PC21_scope=pc21['scope'], qualification_transferred=False,
             note='Same hash may be eligible for source-correctness intake only. StandalonePIPE0 gate doesnot qualify64PIPE1slots, full640source, persistence, peertransport, or SSFF.'),
        physical_budget=dict(slot_fit='HOLD_REAL_CONTEXT_REQUIRED',route_capacity='HOLD_MEASURED_SOURCE_ONLY',
             capacity_equation='sum_directional_layers floor(usable_channel_width/pitch)*available_fraction - reserved/blocked tracks; compare per-boundary simultaneous signal demand above',
             geometry='No new geometry fabricated. Original1387.152um is cell-origin polyline, not routedwirelength. Original9537loads are oldstubfanout. No realsource placement/route capacity receipt supplied.',
             backend_additional_area_mm2=lease['backend_correction']['additional_backend_ports_and_area']['additive_footprint_mm2'],
             frontend_WC_total_area_mm2=.0004689648,
             frontend_WC_mux_only_additive_area_mm2=round(.0004689648-14*.2916/1000000,10),
             no_double_count='W/C14FF included inaddedbudget; addfrontendmux-only. Backend.0443039744 includes8192FF; do not addbackendFFareaagain. StageLEFarea is optionalreplacementbranch, not a newaddition to behavioralFFestimate.',
             explicit_source_array_FF_realization_um2=round(sum(storage.values())*.2916,4),
             array_area_scope='Screen ifall listed sourcepayloadarrays realized asFF; doesnot claim mappedarea. Existing dictionaries/registers/control/pipeline omitted; macroalternative onlyforstage whereactualsourcebranch exists.',
             closure='No headlineclock, latencygain or >=1%adoption claim. Preserve SS-750.63ps FF-53.12psFAIL and60/25psuncertainty. RealcontextSSFF/hubroute gate required after modelreview.'),
        four_targets=dict(DeepSeek_V41_ROM='Direct opt-in640row source/controller model; mandatory provider andphysicaljoins pending',
             Qwen3_ROM='Different source/shape; no controller/latency transfer',
             DeepSeek_V41_GPU_HBM='Ordinary SM/TensorCore/RF/TMEM/L2/HBM organisation; selectedKVworkload may share demand, not dedicatedDSROMcuts',
             Qwen3_GPU_HBM='Ordinary GPU comparator; no ROMspecific state or cut transfer'),
        checks=dict(ISA144_reencode=True,L20_source_list_hashes=True,contract_pin_audit=True,
             row160_accepts=True,credit_conservation=True,common_cut_two_cycles=True,bank_issue_invariance=True,
             collector_buffer_calendar_cases=merger_checks,negative_credit_sensitivity=True),
        operations=dict(new_files_only=True,RTL_edits=0,original_model_edits=0,payload_reads=0,builds=0,PnR=0,live_process_operations=0),pins=PINS)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    result=build()
    result['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=json.dumps(result,sort_keys=True,indent=2)+'\n'
    if args.output:
        if args.output.exists() and args.output.read_text()!=out:
            raise SystemExit('Immutable evidence differs; choose a new path')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(out)
    else:
        print(out,end='')

if __name__=='__main__':
    main()
