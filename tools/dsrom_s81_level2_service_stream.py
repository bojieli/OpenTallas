#!/usr/bin/env python3
"""One level-2 hub adjacency candidate. Source metadata only; no RTL adoption.

Optimises a fixed source dependency ledger, not stage count/ROM depth. The
ledger's historical worst-alias selection is not an actual expert trajectory.
"""
import argparse
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

BASE = 'results/uarch/dsrom_s81_service_capacity_split_20261004/r1/'
STAGES = 'results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json'
GROUP = 'results/uarch/dsrom_s81_minimum_protected_group_20261004/model.json'
CAPTURE = 'rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv'
SPINE = 'rtl/dsrom_sys/s81_capture_parent/ot_v41_spine_w17w10.sv'
TILE = 'rtl/dsrom_sys/s81_capture_parent/ot_chip_v41x_tile.sv'
PINS = [BASE+'model.json', BASE+'transport_movements.jsonl.gz', STAGES, GROUP,
        CAPTURE, SPINE, TILE,
        'results/uarch/dsrom_s81_split_latency_20261004/assessment.json',
        'tools/dsrom_s81_level2_service_stream.py']


def anchor_cost(transfers, anchor):
    """Worst rank byte-hop objective, preserving serial fragment demand."""
    ranks = defaultdict(int)
    for t in transfers:
        ranks[t['rank']] += abs(t['source_stage']-anchor)*(t['input_bytes']+t['output_bytes'])
    return max(ranks.values(), default=0)


def choose_anchor(transfers, allowed):
    if not allowed:
        raise ValueError('no canonical field home')
    return min(allowed, key=lambda a:(anchor_cost(transfers,a),a))


def reserve_before_go(quotas, positions, seats):
    if len(quotas)!=128 or len(seats)!=128 or not 1<=positions<=8:
        raise ValueError('full root/position shape required')
    demand=[q*positions for q in quotas]
    if any(q<0 or c<q for q,c in zip(demand,seats)):
        raise ValueError('no-ready phase exceeds reserved held storage')
    return demand


def model(root):
    load=lambda p:json.loads((root/p).read_text())
    stages=load(STAGES); group=load(GROUP); old=load(BASE+'model.json')
    reject=load('results/uarch/dsrom_s81_split_latency_20261004/assessment.json')
    assert reject['verdict']=='REJECT_SPLIT_AS_SUBMITTED'
    # Read actual accepted-port semantics rather than changing source.
    assert 'vm_accept' in (root/CAPTURE).read_text()
    assert 'capture_vm_accept' in (root/TILE).read_text()
    assert 'bt_xs_v <= s_adv' in (root/SPINE).read_text()
    nodes=[]; perlayer=defaultdict(list)
    with gzip.open(root/(BASE+'transport_movements.jsonl.gz'),'rt') as f:
        for line in f:
            n=json.loads(line); layer=int(n['node'].split('.')[0][1:])
            nodes.append((layer,n)); perlayer[layer].extend(n['transfers'])
    homes=[]; oldcuts=newcuts=branchbytes=0
    for l,ts in sorted(perlayer.items()):
        allowed=stages['layer_matrix_stages'][str(l)]
        anchor=choose_anchor(ts,allowed)
        newcuts+=anchor_cost(ts,anchor); oldcuts+=anchor_cost(ts,2*l)
        branchbytes+=max(sum(t['input_bytes']+t['output_bytes'] for t in ts if t['rank']==r) for r in range(4))
        homes.append(dict(layer=l,hub_endpoint=81+l,adjacent_field_stage=anchor,
            rank_die_ids=[4*(81+l)+r for r in range(4)],
            canonical_field_stages=allowed,
            topology='new service-only die adjacent to anchor; existing field chain unchanged',
            additional_chain_byte_hops_worst_rank=anchor_cost(ts,anchor),
            unavoidable_hub_branch_raw_payload_bytes_worst_rank=max(sum(t['input_bytes']+t['output_bytes'] for t in ts if t['rank']==r) for r in range(4))))
    area=old['capacity_screen']
    # New hubs do not steal any field capacity or copy HE/CROM. The prior
    # service outline is kept as an upper reservation (includes nine providers
    # and full return); those unnecessary blocks receive NO area credit here.
    hub_area=area['service_die_mm2']; field_area=area['field_die_mm2']
    ii=group['service']['bank_service_II_ns']; banks=128*2
    # Full64-byte complete masks ONLY; partial-stripe RMW cannot inherit this.
    optimistic_vm_GBps=banks*64/ii
    return dict(schema='opentallas.S81.level2_service_stream.v1',
        candidate='S81-L2-HUB40-NATIVE-ROOT-TP4',adopted=False,physical_build_admitted=False,
        predecessor_disposition='S81-SERVICE9-FIELD2417-SISTER40-TP4 REJECTED/INACTIVE as submitted; immutable artifacts retained',
        source_pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in PINS},
        scope='40-layer frozen worst-alias field ledger; HEAD/embedding and actual selected expert/calendar excluded',
        homes=homes,added_rank_dies=160,added_serial_stages=0,
        original_field_mapping_unchanged=True,field37_38_unchanged=True,
        storage_compute='all original 81*4 field dies, 2417 complete pairs/die and all canonical payload/provider identities retained; no fragmentation/pruning/depth/reassociation',
        placement=dict(same_die_collocation=False,
            selected='adjacent service-only hub plus local field-edge capture; no field move or serial SU matrix copy',
            reason='protected service and full field do not fit one die; adjacency is explicitly a cross-die boundary',
            field_mm2_before_new_overlays=field_area,field_overlay_budget_mm2=858-field_area,
            hub_reserved_mm2=hub_area,hub_overlay_budget_mm2=858-hub_area,
            reservation_reuse='prior fixed465.477 and strict5090 RD64 charges retained; prior nine-provider/full-return upper reservation kept on hub, zero removal credit',
            actual_rectangles_native_pins_PG_clock_union=None,placed_fit=False),
        cut=dict(objective='minimax rank raw dependency byte-hops over canonical field stages; deterministic earliest tie',
            old_provider_anchor_chain_byte_hops=oldcuts,selected_anchor_chain_byte_hops=newcuts,
            unavoidable_one_branch_raw_bytes=branchbytes,
            alias_choice_bias='frozen worst alias selected under predecessor metric, not exhaustive new-metric minimax or actual runtime',
            serialization_edges_raw_payload_floor=(branchbytes+63)//64,
            link_64B_target_edge_ns=1/1.2,
            serialization_only_floor_us=branchbytes/64/1.2/1000,
            serialization_scope='sum of raw payload floors in frozen sequential ledger, not a bound on actual overlapped full-token critical path; no source compression/reuse credit',
            accepted_packet_start_CDC_reverse_and_overlap_cost=None,
            single_user_token_delta_ns=None,full_MTP_iteration_delta_ns=None),
        endpoints=dict(
            activation=dict(source=f'{SPINE}: registered bt_xs_v/bt_xb_v under s_adv',
                fp4_bits_including_valid=549,full_PHW10_data_control_bits=1632,
                local='candidate hub-owned source stream feeds existing local field broadcast, no SU256 restore-copy operation',
                existing_native_interdie_export_implemented=False,
                crossdie='finite packetisation/CE-ready and identity binding required; 549/1632 widths are not link bandwidth',
                compressed_stream_bytes=None,raw_payload_charged_once=True),
            result=dict(source=f'{CAPTURE}: no-ready root_valid -> records -> held vm_valid -> positive vm_accept',
                roots=128,source_held_record_bits=68,raw_record_with_valid_bits=69,peak_raw_record_bits_per_native_edge=128*69,
                peak_scalar_bytes_per_native_edge=512,
                native_identity_bits=47,native_phase_bits=10,
                proposed_full_context_bits=169,physical_route_shard_bits=1,
                owner_binding='freeze full context before phase_take; map native47/phase10 to one held169 context; no truncation/era alias',
                retained_source_capture_CAP1_sufficient=False,
                admission='reserve each root quota*(np+1) before GO; bank/phase must not overlap; hold all accepted data on link/protection fault',
                required_protected_capture_storage_bits='sum(root_quota*(np+1))*144 plus protected context/control: two W6 64-bit stripes per69-bit record',
                raw_FF50_floor_um2_per_record=69*.2952*2,
                protected_FF50_floor_um2_per_record=144*.2952*2,
                quota_manifest_and_positions_selected=None,
                remote_transfer='formatter at field hub-edge; transport owned scalar packet, never reread result via SU',
                retirement='root capture stays owned until same-context protected home visibility AND positive captured reverse credit; packet ACK alone insufficient'),
            publication=dict(source=f'{TILE}: capture_commit/capture_vm_accept native last-writer veto',
                functional_scalar_ports=128,functional_bytes_per_edge=512,
                physical_provider=group['selected_provider'],physical_groups=128,banks_per_group=2,
                accept_condition='exclusive initialized old-read/merge/write/postverify; six matched checked copy commits and receiver-visible owner match before captured return; native array write alone is not protected ACK',
                bank_capacity_rows=1,bank_II_slow_edges=28,serial_target_GHz=.9,
                complete64B_mask_optimistic_GBps=optimistic_vm_GBps,
                ingress_link_GBps_target=76.8,
                column_coalescing_and_address_bank_conflicts=None,
                source_consumer_fence='effective adapter idle only after matching VM visible, packet retired and captured credit; address-version lease through native SU read+R+2 tag',
                packet_control_clock_routes_protected_slot_extra_mm2=None,
                clock_qualified=False)),
        composition_tasks=[
            'Nash: canonical S81 phase root quotas/np, exact address-to-W11 bank coalescing, finite masks and accepted held credit model for these hubs',
            'Claude: field-edge capture and hub link pins/home rectangles within field overlay budget, service-only hub outlines and clock/PG union',
            'Sagan/Popper: reuse activation source leases and actual selected expert/source dependencies; replace SU restore-copy PCs with native offered/accepted stream interfaces in model only',
            'Arch: bind full169 context and consumer visibility/fence to existing C8 caller, without changing field37/38 or live runtime'],
        not_admitted_because='selected quota/loaded links/CDC/slot union and accepted source consumer calendar not yet bound; no unknown assigned zero')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(model(root),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
