#!/usr/bin/env python3
"""Stimulus + golden of the S81 one-layer die bench tb_s81_die_layer (s81die-1011/ctrl bench, 2026-10-11).

One DeepSeek-V4.1 layer L (default L0 = the 1M token's L0 attn + L0 ffn, the hc_gate golden chain) as ONE stage
program of the die controller, built from the committed stage programs (results/rtl/s81_ctrl_20261008/programs:
every op whose id starts with "<L>.attn." / "<L>.ffn."), rewritten onto the REAL masters' native descriptors:

  hc (port 2, dsfd_sp_hc_c): GAIN attn, GAIN ffn, H_LOAD (the HIDDEN payload rows 0..639) at layer entry;
      <blk>.hc_pre  -> COEF_LOAD + NORM (hc_pre mix -> RMSNorm -> FP8 act-quant; ffn also YOUT): the master's fused
                       norm, which also IS the SU ops <L>.attn.quant / <L>.ffn.norm.scale / <L>.ffn.quant (removed;
                       their consumers depend on the NORM);
      <blk>.hc_post -> POST (y on the collective -> HC bus);
      H_STORE (the layer output h, rows S_BASE..) at layer exit.
  hcx (port 9, behavioural): <blk>.hc.fn / sumsq / rsqrt / pre_post / sinkhorn -- the coefficient producers the HC
      master does not implement (it loads comb / pre / post / eps from 2 VM rows); pre_post writes the golden
      pre/post/eps row, sinkhorn the golden comb row (the HC COEF job's f_inp waits on both rows).
  coll (port 3, dsfd_sp_collective_c, 4-die TP4 group): every coll op is one message {mode, records}; all-reduce
      (mode 0, D/16 = 320 records of 16 binary32) partials per rank = a bit partition of the golden y's significand
      (any association of the 4 partials is exact, so the reduced word IS the golden y whatever the tree order);
      all-gather (mode 1) records: random binary32.
  fld (port 0): real field phases (gen_stim, as tb_s81_die_fld).  others: behavioural (golden durations).

Files (<out>/): prog.txt (port arg dur np p0..p3 ph cmsg wrow), stim.txt (field phases), coll_msg.txt (mode nrec),
coll_own.mem (record r, die d at line 4r+d), y_gold.mem (the all-reduce words the HC must receive, in order),
vm_boot.mem (gain rows), coef.mem (row data written by hcx ops: "@row" + data), payload.mem (640 h rows),
expa.mem / expd.mem (golden VM rows: NORM outputs + H_STORE), n.mem, meta.json.
"""
import argparse, json, pickle, random, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'rtl/dsrom_sys/s81_ph/test'))
sys.path.insert(0, str(ROOT / 'tools/s81_suhc'))
import gen_stim  # noqa: E402
import hc_gate as HG  # noqa: E402

D = HG.D
G_BASE, C_BASE, O_BASE, S_BASE, H_BASE = 1280, 2560, 3072, 6144, 0
HX_PORT, HC_PORT, COLL_PORT = 9, 2, 3
GATHER_REC = {'router_allgather': 4, 'a_allgather': 12, 'rows_allgather': 64, 'idx.topk_merge': 8}
SU_IN_NORM = {'attn': ['quant'], 'ffn': ['norm.scale', 'quant']}


def hc_arg(kind, base, gsel=0, quant=0, yout=0):
    return (kind << 20) | (gsel << 18) | (yout << 15) | (quant << 14) | base


def partition(y):
    """4 binary32 partials of each y word whose every subset sum is exact: significand bits dealt round-robin."""
    b = HG.u32(y).astype(np.int64)
    s, e, m = b >> 31, (b >> 23) & 0xFF, b & 0x7FFFFF
    assert np.all(e != 0xFF), "non-finite golden y"
    sig = np.where(e > 0, m | (1 << 23), m)
    ex = np.where(e > 0, e, 1) - 150                     # value = sig * 2^ex
    parts = []
    for r in range(4):
        msk = sum(1 << k for k in range(24) if k % 4 == r)
        v = np.ldexp((sig & msk).astype(np.float64), ex.astype(np.int64))
        v = np.where(s == 1, -v, v)
        p = v.astype(np.float32)
        assert np.array_equal(p.astype(np.float64), v), "partial not representable"
        p = np.where(p == 0, np.where(s == 1, np.float32(-0.0), np.float32(0.0)), p).astype(np.float32)
        parts.append(p)
    return parts


def layer_ops(progdir, L):
    ops = []
    for f in sorted(progdir.glob('S*.json')):
        p = json.loads(f.read_text())
        loc = {o['op']: o['id'] for o in p['ops']}
        for o in p['ops']:
            if o['id'].startswith(f'{L}.attn.') or o['id'].startswith(f'{L}.ffn.'):
                ops.append(dict(o, preds_id=[loc[q] for q in o['preds']]))
    return ops


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--cases', required=True)
    ap.add_argument('--layer', default='L0', choices=['L0', 'L2'])
    ap.add_argument('--ng', type=int, default=16)
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--programs', type=Path, default=ROOT / 'results/rtl/s81_ctrl_20261008/programs')
    a = ap.parse_args()
    rng = random.Random(a.seed)
    npr = np.random.default_rng(a.seed)
    a.out.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ golden chain (hc_gate.chains_golden)
    cases = pickle.loads(Path(a.cases).read_bytes())
    ch = HG.chains_golden(cases)[0 if a.layer == 'L0' else 1]
    run = HG.Run(a.ng)
    h = np.asarray(ch['h'], np.float32).reshape(HG.HC, D)
    payload = run.h_rows(h)
    gold = {}
    for b, blk in enumerate(('attn', 'ffn')):
        pre, w, eps, comb, post, y = ch[blk]
        yn = HG.g_norm(h, pre, w, eps)
        run.norm_rows(O_BASE + 512 * b, yn, 1, 1 if blk == 'ffn' else 0)
        h = HG.g_post(h, np.asarray(y, np.float32), np.asarray(comb, np.float32).reshape(4, 4), np.asarray(post, np.float32))
        nck, pck, _hn, _hp = ch[blk + '_checks']
        (_l, _a, bits, _k), = nck
        assert np.array_equal(HG.u32(yn), np.asarray(bits, np.uint32)), (blk, 'norm vs pickle')
        (_l, _a, bits, _k), = pck
        assert np.array_equal(HG.u32(h).reshape(-1), np.asarray(bits, np.uint32)), (blk, 'post vs pickle')
        gold[blk] = dict(y=np.asarray(y, np.float32), comb=comb, pre=pre, post=post, eps=eps, w=w)
    for q, row in enumerate(run.h_rows(h)):
        run.exp[S_BASE + q] = row
    vm_boot = {}
    for b, blk in enumerate(('attn', 'ffn')):
        wv = HG.u32(gold[blk]['w'])
        for r in range(HG.GROWS):
            vm_boot[G_BASE + b * HG.GROWS + r] = HG.pack(wv[16 * r:16 * r + 16], 32)
    coef = {}
    for b, blk in enumerate(('attn', 'ffn')):
        g = gold[blk]
        coef[C_BASE + 2 * b] = HG.pack(HG.u32(np.asarray(g['comb'], np.float32).reshape(-1)), 32)
        coef[C_BASE + 2 * b + 1] = HG.pack(list(HG.u32(g['pre'])) + list(HG.u32(g['post'])) + [int(HG.u32([g['eps']])[0])], 32)

    # ------------------------------------------------------------------ program rewrite (by name, then topological)
    src = layer_ops(a.programs, a.layer)
    nodes = {}

    def add(name, port, dur, preds, arg=None, cmsg=-1, wrow=-1, eng='', order=0.0):
        nodes[name] = dict(id=name, port=port, dur=dur, preds=list(dict.fromkeys(preds)), arg=arg, ph=-1, cmsg=cmsg,
                           wrow=wrow, eng=eng, order=order)

    L = a.layer
    add(f'{L}.hc.gain_attn', HC_PORT, 0, [], hc_arg(5, G_BASE, gsel=0), eng='hc', order=-3)
    add(f'{L}.hc.gain_ffn', HC_PORT, 0, [], hc_arg(5, G_BASE + HG.GROWS, gsel=1), eng='hc', order=-2)
    add(f'{L}.hc.h_load', HC_PORT, 0, [], hc_arg(0, H_BASE), eng='hc', order=-1)
    alias = {f'{L}.{blk}.{s}': f'{L}.{blk}.hc_pre' for blk in SU_IN_NORM for s in SU_IN_NORM[blk]}
    names = {o['id'] for o in src}
    msgs = []
    for i, o in enumerate(src):
        nm = o['id']
        blk = nm.split('.')[1]
        b = 0 if blk == 'attn' else 1
        tail = nm.split('.', 2)[2]
        if nm in alias:
            continue
        preds = [alias.get(p, p) for p in o['preds_id'] if alias.get(p, p) in names]
        if blk == 'ffn' and tail in ('hc.fn', 'hc.sumsq', 'hc_pre'):
            preds.append(f'{L}.attn.hc_post')            # the ffn block reads the h the attn hc_post wrote
        if o['eng'] == 'hc':
            if tail == 'hc_pre':
                add(f'{L}.{blk}.hc.coef', HC_PORT, 0, [f'{L}.{blk}.hc.pre_post', f'{L}.{blk}.hc.sinkhorn'],
                    hc_arg(2, C_BASE + 2 * b), eng='hc', order=i - 0.5)
                add(nm, HC_PORT, o['dur'], preds + [f'{L}.{blk}.hc.coef'],
                    hc_arg(4, O_BASE + 512 * b, gsel=b, quant=1, yout=b), eng='hc', order=i)
            elif tail == 'hc_post':
                add(nm, HC_PORT, o['dur'], preds, hc_arg(3, 0), eng='hc', order=i)
            else:      # coefficient producers: behavioural on hcx
                wrow = {'hc.pre_post': C_BASE + 2 * b + 1, 'hc.sinkhorn': C_BASE + 2 * b}.get(tail, -1)
                add(nm, HX_PORT, o['dur'], preds, wrow=wrow, eng='hcx', order=i)
        elif o['eng'] == 'coll':
            mode = 0 if 'allreduce' in tail else 1
            nrec = D // 16 if mode == 0 else GATHER_REC[tail]
            msgs.append(dict(op=nm, mode=mode, nrec=nrec, blk=blk))
            add(nm, COLL_PORT, o['dur'], preds, (mode << 16) | nrec, eng='coll', order=i)
        else:
            add(nm, o['port'], o['dur'], preds, eng=o['eng'], order=i)
    add(f'{L}.hc.h_store', HC_PORT, 0, [f'{L}.ffn.hc_post'], hc_arg(1, S_BASE), eng='hc', order=1e9)
    # Kahn, ties broken by the source program order
    prog, done = [], set()
    while len(prog) < len(nodes):
        ready = [n for n in nodes.values() if n['id'] not in done and all(p in done for p in n['preds'])]
        assert ready, 'cycle'
        n = min(ready, key=lambda x: x['order'])
        prog.append(n); done.add(n['id'])
    idx = {n['id']: k for k, n in enumerate(prog)}
    stim = open(a.out / 'stim.txt', 'w')
    nph, cm = 0, {m['op']: k for k, m in enumerate(msgs)}
    msgs.sort(key=lambda m: idx[m['op']])                # messages in program (= coll port) order
    cm = {m['op']: k for k, m in enumerate(msgs)}
    for n in prog:
        n['preds'] = sorted(idx[p] for p in n['preds'])
        if n['eng'] == 'fld':
            gen_stim.phase(rng, stim, nph, rng.choice([64, 128, 256, 300]), rng.choice([0, 1, 3]), nph % 3,
                           burst=rng.random() < 0.5, maxseg=4)
            n['ph'] = n['arg'] = nph
            nph += 1
        if n['eng'] == 'coll':
            n['cmsg'] = cm[n['id']]
    stim.close()
    assert len(prog) <= 128, len(prog)
    lines = []
    for k, o in enumerate(prog):
        assert len(o['preds']) <= 4, o
        arg = o['arg'] if o['arg'] is not None else k
        lines.append(' '.join(str(v) for v in [o['port'], arg, o['dur'], len(o['preds'])] + (o['preds'] + [0] * 4)[:4]
                              + [o['ph'], o['cmsg'], o['wrow']]))
    (a.out / 'prog.txt').write_text('\n'.join(lines) + '\n')

    # ------------------------------------------------------------------ collective records
    own, ygold, nred = [], [], 0
    for m in msgs:
        if m['mode'] == 0:
            y = gold[m['blk']]['y']
            parts = partition(y)
            for r in range(m['nrec']):
                own.append([HG.pack(HG.u32(parts[d][16 * r:16 * r + 16]), 32) for d in range(4)])
                ygold.append(HG.pack(HG.u32(y[16 * r:16 * r + 16]), 32))
            nred += 1
        else:
            for r in range(m['nrec']):
                own.append([HG.pack(npr.integers(0, 2 ** 32, 16, dtype=np.uint64), 32) for d in range(4)])
    with open(a.out / 'coll_own.mem', 'w') as f:
        for rec in own:
            for d in range(4):
                f.write(f'{rec[d]:0128x}\n')
    (a.out / 'coll_msg.txt').write_text(''.join(f"{m['mode']} {m['nrec']}\n" for m in msgs))
    (a.out / 'y_gold.mem').write_text(''.join(f'{v:0128x}\n' for v in ygold))
    with open(a.out / 'vm_boot.mem', 'w') as f:
        for r in sorted(vm_boot):
            f.write(f'@{r:x}\n{vm_boot[r]:0128x}\n')
    with open(a.out / 'coef.mem', 'w') as f:
        for r in sorted(coef):
            f.write(f'@{r:x}\n{coef[r]:0128x}\n')
    (a.out / 'payload.mem').write_text(''.join(f'{v:0128x}\n' for v in payload))
    with open(a.out / 'expa.mem', 'w') as fa, open(a.out / 'expd.mem', 'w') as fd:
        for r in sorted(run.exp):
            fa.write(f'{r:04x}\n')
            fd.write(f'{run.exp[r]:0128x}\n')
    nst = sum(1 for r in run.exp if r >= S_BASE)
    (a.out / 'n.mem').write_text(f'{len(run.exp):08x}\n{len(own):08x}\n{len(msgs):08x}\n{len(ygold):08x}\n{nst:08x}\n')
    meta = dict(layer=a.layer, ng=a.ng, ops=len(prog), field_phases=nph, coll_messages=msgs, coll_records=len(own),
                y_words=len(ygold), exp_rows=len(run.exp), hstore_rows=nst, golden_checks_vs_pickle=4,
                program=[dict(k=k, id=o['id'], port=o['port'], eng=o['eng'], preds=o['preds']) for k, o in enumerate(prog)],
                cases_sha256=HG.sha(a.cases))
    (a.out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(f"{a.layer}: {len(prog)} ops, {nph} field phases, {len(msgs)} coll messages ({len(own)} records, "
          f"{len(ygold)} y words), {len(run.exp)} golden VM rows ({nst} H_STORE)")


if __name__ == '__main__':
    main()
