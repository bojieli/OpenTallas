#!/usr/bin/env python3
"""KV-CLOCK 10-18: price the KV die's forwarded half-cycle lanes + landings (kv_fwd_lanes.py, LANDING-CONTRACT L4 + section
7) into the STATIC KV schedule and onto the Qwen ROM + KV token path (results/arch/token_path_20261009/qwen_rom.json,
tools/throughput/accepted_cost.py longest-path solve; loss = 1 - T_base / T_new).

Per lane of n stations: today n + 1 edges (n relays + the block flop); landed E + 2 (+ post stages) (the ring age E
covers hop 0 and the half-cycle stations, + the landing o flop + the block flop; KVR-FWDAGE 10-19: the old
1 + (n-2)/2 + 1 + E + 1 counted the station delay twice); E = planned (kv_fwd_lanes.planned_e) until the die STA measures
it.  added = landed - today is NEGATIVE for most lanes (half-cycle hops beat n full-cycle relays): the bundle records its
signed worst lane, the token charge takes max(0, worst) (no credit taken against a baseline priced on plan stages).  A bundle (one compiler slot: the lanes of one bus family and stack) pays its worst lane once.  The
schedule is static (no credits, no backpressure): every added edge is a fixed, compile-time latency per bundle.

On the token path the KV die sits in L*.attn_kv (8K-context attention of every layer) and L*.qknorm_rope (KV append):
  c -> stack  query / command / K-V write bundles     (aq, am, kc, est, ks_kvs_emb_px_*, ks_kvs_hroot_*, kg, hch*, hs*)
  stack -> c  score / partial / V word bundles       (ap, af, pvin, ks_kvpc_*, ks_slg_*, ks_afe_*)
charged in SERIES once per layer each way on attn_kv (conservative: the compiler normally overlaps the K-V append with
the next layer's projections).  Lanes of other families are reported, not charged.

    kv_fwd_lane_price.py --lanes RUN/fwd_lanes.json [--layers 36] --out price.json
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'throughput'))
import accepted_cost as AC  # noqa: E402

C2S = re.compile(r'(^|_)(aq|am|kc|est|ks_kvs_emb_px_t(ok|ep)|ks_kvs_hroot|kg|hch[a-z]|hs[a-z]{2})(_|$)')
S2C = re.compile(r'(^|_)(ap|af|pvin|ks_kvpc|ks_slg|ks_afe)(_|$)')


def family(st):
    n = re.sub(r'^(rly_|pinfix_)+', '', re.sub(r'__s\d+$', '', st))
    n = re.sub(r'^pinfix_', '', n)
    n = re.sub(r'_r\d+(_\d+)?$', '', n)
    n = re.sub(r'_\d+$', '', n)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lanes', required=True)
    ap.add_argument('--layers', type=int, default=36)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    L = json.load(open(a.lanes))['lanes']
    bundles = defaultdict(lambda: dict(lanes=0, bits=0, worst_added=None, worst_n=0, E=0, dir=None))
    for x in L:
        f = family(x['stations'][-1])
        d = 'c->st' if x['src_tree'] == 'c' else 'st->c' if x['dst_tree'] == 'c' else 'st->st'
        b = bundles[(f, d)]
        b['lanes'] += 1
        b['bits'] += x['S']
        if b['worst_added'] is None or x['added'] > b['worst_added']:
            b.update(worst_added=x['added'], worst_n=x['n'], E=x['E_planned'])
        b['dir'] = d
    charge = {}
    for d, rx in (('c->st', C2S), ('st->c', S2C)):
        cand = {k: v for k, v in bundles.items() if v['dir'] == d and rx.search(k[0])}
        if cand:
            k = max(cand, key=lambda k_: cand[k_]['worst_added'])
            charge[d] = dict(bundle=k[0], added_edges=max(0, cand[k]['worst_added']), worst_added_signed=cand[k]['worst_added'],
                             n=cand[k]['worst_n'], E=cand[k]['E'])
    per_layer = sum(v['added_edges'] for v in charge.values())
    doc = AC.load_path('qwen_rom')
    base, _ = AC.solve(doc['nodes'], doc['edges'])
    delta = {n['id']: per_layer for n in doc['nodes'] if re.match(r'^L\d+\.attn_kv$', n['id'])}
    new, _ = AC.solve(doc['nodes'], doc['edges'], delta)
    hz = doc['clock_hz']
    rec = dict(schema='opentallas.qwen_kv_fwd_lane_price.v1', lanes=a.lanes, lanes_total=len(L),
               rule='landed = E + 2 (+ post) vs today n + 1 (KVR-FWDAGE 10-19); worst lane per bundle, charged max(0, .); '
                    'c->st + st->c bundles in series on every L*.attn_kv (conservative)',
               bundles={f'{k[0]}|{k[1]}': v for k, v in sorted(bundles.items())}, charged_per_layer=charge,
               added_edges_per_layer=per_layer, layers_charged=len(delta),
               token=dict(base_cycles=base, new_cycles=new, base_tok_s=round(hz / base, 2), new_tok_s=round(hz / new, 2),
                          loss_pct=round(AC.loss_pct(base, new), 3)),
               note='E planned (S81 p4j half-cycle fit) until the KV die STA measures S1 per landing at TT and FF; the '
                    'accepted-cost ledger takes the measured figure')
    json.dump(rec, open(a.out, 'w'), indent=1)
    print(json.dumps(dict(charged=charge, per_layer=per_layer, token=rec['token'])))


if __name__ == '__main__':
    main()
