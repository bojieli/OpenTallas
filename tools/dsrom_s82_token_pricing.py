"""Conditional S82 serial-path composition; no RTL or physical rate grant."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1/'
OUT = 'results/uarch/dsrom_s82_token_pricing_20261003/model.json'


def compose(baseline, inventory, ret, physical, multicast):
    if (inventory['stages'], inventory['pairs_per_rank_die'], inventory['BF_dual_pairs'],
            inventory['q_only_pairs'], inventory['layer_dies']) != (82, 2388, 512, 1876, 328):
        raise ValueError('exact S82 inventory required')
    if (ret['RD'], ret['ROOTD'], ret['existing_storage_NP']) != (64, 128, 4096):
        raise ValueError('RD4 rejected; retain full existing return')
    if ret['latency_credit_cycles'] != 0 or ret['RD4_credit_area_or_gain_claim']:
        raise ValueError('no return latency or area saving')
    if physical['UCIe_owner_crossings'] != 0:
        raise ValueError('PAIR1 required; do not transfer PAR2 crossing calendar')
    # Baseline already includes 57 board stage hops and their endpoint wires.
    # Retain that price for the new 24 hops; it is a source-model constraint,
    # not a contextual routed closure of the new 26x33 mm die.
    hop = baseline['hop_us']
    wire = 2 * 45 / 1200
    if abs(hop - (23.2 / 57 + wire)) > 1e-12:
        raise ValueError('baseline must include BOTH endpoint wires')
    for call in multicast['calls']:
        rows = call['result_rows']
        if call['destination_ranks'] != [1, 2, 3] or call['result_record_bits'] != 69:
            raise ValueError('actual TP4 canonical-owner multicast required')
        if abs(call['lower_model_us'] - ((rows + 2) / 1200 + wire)) > 1e-12:
            raise ValueError('missing multicast CDC or endpoint wire')
        if abs(call['shared_link_model_us'] - ((3 * rows + 2) / 1200 + wire)) > 1e-12:
            raise ValueError('missing serialized destinations or wire')
    extra = (82 - 58) * hop
    tau, draft = 3.649, .1173  # inherited model assumptions, not measured acceptance
    scenarios = []
    for ctx in ('1048576', '200000'):
        ar0 = 1e6 / baseline['m0_ar'][ctx]
        step0 = tau * 1e6 / baseline['m0_mtp'][ctx]
        verify0 = step0 - draft * ar0
        # Expose repetition instead of asserting a six-position multicast
        # shares data. Exact position-specific calendar remains necessary.
        for link in ('parallel_ports', 'one_shared_link'):
            field = 'lower_model_us' if link == 'parallel_ports' else 'shared_link_model_us'
            multicast_us = sum(c[field] for c in multicast['calls'])
            for repeats in (1, 6):
                ar = ar0 + extra + multicast_us
                verify = verify0 + extra + repeats * multicast_us
                draft_us = draft * ar
                step = verify + draft_us
                scenarios.append(dict(context=ctx, link_assumption=link,
                    verify_multicast_repetitions_assumed=repeats,
                    baseline_AR_us=ar0, baseline_verify_us=verify0,
                    added_stage_hops_us=extra, indexer_multicast_AR_us=multicast_us,
                    indexer_multicast_verify_us=repeats * multicast_us,
                    conditional_AR_us=ar, conditional_AR_tokens_s=1e6 / ar,
                    conditional_verify_us=verify, conditional_draft_us=draft_us,
                    conditional_MTP_step_us=step, conditional_MTP_tokens_s=tau * 1e6 / step))
    return dict(schema='opentallas.dsrom.s82.serial-path-price.v1',
        status='CONDITIONAL_MODEL_COMPONENT_COMPOSITION_NOT_FULL_TOKEN_QUALIFICATION',
        stages=82, layer_dies=328, total_dies=372, delta_dies_vs_S73=36,
        field_pairs_per_die=2388, BF_pairs=512, q_only_pairs=1876,
        return_RD=64, return_FF50_mm2=ret['FF50_reservation_mm2'],
        area_screen_mm2=856.5356341582075, screen_margin_mm2=858-856.5356341582075,
        stage_hops=dict(total=81, inherited=57, added_vs_S58=24, added_vs_S73=9,
            per_hop_us=hop, endpoint_wire_stages_per_side=45,
            endpoint_wire_us_per_hop=wire, total_endpoint_wire_us=81*wire,
            added_endpoint_wire_us_vs_S58=24*wire,
            added_stage_hops_us_vs_S58=extra, added_stage_hops_us_vs_S73=9*hop,
            includes_existing_link_serialization_transit=True),
        multicast_calls=len(multicast['calls']), scenarios=scenarios,
        tau_assumed=tau, draft_fraction_assumed=draft,
        double_count_rule='S58 already pays 57 hop endpoint wires; add only 24. Multicast price already pays its own two endpoints and CDC. Draft pays the composed AR change once.',
        missing_costs_not_zero=['matrix row-fragment gather and auxiliary-provider calendar',
            'actual S82 source/consumer/ready calendar and link arbitration',
            'position-specific six-position multicast reuse/repetition proof',
            'W3 selected scan homes, non-scan one-stack service and credit/refresh costs',
            'actual 26x33mm die endpoint routing and SS60/FF25 closure'],
        full_token_AR_us=None, full_token_MTP_us=None, physical_fit=False,
        adopted=False, headline_rate=None, old_S73_headline_transferred=False,
        no_PAR2_owner_crossing_credit_transferred=True)


def build(root=ROOT):
    paths = ['results/uarch/dsrom_return_storage_hbm_20261003/model.json'] + [BASE + f for f in
        ('inventory.json', 'return_baseline.json', 'physical_contract.json', 'indexer_multicast_model.json',
         'stage_map.json', 'area_ledger.json', 'uarch_contract.json')]
    blobs = {p: (root / p).read_bytes() for p in paths}
    objs = {p: json.loads(b) for p, b in blobs.items()}
    result = compose(objs[paths[0]]['baseline_at_model'], *[objs[p] for p in paths[1:5]])
    result['input_sha256'] = {p: hashlib.sha256(b).hexdigest() for p, b in blobs.items()}
    result['tool_sha256'] = hashlib.sha256((root / 'tools/dsrom_s82_token_pricing.py').read_bytes()).hexdigest()
    result['unified_model_sha256'] = hashlib.sha256((root / 'tools/uarch_model.py').read_bytes()).hexdigest()
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verify', action='store_true')
    args = ap.parse_args()
    payload = json.dumps(build(), indent=2, sort_keys=True) + '\n'
    path = ROOT / OUT
    if args.verify:
        if path.read_text() != payload: raise ValueError('record drift')
    else:
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(payload)
    print('PASS conditional S82 composition; physical/full-token admission absent')
