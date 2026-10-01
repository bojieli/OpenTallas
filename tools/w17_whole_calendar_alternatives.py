#!/usr/bin/env python3
"""Compare integer Q fields and atomic schedules; compose priced partial paths.

All times are candidate service costs. Unknown operator/PHY/consumer/wake costs
remain explicit and prevent complete admission. No duty-factor power credit.
"""
import argparse
import json
import math
import types
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
import numpy as np
import w17_integer_expert_residency as R
from w17_conservative_geometry_search import search
from w17_dispatch_alternatives import worst_selection, ceildiv
from w17_whole_dsrom_candidate import build as whole_candidate


def components(template):
    """Keep all segments of an output super-row in the same pair wave."""
    parent = {p['pair']: p['pair'] for p in template['pairs']}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    rows = defaultdict(list)
    for p in template['pairs']:
        for s in p['segments']:
            rows[s['row']].append(p['pair'])
    for ps in rows.values():
        for p in ps[1:]:
            parent[find(p)] = find(ps[0])
    out = defaultdict(list)
    for p in parent:
        out[find(p)].append(p)
    return sorted((sorted(v) for v in out.values()), key=lambda x: (-len(x), x))


def waves(template, limit):
    groups = components(template)
    if max(map(len, groups)) > limit:
        raise ValueError('mask splits an atomic output-row component')
    bins = []
    for g in groups:
        selected = next((b for b in bins if len(b) + len(g) <= limit), None)
        if selected is None:
            bins.append(list(g))
        else:
            selected.extend(g)
    return [sorted(b) for b in bins]


def wave_stream(template, pairs):
    chosen = set(pairs)
    units, demands = defaultdict(set), defaultdict(int)
    for p in template['pairs']:
        if p['pair'] not in chosen:
            continue
        for si, u, b, h in p['word_order']:
            s = p['segments'][si]
            q = (u - s['first_K'] // 512) // 8
            units[q, b].add(u)
            demands[q, b, p['pair']] += 1
    rounds = []
    for q, b in sorted(units):
        count = len(units[q, b])
        demand = max(v for (qq, bb, p), v in demands.items() if (qq, bb) == (q, b))
        rounds.append(dict(subblock=q, block=b, input_512bit_beats=count,
                           pair_read_cycles=demand, issue_cycles=max(8, count, demand)))
    return dict(rounds=rounds, stream_issue_cycles=sum(x['issue_cycles'] for x in rounds),
                activation_refill_bytes=sum(x['input_512bit_beats'] for x in rounds) * 64)


def head_layout():
    names = ['npow2','model_split','segments','unit_range','unit_halves','seg_words',
             'segment_order','element_order','family','seg_units']
    env = R.source_functions(R.blob(R.SEG), names, dict(math=math, CHUNK_EL=256, IL=8))
    S = types.SimpleNamespace(**{k: env[k] for k in names})
    place = R.source_functions(R.blob(R.PLACE), ['_place'], dict(np=np, S=S,
                               Field=R.MetadataField, Mat=object))['_place']
    field = R.MetadataField(1024)
    field.bf[:] = True
    tiles = []
    for offset, rows in [(0,16384),(16384,15936)]:
        sg, info, _ = place(field, [types.SimpleNamespace(rows=rows, K=5120,
                                       fmt='bf16', name='head')])
        bypair = defaultdict(list)
        for s in sg:
            bypair[s['pair']].append(s)
        unitsets, demands = defaultdict(set), defaultdict(int)
        order_receipt = []
        for p, ps in sorted(bypair.items()):
            order = S.element_order(ps)
            start = int(field.fill[p])
            assert len(ps) <= 8 and start + len(order) <= 8192
            for si, u, b, h in order:
                first, _ = S.unit_range('bf16', ps[si]['e0'], ps[si]['elems'])
                q = (u - first) // 8
                unitsets[q,b].add(u)
                demands[q,b,p] += 1
            field.fill[p] += len(order)
            order_receipt.append(dict(pair=p, logical_mate_start=start,
                logical_mate_words=len(order), physical_max_row=(int(field.fill[p])-1)//2,
                segments=len(ps)))
        issue = 0
        for q,b in sorted(unitsets):
            # Existing BF16 port carries64 elements/cycle: four16-lane units.
            issue += max(8,ceildiv(len(unitsets[q,b]),4),
                         max(v for (qq,bb,p),v in demands.items() if (qq,bb)==(q,b)))
        tiles.append(dict(output_row_offset=offset, output_rows=rows,
            rank_local_MACs=rows*5120, pair_address_receipt=order_receipt,
            stream_issue_cycles=issue, stream_output_FP32_bytes=rows*4,
            configuration_cycles=None, registered_capture_return_merge_cycles=None))
    words = int(field.fill.sum())*2
    assert words == 10342400 and int(field.fill.max()) == 5120
    return dict(tiles=tiles, physical_words_per_rank=words,
        maximum_logical_mate_fill=int(field.fill.max()), physical_rows_per_parity=4096,
        logical_to_physical='mate unchanged; parity=address%2; row=address//2',
        stream_issue_cycles=sum(t['stream_issue_cycles'] for t in tiles),
        actual_image_and_FP32_return_exactness=False, spatial_fit=False)


def dispatch_calendar(owners, width, route=75):
    layers = []
    for l in range(40):
        counts = defaultdict(int)
        for o in owners:
            if o['layer'] == l:
                counts[o['stage']] += 1
        anchor = min(counts)
        def cost(distance,k):
            # Activation reused at destination for w1/w3, not the w2 gather.
            serial = ceildiv(81920+k*256,width)+ceildiv(k*(20480+256),width)
            return distance*(serial+2*route)*3 + 15+k*16+31+k*12
        ticks, selections = worst_selection([(s,n,s-anchor+1) for s,n in sorted(counts.items())],cost)
        layers.append(dict(layer=l, earliest_owner=anchor, worst_six_distinct=selections,
                           partial_transport_ticks=ticks))
    return dict(per_layer=layers, total_ticks=sum(x['partial_transport_ticks'] for x in layers))


def build():
    whole = whole_candidate()
    power_pin=('fea811df4','results/uarch/w10_q_existing_icg_r1/phases.json')
    power_raw=R.blob(power_pin)
    power=json.loads(power_raw)
    historical_q1024=next(r for r in power['candidates'] if r['q_pairs']==1024)
    phase1024=historical_q1024['active_family_phases']['w2']
    root_clock=D(phase1024['root_q_clock_W'])/1024
    q_leak=D(phase1024['resident_Q_leakage_W'])/1024
    leaf_clock=D(phase1024['existing_ICG_leaf_clock_W'])/1024
    qdata=power['q_data']
    metadata_path = Path(__file__).resolve().parents[1]/'results/quality/w16_w17_whole_calendar_20261001/actual_program_metadata.json'
    metadata_raw = metadata_path.read_bytes()
    program = json.loads(metadata_raw)
    producer = program['producer_source_pin']
    assert R.sha(R.blob((producer['commit'],producer['path']))) == producer['sha256']
    assert len(program['stages']) == 40 and len(program['functional_ops']) == 327
    engram_pin = ('b0cfaee4c','results/quality/w16_engram_home_service_demand_20261001/demand.json')
    engram_raw = R.blob(engram_pin)
    engram_demand = json.loads(engram_raw)
    crom_pin=('f4bce8fa0','results/uarch/w11_crom_demand_20261001/summary.json')
    crom_raw=R.blob(crom_pin)
    crom_demand=json.loads(crom_raw)
    assert all(r['per_command_unique_prefetch_cycles']==549760 for r in crom_demand['rank_summaries'])
    engram_homes = []
    for home_id,col in enumerate(engram_demand['ROM_candidate']['columns']):
        banks = col['macros']
        padded = 1 << (banks-1).bit_length()
        levels = (padded-1).bit_length()
        muxbits = (padded-1)*274
        capturebits = banks*274
        # Register every level: explicit conservative selection pipeline,
        # not an unregistered ~31K-way mux after a744ps macro output.
        selectregs = (padded-1)*274
        macro_area = D('7881.3648')*banks/D(1000000)
        FF_area = D(capturebits+selectregs)*D('.2916')/D('.5')/D(1000000)
        mux_area = D(muxbits)*D('.2')/D('.5')/D(1000000)
        engram_homes.append(dict(layer=col['layer'], column=col['column'], proposed_storage_die=home_id,
            complete_table_copies=1, rows=col['rows'], physical_macros=banks,
            word_address_bits=27, address='residue*8+beat; bank=address//4096,row=address%4096',
            row_read_issue_cycles=8, output_bits_per_cycle=264,
            input_capture_FF_bits=capturebits, registered_select_FF_bits=selectregs,
            mux2_bits=muxbits, select_pipeline_levels=levels,
            proposed_address_decode_fanout_cycles=levels,
            proposed_last_beat_capture_select_cycle=levels+8+1+levels,
            macro_area_mm2=str(macro_area), capture_select_FF_area_screen_mm2=str(FF_area),
            select_mux_area_screen_mm2=str(mux_area),
            allocated_macro_capture_select_mm2=str(macro_area+FF_area+mux_area),
            geometry_usable_field_mm2='457.96549650802586',
            selector_clock_IO_routes_enable_area_and_power=None,
            macro_SS_residual_before_capture_ps=4, contextual_FF_hold=None,
            macro_clock_enable_and_exact_image=False))
    m = R.inputs()
    sizes = search([1024,768,512,256,128])
    rows = []
    # Historical CROM512 reservation retained explicitly; it is not current
    #45-bank physical service/clock qualification. No silent replacement.
    pair_static = root_clock+q_leak
    fixed = D(historical_q1024['always_clock_leak_IO_reservation_W']) - 1024*pair_static
    for geometry in sizes['candidates']:
        if geometry['status'] != 'INTEGER_EXPERT_SUBPROBLEM_PASS':
            rows.append(geometry)
            continue
        q = geometry['q_pairs']
        templates, stride = R.templates(m,q)
        owners, stages, cap = R.assignments(m,templates,stride)
        schedules = []
        for active_limit in sorted(set([q,max(8,q//2),max(8,q//4),64,32,16,8]), reverse=True):
            families = []
            for f,t in templates.items():
                bins = waves(t, active_limit)
                chunks = [wave_stream(t,b) for b in bins]
                assert sorted(p for b in bins for p in b) == sorted(p['pair'] for p in t['pairs'])
                awake = max(map(len,bins))
                baseline = fixed + q*pair_static
                leaf = leaf_clock*awake
                # No unqualified root isolation. Wire ceiling deliberately
                # charged to every resident Q pair, not averaged over waves.
                root_data=q*D(qdata['root_data_internal_pin_upper_W_per_resident_pair'])
                leaf_data=awake*D(qdata['leaf_data_internal_pin_upper_W_per_enabled_pair'])
                wire=q*D(qdata['unresolved_wire_upper_W_per_resident_pair'])
                data=root_data+leaf_data+wire
                bf_root=1024*D(power['BF']['root_reachable_data_and_wire_upper_W_per_pair'])
                hub_data=sum(D(v) for v in power['hub']['configured_all_units_dynamic_upper_W'].values())
                families.append(dict(family=f, atomic_components=len(components(t)),
                    largest_atomic_component=max(map(len,components(t))),
                    wave_count=len(bins), active_pairs_per_wave=list(map(len,bins)),
                    pair_wave_membership_sha256=R.sha(json.dumps(bins).encode()),
                    stream_issue_cycles=sum(x['stream_issue_cycles'] for x in chunks),
                    activation_refill_bytes=sum(x['activation_refill_bytes'] for x in chunks),
                    repeated_configuration_cycles=len(bins)*geometry['descriptor']['cfg_cycles'],
                    baseline_static_W=str(baseline), awake_leaf_clock_W=str(leaf),
                    clock_static_W=str(baseline+leaf), clock_static_margin_W=str(D('474.56')-baseline-leaf),
                    root_data_pin_internal_W=str(root_data),awake_leaf_data_pin_internal_W=str(leaf_data),
                    separate_CFG_only_Q_W=str(q*D(qdata['CFG_only_data_upper_W_per_pair'])),
                    unresolved_wire_ceiling_W=str(wire),
                    BF_idle_root_data_wire_upper_W=str(bf_root),hub_all_units_dynamic_upper_W=str(hub_data),
                    pin_internal_STREAM_allocation_W=str(baseline+leaf+root_data+leaf_data+bf_root+hub_data),
                    conservative_data_allocation_W=str(data), data_clock_static_W=str(baseline+leaf+data),
                    BF_hub_nonexpert_data_W='BF root and hub source ceilings included above; BF-active macro/nonexpert switching remains unbound.',
                    power_values_source_pinned=True,power_physical_qualified=False,
                    wake_drain_consumer_cycles=None,
                    no_PG_wake_assumed=True, no_leaf_wake_completion_credit=True))
            partial = sum(f['stream_issue_cycles']+f['repeated_configuration_cycles'] for f in families)
            links = []
            for width in (512,1024,2048):
                calendar = dispatch_calendar(owners,width)
                cfg_ticks = 40*6*partial*3
                # Optional stage-state path shown separately. Anchors are
                # candidate homes, not physical nonexpert placements.
                anchors = [min(o['stage'] for o in owners if o['layer']==l) for l in range(40)]
                distances = [anchors[l+1]-anchors[l] for l in range(39)]
                state_ticks = sum(d*(ceildiv(40976*8,width)+75)*3 for d in distances)
                state_ticks += 39*(15+16+31)
                links.append(dict(width_bits_per_rank_fast_cycle=width, separate_rank_links=4,
                    aggregate_bits_per_fast_cycle=4*width,
                    added_tracks_both_directions=2*(width+64),
                    corridors_required=ceildiv(832+2*(width+64),1153),
                    all40_dispatch=calendar,
                    all40_expert_cfg_stream_ticks=cfg_ticks,
                    hypothetical_39_anchor_stage_state_ticks=state_ticks,
                    dispatch_cfg_stream_partial_us=str(D(calendar['total_ticks']+cfg_ticks)/3600),
                    state_plus_dispatch_cfg_partial_us=str(D(calendar['total_ticks']+cfg_ticks+state_ticks)/3600),
                    actual_anchor_nonexpert_homes=False,
                    PHY_collective_wake_and_completion_ticks=None))
            schedules.append(dict(active_limit=active_limit, families=families,
                per_expert_repeated_cfg_stream_cycles=partial,
                dispatch_alternatives=links, verdict='REJECTED_FOR_ADMISSION_AVAILABLE_DATA_BOUND_EXCEEDS_BUDGET',
                exact_address_recipe='Original slot*pair_stride+family_prefix, same pair templates. Waves filter pair go only; never repack words or reorder golden row sums.',
                exact_wave_control_and_output_gate=False))
        rows.append(dict(q_pairs=q,BF_reserved_pairs=1024,
            integer_geometry=geometry, expert_die_count=4*len(stages),
            allocated_expert_plus_head_embed_dies=4*len(stages)+8,
            complete_product_die_count=None, schedules=schedules))
    head = head_layout()
    vocabulary = []
    collective_calendars = []
    for width in (512,1024,2048):
        # Explicit proposed one-link-hop embedding multicast tree (3 edges),
        # head broadcast tree (3 edges), and two-level64-bit argmax tree.
        # Sequential edges is conservative; no invented multicast crossbar.
        embed_ticks = 320*3+3*((ceildiv(10240*8,width)+75)*3+15+16+31)
        head_input_ticks = 3*((ceildiv(10240*8,width)+75)*3+15+16+31)
        argmax_ticks = 2*((ceildiv(64,width)+75)*3+15+16+31)
        vocabulary.append(dict(width_bits_per_rank_fast_cycle=width,
            embedding_row_issue_cycles=320, proposed_embedding_three_edge_partial_ticks=embed_ticks,
            proposed_head_three_edge_input_ticks=head_input_ticks,
            head_BF_stream_issue_cycles=head['stream_issue_cycles'],
            two_level_64bit_argmax_transport_ticks=argmax_ticks,
            argmax_compare_cycles=None, head_config_return_CROM_norm_and_consumer_cycles=None,
            embedding_image_reader_capture_select_and_done_cycles=None,
            actual_vocab_topology_and_ports=False))
        events = []
        for stage in program['stages']:
            for c in stage['collectives']:
                # Conservative local TP4 service proposal, in programme order.
                # Gather: three ring rounds, each rank source preserves its
                # own FP32 byte slice. Reduction: three tree edges followed by
                # three broadcast edges, serialized to avoid invented ports.
                # No reassociation/early BF16 rounding or in-switch free adds.
                rounds = 3 if c['op'] == 1 else 6
                size = c['input_bytes_per_rank']
                edge_ticks = (ceildiv(size*8,width)+75)*3+15+16+31
                events.append(dict(layer=stage['layer'], instruction=c['instruction'],
                    tag=c['tag'], collective_op=c['op'], input_bytes_per_rank=size,
                    output_bytes_per_rank=c['output_bytes_per_rank'],
                    serialization_cycles_per_edge=ceildiv(size*8,width),
                    proposed_local_service_edges_or_rounds=rounds,
                    partial_transport_ticks=rounds*edge_ticks,
                    reduction_arithmetic_cycles=None, final_consumer_credit_return_tick=None,
                    expert_cross_stage_actual_distance=None, ports_hardware_bound=False))
        collective_calendars.append(dict(width_bits_per_rank_fast_cycle=width,
            actual_collective_commands=len(events), all40_collective_events=events,
            total_local_partial_transport_ticks=sum(e['partial_transport_ticks'] for e in events),
            transport_us=str(D(sum(e['partial_transport_ticks'] for e in events))/3600),
            nonoverlap_policy='All498 collective commands serial in programme order; no overlap/port-sharing credit.',
            golden_order='TP4 reduction ((r0+r1)+(r2+r3)); FP32 until specified final rounding.',
            cross_stage_weight_owners_routes_and_operators_unbound=True))
    return dict(schema='opentallas.w17.whole-calendar-alternatives.v1',
        baseline_candidate_source_pins=whole['source_pins'], geometry_search=sizes,
        power_phase_source_pin=dict(commit=power_pin[0],path=power_pin[1],sha256=R.sha(power_raw)),
        power_phase_scope=power['phase_simultaneity'],
        historical_CROM512_reservation_W=power['CROM_proposal'],
        current45bank_CROM_provider_clock_power_qualified=False,
        actual_CROM_demand=dict(source_pin=dict(commit=crom_pin[0],path=crom_pin[1],sha256=R.sha(crom_raw)),
            summary=crom_demand, serialized_scalar_issue_ticks_per_rank=549760*3,
            cold_delivery_capture_route_CDC_ticks=None, overlap_or_cache_reuse_credit=0,
            interpretation='549760read/458.133us demand includes predicated commands; not measured token slowdown. No free prefetch/reuse/overlap.1024unique one-bank burst invalidates capacity-as-bandwidth.'),
        candidate_table=rows, head_exact_integer_layout=head, vocabulary_service_candidates=vocabulary,
        all40_collective_service_candidates=collective_calendars,
        engram_home_candidate=dict(source_pin=dict(commit=engram_pin[0],path=engram_pin[1],sha256=R.sha(engram_raw)),
            storage_homes=48, table_copies=1, homes=engram_homes,
            macro_count=sum(x['physical_macros'] for x in engram_homes),
            per_layer_home_links=24, payload_bits_per_home_cycle=264,
            aggregate_payload_bits_per_cycle=24*264,
            return_channel_tracks_one_direction_including64control_per_home=24*(264+64),
            minimum1153track_corridors=ceildiv(24*(264+64),1153),
            proposed_hub_landing_bits_per_layer=24*8*264,
            logical_total_with_expert_head_embed=780,
            actual_complete_product_die_count=None,
            decoder_consumer_CDC_broadcast_and_home_power_cycles=None,
            capacity_area_screen_only=True, admission=False,
            HBM_alternative=engram_demand['HBM_candidate']),
        actual_program_metadata_pin=dict(path=str(metadata_path.relative_to(metadata_path.parents[3])),
            sha256=R.sha(metadata_raw), producer=producer),
        actual_functional_graph=program['functional_ops'],
        raw_field_ports=dict(pair_ROM_physical_ports=4, physical_word_bits=274,
            pair_MACs_per_issued_cycle=128, existing_activation_spine_payload_bits=512,
            exponent_side_bits=20, return_bytes_per_pair_issue_cycle=8,
            proposed_interdie_BF16_packets_not_existing_quantized_spine=True),
        qualified_power=False, budget_W='474.56',
        provisional_static_rule='Fixed BF/hub/CROM component plus actual physical Q root/leak count; awake leaf charged per wave, no duty averaging or inactive frontend isolation.',
        complete_token_latency_cycles=None, physical_admission=False, hardware_build_ready=False,
        chosen_feasible_point=None, verdict='NO_POINT_CERTIFIABLE_WITH_CURRENT_AVAILABLE_DATA_BOUNDS',
        minimum_correction='Immutable phase-dependent data/load bounds and exact wave control; actual nonexpert/Engram/CROM/collective homes, finite completion and contextual geometry/power remain mandatory.',
        active_jobs_launched=0)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out',required=True)
    a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
