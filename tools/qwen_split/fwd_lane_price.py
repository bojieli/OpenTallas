#!/usr/bin/env python3
"""Q-DIE11-RLY 10-18: price the Qwen compute die's forwarded-clock HALF-CYCLE lanes + landings (OT_SPLIT_FWD_LANES=1,
rtl/qwen_split/qfd_fwd_lane.sv, lanes/LANDING-CONTRACT.md L4) on the Qwen ROM token path, the ledger's machinery
(tools/throughput/accepted_cost.py: results/arch/token_path_20261009/qwen_rom.json, longest-path solve with per-node
deltas, loss = 1 - T_base / T_new).

Per lane of n relay frames (case/fwd_lanes.json of the GEN):
  today (regional-root relays)      n + 1 edges         (n stations + the block's input flop)
  forwarded half-cycle + landing    N/2 + 1 + E + 1     (N = n - 1 half-cycle stations ahead of the landing, the ring,
                                                         the E handoff, the block flop; contract L4 with section 7)
  added a traversal                 N/2 + 2 + E - (n + 1)
E per lane: the GEN's (land plan E when OT_SPLIT_LAND_PLAN is set, else the S81 p4j half-cycle fit ceil((n-1)/2) + 1,
>= 2).  A bundle (several buses of one compiler slot) pays its worst lane once.

Which lanes a token crosses on its critical path (the DV dataflow of the split compute die, per layer of 36):
  attention  (L*.attn_kv)      slice dd -> native59 -> x3 -> d2d / KV die -> rx_payload -> native59 dr -> slice:
                               dv_x0_dd_*, dvw_dd_wo, lnk_x3*, lnk_rx_payload, dvw_dr_wi, dv_x0_dr_*
  all-reduce (L*.allreduce1/2) slice W0 ard -> W5 -> collective -> W5 rd -> W0 -> E0:
                               dv_x0_ar_*, dvw_ar*_wo, dvw_r*_wi, dv_x0_rt_*
  commands   (L*.qkv / o_proj / gate_up / down; --scope conservative only)  tt_ctlm cmd / hr -> slice W5 and the
                               slice status back (dvw_cmd_wi, dvw_hr_wi, dvw_ss_wo, dvw_ag_wo): charged as serial
                               on every ME op (the static schedule normally issues them ahead: upper bound)
  per token  embed (sf_emb_*, dvw_embed_prov_*, dvw_native59_emb_*), head.lm_head (sf_result_*)
Lanes not listed are control / status / configuration lanes off the token's critical path.

    fwd_lane_price.py --lanes case/fwd_lanes.json [--scope data|conservative] --out price.json
"""
import argparse, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'throughput'))
import accepted_cost as AC  # noqa: E402

GROUPS = {   # bundle (parallel buses of one compiler slot: worst lane once; bundles in series add) -> (lane bid regex, node regex)
    'attn_dd_x0': (r'^dv_x0_dd_', r'^L\d+\.attn_kv$'),
    'attn_dd':   (r'^dvw_dd_wo$', r'^L\d+\.attn_kv$'),
    'attn_x3':   (r'^lnk_x3', r'^L\d+\.attn_kv$'),
    'attn_rx':   (r'^lnk_rx_payload$', r'^L\d+\.attn_kv$'),
    'attn_dr':   (r'^dvw_dr_wi$', r'^L\d+\.attn_kv$'),
    'attn_dr_x0': (r'^dv_x0_dr_', r'^L\d+\.attn_kv$'),
    'ar_out_x0': (r'^dv_x0_ar_', r'^L\d+\.allreduce[12]$'),
    'ar_out':    (r'^dvw_ar[dlmtv]_wo$', r'^L\d+\.allreduce[12]$'),
    'ar_in':     (r'^dvw_r[delrv]_wi$', r'^L\d+\.allreduce[12]$'),
    'ar_in_x0':  (r'^dv_x0_rt_', r'^L\d+\.allreduce[12]$'),
    'embed':     (r'^(sf_emb_word_|dvw_embed_prov_|dvw_native59_emb_)', r'^embed$'),
    'head':      (r'^sf_result_', r'^head\.lm_head$'),
}
CONSERVATIVE = {
    'cmd':       (r'^dvw_cmd_wi$', r'^L\d+\.(qkv|o_proj|gate_up|down)$'),
    'hr':        (r'^dvw_hr_wi$', r'^L\d+\.(qkv|o_proj|gate_up|down)$'),
    'status':    (r'^dvw_(ss|ag)_wo$', r'^L\d+\.(qkv|o_proj|gate_up|down)$'),
}


def lane_cost(n, E):
    # Q-DIE11 10-18 kit fix: hop 0 is a full-cycle hop (rising capture), the N - 1 later stations are half-cycle
    N = n - 1
    st = (1 + (N - 1) / 2) if N >= 1 else 0
    return dict(today=n + 1, landed=st + 1 + E + 1, added=st + 2 + E - (n + 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--lanes', required=True, type=Path)
    ap.add_argument('--scope', choices=('data', 'conservative'), default='conservative')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    fl = json.loads(a.lanes.read_text())
    lanes = {r['bid']: r for r in fl['lanes'] if r.get('lane') != 'reset'}   # reset lanes: reset-time only, no token-path cost
    groups = dict(GROUPS, **(CONSERVATIVE if a.scope == 'conservative' else {}))
    doc = AC.load_path('qwen_rom')
    base, _ = AC.solve(doc['nodes'], doc['edges'])
    delta, rows = {}, []
    for g, (lrx, nrx) in groups.items():
        hit = [r for b, r in lanes.items() if re.search(lrx, b)]
        if not hit:
            rows.append(dict(group=g, lanes=[], added_per_traversal=0.0, note='no forwarded lane in this bundle'))
            continue
        costs = {r['bid']: dict(n=r['n'], E=r['E'], **lane_cost(r['n'], r['E'])) for r in hit}
        worst = max(costs.values(), key=lambda c: c['added'])
        add = worst['added']
        nodes = [n['id'] for n in doc['nodes'] if re.search(nrx, n['id'])]
        for i in nodes:
            delta[i] = delta.get(i, 0.0) + add
        rows.append(dict(group=g, lanes=costs, worst=worst, added_per_traversal=add, nodes=len(nodes), node_regex=nrx))
    new, _ = AC.solve(doc['nodes'], doc['edges'], delta)
    rec = dict(schema='opentallas.qwen_split.fwd_lane_price.v1', lanes_file=str(a.lanes), scope=a.scope,
               method=__doc__.split('\n\n')[1].strip(), token_path='results/arch/token_path_20261009/qwen_rom.json',
               base_cycles=round(base, 1), cycles=round(new, 1), added_cycles=round(new - base, 1),
               ar_tok_s_base=round(doc['clock_hz'] / base, 2) if doc.get('clock_hz') else None,
               ar_tok_s=round(doc['clock_hz'] / new, 2) if doc.get('clock_hz') else None,
               ar_change_pct=round(-AC.loss_pct(base, new), 3), mtp='n/a: the Qwen ROM token path has no qualified '
               'speculative composition (qwen_rom.json mtp.available false)',
               e_basis=sorted({r['E_basis'] for r in fl['lanes']}), groups=rows,
               lanes=len(fl['lanes']), stations=fl.get('stations'), landings=fl.get('landings'),
               skipped=[dict(bid=s['bid'], n=s['n'], reason=s['reason']) for s in fl.get('skipped', [])])
    txt = json.dumps(rec, indent=1) + '\n'
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(txt)
    print(json.dumps(dict(scope=a.scope, base=rec['base_cycles'], new=rec['cycles'], added=rec['added_cycles'],
                          ar_tok_s=[rec['ar_tok_s_base'], rec['ar_tok_s']], ar_change_pct=rec['ar_change_pct'])))


if __name__ == '__main__':
    main()
