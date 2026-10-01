#!/usr/bin/env python3
"""Read-only source-pinned controller accounting; no RTL, P&R or payload access.

Run from any checkout retaining the named Git objects. Output is a gap verdict,
not implementation approval. Nominal traffic assumes one accepted beat/cycle;
no claim is made about consumer service or timing closure.
"""
import argparse
import hashlib
import gzip
import json
import math
import re
import subprocess
from decimal import Decimal as D
from pathlib import Path

BASE = 'e72abea5ae169d3167dddc89543013f0e6bb3a7a'
SOURCE = 'b819b7d2963875b1a8f99f1506b6307044b3caf0'
TIMING = '91d60f2bcd25ea7cb073b1d755195ef69796c154'
GEOMETRY = 'cd3621ddeb075084b064937e290a9bb694188a3c'
CHAIN = '21d2a89e318c9279767f70a581b3ab60da87ff62'
ENG = 'rtl/hdc/v41x/ot_hdc_v41x_attn.sv'
TILE = 'rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv'
ADAPT = 'rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv'
SERVICE = 'rtl/chip/ot_chip_v41x_packed_attn_service.sv'
MODEL = 'tools/uarch_model.py'
PINS = {}
TEXT = {}


def blob(commit, path):
    key = commit + ':' + path
    if key not in TEXT:
        raw = subprocess.check_output(['git', 'show', key])
        PINS[key] = {'commit': commit, 'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}
        TEXT[key] = raw.decode()
    return TEXT[key]


def cite(path, needle, commit=SOURCE):
    lines = blob(commit, path).splitlines()
    matches = [{'line': n, 'text': line.strip()} for n, line in enumerate(lines, 1) if needle in line]
    if not matches:
        raise ValueError('Missing source assertion: ' + path + ': ' + needle)
    return {'pin': commit + ':' + path, 'matches': matches}


def case(dim, rows, pwords=2, ilv=1, repl=2, nstage=2):
    h, td, nl = 16, 32, 4
    nt = nl * dim // td
    dpt = dim // nt
    nb = (4 if pwords == 2 else 3) + ilv
    bw = 3 if nb > 4 else 2
    blocks = math.ceil(rows / td)
    pbeats = sum(math.ceil(math.ceil(min(td, rows - b*td)/(td//h))/pwords) for b in range(blocks))
    load = pwords*td*16 + 3 + bw + 8
    issue = td*18 + 1 + bw
    tag = 16 + nl + 2 + math.ceil(math.log2(math.ceil(640/td))) + 8
    guard_p = max(max(0 if (2*g+j)%8 == 0 else 3*((2*g+j)%8-1) for j in range(2)) - g//pwords for g in range(h)) + 1
    state = {'load_bundle_per_tile_bits': load, 'issue_bundle_per_tile_bits': issue,
             'shared_output_tag_bits': tag, 'R0_load_bits_all_tiles': nt*load,
             'R0_issue_bits_all_tiles': nt*issue,
             'stationary_bank_bits': nt*nb*h*td*16,
             'transposer_bits': nt*2*td*dpt*18,
             'staging_bits': nstage*640*(dim//32)*265,
             'p_skid_bits': (2*pwords*td*16+4) if repl else 0,
             'controller_bank_held_count_bits': nb*6,
             'controller_blk_bank_bits': 4*bw,
             'E_load_data_control_bits': dim*16+pwords*td*16+3+bw+8,
             'E_issue_operand_bits': nt*td*18,
             'E_issue_control_bits': 1+1+bw,
             'E_output_tag_bits': tag,
             'REPL_transposer_index_select_copy_bits': nt*(1+1+8+nl+1+8+1) if repl else 0,
             'REPL_transposer_E_operand_bits': nt*td*18 if repl else 0,
             'complete_controller_register_count': None,
             'existing_tile_output_tag_delay_bits': tag*(27+3*2)}
    # Uniform full-bundle retiming is a sizing diagnostic, not a proposal.
    added = 2*(nt*(load+issue)+tag)
    return {'parameters': dict(H=h,D=dim,TD=td,NL=nl,TROWS=640,T=rows,PWORDS=pwords,
                               ILV=ilv,REPL=repl,NSTAGE=nstage,NT=nt,DPT=dpt,NBANK=nb,BW=bw),
            'state': state,
            'compute': {'MACs_per_cycle_peak': nt*h*td,
                        'QK_MACs_per_job': rows*h*dim, 'PV_MACs_per_job': rows*h*dim,
                        'QK_MACs_per_staging_byte': h*dim/((dim//32)*265/8),
                        'note': 'MAC count only; golden chunk8 FP32 chain and padded tree unchanged.'},
            'ports': {'Q_data_Bpc': dim*2, 'P_data_Bpc': pwords*td*2,
                      'KV_staging_write_data_Bpc': nl*(dim//32)*265/8,
                      'KV_one_staging_read_data_Bpc': nl*(dim//32)*265/8,
                      'KV_two_concurrent_reads_Bpc': 2*nl*(dim//32)*265/8 if nstage == 2 else None,
                      'E_to_R0_load_bits_per_cycle_sum_branches': nt*load,
                      'E_to_R0_issue_bits_per_cycle_sum_branches': nt*issue,
                      'E_to_R0_load_distinct_source_bits': dim*16+pwords*td*16+3+bw+8,
                      'scores_data_Bpc': nl*h*4, 'scores_fault_and_tag_bits': nl*h+16+nl+1,
                      'PV_data_Bpc': nt*h*4, 'PV_fault_and_tag_bits': nt*h+8+1,
                      'note': 'Physical registered widths, including format/pad; active payload may be lower. Ready/credit service rates unresolved.'},
            'replica_logic': {'load_select_2to1_mux_output_bits': nt*pwords*td*16,
                              'query_high_half_tied_zero_bits': nt*td*16 if pwords==2 else 0,
                              'stationary_data_three_choice_output_bits': nt*h*td*16,
                              'stationary_write_enable_destinations': nt*h*td,
                              'bank_write_demux_destinations': nt*nb*h*td,
                              'bank_read_mux_output_bits': nt*h*td*16,
                              'bank_read_mux_inputs_each': nb,
                              'mapped_mux_demux_buffer_area_um2': None,
                              'broadcast_control_R0_sink_copies_each': nt,
                              'note': 'Logical counts before optimisation. Real tile mode also fans to data muxes and write-enable decode; 9537 mapped loads is measured only on the stub.'},
            'schedule_counts': {'Q_load_accepts': h, 'P_loader_accepts': pbeats,
                                'total_load_accepts': h+pbeats, 'PV_blocks': blocks,
                                'QK_issue_beats': math.ceil(rows/nl), 'PV_issue_beats': blocks*dpt,
                                'PV_fill_beats': blocks*(td//nl),
                                'QK_to_tile_output_cycles_from_E': 33,
                                'PV_output_merge_cycles': 3*math.ceil(math.log2(20)),
                                'GUARD_P': guard_p, 'GUARD_Q': 20,
                                'P_allocation_count_threshold': 20-guard_p+1,
                                'issue_guard_count_reload': 20+1+(1 if repl>=2 else 0),
                                'load_and_issue_II_peak': 1,
                                'actual_job_II': None},
            'conditional_two_extra_stage_sizing': {'certified': False,
                 'load_only_added_bits': 2*nt*load,
                 'uniform_load_issue_shared_tags_added_bits': added,
                 'DFF_cell_area_um2_estimate': float(D(added)*D('0.2916')),
                 'load_select_existing_mux_area_um2_assumed': nt*pwords*td*16*0.2,
                 'basis': 'DFFHQNx1 0.2916um2 and 0.2um2/bit mux assumptions retained from unified model. Excludes clock/buffers/reset/hold-repair/placement area. Uniform two-stage full bundle diagnostic only; no topology selected.'},
            'restricted_latency_envelope': {
                 'serial_set_dependencies_per_job': 1+blocks,
                 'extra_cycles_interval': [0, 2*(1+blocks)],
                 'upper_extra_ps': 833*2*(1+blocks),
                 'assumptions': 'Only each complete Q set and each P block visibility delayed by 2; II unchanged, all other arrivals fixed, no feedback, arbitration, bank-reuse or credit changes. Longest max-plus path crosses each set dependency at most once. This is NOT a bound on the real engine with changed feedback.',
                 'full_engine_extra_cycles': None,
                 'critical_path_traversals': None,
                 'unrestricted_backpressure_bound': 'No finite upper bound without producer/consumer service guarantees.'}}


def compose_event_graph(graph, extra_fast_cycles, period_ps=833):
    """Max-plus composition on an expanded, source-bound finite event DAG.

    Traffic/credit/reuse recurrence must be expanded by the caller. This helper
    does not replace the engine's dynamic arbitration with independent edges.
    """
    if extra_fast_cycles < 0 or period_ps <= 0:
        raise ValueError('Invalid cycle/clock input')
    base, cand, paths = {}, {}, {}
    for node in graph:
        name = node['id']
        if name in base:
            raise ValueError('Duplicate event')
        dur = D(str(node['duration_ps']))
        if not dur.is_finite() or dur < 0:
            raise ValueError('Event duration must be finite and nonnegative')
        pred = node.get('predecessors', [])
        if any(p not in base for p in pred):
            raise ValueError('Event DAG must be topological and fully bound')
        added = D(str(extra_fast_cycles))*D(str(period_ps)) if node.get('controller_visibility_dependency', False) else D(0)
        base[name] = max((base[p] for p in pred), default=D(0)) + dur
        prev = max(pred, key=lambda p: cand[p]) if pred else None
        cand[name] = (cand[prev] if prev else D(0)) + dur + added
        paths[name] = (paths[prev] if prev else []) + [name]
    if not graph:
        raise ValueError('Empty event graph')
    end = graph[-1]['id']
    by_id = {n['id']:n for n in graph}
    return {'baseline_ps': str(base[end]), 'candidate_ps': str(cand[end]),
            'delta_ps':str(cand[end]-base[end]), 'candidate_path':paths[end],
            'candidate_path_controller_dependencies':sum(bool(by_id[n].get('controller_visibility_dependency',False)) for n in paths[end]),
            'terminal_event':end}


def self_check():
    # Parallel branches can hide latency or switch the critical path. Sink count
    # is intentionally absent; a fanout multiplier cannot enter composition.
    graph = [dict(id='producer',duration_ps=0),
             dict(id='control',predecessors=['producer'],duration_ps=1000,controller_visibility_dependency=True),
             dict(id='other',predecessors=['producer'],duration_ps=2000),
             dict(id='join',predecessors=['control','other'],duration_ps=0)]
    r=compose_event_graph(graph,2)
    assert r['delta_ps']=='666' and r['candidate_path_controller_dependencies']==1
    assert compose_event_graph(graph,1)['delta_ps']=='0'
    serial=[dict(id='Q',duration_ps=0,controller_visibility_dependency=True),
            dict(id='P',predecessors=['Q'],duration_ps=0,controller_visibility_dependency=True)]
    assert compose_event_graph(serial,2)['delta_ps']=='3332'
    for bad in ([], [dict(id='x',predecessors=['missing'],duration_ps=0)],
                [dict(id='x',duration_ps=-1)]):
        try:
            compose_event_graph(bad,2)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid event graph accepted')
    full=case(512,640)
    assert full['schedule_counts']['total_load_accepts']==176
    assert full['state']['load_bundle_per_tile_bits']==1038
    assert full['state']['issue_bundle_per_tile_bits']==580
    assert full['conditional_two_extra_stage_sizing']['uniform_load_issue_shared_tags_added_bits']==207174
    assert full['schedule_counts']['GUARD_P']==18
    assert case(512,128)['schedule_counts']['P_loader_accepts']==32
    # Partial block: second word valid only if another complete R-row group
    # exists; no crossing of a TD-row block to fill the unused high word.
    assert case(512,33)['schedule_counts']['P_loader_accepts']==9
    assert case(512,640,1,0,0,1)['schedule_counts']['P_loader_accepts']==320
    # Occupancy conservation over every legal external push / internal pop.
    for occupancy in range(3):
        for p_valid in (False,True):
            for loader_ready in (False,True):
                push=int(p_valid and occupancy!=2)
                pop=int(occupancy!=0 and loader_ready)
                assert 0 <= occupancy+push-pop <= 2
    return {'event_DAG_overlap_path_switch_and_serial_count':'PASS',
            'invalid_graph_rejection':'PASS','state_widths_and_partial_block_load_counts':'PASS',
            'two_entry_skid_occupancy_conservation':'PASS',
            'scope':'Analytical helper checks only; no real-engine RTL exact or physical gate.'}


def build():
    for path in (ENG,TILE,ADAPT,SERVICE,'rtl/chip/physical/ot_v41_attn_eng_ctl_phys.sv'):
        blob(SOURCE,path)
    model = blob(BASE,MODEL)
    assert re.search(r'DFF_UM2\s*=\s*0\.2916', model)
    assert 'mux_bits * 0.2' in model
    timing_path = 'results/uarch/w11_controller_cts_path_classes_20261001/diagnosis.json'
    geometry_path = 'results/uarch/w11_controller_cts_reach_20261001/diagnosis.json'
    t = json.loads(blob(TIMING,timing_path))
    g = json.loads(blob(GEOMETRY,geometry_path))
    r = json.loads(blob(CHAIN,'results/uarch/w11_controller_reach_model_gap_20261001/receipt.json'))
    for archive, expected in [('4_cts_final.rpt.gz',t['report_sha256']),
                              ('4_cts.sdc.gz',t['saved_CTS_SDC_sha256'])]:
        path='results/uarch/w11_controller_cts_path_classes_20261001/'+archive
        raw=subprocess.check_output(['git','show',TIMING+':'+path])
        unpacked=gzip.decompress(raw)
        assert hashlib.sha256(unpacked).hexdigest()==expected
        PINS[TIMING+':'+path]={'commit':TIMING,'path':path,
              'sha256':hashlib.sha256(raw).hexdigest(),'uncompressed_sha256':expected}
    assert D(r['internal_setup']['slack_ps']) == D('-750.63')
    assert D(r['internal_hold']['slack_from_absolute_report_ps']) == D('-53.12')
    assert g['endpoint_source']['prebuffer_input_loads'] == 9537
    assert g['placement']['polyline_is_actual_routed_wirelength'] is False
    assert D('833')-D('92.15')-D('20.36')-D('60') == D('660.49')
    source_map = {
      'load_capture': cite(ENG,'e_ld_mode <= p_go'),
      'aligned_load_valid': cite(ENG,'e_ld_v <= q_go || p_go'),
      'load_mux_and_tile': cite(ENG,'wire [PWORDS*TD*16-1:0] ldw'),
      'tile_boundary': cite(TILE,'r_ld_mode <= ld_mode'),
      'tile_stationary_data': cite(TILE,'assign wd['),
      'tile_stationary_enable': cite(TILE,'assign we['),
      'p_external_push_vs_loader_pop': cite(ENG,'wire push = p_v && p_ready, pop = p_v_i && p_ready_i'),
      'skid_no_full_pop_bypass': cite(ENG,"assign p_ready = (sk_n != 2'd2)"),
      'p_acceptance': cite(ENG,'wire p_ready_i ='),
      'Q_acceptance': cite(ENG,'assign q_ready ='),
      'KV_acceptance_and_reuse': cite(ENG,'assign kv_ready ='),
      'QK_acceptance': cite(ENG,'wire qk_go ='),
      'PV_acceptance': cite(ENG,'wire pv_go_raw ='),
      'last_load_bypass': cite(ENG,'wire iss_loaded ='),
      'half_reuse': cite(ENG,'wire fl_half_free ='),
      'job_acceptance': cite(ENG,'assign job_ready = !act'),
      'front_back_handoff': cite(ENG,'wire hand ='),
      'bank_read_skew': cite(TILE,'localparam integer DS ='),
      'issue_bank_guard_reload': cite(ENG,'bcnt[iss_bank] <='),
      'tag_alignment': cite(ENG,'ot_hdc_v41x_dly #(.W(16 + NL + 2 + MLEV + 8)'),
      'PV_completion_output': cite(ENG,'pv_v <= m_ov[0]'),
      'adapter_engine_defaults': cite(ADAPT,'ot_hdc_v41x_attn #('),
      'adapter_credit_return': cite(ADAPT,'sc_cr <= sc_v; pv_cr <= pv_v'),
      'adapter_zero_other_half_and_job_count': cite(ADAPT,'the half of the job the op'),
      'adapter_result_completion': cite(ADAPT,'nsc + sc_v == sc_need'),
      'packed_service_engine_defaults': cite(SERVICE,'ot_hdc_v41x_attn #(')}
    consumers = [
      {'boundary':'job', 'accept':'job_v && !act', 'dependency':'ILV front releases at hand after all QK issue and back free; job_ready is not output completion.', 'tag':'job_t[15] means reuse only ILV and NSTAGE=1; ILV rows use low15 bits.'},
      {'boundary':'Q/P load', 'accept':'p_go=p_v_i&&p_ready_i; q_go=q_v&&q_ready; ILV gives P priority.', 'dependency':'First word allocates unheld bank with countdown threshold. Remaining words keep bank. Last P word can make iss_loaded true same cycle.', 'tag':'{ld_v,mode,w2v,bank[BW],grp[8]} + selected BF16 data; no hardware set-ID/epoch.'},
      {'boundary':'skid', 'accept':'push external != pop internal', 'dependency':'two fixed slots + 2bit count + wp/rp; simultaneous push/pop holds count. Full FIFO denies push even if popping. Empty push cannot pop immediately.', 'tag':'payload only, P block/group inferred at pop; downstream epoch drain must be proved.'},
      {'boundary':'KV stage', 'accept':'kv_v&&kv_ready', 'dependency':'prefix mask chronological rows; NSTAGE1 front rewrites after back fill complete unless reuse. NSTAGE2 swaps front/back buffers at hand. Fill shares read with QK only NSTAGE1.', 'tag':'row/mask/pad and front/back identity must remain aligned.'},
      {'boundary':'issue', 'accept':'QK needs loaded Q, arrived rows, score credit; PV needs P block loaded + transposer fill, final block PV credit.', 'dependency':'PV wins shared issue slot; fill wins shared read. fl_half_free caps fills two blocks ahead. Held bank releases at final issue, countdown protects actual skewed reads.', 'tag':'{iv,ibank,TD*18 operand}; {row0[16],mask[NL],pv,fin,blk[MLEV],c[8]} delayed TLAT.'},
      {'boundary':'completion/reuse', 'accept':'scores/PV valid outputs consume reserved credits; returned credits update counters.', 'dependency':'Last issue releases controller context before tile/reduction/merge output; real adapter waits all score and PV beats and drained input valids, then masked result writes. Bank and staging reuse cannot substitute completion.', 'tag':'pairwise QK lane tree and binary-counter PV merge preserve golden reduction order and faults.'}]
    cases = [case(512,640),case(512,128),case(64,640),case(512,640,1,0,0,1)]
    return {
      'schema':'dsrom.attention-controller-composed-gap.v1',
      'base_commit':BASE, 'engine_source_commit':SOURCE,
      'scope':'DSROM attention controller only; standalone model/gap extension, unified-model owner retained; new files only.',
      'verdict':'MODEL_GAP_NOT_BUILD_READY', 'build_ready':False, 'adoption':False,
      'original_failure': {'verdict':r['CTS_verdict'], 'SS_setup_slack_ps':r['internal_setup']['slack_ps'],
          'FF_hold_slack_ps':r['internal_hold']['slack_from_absolute_report_ps'],
          'prebuffer_loads':9537, 'cell_origin_polyline_um':'1387.152', 'actual_routed_wirelength_um':None,
          'destination':g['endpoint_destination'], 'source_location_um':[161.514,116.1],
          'destination_location_um':[460.404,86.13], 'endpoint_manhattan_um':'328.860',
          'scope':'Intermediate CTS characterization stub; no real FP32 timing certificate.',
          'final_routed_SS_FF':None},
      'reuse_audit': {'complete':False,
          'retained':['attention H16/D512/TD32 replica sizing and stationary-bank count', 'Q/KV/P/PV interface widths',
                      'measured PWORDS2 jobs 449/193 and PWORDS1 609 cycles as existing evidence only',
                      'existing DAG, field/collective SS-wire accounting, DFF and assumed bit-mux unit costs'],
          'missing':['E_load to real R0 aligned state and mode fanout model', 'push/pop/credit/guard/completion event join',
                     'controller branch topology and M2-M5 capacity', 'four-target critical-path rate delta'],
          'citations':[cite(MODEL,'out["attention"] = dict(',BASE),cite(MODEL,'measured_job_cycles_pwords2=',BASE),
                       cite(MODEL,'DFF_UM2 =',BASE),cite(MODEL,'mux_bits * 0.2',BASE)]},
      'source_consumers':source_map,
      'state_ledger_scope':'Quantified interface/array and selected controller state only. Not a full flop census: core pipeline, merge rings and remaining controller registers omitted from area subtotal; whole-slot area unresolved.',
      'event_graph_API': {'function':'compose_event_graph(graph, extra_fast_cycles, period_ps=833)',
          'graph_contract':'Topologically ordered nodes with id, predecessors, duration_ps, controller_visibility_dependency. Durations must already include source-pinned issue/stall/credit/reuse/serial-domain service. Caller must expand changed feedback into the graph and bind terminal node to a target token.',
          'result':'Recomputed baseline/candidate longest path, exposed controller dependencies and delta; no 9537 fanout multiplier.',
          'certification':'API alone cannot establish real job or token latency. No complete product event graph supplied.'}, 'acceptance_and_dependencies':consumers,
      'quantified_cases':cases,
      'physical_and_cost_gap': {
          'layers_allowed':['M2','M3','M4','M5'],
          'replica_locations':None, 'branch_lengths_and_loads':None,
          'track_demand': {'per_tile_load_plus_issue_signal_tracks':1618,
                           'whole_uniform_cut_signal_tracks':64*1618+35,
                           'basis':'One track per simultaneously parallel signal at a cut; source sharing and separate corridors change each cut demand. Includes aligned tag bus at shared cut; excludes clocks/returns/spacing.'},
          'capacity_formula':'For each direction-compatible M2-M5 layer: floor(usable_channel_width_um/pitch_um)*available_fraction; sum across allowed layers, subtract obstructions/reserved nets.',
          'capacity_tracks':None,'routing_fit':None,
          'clock_buffers_hold_repair_area_um2':None,'whole_slot_area_um2':None,'whole_slot_fit':None,
          'note':'Do not import the unified field spine capacity as this controller channel. 547bit/504um wire calibration has different load and clock conditions. Cell-origin polyline is not routed length. Need real macro abstracts, branch pins, channel widths/pitches and occupancy before fit can be assessed.'},
      'composed_model': {
          'method':'compose_event_graph API: max-plus event graph, counted along selected token path; additive delay per exposed traversal, never per fanout load.',
          'recurrences':[
            'Q_visible = last_Q_loader_accept + E/R0/write_visibility + diagnostic_load_delay',
            'P_visible[b] = last_P_loader_accept[b] + E/R0/write_visibility + diagnostic_load_delay',
            'QK_issue[r] = max(Q_visible, KV_row_ready[r], score_credit_ready, shared_issue_free, staging_read_free)',
            'PV_issue[b,c] = max(P_visible[b], filled[b], prior_PV_issue+II, shared_issue_free, final_credit_ready)',
            'bank_reusable = max(last_skewed_read + safe_same_edge_margin, outstanding_aligned_loads_drained)',
            'output_done = max(last_QK_output, last_final_PV_merge_output); adapter_done = output_done + result_write_service',
            'token_done = longest_path(original_target_DAG + bound_controller_accept/complete events)',
            'restricted per-token envelope only if J complete job graphs are serially exposed and feedback unchanged: 0 <= delta_fast_cycles <= sum_j 2*(1+ceil(T_j/32)); J and T_j must be source-bound',
            'rate_ratio = baseline_token_latency / candidate_token_latency; for positive added delay alone, rate cannot improve'],
          'integration_inputs': ['ordered producer valid/ready events and packed-row arrivals', 'score/PV consumer credit service schedule',
                                 'per-job context/head group/layer/position-to-DAG-node binding', 'bank allocation/read/write events',
                                 'actual delayed bundle and topology with measured II and clocks'],
          'added_latency_formula':'sum(delta_cycles_on_exposed_edges / streaming_clock_hz) on recomputed critical path; overlap via max, include changed stalls/reuse/credit edges.',
          'conditional_example_only': {'stages':3,'extra_cycles':2,'per_stage_comb_budget_ps':'660.49',
                       'extra_ps_per_exposed_traversal':1666,'certified_minimum_stages':None,
                       'assumptions':'unchanged 1387.71ps total delay, perfect partition, same clkq/setup/uncertainty, zero interstage skew/CRPR. Uses archived 833ps period; exact 1.2GHz is 833.333...ps, no clock relaxation.'},
          'four_targets': {
            'DeepSeek_V4.1_ROM': {'applicability':'Direct dedicated-engine load/issue accounting; full H16 D512 TD32 NL4 diagnostic with PWORDS2 ILV1 REPL2 NSTAGE2. Actual adapter/service instantiations default PWORDS1 ILV0 REPL0 NSTAGE1; source binding of product configuration required.', 'token_traversals':None,'token_delta_ps':None,'rate_delta_percent':None},
            'Qwen3_ROM': {'applicability':'No proven instantiation of this DS engine. Apply acceptance/visibility/reuse method only after Qwen head/layout/controller source and DAG bindings; DS dimensions/replicas cannot transfer.', 'token_traversals':None,'token_delta_ps':None,'rate_delta_percent':None},
            'Qwen3_GPU_HBM': {'applicability':'DS stationary-bank broadcast hardware inapplicable. Ordinary SM Tensor Core register/TMEM epilogue, RF/shared-memory and collective dependency accounting must use its own consumers. No ROM novelty transfer.', 'token_traversals':None,'token_delta_ps':None,'rate_delta_percent':None},
            'DeepSeek_V4.1_GPU_HBM': {'applicability':'Attention workload shared; DS dedicated controller wiring not certified for GPU organisation. Bind ordinary SM TC/RF/shared-memory issue/completion and software collectives; no direct DSROM cycle penalty.', 'token_traversals':None,'token_delta_ps':None,'rate_delta_percent':None}}},
      'build_readiness_prerequisites': [
        'Bind actual product instance parameters and all four target DAG consumers; reconcile default PWORDS1 adapters with PWORDS2 measured standalone geometry.',
        'Provide finite source-pinned producer/consumer service and job/credit/row event schedules; count critical traversals by longest path, including result writes, not acceptance count or 9537 sinks.',
        'Select and fully price aligned load/data/valid/bank/group/w2v, issue operands/valid/bank and shared output tags at every proposed boundary; include skid outstanding ownership/epoch.',
        'Recompute last-word bypass, allocation thresholds, read/write skew, held/countdown widths, front/back/staging half reuse and credit reservations for any latency change; prove no overwrite/lost/duplicate/stale beats.',
        'Supply actual replica abstracts/slots/pins and directional M2-M5 channel capacities; price mux/demux, fanout trees, reset, clock skew and FF hold repair in whole-slot area.',
        'Produce quantified four-target token delta and per-user rate including 1.2GHz streaming/0.9GHz serial domains; a candidate adoption needs model-priced >=1% per-user rate gain and RTL measurement confirming gain.',
        'Only after complete model, separately authorised off-by-default RTL and real-engine golden exact gate preserving rounding/reduction order and WINDOW tags; no stub-fold exactness substitution.',
        'New hardware must confirm gain and close contextual SS setup/FF hold at original 60ps/25ps uncertainties and pass hub routing-layer check; retain original FAIL and reject slower/nonclosing lever rather than tune.'],
      'operations': {'RTL_edits':0,'PnR_launches':0,'GRT_polls':0,'payload_reads':0,'unified_model_edits':0,
                     'protected_PID':2069324,'documents_edits':0},
      'pins':PINS, 'analytical_validation':self_check()}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    record=build()
    record['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    data=json.dumps(record,sort_keys=True,indent=2)+'\n'
    if args.output:
        if args.output.exists():
            if args.output.read_text()!=data:
                raise SystemExit('Refusing to overwrite differing evidence; choose a new output path')
        else:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(data)
    else:
        print(data,end='')

if __name__=='__main__':
    main()
