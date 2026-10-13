#!/usr/bin/env python3
"""Per-layer throughput record of the S81 one-layer die bench (owner 2026-10-13: DS ROM throughput is qualified at
the PER-LAYER level).  Reads a run_die_layer.sh output directory (stim_<L>/meta.json + prog.txt, run_base_<L>.log
with the bench's "OPT" per-op lines) and the committed token path (results/arch/token_path_20261009/ds_rom*.json).

Per op of the layer: measured = the bench's own start -> end cycles, price = the token-path node of the same id
(the price the token is charged; never changed here).  Only ops whose engine is REAL RTL at production shape in the
bench are measured: hc (dsfd_sp_hc_c: fused hc_pre NORM at D 5,120, hc_post) and coll (dsfd_sp_collective_c, 4-die
TP4, production record counts).  Field phases run the real gather / capture but on synthetic phase shapes, and su /
svc / sel / col / hcx are behavioural at their program duration: both stay AT PRICE and are listed as not covered.
The layer is re-solved on the bench program's own DAG: every op at price, then measured ops at their measured
cycles; end to end, each measured op class's (measured - price) is put on every layer's node of that op in the AR
and MTP token paths (tools/throughput/accepted_cost.py solve).

    python3 tools/s81_ctrl/die_layer_tput.py <run dir> --layers L0 L2 --out results/rtl/<record>/record.json
"""
import argparse, collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/throughput'))
import accepted_cost as AC  # noqa: E402

REAL = ('hc', 'coll')
FUSED = {'attn.hc_pre': ['attn.quant'], 'ffn.hc_pre': ['ffn.norm.scale', 'ffn.quant']}   # SU ops inside the HC NORM
UNPRICED = ('hc.gain_attn', 'hc.gain_ffn', 'hc.h_load', 'hc.h_store', 'attn.hc.coef', 'ffn.hc.coef')


def lpath(ops, dur):
    end = {}
    for o in ops:                                        # program order is topological
        end[o['k']] = max((end[p] for p in o['preds']), default=0.0) + dur[o['k']]
    return max(end.values())


def layer(run, L, tp):
    meta = json.loads((run / f'stim_{L}/meta.json').read_text())
    prog = [l.split() for l in (run / f'stim_{L}/prog.txt').read_text().splitlines()]
    log = (run / f'run_base_{L}.log').read_text()
    verdict = re.search(r'TB_S81_DIE_LAYER (PASS|FAIL)', log).group(1)
    summ = re.search(r'SUMMARY .*', log).group(0)
    opt = {int(m[1]): (int(m[3]), int(m[4]), int(m[5])) for m in re.finditer(r'OPT (\d+) port (\d+) dur (-?\d+) start (-?\d+) end (-?\d+)', log)}
    by = {n['id']: n for n in tp['nodes']}
    ops = []
    for o in meta['program']:
        k = o['k']; tail = o['id'].split('.', 1)[1]
        d, st, en = opt[k]
        assert d == int(prog[k][2])
        price = None
        if o['id'] in by:
            price = by[o['id']]['cycles'] + sum(by[f"{L}.{f}"]['cycles'] for f in FUSED.get(tail, []) if f"{L}.{f}" in by)
        pend = max((opt[p][2] for p in o['preds']), default=None)
        ops.append(dict(k=k, id=o['id'], op=tail, eng=o['eng'], preds=o['preds'], program_dur=d, start=st, end=en,
                        measured=en - st, price=price, real=o['eng'] in REAL,
                        critical=bool(by.get(o['id'], {}).get('critical')), slack=by.get(o['id'], {}).get('slack'),
                        dispatch_wait=None if pend is None else st - pend))
    base = {o['k']: float(o['price'] if o['price'] is not None and o['real'] else o['program_dur']) for o in ops}
    meas = dict(base)
    for o in ops:
        if o['real']:
            meas[o['k']] = float(o['measured'])
    cls = collections.OrderedDict()
    for o in ops:
        if not o['real']:
            continue
        key = ('hc.unpriced' if o['op'] in UNPRICED else o['eng'] + ':' + o['op'])
        c = cls.setdefault(key, dict(runs=0, measured=0, price=0.0, critical=o['critical']))
        c['runs'] += 1; c['measured'] += o['measured']; c['price'] += o['price'] or 0.0
    for c in cls.values():
        c['price'] = round(c['price'], 1)
        c['ratio'] = round(c['measured'] / c['price'], 3) if c['price'] else None
    waits = [o['dispatch_wait'] for o in ops if o['dispatch_wait'] is not None and o['eng'] != 'fld']
    return dict(layer=L, verdict=verdict, summary=summ, ops=ops, classes=cls,
                layer_path_at_price=round(lpath(ops, base), 1), layer_path_measured=round(lpath(ops, meas), 1),
                layer_ratio=round(lpath(ops, meas) / lpath(ops, base), 4),
                bench_layer_cycles=int(re.search(r'layer_cycles=(\d+)', summ).group(1)),
                dispatch_wait=dict(n=len(waits), median=sorted(waits)[len(waits) // 2], max=max(waits)),
                not_covered=dict(field_ops=sum(o['eng'] == 'fld' for o in ops),
                                 behavioural_ops={e: sum(o['eng'] == e for o in ops) for e in sorted({o['eng'] for o in ops} - set(REAL) - {'fld'})}),
                cases_sha256=meta['cases_sha256'])


def e2e(delta_by_op):
    """delta_by_op: {token-path op name: added cycles}; -> per workload loss with every layer's node moved"""
    out = {}
    for wl, name in AC.DESIGNS['s81']['workloads'].items():
        doc = json.loads((AC.TP / f'{name}.json').read_text())
        base, _ = AC.solve(doc['nodes'], doc['edges'])
        per = {}
        for sel in list(delta_by_op) + ['ALL']:
            delta = {n['id']: delta_by_op[n['op']] for n in doc['nodes'] if n.get('op') in delta_by_op and (sel == 'ALL' or n['op'] == sel)}
            wave = [n['id'] for n in doc['nodes'] if n.get('op') == 'wave.busy']
            if wave:                                     # as accepted_cost.rom_loss: the slowest verify stage's share once per wave position
                stages = [g for g in doc.get('groups', []) if g.get('kind') in ('stage', 'layer', 'embed')]
                worst = max(stages, key=lambda g: g['cycles'])['id']
                add = sum(delta.get(n['id'], 0.0) for n in doc['nodes'] if n.get('group') == worst)
                for i in wave:
                    delta[i] = delta.get(i, 0.0) + add
            new, _ = AC.solve(doc['nodes'], doc['edges'], delta)
            per[sel] = dict(nodes=len(delta) - len(wave), added_cycles=round(new - base, 1), e2e_loss_pct=round(AC.loss_pct(base, new), 3))
        out[wl] = dict(base_cycles=round(base, 1), by_op=per)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run', type=Path); ap.add_argument('--layers', nargs='+', default=['L0', 'L2'])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    tp = json.loads((AC.TP / 'ds_rom.json').read_text())
    layers = [layer(a.run, L, tp) for L in a.layers]
    # worst measured - price per op name over the layers run (hc_pre: the fused NORM against hc_pre + its SU ops,
    # the delta is put on the hc_pre node)
    d = {}
    for l in layers:
        for o in l['ops']:
            if o['real'] and o['price'] is not None:
                d[o['op']] = max(d.get(o['op'], -1e9), o['measured'] - o['price'])
    rec = dict(schema='opentallas.s81_layer_tput.v1', layers=layers, delta_by_op={k: round(v, 1) for k, v in d.items()},
               e2e=e2e(d), e2e_over_only=e2e({k: v for k, v in d.items() if v > 0}))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    for l in layers:
        print(l['layer'], l['verdict'], 'bench layer cycles', l['bench_layer_cycles'], 'path price', l['layer_path_at_price'], 'measured', l['layer_path_measured'], l['layer_ratio'], l['dispatch_wait'])
        for k, c in l['classes'].items():
            print('   %-28s runs %d measured %6d price %8.1f ratio %s crit %s' % (k, c['runs'], c['measured'], c['price'], c['ratio'], c['critical']))
    for wl, v in rec['e2e'].items():
        print(wl, json.dumps(v['by_op']))
    print('over-only', {wl: v['by_op']['ALL'] for wl, v in rec['e2e_over_only'].items()})


if __name__ == '__main__':
    main()
