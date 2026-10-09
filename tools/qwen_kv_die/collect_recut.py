#!/usr/bin/env python3
"""kv-die 2026-10-09 (review-0528 KV1(b), CRITICAL PATH): the row engine <-> stack aggregator re-cut record.

Folds the layer-step bench campaigns (rtl/test/qwen_kv_die/bench_run.sh results.jsonl) of the reference stack (_p, the
abutted 16.5 k / 16.8 k-bit boundary) and of every re-cut variant into results/arch/qwen_kv_die_20261009/recut.json:
per variant the boundary bits, exactness on every vector, the ctx-8192 layer step and its delta against the reference
(the cost of every added stage, measured), the per-token cost (x 36 layers) and the area the variant adds.

    python3 tools/qwen_kv_die/collect_recut.py --ref NAME:DIR --var KEY:NAME:DIR ... --area FILE --out recut.json
"""
import argparse
import json
from pathlib import Path

LAYERS = 36
HD = 128
LN = 4 * HD
VARIANTS = {
    'p': dict(name='reference _p (no re-cut)', rtl='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv',
              eng_in=1 + 14 + 3 + 1 + 16384 + 32 + 64 + 1, eng_out_leaf=1 + 1 + 4 + 3 + 16384,
              what='q registers in the aggregator (16,384 b broadcast); the aggregator tree takes each 16,384-b leaf from '
                   'the engine loop'),
    'c': dict(name='re-cut C', rtl='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_c.sv (tools/qwen_kv_die/stack_c_gen.py)',
              what='q beat broadcast (519 b) into engine q registers; every leaf latched and serialised in LFB beats into '
                   'an LBD-leaf staging FIFO per engine; the aggregator tree unchanged'),
    'd': dict(name='re-cut D', rtl='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_d.sv (tools/qwen_kv_die/stack_d_gen.py)',
              what='q beat broadcast; P.V levels 1-3 in the engine on its own 512-lane adder bank (the residue group\'s '
                   '8 slots); one level-3 node a group in LFB beats under ND credits; aggregator tree levels 4-7'),
    'e': dict(name='re-cut E', rtl='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_e.sv (tools/qwen_kv_die/stack_e_gen.py)',
              what='as D, but levels 1-3 on the lane loop adders (one X word and one output word a lane, one loop pass '
                   'a level), no extra adder bank'),
}


def load(d):
    rows = [json.loads(x) for x in (Path(d) / 'results.jsonl').read_text().splitlines() if x.strip()]
    base = [r for r in rows if r['run'] == 'base']
    st = (Path(d) / 'STATUS').read_text().splitlines()[0] if (Path(d) / 'STATUS').exists() else ''
    step = {}
    for r in base:
        if r['res']:
            m = r['res']['marks']
            step.setdefault(r['vec'], set()).add(m['res_last_at_vm'] - m['ctl_sent'])
    return dict(status=st, runs=len(base), exact_all=bool(base) and all(r['rc'] == 0 and r['res'] and r['res']['exact']
                                                                       for r in base),
                vectors=sorted({r['vec'] for r in base}),
                step={k: max(v) for k, v in sorted(step.items())})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', required=True)
    ap.add_argument('--var', action='append', required=True)
    ap.add_argument('--area', type=Path)
    ap.add_argument('--adopt', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    rname, rdir = a.ref.split(':', 1)
    ref = load(rdir)
    r8 = max(ref['step'].get('8192_normal', 0), ref['step'].get('8192_peaky', 0))
    out = dict(schema='opentallas.qwen-kv-die.recut.v1', date='2026-10-09',
               question='review-0528 KV1(b): re-cut the near-HBM row engine <-> stack aggregator boundary (16,385 b in / '
                        '16,392 b out per engine, 8 engines on one aggregator), bench it, price every added stage',
               bench='rtl/test/qwen_kv_die/bench_run.sh (STACK=c|d|e): one attention layer step through the ROM <-> KV '
                     'link at the r22k / KV-die stage counts (28 1 5 5 23 22 24), bit-exact vs tools/hdc_golden.py on 7 '
                     'vectors x VM stall 0 / 1, t = T-1 HBM rows poisoned',
               reference=dict(run=rname, variant=VARIANTS['p'], **ref, step_8192=r8), variants={})
    for spec in a.var:
        key, name, d = spec.split(':', 2)
        res = load(d)
        s8 = max(res['step'].get('8192_normal', 0), res['step'].get('8192_peaky', 0))
        v = dict(VARIANTS[key[0]], params=name, **res, step_8192=s8 or None)
        if s8:
            v['delta_cycles_per_layer'] = s8 - r8
            v['delta_cycles_per_token'] = LAYERS * (s8 - r8)
        out['variants'][key] = v
    if a.area and a.area.exists():
        out['area'] = json.loads(a.area.read_text())
    out['adopted'] = a.adopt
    ad = out['variants'][a.adopt]
    lfb = int(a.adopt.split('_l')[1].split('n')[0]) if '_l' in a.adopt else 4
    out['adopted_boundary_bits'] = dict(engine_in_q=1 + 6 + 512, engine_out_node=1 + 4 + 1 + 4 + LN * 32 // lfb + 1,
                                        reference_in=VARIANTS['p']['eng_in'], reference_out_leaf=VARIANTS['p']['eng_out_leaf'])
    out['verdict'] = (f"ADOPT {a.adopt}: exact on every vector, ctx-8192 step {ad['step_8192']} against {r8} for the "
                      f"reference ({ad['delta_cycles_per_layer']:+d} cycles a layer, {ad['delta_cycles_per_token']:+d} a "
                      f"token); C rejected (slower), E kept as the area-minimal fallback")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(out['verdict'])
    for k, v in out['variants'].items():
        print(k, v['exact_all'], v['step_8192'], v.get('delta_cycles_per_layer'))


if __name__ == '__main__':
    main()
