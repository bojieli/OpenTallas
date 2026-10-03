#!/usr/bin/env python3
"""Source VM ordering and finite completion obligations for the DS split parent.

The reference below models one retained logical edge, not a two-clock RTL
implementation. It exposes the read-old / ordered-write behavior that a real
provider and compiler calendar must preserve. No free memory ports or cycles.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_split_vm_contract_20261003'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_inputs():
    for row in json.loads((BASE / 'inputs/origins.json').read_text()):
        path = BASE / ('inputs/' + row['copy'] if 'kind' not in row and row['copy'] in ('tile.sv', 'core.sv', 'parent_model.json') else row['copy'])
        if digest(path) != row['sha256']:
            raise ValueError('Pinned input drift: ' + str(path))


# Order and anchors are the literal retained clocked block. Later NBA wins.
WRITE_SPEC = [
    ('HE', 'if (ww_h_we)', 32, True),
    ('field', 'if (rom_we[q])', 64, True),
    ('ME', 'if (vw_me_mask[q*W + l])', 64, True),
    ('legacy_SU', 'if (vw_su_we[q])', 8, False),
    ('legacy_reducer', 'if (vw_rd_we[q])', 8, False),
    ('SU', 'if (xs_vm_we[q])', 256, True),
    ('SU_reducer', 'if (xs_res_we[q])', 32, True),
    ('XU_scalar', 'if (vw_xe_we)', 1, True),
    ('QE', 'if (ww_q_mask[q])', 32, True),
    ('XU_block', 'if (ww_x_mask[q])', 32, True),
    ('package', 'if (xa_we)', 16, True),
    ('collective', 'if (xb_we4[b])', 64, True),
]
READ_SPEC = [
    ('HE', 'if (vh_re[q])', 8, True),
    ('ME', 'if (vx_re[q])', 4, True),
    ('legacy_SU', 'if (vs_re[q])', 32, False),
    ('legacy_gather', 'if (vi_re[q])', 8, False),
    ('QE_id', 'if (vq_re)', 1, True),
    ('field_activation', 'if (rom_xre)', 64, True),
    ('field_id', 'if (rom_vre)', 1, True),
    ('XU_scalar', 'if (vr_re)', 1, True),
    ('QE_block', 'if (wqr_re)', 32, True),
    ('XU_block', 'if (wxr_re)', 32, True),
    ('selector', 'if (vsl_re[q])', 64, True),
    ('SU_indirect', 'if (xs_vi_re[q])', 256, True),
    ('SU_operands', "2'd0: xs_rd_q", 1024, True),
    ('HBM_weight_id', 'if (xi_re)', 1, True),
    ('package', 'if (xa_re)', 16, True),
    ('collective', 'if (xb_re)', 16, True),
]


def ordered_edge(memory, reads, writes):
    """Reads [(id,address)], writes [(id,address,value)] in source NBA order.

    Losing writes retire as superseded; they do not get a visible-write ACK.
    Addresses here are already expanded according to the source expressions.
    Expanded addresses must be integers within VM_AW19; booleans are not
    addresses. Request identities are opaque nonnegative integers or nonempty
    test labels, unique within each direction. Same-address fanout uses distinct
    read identities; this reference never collapses accepted requests.
    """
    reads = tuple(reads)
    writes = tuple(writes)
    limit = 1 << 19
    for _, address in reads:
        if type(address) is not int or not 0 <= address < limit:
            raise ValueError('Read outside retained VM extent')
    for _, address, _ in writes:
        if type(address) is not int or not 0 <= address < limit:
            raise ValueError('Write outside retained VM extent')
    for direction, requests in [('Read', reads), ('Write', writes)]:
        ids = [request[0] for request in requests]
        if any(not ((type(rid) is int and rid >= 0) or
                    (type(rid) is str and rid != '')) for rid in ids):
            raise ValueError(direction + ' identity must be a nonnegative integer or nonempty label')
        if len(ids) != len(set(ids)):
            raise ValueError(direction + ' transaction identity reused')
    reply = {rid: memory[address] for rid, address in reads}
    winners = {address: wid for wid, address, _ in writes}
    after = dict(memory)
    receipts = {}
    for wid, address, value in writes:
        after[address] = value
        receipts[wid] = 'VISIBLE_WINNER' if winners[address] == wid else 'SUPERSEDED_NOT_VISIBLE'
    return reply, after, receipts


def idle_join(original_idle, pending_requests, pending_writes, journal_rows,
              engine_retired, epoch_live):
    return bool(original_idle and epoch_live and engine_retired and
                pending_requests == pending_writes == journal_rows == 0)


def source_waited(waitmask, joined_idles, gos):
    return (waitmask & ~(joined_idles & ~gos) & 31) == 0


def finite_batches(pending, width, interval, response_latency):
    """Conditional service bound; grant interval is a provider obligation.

    No caller may supply zero cost or count memory acceptance as visibility.
    This function does not establish a grant interval from a source array.
    """
    if min(width, interval) < 1 or pending < 0 or response_latency < 1:
        raise ValueError('Missing positive finite provider contract')
    return math.ceil(pending / width) * interval + response_latency if pending else 0


def build():
    checked_inputs()
    tile = (BASE / 'inputs/tile.sv').read_text()
    core = (BASE / 'inputs/core.sv').read_text()
    parent = json.loads((BASE / 'inputs/parent_model.json').read_text())
    start = tile.index('always @(posedge clk) begin')
    positions = [tile.index(anchor, start) for _, anchor, _, _ in WRITE_SPEC]
    if positions != sorted(positions):
        raise ValueError('Retained write priority changed')
    for _, anchor, _, _ in READ_SPEC:
        if anchor not in tile[start:]:
            raise ValueError('Retained read port missing: ' + anchor)
    assert "wire waited = ((d_wait & ~(idles & ~gos)) == 5'd0);" in core
    assert 'waited && (&idles) && !coll_busy' in core
    assert 'parameter integer X_SU  = 1' in tile
    for tied in ('assign vi_re = 0', 'assign vs_re = 0', 'assign vw_su_we = 0', 'assign vw_rd_we = 0'):
        assert tied in core
    reads = sum(n for _, _, n, active in READ_SPEC if active)
    writes = sum(n for _, _, n, active in WRITE_SPEC if active)
    # Existing all-ports upper envelope, not actual simultaneous workload or
    # a free multiported SRAM. Reads may coincide; broadcasts need logic.
    out = {
        'schema': 'DS_SPLIT_VM_ORDER_CONTRACT_V1',
        'candidate': parent['candidate'],
        'source_parent_commit': '9ffc7a30c13af94c9dc2f4c69b9fc1c276dd9cdc',
        'profile': {'VM_AW': 19, 'AW': 30, 'SUN': 256, 'ROM_R': 64, 'X_SU': 1},
        'capacity': {'elements': 1 << 19, 'word_bits': 32, 'bits': (1 << 19) * 32},
        'write_priority': [dict(owner=o, anchor=a, expanded_max=n, active=x, order=i)
                           for i, (o, a, n, x) in enumerate(WRITE_SPEC)],
        'read_ports': [dict(owner=o, anchor=a, expanded_max=n, active=x)
                       for o, a, n, x in READ_SPEC],
        'source_semantics': {
            'read_image': 'Pre-edge VM for every read, including reads lexically after writes; NBA commits after the clocked block.',
            'write_image': 'Last enabled write to a given expanded address wins in literal source order. Within a source loop, later lane wins. Collective bank3 wins over banks0..2 and package on the same aligned address.',
            'visible_receipt': 'Only winner is visible in post-edge image. A superseded write can receive source-semantic retirement, never an owner-visible completion. Mandatory publication must reject/suppress aliases unless an exact intended-alias contract is proved.',
            'address': 'Source generally slices AW30 to VM_AW19; masked-block arithmetic can then exceed the VM end. Expanded addresses must be region/home-bound, not assumed valid from high-level instruction width. No silent wrapping of expanded out-of-range addresses.',
            'concurrency': 'd_wait is a selected five-unit mask, not an all-engine barrier. Collective alone requires all idles; unit_ready permits overlap of other independent engines. Do not infer one producer at a time.',
        },
        'demand_envelope': {
            'read_element_ports': reads, 'write_element_ports': writes,
            'read_payload_bits_per_chain_cycle': 32 * reads,
            'write_payload_bits_per_chain_cycle': 32 * writes,
            'read_bytes_per_chain_cycle': 4 * reads,
            'write_bytes_per_chain_cycle': 4 * writes,
            'MACs_per_cycle': 0,
            'meaning': 'Source all-enabled envelope under X_SU1 and selected R64; not observed simultaneous traffic or a required full multiport implementation. Compiler calendar may lower it only with source-bound exclusion/address proof.',
            'SU_readmax_includes_VM_selected_only': True,
            'legacy_SU_ports_pruned_only_by_X_SU1': True,
        },
        'construction': {
            'default_off': 'DS_SPLIT_DOMAINS=0',
            'component_owner': 'Claude: shared FIFO RTL; Archimedes: DS parent source events/provider/clock/reset/rate/load model',
            'admit': 'Original waited/unit_ready/gates AND command credits AND all nonstall preload/result seats reserved AND generation live.',
            'joined_idle': 'original idle AND epoch live AND requests0 AND writes0 AND journal0 AND actual engine/output retired. Separate reverse completion; no enqueue or mergerdone credit.',
            'read': 'Hold accepted request/address/generation until matched response. Store response before arithmetic consumer step; one-cycle implicit replies cannot cross clocks unchanged.',
            'commit': 'Keep source/dependency ordering in logical batches; snapshot all reads before batch writes; coalesce only source-proved same-edge aliases using literal winner rule. Physical backend commits winners, then visible receipts.',
            'two_clock_limit': 'Retained same-edge reference is not proof of split-domain event equivalence. Compiler dependency/address/home map must bind cross-domain ordering; no assumed phase/MCP exception.',
            'service': 'A backend must name native bank/address, read and write grants, maximum interval, macro response/capture latency, RMW/byte-mask semantics, and reset epoch receipts. Source reg array supplies no physical finite grant guarantee.',
            'queue': 'Earlier eight-seat bridge cost is a prospective reservation, not selected shared FIFO depth or a bound on producer bursts. Field raw journal remains reserved independently; do not replace CKV512 immutable seats.',
        },
        'latency': {
            'conditional_bound': 'ceil(pending/grants_per_service)*max_grant_interval + measured_response_capture_cycles; add FIFO launch/capture and visibleACK, at actual destination clock.',
            'no_fixed4_5_upper_bound': True,
            'no_all_enabled_envelope_serial_token_multiplication': True,
            'whole_token_calendar_binding': 'Maxwell + installed source/trace Hubble; Arch per-edge event/reference supplied here.',
        },
        'next_exact_contracts': [
            {'owner': 'Archimedes with Maxwell', 'deliverable': 'Bind actual VM provider homes/banks/masks to grant intervals and route/slot costs; validate witness aliases and compiled non-alias regions.'},
            {'owner': 'Claude with Archimedes', 'deliverable': 'Freeze component ports, real two-clock reset/epoch/drain and measured loaded timing; DS parent dispatch uses resolved command packets, not Qwen ownership transfer.'},
            {'owner': 'Hubble', 'deliverable': 'Installed binary/defines/source lease; issue PC/waitmask/go, request accept/response, VM visible write and engine/output retirement trace.'},
            {'owner': 'Epicurus', 'deliverable': 'CKV generation/accept/immutable512/9 visible writes and QK/PV final retirement; no duplicated CKV implementation.'},
        ],
        'admission': {'engine_RTL': False, 'physical': False, 'full_token': False,
                      'reason': 'Source ordering and demand now bounded; actual memory grants/slot and two-clock event mapping still required.'},
        'pin_access_review': {'commit': '9b7b120388ff0c8888f69bcf38211865c7cee8e7',
                              'independent_tests': 7, 'confirmed_historical_cause': 'p12q9 only',
                              'other_R0_MY': 'Routed TT negative timing preserved',
                              'chosen_placement_check_required': True, 'not_via_PG_closure': True},
        'live_jobs_unchanged': True, 'new_engine_RTL': False,
    }
    (BASE / 'model.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    return out


if __name__ == '__main__':
    model = build()
    print(json.dumps(model['demand_envelope'], indent=2))
