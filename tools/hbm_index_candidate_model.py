#!/usr/bin/env python3
"""Pre-build sizing and literal TP96/global-ID candidate boundary semantics.

No inference, checkpoint conversion, host-oracle instruction operands or measured
clock credit. Selection compares BF16 values, canonicalises signed zero, preserves
lowest-global-ID ties and prices every existing storage/stream boundary.
"""
import argparse
import hashlib
import json
from pathlib import Path

TP = 96
BLOCK = 8
ROOT = Path(__file__).resolve().parents[1]


def key(bits):
    if not 0 <= bits < 65536 or (bits & 0x7f80 == 0x7f80 and bits & 0x7f):
        raise ValueError('BF16 non-NaN score required')
    return 0x8000 if bits & 0x7fff == 0 else (~bits & 0xffff if bits & 0x8000 else bits | 0x8000)


def candidate_local(rows, *, rank, position, k=2048):
    if not 0 <= rank < TP or not 0 <= position < 1 << 20 or not 0 <= k <= 2048:
        raise ValueError('native rank7/position20/candidate count')
    maxima = {}
    previous = -1
    for idx, score in rows:
        if not previous < idx <= position or (idx // BLOCK) % TP != rank:
            raise ValueError('actual globally ascending owned IDs required')
        previous = idx
        block = idx // BLOCK
        if block not in maxima or key(score) > key(maxima[block]):
            maxima[block] = score
    newest = position // BLOCK
    if newest in maxima:
        maxima[newest] = 0x7f80
    chosen = sorted(maxima, key=lambda b: (-key(maxima[b]), b))[:k]
    # Existing candidate publication drops -inf; never silently pins a rank's
    # last local block to make an empty or masked stream non-empty.
    published = sorted(b for b in chosen if maxima[b] != 0xff80)
    return dict(selected=[(b, maxima[b]) for b in chosen], published=published,
                newest_owner=newest % TP, newest_pinned=newest in maxima)


def final_source(rows, *, k=512):
    """Validate the existing radix selector's ACTUAL buffer-order precondition."""
    if k != 512 or len(rows) != TP * 512:
        raise ValueError('actual 96 x 512 gathered candidates required')
    ids = [idx for idx, _ in rows]
    if any(not 0 <= idx < 1 << 20 for idx in ids) or any(a >= b for a, b in zip(ids, ids[1:])):
        raise ValueError('native canonical global-ID gather missing: rank-major TP96 is not global-ID order')
    for _, score in rows:
        key(score)
    return dict(count=len(rows), k=k, literal_global_ids=True, stride=0,
                canonical_global_id_order=True, hardware_source_required=True)


def price():
    return dict(status='PREBUILD_ESTIMATE_NOT_ADOPTED', operating_mode='exact plain AR; no speculative change',
        candidate=dict(replicas=96, quarters=4, score_lanes_per_quarter=16,
            block_lanes_per_quarter=2, maximum_keys_at_1m_per_rank=10928,
            maximum_owned_blocks=1366, candidate_capacity=2048,
            score_input_bits_per_cycle=1024, global_id_input_bits_per_cycle=1280,
            lane_valid_bits_per_cycle=64, quarter_valid_last_bits=8,
            scalar_frame_bits=64, block_output_bits_per_cycle=8*17,
            actual_selected_maxima_output_bits_per_cycle=8*16,
            sram_read_bits_per_cycle=272, sram_write_bits_per_cycle=272,
            sram_read_ports=4, sram_write_ports=4,
            line_storage_bits=4*1024*2*34,
            added_newest_comparators=8, comparator_width=17,
            added_score_mux_bits=8*16, added_wrapper_ff=0,
            replica_mux_demux_cost='existing four independent quarter FIFOs/selector/SRAM; no free fanout',
            held_position_fanout=8, held_context_stable_until_actual_drain=True,
            frontend_edges=3, added_latency_edges=0,
            latency='accepted scores -> three existing frontend edges -> actual selector output/tail; SRAM replay on ovf',
            candidate_publication='ascending literal global block IDs, -inf lane validity zero; one-quarter stalls preserved',
            overflow='actual rep_req/ovf exported; never converted into PASS',
            gather='candidate publication/local and global gather timing unmeasured; no free collective',
            macs_per_cycle=0, communication='no arithmetic reordering; max8 and exact score/index comparison only'),
        final_select=dict(source='rtl/chip/ot_coll_topk_merge.sv', ranks=96, candidates_each=512,
            input_score_bits=32, literal_global_id_bits=20, wire_id_bits=32,
            capacity_entries=96*512, candidate_buffer_bits=96*512*64,
            inherited_protocol='rank/word load then go, out_valid/out_nw/out_last, done; no out_ready',
            exactness_blocker='rank-major round-robin owned IDs are not global-ID order; canonical hardware gather unbound',
            borrowed_419_cycles_credited=False, loaded_clock_qualified=False,
            implementation_scope='fail-closed source/program binding only until canonical gather design supplied'),
        physical=dict(target_GHz=1.2, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
            mapped_area_um2=None, routing_tracks=None, slot_fit=False,
            buffer_clock_wire_cost='positive, unmeasured; parent placement/loaded boundary required',
            route_launch_allowed=False), measured_composition_credit=False)


def capacity_analysis():
    """Source-derived bounds, including legal unbalanced quarter allocation."""
    return dict(global_blocks=131072, rank_blocks_first32=1366,
        rank_blocks_remaining64=1365, block_lanes_per_line=2,
        K_meaning='maximum runtime selected block count, not input storage depth',
        current_quarter_partition='ordered, block aligned; no per-quarter count bound enforced',
        worst_legal_quarter_blocks=1366, maximum_ingest_lines=683,
        maximum_written_or_read_address=682, minimum_direct_depth_power_of_two=1024,
        derivation='131072=96*1365+32; all owned blocks may occupy one quarter; pack emits ceil(valid blocks/2) lines, empty flush emits no line',
        sweep='in-place packing never creates lanes; w cannot exceed lines read; GC writes compacted prefix, ingest head counts original packed lines',
        replay='P2 replay only histograms; P3 replay packs selection at w=0; at most ceil(1366/2)=683 lines, not K/2 inferred allocation',
        overflow='head[AW] suppresses ingest write at 1024; no wrap/alias credit, parent refuses replay overflow',
        conditional_balanced=dict(required_parent_contract='each quarter <=ceil(owned blocks/4), enforced by actual program/source binding',
            maximum_blocks_each=342, maximum_lines_each=171, maximum_address=170,
            minimum_direct_depth_power_of_two=256, current_contract_enforces=False),
        shallower_direct_macro_fits_current_contract=False)


def read_response_analysis():
    return dict(source='rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv',
        edges=['e0 registers mem_re/address and t1 tags',
            'e1 SRAM accepts registered request; rd_out updates after edge; t2 receives t1',
            'e2 sweep r1_d captures mem_rdata, or emit FIFO enqueues mem_rdata with t2_last'],
        actual_consumers=['sweep r1_d input mux: replay / flush-zero / SRAM',
            'emit o_in payload mux into ofq: SRAM / direct P3 / empty'],
        receiver_cone_requirement='bound macro rd_out -> mux -> r1_d and ofq D, including receiver setup, net and skew within remaining SS budget',
        extra_edge_decision='architecture-owned additive successor response-latency parameter, default original one edge; no original source edit',
        must_retime=['valid/flush/emit/last tags together with data',
            'e_infl decrement on actual emit enqueue; OD=4 finite credits',
            'GC infl until actual pack exit; DG=8 finite credits',
            'histogram settle, sweep flush/drain and final output-last release'],
        bypasses='replay i0_lane and direct P3 output bypass SRAM; do not blindly add an edge to these paths',
        conditional_cost=dict(extra_response_edges=1, four_quarter_tag_stage_FF=16,
            payload_capture_stage_FF_if_added=272, clock_reset_mux_wire_cost='positive, unmeasured',
            phase_response_tail_edges_added=1, throughput='II1 only if credits sustain it; actual stalls and composed tail must be measured'),
        implemented=False, original_sources_unchanged=True)


def physical_preparation(parent=None):
    """Concrete memory/IO pricing; availability never selects a parent slot."""
    catalog = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2'
    view = parent['macro_view'] if parent else catalog
    directory = ROOT / view
    metadata = list(directory.glob('*.json'))
    if len(metadata) != 1:
        raise ValueError('one actual macro metadata file required')
    macro = json.loads(metadata[0].read_text())
    spec, area, timing = macro['spec'], macro['area'], macro['timing']
    if spec['ports'] != '1r1w' or spec['words'] < 1024 or spec['bits'] < 68:
        raise ValueError('four independent real 1024x68 1R1W stores required')
    name = spec['name']
    files = [metadata[0], *(directory / (name + ext) for ext in
        ('.lef', '.v', '_bb.v', '_ss.lib', '_ff.lib'))]
    pins = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    shallow_view = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2'
    shallow_name = shallow_view.rsplit('/', 1)[1]
    shallow_metadata = ROOT / shallow_view / (shallow_name + '.json')
    shallow = json.loads(shallow_metadata.read_text())
    required = ['parent_source_pin', 'macro_view', 'macro_instances', 'slot',
        'launch_clock', 'capture_clock', 'input_delays_ps', 'output_delays_ps',
        'output_loads_ff', 'read_response_edges', 'mutable_sram_protection',
        'fullshape_functional_record', 'fullshape_performance_record']
    missing = [k for k in required if parent is None or parent.get(k) is None]
    return dict(schema='opentallas.hbm-index-candidate.physical-preparation.v1',
        candidate_source='rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv',
        candidate_source_sha256=hashlib.sha256((ROOT / 'rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv').read_bytes()).hexdigest(),
        memory=dict(quarters=4, logical_words_each=1024, logical_bits_each=68,
            logical_total_bits=4*1024*68, read_ports=4, write_ports=4,
            read_bits_per_cycle=272, write_bits_per_cycle=272,
            read_bytes_per_cycle=34, write_bytes_per_cycle=34,
            address_bits_per_direction=40, enable_bits_per_direction=4,
            logical_read_response_edges=1, read_during_same_address_write='old data',
            contract_source='rtl/test/tb_hbm_index_candidate_boundary.sv synchronous SRAM',
            macro_selected=parent is not None and 'macro_view' not in missing,
            macro_view=view, macro_name=name, physical_words_each=spec['words'],
            physical_bits_each=spec['bits'], payload_utilization=68/spec['bits'],
            unused_payload_bits_each_line=spec['bits']-68,
            macro_width_um=area['macro_width_um'], macro_height_um=area['macro_height_um'],
            four_macro_area_floor_um2=4*area['macro_area_um2'],
            protection='mutable SRAM protection remains required; no ROM-ECC exemption'),
        macro_source_pins=pins,
        capacity=capacity_analysis(), read_response=read_response_analysis(),
        conditional_shallower_catalog=dict(view=shallow_view,
            metadata_sha256=hashlib.sha256(shallow_metadata.read_bytes()).hexdigest(),
            behavior_sha256=hashlib.sha256((ROOT/shallow_view/(shallow_name+'.v')).read_bytes()).hexdigest(),
            ports=shallow['spec']['ports'], words=shallow['spec']['words'], bits=shallow['spec']['bits'],
            read_response_edges=1, same_address_collision='old data',
            four_macro_area_floor_um2=4*shallow['area']['macro_area_um2'],
            ss_clk_to_q_ps=shallow['timing']['ss']['clk_to_q_ps'],
            ss_remaining_before_net_receiver_setup_skew_ps=833-60-shallow['timing']['ss']['clk_to_q_ps'],
            requires='actual parent <=342 blocks/quarter binding; bounded physical address adapter or priced additive AW successor; mutable SRAM protection',
            fits_current_unbounded_quarter_contract=False, selected=False, qualified=False),
        selector_source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv', 'rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv',
             'tools/hbm_index_candidate_sources.py']},
        io=dict(score_input_bits=1024, global_id_input_bits=1280,
            lane_valid_input_bits=64, independent_quarter_valid_last_bits=8,
            held_context_bits=64, actual_maxima_output_bits=128,
            block_id_output_bits=136, output_lane_valid_bits=8,
            actual_parent_binding=parent, missing_parent_fields=missing),
        timing=dict(target_period_ps=833, ss_setup_uncertainty_ps=60, ff_hold_uncertainty_ps=25,
            ss_macro_clk_to_q_ps=timing['ss']['clk_to_q_ps'],
            ss_macro_input_setup_ps=timing['ss']['setup_ps'],
            ss_macro_min_period_ps=timing['ss']['min_period_ps'],
            ff_macro_clk_to_q_ps=timing['ff']['clk_to_q_ps'],
            ff_macro_input_hold_ps=timing['ff']['hold_ps'],
            ss_available_before_wire_receiver_setup_and_skew_ps=833-60-timing['ss']['clk_to_q_ps'],
            source_model_only=True, loaded_ss_ff_closed=False,
            macro_control_fanout_clock_wire_cost='positive and unmeasured'),
        slot=None if parent is None else parent.get('slot'),
        slot_fit_qualified=False, replica_count=96,
        fullshape_function_performance_qualified=False,
        route_launch_allowed=False, borrowed_419_credit=False,
        status='AVAILABLE_CATALOG_ONLY_PARENT_UNBOUND' if missing else 'PARENT_INPUTS_PRICED_NOT_ROUTE_QUALIFIED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--physical-prep', action='store_true')
    parser.add_argument('--parent-contract', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('preserve existing evidence')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    parent = json.loads(args.parent_contract.read_text()) if args.parent_contract else None
    result = physical_preparation(parent) if args.physical_prep else price()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
