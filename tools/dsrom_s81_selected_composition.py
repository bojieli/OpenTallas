"""Selected S81/RD64 ROM composition. All rates and area remain model-only."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/dsrom_s81_selected_composition_20261003/model.json'
BASE = 'results/uarch/dsrom_s81_selected_composition_20261003/inputs/'
LEDGER = 'results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1/area_ledger.json'
BASELINE = 'results/uarch/dsrom_return_storage_hbm_20261003/model.json'
FF50_MM2_PER_BIT = .37908 / .5 / 1e6


def prune_inventory(np=2417, regions=128):
    """Prospective original 32-pair region binding; keep every live unary node.

    A source-emitted S81 leaf/node inventory must confirm this binding before
    any storage deletion is granted. This is enumeration, not contraction.
    """
    records = []
    for r in range(regions):
        pairs = (r+1)*np//regions-r*np//regions
        nodes = []
        def visit(lo, hi, level):
            if lo >= 2*pairs or hi-lo == 1:
                return
            mid = (lo+hi)//2
            nodes.append(dict(lo=lo, hi=hi, level=level, unary=mid >= 2*pairs))
            visit(lo, mid, level+1)
            visit(mid, hi, level+1)
        visit(0, 64, 0)
        records.append(dict(region=r, active_pairs=pairs, retained_nodes=len(nodes),
            retained_unary_nodes=sum(x['unary'] for x in nodes), nodes=nodes))
    return records


def compose(selected, ledger, baseline, proxy, projections):
    choice = selected['priced']['S81_ragged_RD64_replicated']
    if choice['return_option'] != 'ragged_RD64' or choice['area']['stages'] != 81:
        raise ValueError('selected S81 baseline RD64 required; no RD16 adoption')
    n, bf = math.ceil(195750 / 81), math.ceil(41984 / 81)
    q = n - bf
    if choice['area']['pairs'] != n or choice['indexer_multicast_us'] != 0:
        raise ValueError('active-pair and local-projection selection mismatch')
    ps = projections['records']
    if len(ps) != 20 or len({p['tensor'] for p in ps}) != 20:
        raise ValueError('all 20 source projection weights required')
    for p in ps:
        if (p['reserved_frames_credit_mm2'] != 0 or p['physical_owner_ranks'] != [0]
                or p['duplicate_source_payload_storage_removed'] != 3
                or len(p['rank_slices']) != 4 or any(s != p['rank_slices'][0] for s in p['rank_slices'])
                or p['rank_slices'] != p['reference_rank_slices']):
            raise ValueError('identical four-rank projection reservation; no dedup frame credit')
    s73 = ledger['sensitivity']['source_classified']['S73']
    fixed = s73['base_fixed_mm2']
    variable = s73['base_variable_mm2'] / s73['pairs'] * n
    terms = []
    for t in ledger['terms']:
        factor = {'die': 1, 'BF': bf / 362, 'q': q / 1686, 'sites': n / 2048, 'removed': 0}[t['mode']]
        terms.append(dict(name=t['name'], factor=factor, mm2=t['mm2'] * factor))
    nodes, roots, rd, rootd = 2 * n - 128, 128, 64, 128
    storage = dict(node_two_FIFO_bits=nodes * 2 * rd * 65,
                   node_output_register_bits=nodes * 66,
                   root_input_FIFO_bits=roots * rootd * 65,
                   root_held_sibling_bits=roots * rootd * 66)
    total_bits = sum(storage.values())
    ret_mm2 = total_bits * FF50_MM2_PER_BIT
    screen = fixed + variable + sum(t['mm2'] for t in terms) + ret_mm2
    if round(screen, 3) != choice['area']['die_mm2'] or round(ret_mm2, 3) != choice['area']['return_mm2']:
        raise ValueError('Claude S81 area must reproduce without field/copy/return double charge')
    if (proxy['NP'], proxy['R'], proxy['adder_proxy_mm2']) != (4096, 128, 3.158212608):
        raise ValueError('exact retained W1 proxy required')
    # Storage screen expressly excludes adders. Keep this separate proxy floor
    # positive; it is not a synthesized area of the baseline RD64 node.
    adder_floor = proxy['adder_proxy_mm2'] * nodes / (2 * proxy['NP'] - proxy['R'])
    prune = prune_inventory(n, roots)
    prune_nodes = sum(r['retained_nodes'] for r in prune)
    prune_bits = prune_nodes * (2*rd*65+66) + roots*rootd*(65+66)
    prune_storage = prune_bits*FF50_MM2_PER_BIT
    nonreturn = screen-ret_mm2
    options = dict(
        original_retained=dict(nodes=8064, roots=128,
            FF50_mm2=(8064*(2*rd*65+66)+roots*rootd*(65+66))*FF50_MM2_PER_BIT,
            screen_mm2=nonreturn+(8064*(2*rd*65+66)+roots*rootd*(65+66))*FF50_MM2_PER_BIT,
            source_latency_or_fault_equivalence_qualified=False),
        prune_only=dict(nodes=prune_nodes, roots=128,
            retained_unary_nodes=sum(r['retained_unary_nodes'] for r in prune),
            removed_nodes_vs_original=8064-prune_nodes, FF50_mm2=prune_storage,
            screen_mm2=nonreturn+prune_storage,
            screen_margin_fraction=(858-nonreturn-prune_storage)/858,
            adder_proxy_mm2=proxy['adder_proxy_mm2']*prune_nodes/8064,
            binding='Existing 32-pair regions; first floor((r+1)*2417/128)-floor(r*2417/128) pairs active; preserve all live unary RD64/WAIT/RST stages.',
            actual_source_removed_storage_inventory=None, actual_pruning_qualified=False,
            source_latency_or_fault_equivalence_qualified=False),
        contracted=dict(nodes=nodes, roots=128, FF50_mm2=ret_mm2,
            screen_mm2=screen, screen_margin_fraction=(858-screen)/858,
            adder_proxy_mm2=adder_floor, unary_stages_removed_vs_prune=prune_nodes-nodes,
            actual_source_removed_storage_inventory=None,
            FIFO_WAIT_RST_fault_sites_changed=True,
            source_latency_or_fault_equivalence_qualified=False))
    m0 = baseline['baseline_at_model']
    hop = m0['hop_us']
    wire = 2 * 45 / 1200
    if abs(hop - (23.2 / 57 + wire)) > 1e-12:
        raise ValueError('both hub-to-edge wire paths must remain charged')
    scenarios = []
    for ctx in ('1048576', '200000'):
        ar0 = 1e6 / m0['m0_ar'][ctx]
        verify0 = 3.649 * 1e6 / m0['m0_mtp'][ctx] - .1173 * ar0
        ar = ar0 + 23 * hop
        verify = verify0 + 23 * hop
        step = verify + .1173 * ar
        expected = choice['rate'][ctx]
        if round(ar, 3) != expected['AR_us'] or round(step, 3) != expected['MTP_step_us']:
            raise ValueError('source serial path mismatch')
        scenarios.append(dict(context=ctx, base_AR_us=ar0, base_verify_us=verify0,
            stage_hop_delta_us=23 * hop, indexer_multicast_us=0,
            conditional_AR_us=ar, conditional_AR_tokens_s=1e6 / ar,
            conditional_verify_us=verify, conditional_draft_us=.1173 * ar,
            conditional_MTP_step_us=step, conditional_MTP_tokens_s=3.649e6 / step))
    return dict(schema='opentallas.dsrom.selected-s81.v1', status='SELECTED_BUILD_TARGET_MODEL_ONLY',
        stages=81, layer_dies=324, total_dies=368, pairs_per_rank_die=n, BF_pairs=bf, q_pairs=q,
        selected_return=dict(RD=rd, ROOTD=rootd, contracted_model_nodes=nodes, roots=roots,
            state_bits=storage, total_state_bits=total_bits, FF50_mm2=ret_mm2,
            adder_proxy_scaled_by_nodes_mm2=adder_floor, credit_RD16_adopted=False,
            measured_latency_credit_cycles=None, topology_and_golden_order_qualified=False),
        return_options=options,
        area=dict(fixed_mm2=fixed, all_rank_field_reservation_mm2=variable,
            increment_terms=terms, screen_mm2=screen, screen_margin_fraction=(858-screen)/858,
            screen_plus_excluded_adder_proxy_mm2=screen+adder_floor,
            margin_with_adder_proxy_fraction=(858-screen-adder_floor)/858,
            complete_area_mm2=None, contextual_route_SS_FF_fit=False),
        L4=dict(projection_records=20, rank_copies=4, added_copies_vs_canonical=3,
            copied_elements=sum(p['rows']*p['K']*3 for p in ps),
            frame_credit_mm2=0, incremental_double_charge_mm2=0,
            area_charge='All four copies remain inside ceil(195750/81) field pairs and BF/q/cfg/halo reservations; no dedup frame credit ever applied.',
            result_multicast_required=False, source_payload_bijection_and_rank_local_issue_qualified=False),
        stage_hops=dict(total=80, inherited=57, added=23, per_hop_us=hop,
            endpoint_wire_stages_per_side=45, total_endpoint_wire_us=80*wire,
            added_endpoint_wire_us=23*wire), scenarios=scenarios,
        component_resources=dict(stage_rank_replicas=324, complete_pairs=324*n,
            weight_macros=4*324*n, BF_MACs_per_cycle_per_pair=32, q_MACs_per_cycle_per_pair=64,
            ROM_read_bytes_per_cycle_per_pair=68.5,
            field_return_bits_per_cycle=n*126, node_input_bits_per_cycle_per_node=130,
            node_output_bits_per_cycle_per_node=65, root_output_bits_per_cycle=128*69,
            forward_q_bits=549, forward_BF_bits=1067,
            replica_payload_physical_addresses=None, selected_channel_track_fit=None,
            mux_demux_fanout_contextual_cost=None),
        tau_assumed=3.649, draft_fraction_assumed=.1173,
        missing_costs_not_zero=ledger['exact_cost_gaps'] + [
            'Actual emitted prune-only versus contracted storage inventory and FIFO/WAIT/RST/fault equivalence',
            'S81 full directory/phase reshaping and copied-projection address/issue exactness',
            'actual S81 full-program gather/provider/link/refresh calendar',
            'position-specific verify/draft schedule and actual acceptance tau'],
        full_token_measured=False, adopted=False, headline_rate=None,
        price_scope='Source model assumes no added return delay. Both prune-only and contraction require emitted storage and actual timing/WAIT/RST/fault comparison; changed serial-path debit is unknown, not a zero measured credit.',
        double_count_rule='Copied field reservations once; each topology node FIFOs/output registers once; unchanged 128 root FIFOs/held buffers once; inherited 57 stage wires plus 23 new hops once.')


def build(root=ROOT):
    paths = [BASE+'claude_S81.json', LEDGER, BASELINE, BASE+'W1_return_proxy.json', BASE+'projection_reservations.json']
    blobs = {p: (root/p).read_bytes() for p in paths}
    result = compose(*(json.loads(blobs[p]) for p in paths))
    native_path = BASE+'native_node_mapping.json'
    blobs[native_path] = (root/native_path).read_bytes()
    native = json.loads(blobs[native_path])
    if native['parameters'] != dict(BYPASS=1, RD=64, RST=1) or native['root_logic_mapped']:
        raise ValueError('exact mapped full-RD64 node construction required; roots unmeasured')
    one = native['node_FF50_projection_mm2']/native['native_node_instances']
    for option in result['return_options'].values():
        option['native_complete_node_FF50_projection_mm2'] = one*option['nodes']
        option['native_full_node_projection_is_incremental_debit'] = False
        option['complete_node_fixed_residual_union_reconciled'] = False
        option['root_logic_area_mm2'] = None
    result['native_area_composition_rule'] = 'Mapped complete-node construction includes its storage. Replace that storage slot and reconcile logic with fixed/residual homes; do not blindly add the full node projection or infer fit. Root logic is unmapped.'
    result['input_sha256'] = {p: hashlib.sha256(b).hexdigest() for p,b in blobs.items()}
    result['source_commits'] = dict(selected='73851317fd9b4fb86c56f6ff760e29981ec610f2',
        adder_proxy='046bf5026d36cc4f31813db26045360da618e51f')
    result['tool_sha256'] = hashlib.sha256((root/'tools/dsrom_s81_selected_composition.py').read_bytes()).hexdigest()
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    payload = json.dumps(build(), indent=2, sort_keys=True)+'\n'
    p = ROOT/OUT
    if args.verify:
        if p.read_text() != payload: raise ValueError('record drift')
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(payload)
    print('PASS selected S81 model-only composition')
