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

With --mix-snap, eng.hh/dot/gate/add collapse onto one actual MIX4 descriptor command.
Only key/weight/value operands are booted; H comes from the input producer, and
no post-Engram oracle rows are written to coef.mem. The overall bench still uses
ideal VM and fixture producers, so this mode does not qualify a native layer.

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
GATHER_REC = {'router_allgather': 4, 'a_allgather': 12, 'rows_allgather': 64, 'idx.topk_merge': 8,
              'cand.merge': 32}   # L20 candidate merge (s81-ftok 10-14): 65,536 B = 4x idx.topk_merge's 16,384 B -> 4 x 8 records
SU_IN_NORM = {'attn': ['quant'], 'ffn': ['norm.scale', 'quant']}
PINNED = ('L0', 'L2')                                   # the layers of the pinned su_cases pickle (hc_gate.chains_golden)
ENG_PORT = 10
SUX_PORT = 11                                           # --su-snap: SU ops with no SU job kind (behavioural)


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
    """The committed stage-program ops of layer L.  Raises if the program directory is missing or holds no op of L:
    a source snapshot without results/rtl/s81_ctrl_20261008/programs used to yield an empty layer, whose H_STORE then
    waited on a node that never existed and the topological sort died with a bare 'AssertionError: cycle'."""
    files = sorted(Path(progdir).glob('S*.json'))
    if not files:
        raise SystemExit(f'die_layer_stim: no stage programs (S*.json) under {progdir}: the source snapshot must carry '
                         f'results/rtl/s81_ctrl_20261008/programs (or pass --programs)')
    ops = []
    for f in files:
        p = json.loads(f.read_text())
        loc = {o['op']: o['id'] for o in p['ops']}
        for o in p['ops']:
            if o['id'].startswith((f'{L}.attn.', f'{L}.ffn.', f'{L}.eng.')):
                ops.append(dict(o, preds_id=[loc[q] for q in o['preds']]))
    if not ops:
        raise SystemExit(f'die_layer_stim: layer {L} has no ops in the stage programs under {progdir}')
    return ops


def apply_dur(src, L, items):
    """--dur OP=CYCLES: set the duration of behavioural ops of layer L in src (in place); returns {op id: cycles}."""
    dur_ov = {}
    for kv in items:
        k, v = kv.split('=')
        dur_ov[f'{L}.{k}'] = int(v)
    miss = sorted(set(dur_ov) - {o['id'] for o in src})
    if miss:
        raise SystemExit(f'die_layer_stim: --dur names ops not in layer {L}: {miss}')
    for o in src:
        if o['id'] in dur_ov:
            if o['eng'] in ('hc', 'coll', 'fld'):
                raise SystemExit(f"die_layer_stim: --dur {o['id']}: a real master's op, its cycles are measured, not set")
            o['dur'] = dur_ov[o['id']]
    return dur_ov


def topo_order(nodes):
    """Kahn's order of the rewritten layer program, ties broken by the source program order.  A predecessor that is
    not a node, and a true dependency cycle, are reported by name (both used to surface as 'AssertionError: cycle')."""
    dangling = sorted({(n['id'], p) for n in nodes.values() for p in n['preds'] if p not in nodes})
    if dangling:
        raise ValueError('die_layer_stim: predecessors that are not program nodes: '
                         + ', '.join(f'{n} <- {p}' for n, p in dangling))
    prog, done = [], set()
    while len(prog) < len(nodes):
        ready = [n for n in nodes.values() if n['id'] not in done and all(p in done for p in n['preds'])]
        if not ready:
            raise ValueError('die_layer_stim: dependency cycle among ' + ', '.join(
                sorted(k for k in nodes if k not in done)))
        n = min(ready, key=lambda x: x['order'])
        prog.append(n); done.add(n['id'])
    return prog


def native_operation_audit(prog):
    """Inventory arithmetic provenance; no fixture-backed op qualifies native."""
    targets = {'su': 'dsfd_sp_su_h', 'hc': 'dsfd_sp_hc_c',
               'coll': 'dsfd_sp_collective_c', 'fld': 'dsfd_sp_gather_c'}
    provenance = {
        'su': 'golden SU operand snapshots preloaded in behavioural VM; no native field/SVC producer edge',
        'hc': 'behavioural VM; golden hcx coefficients and golden-partitioned collective y',
        'coll': 'golden y partitioned into four fixture contributions; actual field/SVC partials absent',
        'fld': 'fixture root words; real gather/capture transport only, no field matvec engines',
        'sux': 'numerical operation absent; duration-only substitute',
        'hcx': 'golden coefficient rows written at behavioural done',
        'eng': 'golden post-Engram hidden rows written at behavioural done',
    }
    rows = []
    for index, op in enumerate(prog):
        eng = op['eng']
        rows.append(dict(op_id=op['id'], index=index, engine=eng, port=op['port'],
                         target_module=targets.get(eng),
                         engine_implementation='RTL_TRANSPORT_ONLY' if eng == 'fld' else 'RTL' if eng in targets else 'BEHAVIOURAL_DURATION',
                         operand_provenance=provenance.get(eng, 'behavioural endpoint; no actual native numerical producer'),
                         output_override=eng not in targets,
                         native_memory_bound=False, native_qualified=False,
                         blocking_reasons=['no elaborated whole-die execution binding', 'behavioural VM',
                                           'numerical fixture operands or missing arithmetic engine']))
    return rows


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
    ap.add_argument('--dur', action='append', default=[], metavar='OP=CYCLES',
                    help='override the program duration of a BEHAVIOURAL op of the layer (OP = the id after "<L>.", e.g. '
                    'attn.q_rope=123): a measured unit latency in place of the priced one, to see what the layer '
                    'makes of it.  Real-master ops (hc / coll / fld) are refused; recorded in meta.json dur_override')
    ap.add_argument('--su-snap', type=Path, default=None, help='the REAL SU slab (tb +define+TB_SU_REAL, s81-ftok r3): '
                    'the layer\'s SU operand snapshot (tools/dsrom_1m_su.py golden --engram snap_LXX.pkl); SU ops with an SU '
                    'job kind become jobs of the production slab on the golden operands (tools/s81_ftok/su_layer.py), '
                    'their chain members are aliased to the job, the SU ops with no job kind move to the behavioural port '
                    f'{SUX_PORT} (su.x) at program duration')
    ap.add_argument('--mix-snap', type=Path, help='real MIX4 operands; collapse eng.* onto one actual master command')
    ap.add_argument('--hcx-real', action='store_true', help='port 9: the HC coefficient chain on real RTL (4-rank '
                    'dsfd_sp_hcx_projection + gatherpack + post, ot_s81_hcx_chain_seq) under the fixed issuer: the '
                    'block\'s hc.fn/sumsq/rsqrt/pre_post/sinkhorn leave the dynamic program (one compiled engine-9 command '
                    'per block in fixed_program.mem); NO golden coefficient rows are written (the HC COEF job reads the '
                    'rows the real post writes)')
    ap.add_argument('--hcx-issue', default='', help='compiled issuer ages of the attn,ffn chain commands (phase-2 edges)')
    ap.add_argument('--hcx-p2p', type=int, default=0, help='measured chain command-pin -> done-pin latency (tb_s81_hcx_chain)')
    ap.add_argument('--hcx-set', type=int, default=-1, help='resident HC ROM set index (default: the layer number)')
    ap.add_argument('--program-layer', default=None, help='take the stage program of this backbone layer (e.g. L0) '
                    'for --layer (its op ids renamed): a DSpark stage row (M<st>R<i>, tools/s81_ftok/mtp_golden.py) runs '
                    'on the sliding layer\'s program (window attention + MoE, the same op graph), its own chain and SU '
                    'snapshot')
    ap.add_argument('--vm-coeff-align', action='store_true',
                    help='place each HC coefficient pair in a separate 16-row-aligned VM region for compact native arms')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--programs', type=Path, default=ROOT / 'results/rtl/s81_ctrl_20261008/programs')
    a = ap.parse_args()
    rng = random.Random(a.seed)
    npr = np.random.default_rng(a.seed)
    a.out.mkdir(parents=True, exist_ok=True)

    COEF_STRIDE = 16 if a.vm_coeff_align else 2
    # ------------------------------------------------------------------ golden chain (hc_gate.chains_golden)
    if a.program_layer:                                # a DSpark stage row on a backbone layer's program (s81-ftok r3)
        P_ = a.program_layer
        src = [dict(o, id=a.layer + o['id'][len(P_):], preds_id=[a.layer + q[len(P_):] for q in o['preds_id']])
               for o in layer_ops(a.programs, P_)]
    else:
        src = layer_ops(a.programs, a.layer)          # fail fast on a snapshot without the stage programs
    dur_ov = apply_dur(src, a.layer, a.dur)
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
        if a.hcx_real:                                  # the real post writes these rows; never injected
            break
        g = gold[blk]
        coef[C_BASE + COEF_STRIDE * b] = HG.pack(HG.u32(np.asarray(g['comb'], np.float32).reshape(-1)), 32)
        coef[C_BASE + COEF_STRIDE * b + 1] = HG.pack(list(HG.u32(g['pre'])) + list(HG.u32(g['post'])) + [int(HG.u32([g['eps']])[0])], 32)

    # --coef-split: the early row pair of block b at E_BASE + 2b: row 0 = don't-care combine (zeros, present at job
    # start), row 1 = {pre, zero post, eps}.  attn: present at job start (the previous layer's ffn.hc.pre_post wrote
    # it); ffn: written by <L>.attn.hc.pre_fwd, a 1-cycle hcx op that follows <L>.attn.hc.pre_post.
    E_BASE = C_BASE + 2 * COEF_STRIDE
    boot_ok = []
    if a.coef_split:
        for b, blk in enumerate(('attn', 'ffn')):
            g = gold[blk]
            e1 = HG.pack(list(HG.u32(g['pre'])) + [0] * len(HG.u32(g['post'])) + [int(HG.u32([g['eps']])[0])], 32)
            vm_boot[E_BASE + COEF_STRIDE * b] = 0
            boot_ok.append(E_BASE + COEF_STRIDE * b)
            if b == 0:
                vm_boot[E_BASE + 1] = e1
                boot_ok.append(E_BASE + 1)
            else:
                coef[E_BASE + COEF_STRIDE * b + 1] = e1
    # ------------------------------------------------------------------ program rewrite (by name, then topological)
    eng_ops = [o['id'] for o in src if o['id'].startswith(f'{a.layer}.eng.')]
    assert bool(eng_ops) == (eng_rows is not None), (a.layer, eng_ops, 'Engram ops need an Engram chain fixture')
    if eng_ops and not a.mix_snap:
        for q, row in enumerate(eng_rows):
            coef[(EH_BASE if a.h_stream else H_BASE) + q] = row
    mix_meta = None
    fixed_rows = []          # fixed-issuer calendar rows (engine 10 MIX4 row first: its tag OP_BASE+0 = eng.add's index)
    if a.mix_snap:
        assert eng_ops and not a.h_stream, 'MIX4 currently requires in-place H layout'
        es = pickle.loads(a.mix_snap.read_bytes())
        assert all(es['checks'].values())
        assert np.array_equal(HG.u32(es['h']).reshape(-1), HG.u32(ch['h_in']).reshape(-1)), 'MIX input != layer entry'
        assert np.array_equal(HG.u32(es['out']).reshape(-1), HG.u32(ch['h']).reshape(-1)), 'MIX oracle != HC input'
        # The producer boundary supplies K/W/V operands, never MIX result rows.
        # H is supplied only by the existing package landing producer.
        kb, wb, vb, db = 9000, 10280, 11560, 11880
        for name, base in [('key', kb), ('wgt', wb), ('value', vb)]:
            words = HG.u32(es[name]).reshape(-1, 16)
            for q, row in enumerate(words):
                vm_boot[base + q] = HG.pack(row, 32)
                boot_ok.append(base + q)
        vm_boot[db] = HG.pack([H_BASE, kb, wb, vb, H_BASE,
                              int(HG.u32([es['eps']])[0]), int(HG.u32([es['scale']])[0])], 32)
        boot_ok.append(db)
        sys.path.insert(0, str(ROOT/'tools/s81_static_control'))
        from program import encode_program, issuer_done_row
        # Issuer row semantics (ot_s81_fixed_issue): 'issue' is the age whose edge loads the command
        # register (command pin = issue+1); 'done' is the age whose edge samples the completion pin.
        # MIX4's measured command-pin -> done-pin latency is 772 (component gate), so
        # done = issue + 1 + 772. issue+772 (=1428) misses the completion by one edge: issuer
        # fault code 8 at stream cycle 2681 (tb_s81_engram_mix4_fixed reproduces it).
        MIX_ISSUE, MIX_PIN_TO_PIN = 656, 772
        mix_done = issuer_done_row(MIX_ISSUE, MIX_PIN_TO_PIN)
        fixed_rows.append(dict(engine=10,arg=db,issue=MIX_ISSUE,done=mix_done,pin_to_pin=MIX_PIN_TO_PIN))
        mc = encode_program([dict(engine=10,arg=db,issue=MIX_ISSUE,done=mix_done,pin_to_pin=MIX_PIN_TO_PIN),
                             dict(engine=15,arg=0,issue=mix_done+4,done=0)],stage=0,phase=3)
        mc['hardware_nops']=2
        mc['seal_to_arm_stream_cycles']=3
        (a.out/'mix_program.mem').write_text(''.join(f"{w['word']:09x}\n" for w in mc['writes']))
        (a.out/'mix_calendar.json').write_text(json.dumps(dict(calendar=mc,op_base=2,
            reset_stream_cycle=1000,job_stream_cycle=1250,header_stream_cycle=1250,
            source_context=dict(user=0,pos=0,tok=1000,token_header_bits='146:126'),
            landing_last_write_pin=1892,real_vm_commit_bound=1903,
            actual_vm_scope='ideal row write consumption in this component vehicle',
            physical_clock_phase_qualified=False,full_native_qualified=False),indent=2)+'\n')
        mix_meta = dict(native_qualified=False, master='dsfd_engram_mix4_c', descriptor=db,
                        operand_sha256=HG.sha(a.mix_snap), golden_output_injection=False,
                        scope='actual arithmetic endpoint; ideal VM and fixture producers remain')
    nodes = {}

    def add(name, port, dur, preds, arg=None, cmsg=-1, wrow=-1, eng='', order=0.0):
        nodes[name] = dict(id=name, port=port, dur=dur, preds=list(dict.fromkeys(preds)), arg=arg, ph=-1, cmsg=cmsg,
                           wrow=wrow, eng=eng, order=order)

    L = a.layer
    sub, su_alias = None, {}
    if a.su_snap:
        sys.path.insert(0, str(ROOT / 'tools/s81_ftok'))
        import su_layer
        sub = su_layer.build(a.su_snap, L, check_layer=not a.program_layer)
        su_alias = sub['alias']
        for gain_index, (gain_name, gain_arg) in enumerate((name, arg) for name, arg in sub['arg'].items()
                                                         if '.su.gain_' in name):
            add(gain_name, 1, 0, [], gain_arg, eng='su', order=-2.8 + 0.01 * gain_index)
        su_members = {}
        for k_, v_ in su_alias.items():
            su_members.setdefault(v_, []).append(k_)
    add(f'{L}.hc.gain_attn', HC_PORT, 0, [], hc_arg(5, G_BASE, gsel=0), eng='hc', order=-3)
    add(f'{L}.hc.gain_ffn', HC_PORT, 0, [], hc_arg(5, G_BASE + HG.GROWS, gsel=1), eng='hc', order=-2)
    hl_base = EH_BASE if (a.h_stream and eng_ops) else H_BASE
    add(f'{L}.hc.h_load', HC_PORT, 0, [f'{L}.eng.add'] if eng_ops else [], hc_arg(0, hl_base), eng='hc',
        order=([o['id'] for o in src].index(f'{L}.eng.add') + 0.5 if eng_ops else -1))
    alias = {f'{L}.{blk}.{s}': f'{L}.{blk}.hc_pre' for blk in SU_IN_NORM for s in SU_IN_NORM[blk]}
    names = {o['id'] for o in src}
    msgs = []
    hcx_members = {}
    assert not (a.hcx_real and a.coef_split), '--hcx-real lowers the full coefficient chain (no COEF split)'
    for i, o in enumerate(src):
        nm = o['id']
        blk = nm.split('.')[1]
        if blk == 'eng' and a.mix_snap:
            if nm == f'{L}.eng.add':
                external = [p for x in src if x['id'] in eng_ops for p in x['preds_id'] if p in names and p not in eng_ops]
                add(nm, ENG_PORT, 0, external, db, wrow=H_BASE, eng='mix4', order=i)
            continue
        if blk == 'eng':               # behavioural Engram (port 10): eng.add lands the golden post-Engram h rows
            assert o['port'] == ENG_PORT and o['eng'] == 'eng', o
            add(nm, ENG_PORT, o['dur'], [p for p in o['preds_id'] if p in names],
                wrow=(hl_base if nm == f'{L}.eng.add' else -1), eng='eng', order=i)
            continue
        b = 0 if blk == 'attn' else 1
        tail = nm.split('.', 2)[2]
        if nm in alias or nm in su_alias:
            continue

        def res(p):
            return su_alias.get(alias.get(p, p), alias.get(p, p))
        pids = list(o['preds_id'])
        if sub is not None:                             # an SU job waits on every member's predecessors
            for m_ in su_members.get(nm, []):
                pids += next(x['preds_id'] for x in src if x['id'] == m_)
        preds = [res(p) for p in pids if res(p) in names and res(p) != nm]
        if blk == 'ffn' and tail in ('hc.fn', 'hc.sumsq', 'hc_pre'):
            preds.append(f'{L}.attn.hc_post')            # the ffn block reads the h the attn hc_post wrote
        if eng_ops and blk == 'attn' and tail == 'hc_pre':
            preds = [p for p in preds if p != f'{L}.eng.add'] + [f'{L}.hc.h_load']   # h reaches the HC through H_LOAD
        if o['eng'] == 'hc':
            if tail == 'hc_pre':
                if a.coef_split:
                    cpre = [f'{L}.attn.hc.pre_fwd'] if b else []
                    if b:
                        add(f'{L}.attn.hc.pre_fwd', HX_PORT, 1, [f'{L}.attn.hc.pre_post'], wrow=E_BASE + COEF_STRIDE * b + 1,
                            eng='hcx', order=[x['id'] for x in src].index(f'{L}.attn.hc.pre_post') + 0.25)
                    early = a.h_stream and not b and not eng_ops      # attn COEF-a ahead of the H_LOAD
                    add(f'{L}.{blk}.hc.coef_a', HC_PORT, 0, cpre + ([f'{L}.hc.h_load'] if not b and not early else []),
                        hc_arg(2, E_BASE + COEF_STRIDE * b), eng='hc', order=(-1.5 if early else i - 0.5))
                    add(nm, HC_PORT, o['dur'], preds + [f'{L}.{blk}.hc.coef_a'] + ([f'{L}.hc.h_load'] if early else []),
                        hc_arg(4, O_BASE + 512 * b, gsel=b, quant=1, yout=b), eng='hc', order=i)
                    add(f'{L}.{blk}.hc.coef', HC_PORT, 0, [f'{L}.{blk}.hc.pre_post', f'{L}.{blk}.hc.sinkhorn', nm],
                        hc_arg(2, C_BASE + COEF_STRIDE * b), eng='hc', order=i + 0.25)
                else:
                    add(f'{L}.{blk}.hc.coef', HC_PORT, 0, [f'{L}.{blk}.hc.pre_post', f'{L}.{blk}.hc.sinkhorn'],
                        hc_arg(2, C_BASE + COEF_STRIDE * b), eng='hc', order=i - 0.5)
                    add(nm, HC_PORT, o['dur'], preds + [f'{L}.{blk}.hc.coef'],
                        hc_arg(4, O_BASE + 512 * b, gsel=b, quant=1, yout=b), eng='hc', order=i)
            elif tail == 'hc_post':
                add(nm, HC_PORT, o['dur'], preds + ([f'{L}.{blk}.hc.coef'] if a.coef_split else []), hc_arg(3, 0),
                    eng='hc', order=i)
            elif a.hcx_real:   # coefficient producers: the real chain, one fixed-issuer command per block
                hcx_members.setdefault(blk, []).append(nm)
            else:      # coefficient producers: behavioural on hcx
                wrow = {'hc.pre_post': C_BASE + COEF_STRIDE * b + 1, 'hc.sinkhorn': C_BASE + COEF_STRIDE * b}.get(tail, -1)
                add(nm, HX_PORT, o['dur'], preds, wrow=wrow, eng='hcx', order=i)
        elif o['eng'] == 'coll':
            mode = 0 if 'allreduce' in tail else 1
            nrec = D // 16 if mode == 0 else GATHER_REC[tail]
            msgs.append(dict(op=nm, mode=mode, nrec=nrec, blk=blk))
            add(nm, COLL_PORT, o['dur'], preds, (mode << 16) | nrec, eng='coll', order=i)
        elif sub is not None and o['port'] == 1:
            if nm in sub['arg']:
                add(nm, 1, o['dur'], preds, sub['arg'][nm], eng='su', order=i)
            else:
                add(nm, SUX_PORT, o['dur'], preds, eng='sux', order=i)
        else:
            add(nm, o['port'], o['dur'], preds, eng=o['eng'], order=i)
    add(f'{L}.hc.h_store', HC_PORT, 0, [f'{L}.ffn.hc_post'], hc_arg(1, S_BASE), eng='hc', order=1e9)
    hcx_meta = None
    if a.hcx_real:
        gone = {m for v in hcx_members.values() for m in v}
        for n in nodes.values():                        # consumers read the coefficient rows (VM presence), not a port-9 done
            n['preds'] = [p for p in n['preds'] if p not in gone]
        assert set(hcx_members) == {'attn', 'ffn'}, hcx_members
        iss = [int(x) for x in a.hcx_issue.split(',')] if a.hcx_issue else []
        assert len(iss) == 2 and a.hcx_p2p > 0, '--hcx-issue A,F and --hcx-p2p required'
        hset = a.hcx_set if a.hcx_set >= 0 else int(L[1:]) if L[0] == 'L' else -1
        assert 0 <= hset < 43, hset
        sys.path.insert(0, str(ROOT/'tools/s81_static_control'))
        from program import issuer_done_row
        fixed_rows.extend(dict(engine=11, arg=(hset << 15) | (hl_base << 1) | b, issue=iss[b],
                               done=issuer_done_row(iss[b], a.hcx_p2p), pin_to_pin=a.hcx_p2p) for b in range(2))
        hcx_meta = dict(members=hcx_members, rom_set=hset, issue=iss, pin_to_pin=a.hcx_p2p, h_base=hl_base,
                        coef_rows=[C_BASE, C_BASE + 1, C_BASE + COEF_STRIDE, C_BASE + COEF_STRIDE + 1],
                        golden_coefficient_injection=False, native_qualified=False,
                        declared_boundaries=['ideal bench VM', 'TP4 raw gather bench transport (collective glue)',
                                             'peer ranks read die-0 H rows (replicated residual)'])
    if fixed_rows:
        sys.path.insert(0, str(ROOT/'tools/s81_static_control'))
        from program import encode_program
        rows = fixed_rows + [dict(engine=15, arg=0, issue=max(r['done'] for r in fixed_rows) + 4, done=0)]
        fc = encode_program(rows, stage=0, phase=3)
        (a.out/'fixed_program.mem').write_text(''.join(f"{w['word']:09x}\n" for w in fc['writes']))
        (a.out/'fixed_meta.mem').write_text(f"{len(rows):08x}\n{len(fc['writes']):08x}\n")
        (a.out/'fixed_calendar.json').write_text(json.dumps(dict(rows=rows, op_base=2, reset_stream_cycle=1000,
            job_stream_cycle=1250, semantics='done = issue + 1 + pin_to_pin', full_native_qualified=False), indent=2) + '\n')
    topo_order(nodes)                                  # dangling predecessor / cycle: named, before the SU search
    sched = su_schedule(nodes, a, f'{L}.hc.h_store') if a.su_sched else None
    prog = topo_order(nodes)
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
    su_meta = None
    if sub is not None:
        assert min(sub['vm']) >= su_layer.SU_BASE and sub['top'] <= 16384, (min(sub['vm']), sub['top'])
        assert not set(sub['vm']) & set(vm_boot)
        with open(a.out / 'vm_boot.mem', 'a') as f:
            for r in sorted(sub['vm']):
                f.write(f'@{r:x}\n{sub["vm"][r]:0128x}\n')
        with open(a.out / 'su_expa.mem', 'w') as fa, open(a.out / 'su_expd.mem', 'w') as fd:
            for r in sorted(sub['exp']):
                fa.write(f'{r:04x}\n')
                fd.write(f'{sub["exp"][r]:0128x}\n')
        (a.out / 'su_n.mem').write_text(f'{len(sub["exp"]):08x}\n')
        real = [n['id'] for n in prog if n['eng'] == 'su']
        sux = [n['id'] for n in prog if n['eng'] == 'sux']
        su_meta = dict(snapshot=str(a.su_snap), snapshot_sha256=HG.sha(a.su_snap), real_jobs=real,
                       aliased=su_alias, behavioural_sux=sux, exp_rows=len(sub['exp']), vm_rows=len(sub['vm']),
                       T=sub['T'], softmax_fits=sub['softmax_fits'], qb_fits=sub['qb_fits'],
                       router_fits=sub['router_fits'], checks=sub['checks'],
                       sw_fit=sub['sw_fit'], footprints=sub['footprints'], compressor_outputs=sub['compressor_outputs'],
                       native_allocation=False, jexp={k: list(v) for k, v in sub['jexp'].items()})
        print(f"{L}: REAL SU {len(real)} jobs ({len(sub['exp'])} expected rows), behavioural su.x {sux}")
    (a.out / 'boot_ok.txt').write_text(''.join(f'{r}\n' for r in boot_ok))
    (a.out / 'payload.mem').write_text(''.join(f'{v:0128x}\n' for v in payload))
    with open(a.out / 'expa.mem', 'w') as fa, open(a.out / 'expd.mem', 'w') as fd:
        for r in sorted(run.exp):
            fa.write(f'{r:04x}\n')
            fd.write(f'{run.exp[r]:0128x}\n')
    nst = sum(1 for r in run.exp if r >= S_BASE)
    (a.out / 'n.mem').write_text(f'{len(run.exp):08x}\n{len(own):08x}\n{len(msgs):08x}\n{len(ygold):08x}\n{nst:08x}\n')
    meta = dict(layer=a.layer, native_qualified=False, native_operation_audit=native_operation_audit(prog),
                vm_coefficient_stride=COEF_STRIDE,
                vm_coefficient_bases=[C_BASE, C_BASE + COEF_STRIDE], ng=a.ng, ops=len(prog), field_phases=nph, coll_messages=msgs, coll_records=len(own),
                y_words=len(ygold), exp_rows=len(run.exp), hstore_rows=nst, golden_checks_vs_pickle=4,
                program=[dict(k=k, id=o['id'], port=o['port'], eng=o['eng'],
                              arg=o['arg'] if o['arg'] is not None else k,
                              argument_provenance='native endpoint descriptor' if o['eng'] in ('su', 'hc') else 'fixture program argument; native binding unproven',
                              preds=o['preds']) for k, o in enumerate(prog)],
                cases_sha256=HG.sha(a.cases), coef_split=bool(a.coef_split), h_stream=bool(a.h_stream), su_sched=sched,
                dur_override=dur_ov or None, su_real=su_meta, mix4=mix_meta, hcx=hcx_meta)
    if fx is not None:
        meta.update(chain_fixture_sha256=HG.sha(a.chain), chain_schema=fx['schema'], chain_checks=fx['checks'],
                    shard=fx['shard'], shard_sha256=fx['shard_sha256'], golden_checks_vs_pickle=0,
                    golden_checks_vs_shard=4, payload='layer-entry h (shard h_in)',
                    engram=dict(ops=eng_ops, port=ENG_PORT, hosting=('actual MIX4 endpoint' if a.mix_snap else 'BEHAVIOURAL at program duration (not Engram RTL)'),
                                h_rows_written_by=('MIX4 actual write ports' if a.mix_snap else f'{L}.eng.add at its end: {len(eng_rows)} golden post-Engram h rows '
                                                  f'(shard {L}.engram) over VM rows {H_BASE}..{H_BASE + len(eng_rows) - 1}'),
                                h_load_pred=f'{L}.eng.add') if eng_ops else None)
    (a.out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(f"{a.layer}: {len(prog)} ops, {nph} field phases, {len(msgs)} coll messages ({len(own)} records, "
          f"{len(ygold)} y words), {len(run.exp)} golden VM rows ({nst} H_STORE)")


if __name__ == '__main__':
    main()
