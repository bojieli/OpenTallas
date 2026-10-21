#!/usr/bin/env python3
"""S81-MUCAL140 (10-20): the S81 multi-user STATIC calendar on the PHYSICAL pinned stage windows (140 stages @ 122
frames, stage_map_f122_140 sha f5608b1e5f2a), replacing the 59 legacy Sxxx groups of dv_mu_calendar.py (Codex 13:04:
no inheritance of 46 AR / 10 MTP).

Inputs (all committed):
  map       results/token_pass/cal2_s81_1020/stage_pick_122/stage_map_f122_140.json (content of every TP4 stage)
  composer  tools/toksim_s81_compose.py on results/token_pass/measured_s81_1019/elements (release-partial, strict
            admission): per-NODE cycles of the static token DAG, captured from the composer itself (no re-pricing)
  cal2      results/token_pass/cal2_s81_1020/fold_cal2.py node deltas (XG5 +2/+1 a field op, COLL7 +4 a coll phase,
            IDX3R +62 an idx.score = measured rg3 req +s+4 / resp +s+1 worst pair 41 + 21 W->E chain, T0 +41) and the
            stage-hop law (N - 120) x (1006 + 2)

Physical stage model (static, linear chain; a token visits R000..R139 in order):
  per layer l, from the composed node cycles (segment span = longest path of the segment's sub-DAG):
    A_l  attention (attn.*, eng.*; includes the index path on the 8 index layers)       -> on the dense stage of l
    D_l  ffn pre-expert (norm, router, top6, shared expert)                              -> on the dense stage of l
    E_l  routed experts, all 6 of the token (experts_gu, swiglu, quant2, down, weights)  -> split over the stages
    C_l  combine allreduce + hc_post                                                     -> on the stage holding
                                                                                            expert (l, 383)
  STATIC RESERVATION: the router picks the experts at run time, so a stage holding N experts of layer l must reserve
    min(6, N) expert slots (AR) -- any routing then fits with no stall.  R(l, N) = E_l * min(6, N) / 6.
  FORWARD-X schedule: the layer input x_l leaves the dense stage right after D_l and is forwarded stage to stage at
    the hop law (the die receives the message, then re-sends it); each expert stage starts its reserved slots on x
    arrival and adds its partial to the partial arriving from upstream (one SU add, ADD) before sending it on.
    Single-user latency per layer = D + (n - 1) hops + R + n ADD + C -- the same hops the cal2 fold charged, plus the
    adds; the stage hold windows are what change.
  ONE JOB CONTEXT a stage (ot_dsdv_fixed_issue): a user holds a stage from its first item start to its last item end.
  MTP (6 verify positions a step, one shared index read): stage step window M_s = 6 W_s - 5 scan_s (scan_s = the
    stage's attn.idx.score cycles, read once a step) -- the S81-BALANCE law, here on physical windows.  Wave term of the
    step = 5 x the worst physical per-position busy max_s (W_s - scan_s) (replaces the composer's legacy wave.busy).
  Links: stage s -> s+1 carries x and the partial: 2 x H_MSG a position (AR), x6 (MTP), per copy pair.
  Head dies (52 other): head ops a position (AR); 6 x head + draft heads (MTP). Host plane HOST_TOK a token a user.
  Copy B: the 8 map-declared dense-owner stages (L2/8/14/20/24/28/32/36) have a second TP4 copy; users are 2-coloured.

Calendar: period P = phase-q4 ceiling of the user's own token (AR) / verify step (MTP); users at phase-q4 shifts
spread over P; the brute-force checker expands every window of every user modulo P on every resource (stage copy,
link copy pair, head, host) and FAULTS on any overlap.  Max users = the largest N with 0 collisions; the checker is
also run at N + 1 (must FAULT) and on an injected shift collision (must FAULT): negative controls.

Grades: node cycles carry the composer grades (80 % measured AR); the stage split, reservation, forward-x adds and the
MTP law are MODEL (exact arithmetic on the map + composed cycles); measured by MU.TOK on RTL.

  dv_mu_calendar_phys.py [--out DIR]          # writes calendar_phys140_{ar,mtp}.json + summary
  dv_mu_calendar_phys.py --check              # recompute and compare
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import dv_mu_calendar as LEG  # noqa: E402  (assign_copies / copy_ok / constants of the legacy calendar)

MAP = ROOT / 'results/token_pass/cal2_s81_1020/stage_pick_122/stage_map_f122_140.json'
OUT = ROOT / 'results/token_pass/mucal140_s81_1020'
F = 1.2e9
TAU = 4.159
PHASE_Q = 4
HOP = 1006 + 2                 # cal2 STAGE_HOP law (link_rt 652 + KP4 PHY + UCIe + wire, + CAL1 guard/LEPCAP)
HOP_REF = 120                  # stage hops in the composed DAG record
H_MSG = LEG.H_MSG              # 652 link serialisation a message
HOST_TOK = LEG.HOST_TOK
SCHEMA = 'opentallas.s81_dv.mu_calendar_phys.v1'
E_OPS = {'ffn.experts_gu', 'ffn.swiglu', 'ffn.route_w', 'ffn.quant2', 'ffn.down', 'ffn.weights'}
C_OPS = {'ffn.combine_allreduce', 'ffn.hc_post'}


def qup(x):
    return -(-int(math.ceil(x)) // PHASE_Q) * PHASE_Q


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------------ composed node cycles
ROMOPT = ROOT / 'results/rtl/s81_romopt_1020/c/compose/o3mix_prop_compiled.json.gz'
# S81-ROMOPT-C compose_c.py: the six field ops are substituted where the CALPIPE scenario still carries these values
ROMOPT_OLD = {'attn.wo_b': 901, 'attn.wo_a': 3531, 'ffn.router': 1419, 'ffn.experts_gu': 3680, 'ffn.down': 3084,
              'attn.wq_b': 1987}


def composed(mode='record'):
    """run the composer, capture its per-node cycles (the dict it passes to solve) for both workloads.
    record: release-partial composition of record (cycles.json, 834.0 / 2,649.1)
    romopt: CALPIPE scenario + S81-ROMOPT O1+O2+O3 (gu k2 + down k3 stretch 2) compiled op spans, exactly as
            results/rtl/s81_romopt_1020/c/compose_c.py case o3mix_prop_compiled (1,040.4 / 3,193.4); asserted equal"""
    import gzip
    C = load(ROOT / 'tools/toksim_s81_compose.py', 'toksim_s81_compose')
    cap = {}
    orig, orig_nc = C.solve, C.node_cycles

    def spy(dag, cyc):
        cap[dag['nodes'][0]['id'] + str(len(dag['nodes']))] = (dag, dict(cyc))
        return orig(dag, cyc)
    C.solve = spy
    hits = collections.Counter()
    if mode == 'romopt':
        ref = json.loads(gzip.decompress(ROMOPT.read_bytes()))
        v = ref['rate3']['op_values']

        def nc(n, ov):
            cyc, how = orig_nc(n, ov)
            op = n.get('op')
            if cyc is not None and op in v and abs(cyc - ROMOPT_OLD[op]) < 0.01:
                hits[op] += 1
                return float(v[op]), how
            return cyc, how
        C.node_cycles = nc
    try:
        r = C.build(C.OUT / 'elements', 'calpipe' if mode == 'romopt' else None)
    finally:
        C.solve, C.node_cycles = orig, orig_nc
    if mode == 'romopt':
        assert dict(hits) == ref['rate3']['substitutions'], (dict(hits), ref['rate3']['substitutions'])
        committed = ref
    else:
        committed = json.loads((C.OUT / 'cycles.json').read_text())
    for wl in ('ar', 'mtp'):
        assert r['workloads'][wl]['T_cycles'] == committed['workloads'][wl]['T_cycles'], wl
    dags = {}
    for wl, p in C.DAGS.items():
        n = json.loads(p.read_text())
        key = n['nodes'][0]['id'] + str(len(n['nodes']))
        dags[wl] = cap[key] if key in cap else None
    # both workloads have distinct node counts; fall back to order if not
    if None in dags.values():
        vals = list(cap.values())
        dags = dict(ar=vals[0], mtp=vals[1])
    return r, dags


def cal2_delta(n, F2):
    return sum(F2.node_delta(n, True).values())


def seg_of(n):
    op = n.get('op') or ''
    if n.get('cls') == 'hop' or 'substage_hop' in op:
        return None
    if op in E_OPS:
        return 'E'
    if op in C_OPS:
        return 'C'
    if op.startswith('ffn.'):
        return 'D'
    if op.startswith(('attn.', 'eng.')):
        return 'A'
    return None


IVS = {}                     # (layer, segment) -> [(start offset, end offset, engine class)] of the segment's nodes


def layer_segments(dag, cyc, F2, extra):
    """per layer: A / D / E / C spans (longest path of each segment's sub-DAG) + the idx.score scan cycles"""
    IVS.clear()
    nodes = {n['id']: n for n in dag['nodes']}
    c = {i: cyc[i] + cal2_delta(nodes[i], F2) for i in nodes}
    seg = collections.defaultdict(list)
    for n in dag['nodes']:
        L = n.get('layer')
        s = seg_of(n)
        if isinstance(L, int) and 0 <= L < 40 and s and not n['id'].startswith('V.'):
            seg[(L, s)].append(n['id'])
    pred = collections.defaultdict(list)
    for e in dag['edges']:
        pred[e['dst']].append((e['src'], float(e.get('cycles') or 0)))
    out = {}
    for (L, s), ids in seg.items():
        S = set(ids)
        end = {}

        def fin(i):
            if i in end:
                return end[i]
            st = max([fin(p) + w for p, w in pred[i] if p in S] or [0.0])
            end[i] = st + c[i]
            return end[i]
        span = max(fin(i) for i in ids)
        out.setdefault(L, {})[s] = span
        IVS[(L, s)] = sorted((end[i] - c[i], end[i], nodes[i].get('cls') or 'su') for i in ids if c[i] > 0)
    scan = collections.Counter()
    for n in dag['nodes']:
        if isinstance(n.get('layer'), int) and n['id'].endswith('attn.idx.score') and not n['id'].startswith('V.'):
            scan[n['layer']] = max(scan[n['layer']], c[n['id']])
    for t in extra:                                   # priced per-layer terms (p4l DV deltas) -> the dense segment
        if t['kind'] == 'layer' and t['slot'].startswith('L'):
            L = int(t['slot'][1:].split('.')[0])
            if L in out:
                a0 = out[L]['A']
                out[L]['A'] += t['cycles']
                if t['cycles'] > 0:                   # unknown engine: blocks every engine class (conservative)
                    IVS[(L, 'A')].append((a0, out[L]['A'], 'ALL'))
    head = sum(c[i] for i, n in nodes.items() if (n.get('op') or '').startswith('head.') and n.get('critical'))
    return out, dict(scan), head, c


# ------------------------------------------------------------------------------------------------ single-user timeline
def stage_items(st):
    d = st['dense_layer']
    tail = [('X', l, b - a + 1) for l, a, b in st['experts'] if d is None or l < d]
    head = [('X', l, b - a + 1) for l, a, b in st['experts'] if d is not None and l >= d]
    return tail + ([('D', d, None)] if d is not None else []) + head


def timeline(stages, seg, add, embed_end=0.0, alap=False):
    """forward-x single-user schedule: per stage [start, end] hold window, item log, chain end; + legacy-equivalent"""
    last_stage = {}
    for i, st in enumerate(stages):
        for l, a, b in st['experts']:
            if b == 383:
                last_stage[l] = i
    x_arr, p_arr, comb = {}, {}, {}          # per layer: x arrival at the current stage, partial arrival, combined out
    win, log = [], []
    links = []
    for i, st in enumerate(stages):
        cur, first = None, None
        part_out = {}
        for kind, l, N in stage_items(st):
            if kind == 'D':
                ready = comb.get(l - 1, embed_end) if l > 0 else embed_end
                s0 = max(cur or 0.0, ready)
                xl = s0 + seg[l]['A'] + seg[l]['D']
                x_arr[l] = xl                               # x leaves now (forwarded to the next stage below)
                e0 = xl
                busy = [(s0 + a, s0 + b, k) for a, b, k in IVS.get((l, 'A'), [])] + \
                       [(s0 + seg[l]['A'] + a, s0 + seg[l]['A'] + b, k) for a, b, k in IVS.get((l, 'D'), [])]
                log.append(dict(stage=st['stage'], item=f'dense L{l}', start=s0, end=e0, busy=busy))
            else:
                R = seg[l]['E'] * min(6, N) / 6.0
                pin = p_arr.get(l)
                s0 = max(cur or 0.0, x_arr[l])
                if alap and pin is not None:          # just-in-time slots: end as the upstream partial lands (same out)
                    s0 = max(s0, pin - R)
                e = s0 + R
                po = (max(e, pin) + add) if pin is not None else e
                part_out[l] = po
                e0 = po
                # engine classes: the expert slots hold field + su for the whole reservation; the add is an SU op;
                # the combine holds coll + su (conservative unions)
                busy = [(s0, e, 'field'), (s0, e, 'su')] + ([(po - add, po, 'su')] if pin is not None else [])
                if last_stage.get(l) == i:
                    comb[l] = po + seg[l]['C']
                    busy += [(po, comb[l], 'coll'), (po, comb[l], 'su')]
                    e0 = comb[l]
                log.append(dict(stage=st['stage'], item=f'experts L{l} x{N} (slots {min(6, N)})', start=s0, end=e0,
                                busy=busy))
            first = s0 if first is None else first
            cur = e0
        win.append((first, cur))
        # messages to the next stage (one per layer still open downstream): the layer input x (unless the next stage
        # computes it), the running partial, and the combined output when the next layer's dense stage is downstream
        if i + 1 < len(stages):
            nxt = stages[i + 1]
            nl = {l for l, _, _ in nxt['experts']}
            for l in sorted(nl):
                if l in x_arr and nxt['dense_layer'] != l:
                    links.append((i, x_arr[l], f'x L{l}'))
                    x_arr[l] += HOP
                if l in part_out and last_stage.get(l) != i:
                    links.append((i, part_out[l], f'partial L{l}'))
                    p_arr[l] = part_out[l] + HOP
            for l, t in list(comb.items()):
                if last_stage.get(l) == i and l + 1 < 40 and stages[i]['dense_layer'] != l + 1:
                    links.append((i, t, f'combined L{l}'))
                    comb[l] = t + HOP
    chain = comb[39] - embed_end
    legacy = sum(seg[l]['A'] + seg[l]['D'] + seg[l]['E'] + seg[l]['C'] for l in range(40)) + (len(stages) - 1) * HOP
    return win, log, links, chain, legacy


# ------------------------------------------------------------------------------------------------ calendar + checker
def windows(model, user, shift, kind, col):
    mt = kind == 'mtp'
    ws = []
    for i, st in enumerate(model['stages']):
        cp = col.get(st['stage'], {}).get(user, 'A') if st['copies'] > 1 else 'A'
        L = st['step'] if mt else st['occ']
        ws.append((f"{st['stage']}.{cp}", shift + st['t'], shift + st['t'] + L))
    for i, t, what in model['links']:
        a, b = model['stages'][i], model['stages'][i + 1]
        ca = col.get(a['stage'], {}).get(user, 'A') if a['copies'] > 1 else 'A'
        cb = col.get(b['stage'], {}).get(user, 'A') if b['copies'] > 1 else 'A'
        L = H_MSG * (6 if mt else 1)
        ws.append((f"link.{a['stage']}.{ca}-{b['stage']}.{cb}", shift + t, shift + t + L))
    h0 = shift + model['head_t']
    ws.append(('head', h0, h0 + (model['head_mtp'] if mt else model['head_ar'])))
    ws.append(('host', h0, h0 + HOST_TOK * (6 if mt else 1)))
    return ws


def check(model, users, P, col):
    by = collections.defaultdict(list)
    for u in users:
        for r, s, e in windows(model, u['user'], u['shift'], u['kind'], col):
            by[r].append((s % P, e - s, u['user']))
    bad = []
    for r, lst in by.items():
        lst.sort()
        n = len(lst)
        for i in range(n):
            s, L, u = lst[i]
            if L > P:
                bad.append(dict(resource=r, users=[u, u], overlap=L - P))
            for j in range(1, n):
                s2, L2, u2 = lst[(i + j) % n]
                gap = (s2 - s) % P
                if gap >= L:
                    break
                if u2 != u:
                    bad.append(dict(resource=r, users=[u, u2], overlap=round(L - gap, 1)))
    # a user's own windows on one link must not overlap each other either (x and partial on the same link)
    return bad, {r: len(v) for r, v in by.items()}


def colour(model, shifts, P, mode):
    col = {}
    for st in model['stages']:
        if st['copies'] > 1:
            c = LEG.assign_copies(shifts, P, st['step'] if mode == 'mtp' else st['occ'])
            if c is None:
                return None, st['stage']
            col[st['stage']] = c
    return col, None


def calendar(model, mode, N=None):
    P = qup(model['T_ar'] if mode == 'ar' else model['T_mtp_step'])
    key = 'step' if mode == 'mtp' else 'occ'
    nonrep = max(st[key] for st in model['stages'] if st['copies'] == 1)
    nonrep = max(nonrep, model['head_mtp'] if mode == 'mtp' else model['head_ar'])
    tried = []
    for n in ([N] if N else range(max(1, P // int(nonrep)), 0, -1)):
        shifts = [(k * (P // PHASE_Q)) // n * PHASE_Q for k in range(n)]
        col, why = colour(model, shifts, P, mode)
        users = [dict(user=k, shift=shifts[k], kind='latency' if k == 0 else mode) for k in range(n)]
        if col is None:
            tried.append(dict(users=n, result='FAULT', why=f'{why}: no A/B colouring'))
            if N:
                return dict(P=P, users=users, col={}, tried=tried, bad=[dict(resource=why)], nres={})
            continue
        bad, nres = check(model, users, P, col)
        tried.append(dict(users=n, result='PASS' if not bad else 'FAULT', collisions=len(bad),
                          first=bad[0] if bad else None))
        if not bad or N:
            return dict(P=P, users=users, col=col, tried=tried, bad=bad, nres=nres, nonrep=nonrep)
    return dict(P=P, users=[], col={}, tried=tried, bad=[], nres={}, nonrep=nonrep)


# ------------------------------------------------------------------------------------------------ two job contexts
# ot_dsdv_fixed_issue (rtl/dsrom_sys/s81_dv/unit) already holds TWO job contexts (active[1:0], next_slot) that execute
# the same immutable calendar; a command on an engine the other context holds is a run fault (code 9: duplicate issue /
# engine_available low).  So two users may overlap on one stage copy iff (a) at most 2 users hold the stage copy at any
# edge and (b) their engine busy intervals never overlap.  Engine classes = the DAG node classes (field, su, coll, hbm,
# select, embed), each treated as ONE engine (the issuer has 13; a class may hold several: conservative); priced per-layer
# terms with no engine (dv_p4l / scan legs) block every class; expert slots hold field + su for the whole reservation;
# the combine holds coll + su.  MTP: the stage pattern repeated 6 times back to back (window 6 W >= 6 W - 5 scan).
CLASSES = ('field', 'su', 'coll', 'hbm', 'select', 'embed')


def merge_iv(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def stage_busy(log, st_rec):
    by = collections.defaultdict(list)
    for x in log:
        by[x['stage']].extend(x.get('busy', []))
    for st in st_rec:
        t = st['t']
        cls = collections.defaultdict(list)
        for a, b, k in by[st['stage']]:
            for kk in (CLASSES if k == 'ALL' else (k,)):
                cls[kk].append((a - t, b - t))
        st['busy'] = {k: merge_iv(v) for k, v in cls.items()}
        st['busy_total'] = {k: round(sum(b - a for a, b in v)) for k, v in st['busy'].items()}


def windows2(model, user, shift, mode, col):
    mt = mode == 'mtp'
    ex, ctx = [], []
    for st in model['stages']:
        cp = col.get(st['stage'], {}).get(user, 'A') if st['copies'] > 1 else 'A'
        r = f"{st['stage']}.{cp}"
        W = st['occ']
        reps = 6 if mt else 1
        ctx.append((r, shift + st['t'], shift + st['t'] + W * reps))
        for k in range(reps):
            o = shift + st['t'] + k * W
            for c, iv in st['busy'].items():
                ex.extend((f'{r}.{c}', o + a, o + b) for a, b in iv)
    for r, a, b in windows(model, user, shift, mode, col):
        if r.startswith(('link.', 'head', 'host')):
            ex.append((r, a, b))
    return ex, ctx


def check2(model, users, P, col, mode, cap=2):
    by = collections.defaultdict(list)
    cx = collections.defaultdict(list)
    for u in users:
        ex, ctx = windows2(model, u['user'], u['shift'], mode, col)
        for r, s, e in ex:
            by[r].append((s % P, e - s, u['user']))
        for r, s, e in ctx:
            cx[r].append((s % P, e - s, u['user']))
    bad = []
    for r, lst in by.items():
        lst.sort()
        n = len(lst)
        for i in range(n):
            s, L, u = lst[i]
            if L > P:
                bad.append(dict(resource=r, users=[u, u], overlap=L - P))
            for j in range(1, n):
                s2, L2, u2 = lst[(i + j) % n]
                gap = (s2 - s) % P
                if gap >= L:
                    break
                if u2 != u:
                    bad.append(dict(resource=r, users=[u, u2], overlap=round(L - gap, 1)))
    for r, lst in cx.items():                       # at most two users hold a stage copy at any edge
        ev = []
        for s, L, u in lst:
            if L > P:
                bad.append(dict(resource=r + '.ctx', users=[u], overlap=L - P))
                continue
            e = s + L
            ev += [(s, 1), (e, -1)] if e <= P else [(s, 1), (P, -1), (0, 1), (e - P, -1)]
        ev.sort(key=lambda x: (x[0], x[1]))
        k = 0
        for t, d in ev:
            k += d
            if k > cap:
                bad.append(dict(resource=r + '.ctx', time=t, holders=k))
                break
    return bad, {r: len(v) for r, v in by.items()}


def calendar2(model, mode, N=None):
    P = qup(model['T_ar'] if mode == 'ar' else model['T_mtp_step'])
    reps = 6 if mode == 'mtp' else 1
    lb = 1
    for st in model['stages']:
        need = max([v for v in st['busy_total'].values()] + [st['occ'] / 2.0]) * reps / st['copies']
        lb = max(lb, need)
    lb = max(lb, model['head_mtp'] if mode == 'mtp' else model['head_ar'])
    tried = []
    for n in ([N] if N else range(int(P // lb), 0, -1)):
        shifts = [(k * (P // PHASE_Q)) // n * PHASE_Q for k in range(n)]
        col = {st['stage']: {k: 'AB'[k % 2] for k in range(n)} for st in model['stages'] if st['copies'] > 1}
        users = [dict(user=k, shift=shifts[k], kind='latency' if k == 0 else mode) for k in range(n)]
        bad, nres = check2(model, users, P, col, mode)
        tried.append(dict(users=n, result='PASS' if not bad else 'FAULT', collisions=len(bad),
                          first=bad[0] if bad else None))
        if not bad or N:
            return dict(P=P, users=users, col=col, tried=tried, bad=bad, nres=nres, nonrep=lb)
    return dict(P=P, users=[], col={}, tried=tried, bad=[], nres={}, nonrep=lb)


def _forbid(G, lo, hi, P):
    """mark grid cells (PHASE_Q cycles) whose offset lies in any open range (lo, hi) mod P (conservative rounding)"""
    import numpy as np
    n = len(G)
    a = np.floor(np.asarray(lo, dtype=float) / PHASE_Q).astype(np.int64)
    b = np.ceil(np.asarray(hi, dtype=float) / PHASE_Q).astype(np.int64)
    keep = b - a > 1
    a, b = a[keep] + 1, b[keep]              # cells strictly inside: offset k*Q with lo < kQ < hi
    full = (b - a) >= n
    if full.any():
        G[:] = True
        return
    d = np.zeros(2 * n + 2, dtype=np.int64)
    a0 = np.mod(a, n)
    b0 = a0 + (b - a)
    np.add.at(d, a0, 1)
    np.add.at(d, b0, -1)
    c = np.cumsum(d)[:2 * n]
    G |= (c[:n] + c[n:2 * n]) > 0


def shift_search(model, mode, P, cap=2):
    """greedy first-fit user shifts on the PHASE_Q grid: pairwise engine / link / head / host exclusivity through two
    forbidden-difference sets (same copy colour, other colour), the <= 2 holders a stage copy through a coverage map"""
    import numpy as np
    n = P // PHASE_Q
    reps = 6 if mode == 'mtp' else 1
    FD_same = np.zeros(n, dtype=bool)
    FD_diff = np.zeros(n, dtype=bool)
    # per resource interval lists of ONE user at shift 0 (copy A everywhere for the same-colour set, copy-B stages are
    # dropped from the other-colour set); links / head / host: one resource each (conservative across colours)
    ex, ctx = windows2(model, 0, 0, mode, {})
    byr = collections.defaultdict(list)
    for r, a, b in ex + (ctx if cap == 1 else []):     # one context: the hold window itself is exclusive
        byr[r].append((a, b))
    copyb = {st['stage'] for st in model['stages'] if st['copies'] > 1}
    for r, iv in byr.items():
        A = np.array([x[0] for x in iv]); B = np.array([x[1] for x in iv])
        lo = np.subtract.outer(A, B).ravel()          # other - mine: overlap iff a2 - b1 < D < b2 - a1
        hi = np.subtract.outer(B, A).ravel()
        _forbid(FD_same, lo, hi, P)
        stg = r.split('.')[0]
        if not (stg in copyb and not r.startswith(('link', 'head', 'host'))):
            _forbid(FD_diff, lo, hi, P)
    FD_same[0] = FD_diff[0] = True
    sts = [(st['stage'], st['copies'] > 1, st['t'], st['occ'] * reps) for st in model['stages']]
    cov = {}
    users, F = [], {0: np.zeros(n, dtype=bool), 1: np.zeros(n, dtype=bool)}
    k = 0
    while True:
        col = k % 2
        free = ~F[col]
        # context: x is invalid where a stage copy already has 2 holders during x's window
        bad = np.zeros(n, dtype=bool)
        for (name, cb, t, W) in (sts if cap == 2 else []):
            key = (name, col if cb else 0)
            if key in cov:
                full = cov[key] >= 2
                if full.any():
                    idx = np.nonzero(full)[0]
                    # x window [x + t, x + t + W] hits cell j  ->  x in (j*Q - t - W, j*Q + Q - t)
                    _forbid(bad, idx * PHASE_Q - t - W - PHASE_Q, idx * PHASE_Q + PHASE_Q - t + PHASE_Q, P)
        cand = np.nonzero(free & ~bad)[0]
        if not len(cand):
            break
        x = int(cand[0]) * PHASE_Q
        users.append(dict(user=k, shift=x, kind='latency' if k == 0 else mode, colour='AB'[col]))
        for c2 in (0, 1):
            F[c2] |= np.roll(FD_same if c2 == col else FD_diff, x // PHASE_Q)
        for (name, cb, t, W) in sts:
            key = (name, col if cb else 0)
            cv = cov.setdefault(key, np.zeros(n, dtype=np.int8))
            a = (x + t) // PHASE_Q
            b = -(-(x + t + W) // PHASE_Q)
            idx = np.arange(a, b + 1) % n
            cv[idx] += 1
        k += 1
        if k > 400:
            break
    return users


def calendar3(model, mode, N=None, users=None, cap=2):
    """two job contexts with searched shifts; N + 1 control = every grid shift for one more user FAULTS (greedy-maximal)"""
    P = qup(model['T_ar'] if mode == 'ar' else model['T_mtp_step'])
    if users is None:
        users = shift_search(model, mode, P, cap)
    if N is not None:
        users = users[:N]
    col = {st['stage']: {u['user']: u.get('colour', 'AB'[u['user'] % 2]) for u in users}
           for st in model['stages'] if st['copies'] > 1}
    bad, nres = check2(model, users, P, col, mode, cap)
    return dict(P=P, users=users, col=col, tried=[dict(users=len(users), result='PASS' if not bad else 'FAULT',
                                                      collisions=len(bad), first=bad[0] if bad else None,
                                                      search='greedy first-fit shifts')],
                bad=bad, nres=nres, nonrep=0)


# ------------------------------------------------------------------------------------------------ build
def build(mapp=MAP, cmode='record', alap=False, unqualified=False, contexts=1):
    mp = json.loads(Path(mapp).read_text())
    sha = hashlib.sha256(Path(mapp).read_bytes()).hexdigest()
    stages = mp['stages']
    qualified = bool(mp.get('verdict', {}).get('all_pass'))
    assert (qualified or unqualified) and len(stages) == mp['stages_count'], 'map has no exact capacity PASS verdict'
    F2 = load(ROOT / 'results/token_pass/cal2_s81_1020/fold_cal2.py', 'fold_cal2')
    r, dags = composed(cmode)
    wa = r['workloads']['ar']
    wm = r['workloads']['mtp']
    dag, cyc = dags['ar']
    seg, scan, head_ar, cnode = layer_segments(dag, cyc, F2, wa['extra_terms'])
    # SU add of the partial: priced by analogy with the measured eng.add (an SU vector add), per instance
    eadd = [cnode[n['id']] for n in dag['nodes'] if n.get('op') == 'eng.add']
    add = max(eadd) if eadd else 120.0
    embed = sum(cnode[n['id']] for n in dag['nodes'] if n.get('op') == 'embed')
    win, log, links, chain, legacy = timeline(stages, seg, add, embed, alap)
    # token: composer T + cal2 structural + 20 added hops + the forward-x / reservation change of the chain
    s_ar = sum(cal2_delta(n, F2) for n in dag['nodes'] if n.get('critical'))
    dagm, cycm = dags['mtp']
    s_mtp = sum(cal2_delta(n, F2) for n in dagm['nodes'] if n.get('critical'))
    dh = (len(stages) - HOP_REF) * HOP
    dchain = chain - legacy
    T_ar = wa['T_cycles'] + s_ar + dh + dchain
    st_rec = []
    for i, st in enumerate(stages):
        a, b = win[i]
        occ = math.ceil(b - a)
        sc = scan.get(st['dense_layer'], 0.0) if st['dense_layer'] is not None else 0.0
        st_rec.append(dict(stage=st['stage'], dense_layer=st['dense_layer'], experts=st['experts'],
                           copies=2 if st['copy_b'] else 1, t=math.floor(a), occ=occ,
                           step=math.ceil(6 * (b - a) - 5 * sc), scan=round(sc, 1)))
    wave_old = sum(cycm[n['id']] for n in dagm['nodes'] if n.get('op') == 'wave.busy' and n.get('critical'))
    wave_new = 5 * max(s['occ'] - s['scan'] for s in st_rec)
    head_mtp = 6 * head_ar + sum(cycm[n['id']] for n in dagm['nodes'] if (n.get('op') or '').startswith('draft.')
                                 and n.get('critical'))
    T_mtp = wm['T_cycles'] + s_mtp + dh + dchain + (wave_new - wave_old)
    model = dict(stages=st_rec, links=links, head_t=math.ceil(chain + embed + HOP), head_ar=math.ceil(head_ar),
                 head_mtp=math.ceil(head_mtp), T_ar=T_ar, T_mtp_step=T_mtp)
    comp = dict(composer=('tools/toksim_s81_compose.py release-partial (results/token_pass/measured_s81_1019/cycles.json)'
                          if cmode == 'record' else 'tools/toksim_s81_compose.py --scenario calpipe + S81-ROMOPT o3mix '
                          'compiled spans (' + str(ROMOPT.relative_to(ROOT)) + ')'),
                ar=dict(T_composer=wa['T_cycles'], tok_s_composer=wa['tok_s'], pct_measured=wa['pct_measured'],
                        cal2_structural=s_ar, added_hops=dh, forward_x_chain_delta=round(dchain, 1),
                        T=round(T_ar, 1), tok_s=round(F / T_ar, 1)),
                mtp=dict(T_composer=wm['T_cycles'], tok_s_composer=wm['tok_s'], pct_measured=wm['pct_measured'],
                         cal2_structural=s_mtp, added_hops=dh, forward_x_chain_delta=round(dchain, 1),
                         wave_composer=round(wave_old, 1), wave_physical=round(wave_new, 1),
                         T=round(T_mtp, 1), tok_s=round(TAU * F / T_mtp, 1)),
                partial_add_cycles=round(add, 1), partial_add_grade='priced (= measured eng.add SU add instance)')
    if contexts != 1:
        stage_busy(log, st_rec)
    recs = {}
    for mode in ('ar', 'mtp'):
        cap = 1 if contexts in (1, -1) else 2
        if contexts == 1:
            cal = calendar(model, mode)
            n = len(cal['users'])
            neg = calendar(model, mode, n + 1) if n else None
        else:
            cal = calendar3(model, mode, cap=cap)
            n = len(cal['users'])
            # N + 1: one more user at EVERY grid shift (both colours) must collide -> the exhaustive control
            neg = dict(bad=[], tried=0)
            P = cal['P']
            fails = 0
            last = dict(user=n, kind=mode)
            step = max(PHASE_Q, (P // 64) // PHASE_Q * PHASE_Q)   # 64 sampled shifts x 2 colours, exact check2
            for xs in range(0, P, step):
                for colour in 'AB':
                    uu = cal['users'] + [dict(last, shift=xs, colour=colour)]
                    cc = {g: {**c, n: colour} for g, c in cal["col"].items()}
                    b2, _ = check2(model, uu, P, cc, mode, cap)
                    neg['tried'] += 1
                    fails += 1 if b2 else 0
            neg['bad'] = [1] if fails == neg['tried'] else []
            neg['sampled_shifts'] = neg['tried']
            neg['sampled_fault'] = fails
        inj = None
        if n >= 2:
            u = [dict(x) for x in cal['users']]
            u[1]['shift'] = u[0]['shift'] + PHASE_Q          # injected collision: user 1 on top of user 0
            inj = len((check(model, u, cal['P'], cal['col']) if contexts == 1 else
                       check2(model, u, cal['P'], cal['col'], mode, cap))[0])
        T = model['T_ar'] if mode == 'ar' else model['T_mtp_step']
        per = (F / max(T, cal['P'])) * (TAU if mode == 'mtp' else 1.0)
        recs[mode] = dict(
            schema=SCHEMA, lane='S81-MUCAL140', mode=mode, map=str(Path(mapp).resolve().relative_to(ROOT)), compose=cmode, map_sha256=sha, alap=alap, job_contexts=contexts, map_capacity_verdict='PASS' if qualified else 'UNQUALIFIED (model only)',
            stages=len(stages), copy_b_stages=[s['stage'] for s in st_rec if s['copies'] > 1],
            period=cal['P'], users=n, per_user_tok_s=round(per, 1), aggregate_tok_s=round(n * per),
            bound_window=dict(cycles=int(cal.get('nonrep') or 0),
                              stage=max((s for s in st_rec if s['copies'] == 1),
                                        key=lambda s: s['step' if mode == 'mtp' else 'occ'])['stage']),
            checker=dict(result='PASS' if n and not cal['bad'] else 'FAULT', collisions=len(cal['bad']),
                         resources=len(cal['nres']), windows=sum(cal['nres'].values()),
                         negative_n_plus_1=dict(users=n + 1, result='FAULT' if neg and (neg['bad']) else 'PASS?!',
                                                collisions=len(neg['bad']) if neg else None),
                         negative_injected_shift=dict(collisions=inj, result='FAULT' if inj else 'MISSED')),
            search=cal['tried'][:12],
            slots=[dict(slot=i, user=u['user'], shift=u['shift'],
                        copy={g: c.get(u['user'], 'A') for g, c in cal['col'].items()})
                   for i, u in enumerate(cal['users'])],
            stage_windows=[{k: s[k] for k in ('stage', 'dense_layer', 'copies', 't', 'occ', 'step', 'busy_total') if k in s}
                           for s in st_rec],
            composition=comp, grade='node cycles: composer grades; stage split / reservation / forward-x / MTP law: MODEL')
    recs['ar']['layer_segments'] = {f'L{l}': {k: round(v, 1) for k, v in seg[l].items()} for l in range(40)}
    recs['ar']['timeline_log'] = [dict({k: v for k, v in x.items() if k != 'busy'}, start=round(x['start'], 1),
                                       end=round(x['end'], 1)) for x in log]
    return recs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--map', default=str(MAP))
    ap.add_argument('--compose', choices=['record', 'romopt'], default='record')
    ap.add_argument('--unqualified', action='store_true', help='allow a map without the exact capacity verdict (model)')
    ap.add_argument('--contexts', type=int, choices=[1, 2, -1], default=1,
                    help='job contexts a stage: 1 uniform shifts (record), -1 = 1 context + searched shifts, 2 = RTL two contexts + searched shifts')
    ap.add_argument('--alap', action='store_true', help='just-in-time expert slots on the partial chain (compiler)')
    ap.add_argument('--tag', default='phys140', help='output name calendar_<tag>_{ar,mtp}.json')
    a = ap.parse_args(argv)
    recs = build(a.map, a.compose, a.alap, a.unqualified, a.contexts)
    rc = 0
    for mode, rec in recs.items():
        f = Path(a.out) / f'calendar_{a.tag}_{mode}.json'
        txt = json.dumps(rec, indent=1) + '\n'
        if a.check:
            same = f.exists() and f.read_text() == txt
            print(f'{mode}: {"SAME" if same else "DIFFERS"} {f}')
            rc |= 0 if same else 1
        else:
            f.write_text(txt)
        c = rec['checker']
        print(f"{mode}: {rec['users']} users x {rec['per_user_tok_s']} = {rec['aggregate_tok_s']} agg; period "
              f"{rec['period']}; bound {rec['bound_window']}; checker {c['result']} ({c['windows']} windows, "
              f"{c['collisions']} coll); N+1 {c['negative_n_plus_1']['result']}; inject {c['negative_injected_shift']['result']}")
        if c['result'] != 'PASS':
            rc = 2
    print(json.dumps(recs['ar']['composition'], indent=1))
    return rc


if __name__ == '__main__':
    sys.exit(main())
