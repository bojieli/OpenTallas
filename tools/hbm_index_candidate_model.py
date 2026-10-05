#!/usr/bin/env python3
"""Pre-build sizing and literal TP96/global-ID candidate boundary semantics.

No inference, checkpoint conversion, host-oracle instruction operands or measured
clock credit. Selection compares BF16 values, canonicalises signed zero, preserves
lowest-global-ID ties and prices every existing storage/stream boundary.
"""
import argparse
import json
from pathlib import Path

TP = 96
BLOCK = 8


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('preserve existing evidence')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(price(), indent=2) + '\n')
