#!/usr/bin/env python3
"""LB2-S81/CC-GU bench kit: lowers the layer's G-unit ops with tools/s81_dv/layer_prog/lower_gu.py through the compiler's
own Prog / absorb / finish (dv_layer_compile), and writes for tb_gu_layer.sv:
  prog/host_boot.memh      the compiled host boot stream (calendar rows of the gunit jobs + KIT / END, job templates,
                           the 0x14 table rows) -- booted into the REAL dsdv_seq_host
  stim_n.memh / stim_s.memh   {cycle 32, beat 276} HP / SC beats on u_gunit vi_n / vi_s at the lowering's planned
                           layer edges; beat data = the slice model of the fixture (chunk sums of 8 from +0, maximal
                           aligned subtree roots per slice: the golden's own tree, independent of the RTL)
  exp_n / exp_s / exp_c.memh  {cycle 32, value 276} every expected beat on vo_n / vo_s and every gunit job on the cw pin
                           ({cw_a, cw_d}) at the lowering's planned edges; values from the L0 fixtures (pre / post /
                           comb, top6_order ids, routing weights)
  exp_int.memh             per HC job: fn[0..23], sum of squares, rsqrt (the fixtures; the bench reads them at L4 / L4r)
  kit.json                 counts, the plan, the fixture sha256 of every file read
  gu_kit.py --layer L0 --fixtures DIR --die-src TREE --out DIR [--mutant NAME]
Mutants (image faults the bench must catch): which (wrong field: the attn HC job's which bit flipped, so it reads the
ffn bases / scales), late (shifted cycle: the attn HC job's calendar issue 40 edges late, after its first HP beat).
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv/layer_prog'))
import dv_layer_compile as C   # noqa: E402
import lower_gu as L           # noqa: E402
sys.path.insert(0, str(ROOT / 'tools/s81_dv/layer_prog/gu'))
from gu_values import Fx, u32, hc_roots, hc_coef, router_vals   # noqa: E402,F401  (shared with lower_gu.encode)


def build(layer, fixtures, tree, out, mutant=None):
    out = Path(out)
    (out / 'prog').mkdir(parents=True, exist_ok=True)
    fx = Fx(fixtures)
    die = C.Die(tree)
    sched = C.layer_schedule(tree, layer)
    ctx = dict(layer=layer, slice='u_s_0S', sched=sched, fixtures=Path(fixtures))
    prog = C.Prog(die)
    res = {}
    for o in sched['ops']:
        if not any(__import__('re').search(rx, o['op']) for rx in L.OPS):
            continue
        r = L.lower(die, o, dict(ctx, t_issue=int(math.floor(o['start']))))
        if mutant == 'which' and o['op'] == 'attn.hc.fn':
            r['templates'] = [(n, p ^ (1 << 41)) for n, p in r['templates']]
        if mutant == 'late' and o['op'] == 'attn.hc.fn':
            r['rows'] = [dict(x, issue=x['issue'] + 40) for x in r['rows']]
        res[o['op']] = r
        prog.absorb('gu', o, r)
    rows, hs, endage = C.finish(prog)
    (out / 'prog/host_boot.memh').write_text(C.memh(hs, 515))
    for rel, text in prog.files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(text)
    sid = die.strap('u_gunit', 'sid')
    stim = {'vi_n': [], 'vi_s': []}
    exp = {'vo_n': [], 'vo_s': [], 'cw': []}
    exp_int = []
    # ---- HC jobs (the unmutated plan: the bench expects what the compiler planned)
    for pre in ('attn.', 'ffn.'):
        pl = json.loads(prog.files[f'prog/gu/{pre}hc.plan.json'])
        which = pre[:-1]
        roots = hc_roots(fx, which)
        for b in pl['beats']:
            stim[b['port']].append((b['cycle'], L.hp_beat(b['acc'], b['g'], b['h'], roots(b['acc'], b['g'], b['h']), b['g'])))
        coef = hc_coef(fx, which)
        for e in [e for o, r in res.items() if o.startswith(pre + 'hc.') for e in r['events']]:
            if e['dir'] == 'out':
                i = int(e['tag'][-1])
                d = sum(coef[4 * i + j] << (32 * j) for j in range(4))
                exp[e['port']].append((e['cycle'], L.ctl_row_beat(pl['row'] + i, 0xF, d, L.SMASK, L.LMASK, sid)))
        jw = L.job_hc(pl['which'], pl['set'], pl['row'], L.LMASK, L.SMASK)
        cwv = (0b1000000001 << 256) | jw
        exp['cw'].append((pl['t_issue'] + L.SEQ_GUNIT_TO_CW + pl['cw_age'], cwv))
        exp_int.append([u32(v) for v in fx(f'ops/{which}.hc.fn.bin')] + [u32(fx(f'ops/{which}.hc.sumsq.bin')[0]),
                                                                          u32(fx(f'ops/{which}.hc.rsqrt.bin')[0])])
    # ---- router
    pl = json.loads(prog.files['prog/gu/ffn.router.plan.json'])
    sc, vals = router_vals(fx)
    for b in pl['beats']:
        stim[b['port']].append((b['cycle'], L.sc_beat(b['row'], sc[7 * b['row']:7 * b['row'] + 7], b['row'] % 16)))
    for o in ('ffn.top6', 'ffn.top6_order', 'ffn.weights'):
        for e in res.get(o, {}).get('events', []):
            if e['dir'] == 'out':
                dr, m, d = vals[e['tag'].rsplit('.', 1)[1]]
                exp[e['port']].append((e['cycle'], L.ctl_row_beat(pl['row'] + dr, m, d, L.SMASK, L.LMASK, sid)))
    jw = L.job_router(pl['set'], pl['ne'], pl['row'], L.LMASK, L.SMASK)
    exp['cw'].append((pl['t_issue'] + L.SEQ_GUNIT_TO_CW + pl['cw_age'], (0b1000000000 << 256) | jw))
    # ---- files
    def wr(name, items, w):
        items = sorted(items)
        assert len({t for t, _ in items}) == len(items), f'{name}: two beats on one edge'
        (out / name).write_text(''.join(f'{t:08x}{v:0{w // 4}x}\n' for t, v in items))
        return len(items)
    n = dict(stim_n=wr('stim_n.memh', stim['vi_n'], 276), stim_s=wr('stim_s.memh', stim['vi_s'], 276),
             exp_n=wr('exp_n.memh', exp['vo_n'], 276), exp_s=wr('exp_s.memh', exp['vo_s'], 276),
             exp_c=wr('exp_c.memh', exp['cw'], 276))
    (out / 'exp_int.memh').write_text(''.join(f'{w:08x}\n' for job in exp_int for w in job))
    lowered = {o: dict(status=r['status'], gap=r['gap'], deps=r.get('deps'), note=r.get('note')) for o, r in res.items()}
    (out / 'kit.json').write_text(json.dumps(dict(
        layer=layer, mutant=mutant, counts=n, host_words=len(hs), calendar=[dict(issue=r['issue'], eng=r['eng'],
        arg=r['arg'], what=r['what']) for r in rows], end_age=endage, lowered=lowered, fixtures=str(fixtures),
        fixture_sha256=fx.read, die_v_sha256=die.die_sha), indent=1) + '\n')
    (out / 'tb.args').write_text(f"+dir={out} +nhs={len(hs)} +nsn={n['stim_n']} +nss={n['stim_s']} +nen={n['exp_n']} "
                                f"+nes={n['exp_s']} +nec={n['exp_c']} +njob=2 +tend={max(t for t, _ in exp['vo_n']) + 50}\n")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layer', default='L0')
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--die-src', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mutant', default=None, choices=('which', 'late'))
    a = ap.parse_args()
    print(json.dumps(build(a.layer, a.fixtures, Path(a.die_src), a.out, a.mutant)))


if __name__ == '__main__':
    main()
