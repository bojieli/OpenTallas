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


def stage_grade(name, g, row=None):
    if row is not None and row.get('grade'):
        return row['grade']
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


_LOAD = {'slice': L.D.load_ages, 'vec': L.V.load_ages}
_DELTA = {}


def _shift(v, d):
    if isinstance(v, list):
        return [_shift(x, d) for x in v]
    if isinstance(v, dict):
        return {k: _shift(x, d) for k, x in v.items()}
    return v + d if isinstance(v, (int, float)) and not isinstance(v, bool) else v


def _loader(kind):
    def load(path=None):
        a = _LOAD[kind]() if path is None else _LOAD[kind](path)
        for k, d in _DELTA.get(kind, {}).items():
            a[k] = _shift(a[k], d)
        return a
    return load


L.D.load_ages = _loader('slice')
L.V.load_ages = _loader('vec')


def set_dv_ages(ages):
    """inputs dv.ages = {slice, vec, stn} repo-relative paths of the DV family ages MEASURED on the release slice RTL
    (TOKSIM-QW/STG gen3 calibrations); they replace the committed qlb_c4/qlb_c4b ages for every lowering."""
    if not ages:
        return
    _LOAD['slice'].__defaults__ = (ages['slice'],)
    _LOAD['vec'].__defaults__ = (ages['vec'],)
    L.M.STN_AGES = ages['stn']


def set_age_deltas(dd):
    """QW-TOKSCHED: PRICED per-SU-command age shifts (ledger dv_age_deltas) applied on top of the measured ages, so
    every lowering / the spliced calendar absorbs them (None = measured ages unchanged)"""
    _DELTA.clear()
    if not dd:
        return
    for kind, keys in dd['keys'].items():
        _DELTA[kind] = {k: dd['per_su_command'] + (dd.get('vm_write_extra', 0) if k == 'red_vm' else 0) for k in keys}


def apply_ledger(inp, variant=None):
    """QW-TOKSCHED 10-20: inputs.sched.ledger = the ONE priced-edge ledger (die + release-successor edges). Returns
    (die_edges section, lane_ages path, dv_age_deltas | None, qtp8 overrides). variant 'asbuilt' drops every
    'successor' item (cycles_asbuilt when given, else 0); other variants pick cycles_<variant> as before."""
    sc = inp.get('sched')
    if not sc:
        return inp['die_edges'], L.LANE_AGES, None, inp['allreduce'].get('qtp8')
    lg = json.loads((L.ROOT / sc['ledger']).read_text())
    asb = variant == 'asbuilt'
    edges = []
    for e in lg['die_edges']:
        e = dict(e)
        if asb and e.get('scope') == 'successor':
            e['cycles'] = e.get('cycles_asbuilt', 0)
        edges.append(e)
    de = dict(inp['die_edges'], edges=edges, source=f"{sc['ledger']} ({lg['lane']})")
    q8 = dict(inp['allreduce'].get('qtp8') or {})
    if not asb and lg.get('allreduce', {}).get('qtp8'):
        q8.update(lg['allreduce']['qtp8'])
    dd = None if asb else lg.get('dv_age_deltas')
    return de, lg['lane_ages']['path'], dd, q8


def die_edge_map(de, variant=None):
    """inputs die_edges.edges (TOK.QW.SCHED) -> dv_layer.compose die_edges {boundary: [edge]}; variant picks each
    edge's cycles_<variant> when present (e.g. the slice2 plan bound 'plan' vs the root-accepted bound)"""
    if not de or 'edges' not in de:
        return None
    m = {}
    for e in de['edges']:
        cyc = e.get(f'cycles_{variant}', e['cycles']) if variant else e['cycles']
        for b in e['at']:
            m.setdefault(b, []).append(dict(label=e['label'], cycles=cyc, grade=e.get('grade', 'PRICED'),
                                            source=e.get('source', '')))
    return m


def split_attention(stages, att):
    """attention row -> D2D C2K (REL) + KV die service (its own grade) + K2C / landing tail (REL), same total"""
    sp = att.get('split')
    if not sp:
        return stages
    out = []
    for s in stages:
        if s['stage'].startswith('attention (D2D'):
            parts = [('attention D2D C2K: cmd issue -> KV land (REL pair RTL)', sp['c2k'], sp['c2k_grade']),
                     ('attention KV die service: cmd land -> r31 issue', sp['kv_service'], sp['kv_service_grade']),
                     ('attention D2D K2C: r31 issue -> landing tail (plan done)', s['cycles'] - sp['c2k'] - sp['kv_service'],
                      sp['k2c_grade'])]
            t = s['start']
            for n, cyc, gr in parts:
                out.append(dict(stage=n, start=t, end=t + cyc, cycles=cyc, priced_cycles=None, grade=gr))
                t += cyc
            assert t == s['end'], (t, s)
        else:
            out.append(s)
    return out


def compose(inp, variant=None):
    tm = {k: dict(v, far=inp['tile']['far']) for k, v in inp['tile']['ops'].items()}
    q8_meas = inp['allreduce'].get('qtp8')
    att = inp['attention']['round_trip_plan_cycles']
    die_sec, lane_ages, age_dd, q8 = apply_ledger(inp, variant)
    inp = dict(inp, die_edges=die_sec)
    de = die_edge_map(die_sec, None if variant == 'asbuilt' else variant)
    out = {}
    runs = {}
    base_ages = inp['dv'].get('base_ages')
    set_age_deltas(None)
    if base_ages:                                 # the committed (pre-gen3) ages -> per-stage REL vs DIAG rows
        set_dv_ages(base_ages)
        runs['dv_base'] = L.compose(1, 40, 'row', lane_ages, tile_mode='measured', attn_cycles=att, tile_meas=tm,
                                    qtp8=q8, die_edges=de)
    set_dv_ages(inp['dv'].get('ages'))
    # no-edge reference: measured ages, dv2f14bi lane ages, measured AR, no die edges (the 4u frame's own timing basis)
    runs['noedge'] = L.compose(1, 40, 'row', L.LANE_AGES, tile_mode='measured', attn_cycles=att, tile_meas=tm,
                               qtp8=q8_meas)
    if age_dd or q8 != q8_meas:
        # same edges / lane ages, measured ages + measured AR: the cycles the PRICED successor terms add are re-graded
        runs['no_successor_terms'] = L.compose(1, 40, 'row', lane_ages, tile_mode='measured', attn_cycles=att,
                                               tile_meas=tm, qtp8=q8_meas, die_edges=de)
    set_age_deltas(age_dd)
    for name, kw in (('measured', dict(tile_mode='measured', attn_cycles=att, tile_meas=tm, qtp8=q8, die_edges=de)),
                     ('dv_layer_priced', dict(tile_mode='priced'))):
        r = L.compose(1, 40, 'row', lane_ages if name == 'measured' else L.LANE_AGES, **kw)
        runs[name] = r
    set_age_deltas(None)
    c = runs['measured']['composition']
    cp = runs['dv_layer_priced']['composition']
    g = {k: v['grade'] for k, v in inp.items() if isinstance(v, dict) and 'grade' in v}
    stages = []
    for s in c['stages']:
        stages.append(dict(stage=s['stage'], start=s['start'], end=s['end'], cycles=s['cycles'],
                           priced_cycles=s['priced_cycles'], grade=stage_grade(s['stage'], g, s)))
    stages = split_attention(stages, inp['attention'])
    dv_rows = []
    if 'dv_base' in runs:
        bs = {s['stage']: s['cycles'] for s in runs['dv_base']['composition']['stages']}
        for s in stages:
            if s['grade'] == g['dv'] and '(DV)' in s['stage'] and s['stage'] in bs:
                dv_rows.append(dict(stage=s['stage'], rel_cycles=s['cycles'], base_cycles=bs[s['stage']],
                                    delta=s['cycles'] - bs[s['stage']], grade=s['grade'], replaces='DIAG'))
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
    folded = de is not None
    head = inp['head']
    emb = inp['embed_fetch']
    terms = [
        dict(term='L0 cold layer (stage-0 embedding landing + layer)', n=1, cycles=cold, grade='composed', by_grade=None),
        dict(term='L1..L35 chained layer period', n=35, cycles=chained, grade='composed', by_grade=None),
        dict(term='per-layer die edges NOT folded into the layer schedule', n=36,
             cycles=die_edges.get('unfolded_cycles', 0) if folded else die_edges['cycles'],
             grade=die_edges['grade'], src=die_edges['source']),
    ]
    # QW-TOKSCHED2: ledger edges with cycles_l0 (e.g. the XDIE L0 attention window) differ in the cold layer: the
    # composed L0 carries the chained value, this term moves it to the L0 value (one row per grade)
    l0c = {}
    for e in (die_edges.get('edges') or []) if folded else []:
        if 'cycles_l0' in e:
            d0 = e['cycles_l0'] - e['cycles']
            if d0:
                l0c[e.get('grade', 'PRICED')] = l0c.get(e.get('grade', 'PRICED'), 0) + d0
    terms += [dict(term=f'L0-only die-edge correction (ledger cycles_l0, {gr})', n=1, cycles=v, grade=gr,
                   src=die_edges['source']) for gr, v in sorted(l0c.items())]
    terms += [
        dict(term='LM head + argmax (compute die)', n=1, cycles=head['cycles'], grade=head['grade'], src=head['source']),
        dict(term='embedding row fetch through the KV die (token start)', n=1, cycles=emb['cycles'], grade=emb['grade'],
             src=emb['source']),
    ]
    T = sum(t['n'] * t['cycles'] for t in terms)
    # cycles by grade over the token: layer cycles split by the layer critical-path shares
    layer_cyc = cold + 35 * chained
    span = sum(by.values())
    tg = {k: layer_cyc * v / span for k, v in by.items()}
    succ = 0
    if 'no_successor_terms' in runs:      # PRICED SU8/VM8l age deltas + COLL-split AR inside REL/DIAG-graded rows
        ns = runs['no_successor_terms']['composition']
        succ = layer_cyc - (ns['l0_cold'] + 35 * ns['chained_period'])
        donor = max(tg, key=tg.get)
        tg[donor] -= succ
        tg['PRICED'] = tg.get('PRICED', 0) + succ
    for t in terms[2:]:
        tg[t['grade']] = tg.get(t['grade'], 0) + t['n'] * t['cycles']
    measured = sum(v for k, v in tg.items() if k in ('REL', 'NEWEST'))
    price = inp['price_of_record']
    one = dict(
        users=1, cycles_per_token=round(T), tok_s=round(tok_s(T), 1), clock_ps=CLK_PS,
        layer=dict(chained=chained, l0_cold=cold, layer_latency=c['layer_latency'],
                   priced_chained_ctlm=cp['priced_chained_period'], dv_layer_priced_chained=cp['chained_period'],
                   calendar=runs['measured']['calendar']['model'], calendar_clashes=runs['measured']['calendar']['clashes'],
                   stages=stages, critical_path_cycles_by_grade=by, tile=c['tile'],
                   die_edges_per_layer=sum(s['cycles'] for s in c['stages'] if s.get('die_edge')),
                   noedge_chained=runs['noedge']['composition']['chained_period'],
                   sched_added_per_layer=chained - runs['noedge']['composition']['chained_period'],
                   lane_ages=lane_ages, dv_age_deltas=age_dd, qtp8=q8,
                   successor_priced_chained=(chained - runs['no_successor_terms']['composition']['chained_period']
                                             if 'no_successor_terms' in runs else 0),
                   dv_rel_rows=dv_rows,
                   dv_base_chained=runs['dv_base']['composition']['chained_period'] if 'dv_base' in runs else None),
        terms=terms,
        token_cycles_by_grade={k: round(v) for k, v in tg.items()},
        pct_measured=round(100 * measured / T, 1), pct_rel=round(100 * tg.get('REL', 0) / T, 1),
        pct_newest=round(100 * tg.get('NEWEST', 0) / T, 1),
        price_of_record=price, vs_price_pct=round(100 * (tok_s(T) / price['tok_s'] - 1), 2),
        gaps=runs['measured']['gaps'])
    out['1u'] = one
    mu = inp['multi_user']
    out['4u'] = dict(mu, note=mu.get('note'))
    sc = mu.get('schedule_scale')
    if sc:      # the 4u link-schedule frame re-timed by the same per-layer die edges (every user's layer moves)
        ref = sc['ref_layer_period']
        f = (ref + one['layer']['sched_added_per_layer']) / ref
        cpt = [round(c_ * f) for c_ in mu['cycles_per_token_by_user']]
        agg = 1 / sum(1 / x for x in cpt)
        out['4u_scheduled'] = dict(
            grade=mu['grade'], rule=sc['rule'], frame_scale=round(f, 5), frame_cycles=round(mu['frame_cycles'] * f),
            cycles_per_token_by_user=cpt,
            per_user_tok_s=[round(tok_s(x), 1) for x in cpt], aggregate_cycles_per_token=round(agg),
            aggregate_tok_s=round(tok_s(agg), 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inputs', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    inp = json.loads(Path(a.inputs).read_text())
    r = compose(inp)
    for v in inp['die_edges'].get('variants', []):
        rv = compose(inp, v)
        r[f'variant_{v}'] = {k: rv['1u'][k] for k in ('cycles_per_token', 'tok_s', 'token_cycles_by_grade', 'pct_rel',
                                                    'vs_price_pct')}
        r[f'variant_{v}']['chained'] = rv['1u']['layer']['chained']
        r[f'variant_{v}']['sched_added_per_layer'] = rv['1u']['layer']['sched_added_per_layer']
        if '4u_scheduled' in rv:
            r[f'variant_{v}']['4u_aggregate_tok_s'] = rv['4u_scheduled']['aggregate_tok_s']
    rec = dict(schema='opentallas.toksim.qwen_rom.v1', lane='TOKSIM-QW', tool='tools/qwen_layerbench/toksim_compose.py',
               inputs=a.inputs, release_source=inp['release_source'], result=r)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    o = r['1u']
    print(json.dumps(dict(cycles=o['cycles_per_token'], tok_s=o['tok_s'], chained=o['layer']['chained'],
                          l0_cold=o['layer']['l0_cold'], pct_measured=o['pct_measured'], pct_rel=o['pct_rel'],
                          vs_price=o['vs_price_pct'], by=o['token_cycles_by_grade'],
                          die_edges_per_layer=o['layer']['die_edges_per_layer'],
                          sched_added_per_layer=o['layer']['sched_added_per_layer'],
                          u4=r.get('4u_scheduled', {}).get('aggregate_tok_s', r['4u'].get('aggregate_tok_s')),
                          variants={k: (v['tok_s'], v.get('4u_aggregate_tok_s')) for k, v in r.items()
                                    if k.startswith('variant_')})))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
