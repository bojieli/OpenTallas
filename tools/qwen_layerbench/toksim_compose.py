#!/usr/bin/env python3
"""toksim_compose: Qwen3-8B decode token on the Qwen ROM release dies, composed from MEASURED RTL stage cycles
(TOKSIM-QW 10-19, owner 18:18: cycle-accurate RTL measurement replaces the prices of record).

Static schedule => every stage's cycles are deterministic; the token is
    T = L0_cold + 35 x L_chained + head + per-layer priced die edges x 36 + embedding fetch
where L_chained / L0_cold come from dv_layer.compose (the ONE spliced decode calendar on the W5 pin timeline, the ctlm
plan's dependency gaps kept) with every PRICED stage replaced by its measured RTL value:
    DV families (SSQ / qk-norm+RoPE / residual / SiLU / STN / AR stagger)  ages from their Verilator benches
    column-tile matvec compute                                         XT1 column-slice RTL run (hr go -> rs / final)
    attention round trip (C2K + KV die + K2C)                          compute<->KV D2D pair RTL co-sim
    TP8 all-reduce                                                     TP8 collective RTL bench
Each term carries a grade:
    REL      measured on RTL byte-identical to the release source (origin/claude/qw-gen3-1019)
    NEWEST   measured on the newest bench-passing RTL of that element (not yet the release source) -- labelled
    PRICED   analytic / plan price (no measurement yet)
Usage: toksim_compose.py --inputs results/token_pass/measured_qwen_1019/inputs.json --out .../cycles.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_layer as L  # noqa: E402

CLK_PS = 833.0
HZ = 1e12 / CLK_PS


def tok_s(cycles):
    return HZ / cycles


def stage_grade(name, g):
    n = name.lower()
    if 'attention return' in n:
        return g['attn_return']
    if 'attention' in n:
        return g['attention']
    if 'all-reduce' in n:
        return g['allreduce']
    if 'matvec' in n:
        return g['tile']
    return g['dv']


def compose(inp):
    tm = {k: dict(v, far=inp['tile']['far']) for k, v in inp['tile']['ops'].items()}
    q8 = inp['allreduce'].get('qtp8')
    att = inp['attention']['round_trip_plan_cycles']
    out = {}
    runs = {}
    for name, kw in (('measured', dict(tile_mode='measured', attn_cycles=att, tile_meas=tm, qtp8=q8)),
                     ('dv_layer_priced', dict(tile_mode='priced'))):
        r = L.compose(1, 40, 'row', L.LANE_AGES, **kw)
        runs[name] = r
    c = runs['measured']['composition']
    cp = runs['dv_layer_priced']['composition']
    g = {k: v['grade'] for k, v in inp.items() if isinstance(v, dict) and 'grade' in v}
    stages = []
    for s in c['stages']:
        stages.append(dict(stage=s['stage'], start=s['start'], end=s['end'], cycles=s['cycles'],
                           priced_cycles=s['priced_cycles'], grade=stage_grade(s['stage'], g)))
    # critical-path share by grade: walk the layer timeline, assign each cycle of [first start, layer end) to the
    # LAST-ending stage covering it (the stage that holds the chain at that edge)
    t0, t1 = c['stages'][0]['start'], c['layer_latency']
    by = {}
    for t in range(t0, t1):
        cov = [s for s in stages if s['start'] <= t < s['end']]
        gr = max(cov, key=lambda s: s['end'])['grade'] if cov else 'PLAN_GAP'
        by[gr] = by.get(gr, 0) + 1
    chained, cold = c['chained_period'], c['l0_cold']
    die_edges = inp['die_edges']
    head = inp['head']
    emb = inp['embed_fetch']
    terms = [
        dict(term='L0 cold layer (stage-0 embedding landing + layer)', n=1, cycles=cold, grade='composed', by_grade=None),
        dict(term='L1..L35 chained layer period', n=35, cycles=chained, grade='composed', by_grade=None),
        dict(term='per-layer die edges not yet in the compiler (landings/n59/ctlm)', n=36, cycles=die_edges['cycles'],
             grade=die_edges['grade'], src=die_edges['source']),
        dict(term='LM head + argmax (compute die)', n=1, cycles=head['cycles'], grade=head['grade'], src=head['source']),
        dict(term='embedding row fetch through the KV die (token start)', n=1, cycles=emb['cycles'], grade=emb['grade'],
             src=emb['source']),
    ]
    T = sum(t['n'] * t['cycles'] for t in terms)
    # cycles by grade over the token: layer cycles split by the layer critical-path shares
    layer_cyc = cold + 35 * chained
    span = sum(by.values())
    tg = {k: layer_cyc * v / span for k, v in by.items()}
    for t in terms[2:]:
        tg[t['grade']] = tg.get(t['grade'], 0) + t['n'] * t['cycles']
    measured = sum(v for k, v in tg.items() if k in ('REL', 'NEWEST'))
    price = inp['price_of_record']
    one = dict(
        users=1, cycles_per_token=round(T), tok_s=round(tok_s(T), 1), clock_ps=CLK_PS,
        layer=dict(chained=chained, l0_cold=cold, layer_latency=c['layer_latency'],
                   priced_chained_ctlm=cp['priced_chained_period'], dv_layer_priced_chained=cp['chained_period'],
                   calendar=runs['measured']['calendar']['model'], calendar_clashes=runs['measured']['calendar']['clashes'],
                   stages=stages, critical_path_cycles_by_grade=by, tile=c['tile']),
        terms=terms,
        token_cycles_by_grade={k: round(v) for k, v in tg.items()},
        pct_measured=round(100 * measured / T, 1), pct_rel=round(100 * tg.get('REL', 0) / T, 1),
        pct_newest=round(100 * tg.get('NEWEST', 0) / T, 1),
        price_of_record=price, vs_price_pct=round(100 * (tok_s(T) / price['tok_s'] - 1), 2),
        gaps=runs['measured']['gaps'])
    out['1u'] = one
    mu = inp['multi_user']
    out['4u'] = dict(mu, note=mu.get('note'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    inp = json.loads(Path(a.inputs).read_text())
    r = compose(inp)
    rec = dict(schema='opentallas.toksim.qwen_rom.v1', lane='TOKSIM-QW', tool='tools/qwen_layerbench/toksim_compose.py',
               inputs=a.inputs, release_source=inp['release_source'], result=r)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    o = r['1u']
    print(json.dumps(dict(cycles=o['cycles_per_token'], tok_s=o['tok_s'], chained=o['layer']['chained'],
                          l0_cold=o['layer']['l0_cold'], pct_measured=o['pct_measured'], pct_rel=o['pct_rel'],
                          vs_price=o['vs_price_pct'], by=o['token_cycles_by_grade'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
