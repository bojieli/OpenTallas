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

Layers outside the pinned su_cases pickle (L14, an Engram layer): --chain <fixture of tools/s81_ctrl/die_layer_chain.py>
(the HC golden chain rebuilt from the released checkpoint + the 1M shard, bit-exact against the shard).  The layer's
<L>.eng.* ops (hh / dot / gate / add, port 10) are BEHAVIOURAL at program duration in this vehicle (no Engram RTL):
the HIDDEN payload is the layer-ENTRY h (rows 0..639, landed by the package controller); eng.hh / eng.dot start when
those rows have landed; eng.add at its end writes the golden post-Engram h rows over rows 0..639 (wrow = H_BASE, the
rows in coef.mem, as the hcx ops land the golden coefficient rows); H_LOAD depends on eng.add and its f_inp waits on
that write, so the real HC master's attn hc_pre / hc_post consume the post-Engram h.

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
EH_BASE = 8192                                           # --h-stream: the post-Engram h rows (Engram layers)
HX_PORT, HC_PORT, COLL_PORT = 9, 2, 3
GATHER_REC = {'router_allgather': 4, 'a_allgather': 12, 'rows_allgather': 64, 'idx.topk_merge': 8}
SU_IN_NORM = {'attn': ['quant'], 'ffn': ['norm.scale', 'quant']}
PINNED = ('L0', 'L2')                                   # the layers of the pinned su_cases pickle (hc_gate.chains_golden)
ENG_PORT = 10


def hc_arg(kind, base, gsel=0, quant=0, yout=0):
    return (kind << 20) | (gsel << 18) | (yout << 15) | (quant << 14) | base


def sched_est(n, a):
    """duration estimate of a program node for the SU schedule search (bench shapes: measured where the engine is real)"""
    if n['eng'] == 'hc':
        kind = (n['arg'] >> 20) & 7
        return {0: 20 if a.h_stream else 336, 1: 387, 2: 17, 3: 45, 4: 713, 5: 176}[kind]
    if n['eng'] == 'fld':
        return 125
    if n['eng'] == 'coll':
        return 452 if 'allreduce' in n['id'] else 100
    return max(n['dur'], 1)


def sched_sim(nodes, ports, a, land=641):
    """in-order engines: every port runs its list in order, one job at a time; returns (start, end) or None (deadlock)"""
    pos = {p: 0 for p in ports}
    free = {p: 0 for p in ports}
    st, en = {}, {}
    left = sum(len(v) for v in ports.values())
    while left:
        moved = False
        for p, lst in ports.items():
            while pos[p] < len(lst):
                n = nodes[lst[pos[p]]]
                if any(q not in en for q in n['preds']):
                    break
                post = n['eng'] == 'hc' and ((n['arg'] >> 20) & 7) == 3
                cp = [q for q in n['preds'] if nodes[q]['eng'] == 'coll'] if post else []
                t = max([free[p]] + [en[q] for q in n['preds'] if q not in cp] + [st[q] + 40 for q in cp]
                        + ([land] if not n['preds'] and n['eng'] != 'hc' else []))
                e = (max([t] + [en[q] for q in cp]) if post else t) + sched_est(n, a)
                st[n['id']], en[n['id']] = t, e
                free[p] = e
                pos[p] += 1
                left -= 1
                moved = True
        if not moved:
            return None
    return st, en


def su_schedule(nodes, a, sink):
    """local search on the SU port's order (insertion moves); objective (layer end, sum of ends)"""
    base = sorted(nodes.values(), key=lambda n: n['order'])
    # the present program order: Kahn with the source order as the tie break
    prog, done = [], set()
    while len(prog) < len(base):
        ready = [n for n in base if n['id'] not in done and all(q in done for q in n['preds'])]
        n = min(ready, key=lambda x: x['order'])
        prog.append(n['id']); done.add(n['id'])
    ports = {}
    for i in prog:
        ports.setdefault(nodes[i]['port'], []).append(i)

    def cost(ps):
        r = sched_sim(nodes, ps, a)
        return None if r is None else (r[1][sink], sum(r[1].values()))
    best = cost(ports)
    c0 = best
    su = list(ports.get(1, []))
    improved = True
    while improved:
        improved = False
        for j in range(len(su)):
            for i in range(len(su)):
                if i == j:
                    continue
                t = list(su)
                t.insert(i, t.pop(j))
                c = cost({**ports, 1: t})
                if c is not None and c < best:
                    best, su, improved = c, t, True
    ports[1] = su
    st, _ = sched_sim(nodes, ports, a)
    rank = {i: k for k, i in enumerate(sorted(prog, key=lambda i: (st[i], prog.index(i))))}
    # the SU port keeps the searched order whatever the ties: its ranks are re-spread in that order
    slots = sorted(rank[i] for i in su)
    for k, i in enumerate(su):
        rank[i] = slots[k]
    for i in prog:
        nodes[i]['order'] = rank[i]
    return dict(layer_end_before=c0[0], layer_end_after=best[0], su_order_before=ports_before_su(prog, nodes), su_order_after=su)


def ports_before_su(prog, nodes):
    return [i for i in prog if nodes[i]['port'] == 1]


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
            if o['id'].startswith((f'{L}.attn.', f'{L}.ffn.', f'{L}.eng.')):
                ops.append(dict(o, preds_id=[loc[q] for q in o['preds']]))
    return ops


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('out', type=Path)
    ap.add_argument('--cases', required=True)
    ap.add_argument('--layer', default='L0', help='L0 / L2 (the pinned pickle) or a layer of the --chain fixture (L14)')
    ap.add_argument('--chain', default=None, help='HC chain fixture (tools/s81_ctrl/die_layer_chain.py) for a layer '
                    'the pinned pickle does not hold')
    ap.add_argument('--ng', type=int, default=16)
    ap.add_argument('--coef-split', action='store_true', help='two COEF jobs a block instead of one: COEF-a before the '
                    'NORM reads the row pair that holds this block\'s pre mix (written by the PREVIOUS block\'s '
                    'hc.pre_post, as the priced token path has it), COEF-b after the NORM reads the block\'s own '
                    'post / combine rows before the POST.  Same RTL, same golden; without it the single COEF waits '
                    'for this block\'s whole coefficient chain (fn .. sinkhorn) before the NORM can start')
    ap.add_argument('--h-stream', action='store_true', help='program for the H landing streamer (tb HST=1): the attn '
                    'COEF-a is issued BEFORE the H_LOAD (its row is present at the job start, so its VM read hides '
                    'under the landing) and the H_LOAD carries no VM dependency; on an Engram layer eng.add writes the '
                    'post-Engram h to its own rows (EH_BASE) and the H_LOAD reads those through the VM as before')
    ap.add_argument('--su-sched', action='store_true', help='order the SU port (an in-order, one-job engine) by a '
                    'schedule search instead of the golden ASAP start order: the committed programs list SU jobs by '
                    'their start on an engine of unlimited concurrency, so a critical SU job queues behind long '
                    'off-critical ones (kv_rope_qdq before q_rope, the shared-expert jobs before swiglu).  The search '
                    'simulates every in-order port with duration estimates and moves SU jobs while the layer end improves')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--programs', type=Path, default=ROOT / 'results/rtl/s81_ctrl_20261008/programs')
    a = ap.parse_args()
    rng = random.Random(a.seed)
    npr = np.random.default_rng(a.seed)
    a.out.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ golden chain (hc_gate.chains_golden)
    cases = pickle.loads(Path(a.cases).read_bytes())
    fx = None
    if a.layer in PINNED:
        ch = HG.chains_golden(cases)[PINNED.index(a.layer)]
    else:
        assert a.chain, f'{a.layer} is not in the pinned pickle: --chain <fixture> required'
        import die_layer_chain
        fx = die_layer_chain.load(a.chain, a.layer)
        ch = fx['chain']
    run = HG.Run(a.ng)
    h = np.asarray(ch['h'], np.float32).reshape(HG.HC, D)
    # the HIDDEN payload is the layer-ENTRY h; on an Engram layer the HC reads h only after eng.add rewrote the rows
    payload = run.h_rows(np.asarray(ch.get('h_in', ch['h']), np.float32).reshape(HG.HC, D))
    eng_rows = run.h_rows(h) if fx is not None and fx['engram'] else None
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

    # --coef-split: the early row pair of block b at E_BASE + 2b: row 0 = don't-care combine (zeros, present at job
    # start), row 1 = {pre, zero post, eps}.  attn: present at job start (the previous layer's ffn.hc.pre_post wrote
    # it); ffn: written by <L>.attn.hc.pre_fwd, a 1-cycle hcx op that follows <L>.attn.hc.pre_post.
    E_BASE = C_BASE + 4
    boot_ok = []
    if a.coef_split:
        for b, blk in enumerate(('attn', 'ffn')):
            g = gold[blk]
            e1 = HG.pack(list(HG.u32(g['pre'])) + [0] * len(HG.u32(g['post'])) + [int(HG.u32([g['eps']])[0])], 32)
            vm_boot[E_BASE + 2 * b] = 0
            boot_ok.append(E_BASE + 2 * b)
            if b == 0:
                vm_boot[E_BASE + 1] = e1
                boot_ok.append(E_BASE + 1)
            else:
                coef[E_BASE + 2 * b + 1] = e1
    # ------------------------------------------------------------------ program rewrite (by name, then topological)
    src = layer_ops(a.programs, a.layer)
    eng_ops = [o['id'] for o in src if o['id'].startswith(f'{a.layer}.eng.')]
    assert bool(eng_ops) == (eng_rows is not None), (a.layer, eng_ops, 'Engram ops need an Engram chain fixture')
    if eng_ops:
        for q, row in enumerate(eng_rows):
            coef[(EH_BASE if a.h_stream else H_BASE) + q] = row
    nodes = {}

    def add(name, port, dur, preds, arg=None, cmsg=-1, wrow=-1, eng='', order=0.0):
        nodes[name] = dict(id=name, port=port, dur=dur, preds=list(dict.fromkeys(preds)), arg=arg, ph=-1, cmsg=cmsg,
                           wrow=wrow, eng=eng, order=order)

    L = a.layer
    add(f'{L}.hc.gain_attn', HC_PORT, 0, [], hc_arg(5, G_BASE, gsel=0), eng='hc', order=-3)
    add(f'{L}.hc.gain_ffn', HC_PORT, 0, [], hc_arg(5, G_BASE + HG.GROWS, gsel=1), eng='hc', order=-2)
    hl_base = EH_BASE if (a.h_stream and eng_ops) else H_BASE
    add(f'{L}.hc.h_load', HC_PORT, 0, [f'{L}.eng.add'] if eng_ops else [], hc_arg(0, hl_base), eng='hc',
        order=([o['id'] for o in src].index(f'{L}.eng.add') + 0.5 if eng_ops else -1))
    alias = {f'{L}.{blk}.{s}': f'{L}.{blk}.hc_pre' for blk in SU_IN_NORM for s in SU_IN_NORM[blk]}
    names = {o['id'] for o in src}
    msgs = []
    for i, o in enumerate(src):
        nm = o['id']
        blk = nm.split('.')[1]
        if blk == 'eng':               # behavioural Engram (port 10): eng.add lands the golden post-Engram h rows
            assert o['port'] == ENG_PORT and o['eng'] == 'eng', o
            add(nm, ENG_PORT, o['dur'], [p for p in o['preds_id'] if p in names],
                wrow=(hl_base if nm == f'{L}.eng.add' else -1), eng='eng', order=i)
            continue
        b = 0 if blk == 'attn' else 1
        tail = nm.split('.', 2)[2]
        if nm in alias:
            continue
        preds = [alias.get(p, p) for p in o['preds_id'] if alias.get(p, p) in names]
        if blk == 'ffn' and tail in ('hc.fn', 'hc.sumsq', 'hc_pre'):
            preds.append(f'{L}.attn.hc_post')            # the ffn block reads the h the attn hc_post wrote
        if eng_ops and blk == 'attn' and tail == 'hc_pre':
            preds = [p for p in preds if p != f'{L}.eng.add'] + [f'{L}.hc.h_load']   # h reaches the HC through H_LOAD
        if o['eng'] == 'hc':
            if tail == 'hc_pre':
                if a.coef_split:
                    cpre = [f'{L}.attn.hc.pre_fwd'] if b else []
                    if b:
                        add(f'{L}.attn.hc.pre_fwd', HX_PORT, 1, [f'{L}.attn.hc.pre_post'], wrow=E_BASE + 2 * b + 1,
                            eng='hcx', order=[x['id'] for x in src].index(f'{L}.attn.hc.pre_post') + 0.25)
                    early = a.h_stream and not b and not eng_ops      # attn COEF-a ahead of the H_LOAD
                    add(f'{L}.{blk}.hc.coef_a', HC_PORT, 0, cpre + ([f'{L}.hc.h_load'] if not b and not early else []),
                        hc_arg(2, E_BASE + 2 * b), eng='hc', order=(-1.5 if early else i - 0.5))
                    add(nm, HC_PORT, o['dur'], preds + [f'{L}.{blk}.hc.coef_a'] + ([f'{L}.hc.h_load'] if early else []),
                        hc_arg(4, O_BASE + 512 * b, gsel=b, quant=1, yout=b), eng='hc', order=i)
                    add(f'{L}.{blk}.hc.coef', HC_PORT, 0, [f'{L}.{blk}.hc.pre_post', f'{L}.{blk}.hc.sinkhorn', nm],
                        hc_arg(2, C_BASE + 2 * b), eng='hc', order=i + 0.25)
                else:
                    add(f'{L}.{blk}.hc.coef', HC_PORT, 0, [f'{L}.{blk}.hc.pre_post', f'{L}.{blk}.hc.sinkhorn'],
                        hc_arg(2, C_BASE + 2 * b), eng='hc', order=i - 0.5)
                    add(nm, HC_PORT, o['dur'], preds + [f'{L}.{blk}.hc.coef'],
                        hc_arg(4, O_BASE + 512 * b, gsel=b, quant=1, yout=b), eng='hc', order=i)
            elif tail == 'hc_post':
                add(nm, HC_PORT, o['dur'], preds + ([f'{L}.{blk}.hc.coef'] if a.coef_split else []), hc_arg(3, 0),
                    eng='hc', order=i)
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
    sched = su_schedule(nodes, a, f'{L}.hc.h_store') if a.su_sched else None
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
    (a.out / 'boot_ok.txt').write_text(''.join(f'{r}\n' for r in boot_ok))
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
                cases_sha256=HG.sha(a.cases), coef_split=bool(a.coef_split), h_stream=bool(a.h_stream), su_sched=sched)
    if fx is not None:
        meta.update(chain_fixture_sha256=HG.sha(a.chain), chain_schema=fx['schema'], chain_checks=fx['checks'],
                    shard=fx['shard'], shard_sha256=fx['shard_sha256'], golden_checks_vs_pickle=0,
                    golden_checks_vs_shard=4, payload='layer-entry h (shard h_in)',
                    engram=dict(ops=eng_ops, port=ENG_PORT, hosting='BEHAVIOURAL at program duration (not Engram RTL)',
                                h_rows_written_by=f'{L}.eng.add at its end: {len(eng_rows)} golden post-Engram h rows '
                                                  f'(shard {L}.engram) over VM rows {H_BASE}..{H_BASE + len(eng_rows) - 1}',
                                h_load_pred=f'{L}.eng.add') if eng_ops else None)
    (a.out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(f"{a.layer}: {len(prog)} ops, {nph} field phases, {len(msgs)} coll messages ({len(own)} records, "
          f"{len(ygold)} y words), {len(run.exp)} golden VM rows ({nst} H_STORE)")


if __name__ == '__main__':
    main()
