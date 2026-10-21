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
def composed():
    """run the composer of record, capture its per-node cycles (the dict it passes to solve) for both workloads"""
    C = load(ROOT / 'tools/toksim_s81_compose.py', 'toksim_s81_compose')
    cap = {}
    orig = C.solve

    def spy(dag, cyc):
        cap[dag['nodes'][0]['id'] + str(len(dag['nodes']))] = (dag, dict(cyc))
        return orig(dag, cyc)
    C.solve = spy
    r = C.build(C.OUT / 'elements')
    C.solve = orig
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


def layer_segments(dag, cyc, F2, extra):
    """per layer: A / D / E / C spans (longest path of each segment's sub-DAG) + the idx.score scan cycles"""
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
    scan = collections.Counter()
    for n in dag['nodes']:
        if isinstance(n.get('layer'), int) and n['id'].endswith('attn.idx.score') and not n['id'].startswith('V.'):
            scan[n['layer']] = max(scan[n['layer']], c[n['id']])
    for t in extra:                                   # priced per-layer terms (p4l DV deltas) -> the dense segment
        if t['kind'] == 'layer' and t['slot'].startswith('L'):
            L = int(t['slot'][1:].split('.')[0])
            if L in out:
                out[L]['A'] += t['cycles']
    head = sum(c[i] for i, n in nodes.items() if (n.get('op') or '').startswith('head.') and n.get('critical'))
    return out, dict(scan), head, c


# ------------------------------------------------------------------------------------------------ single-user timeline
def stage_items(st):
    d = st['dense_layer']
    tail = [('X', l, b - a + 1) for l, a, b in st['experts'] if d is None or l < d]
    head = [('X', l, b - a + 1) for l, a, b in st['experts'] if d is not None and l >= d]
    return tail + ([('D', d, None)] if d is not None else []) + head


def timeline(stages, seg, add, embed_end=0.0):
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
                log.append(dict(stage=st['stage'], item=f'dense L{l}', start=s0, end=e0))
            else:
                R = seg[l]['E'] * min(6, N) / 6.0
                s0 = max(cur or 0.0, x_arr[l])
                e = s0 + R
                pin = p_arr.get(l)
                po = (max(e, pin) + add) if pin is not None else e
                part_out[l] = po
                e0 = po
                if last_stage.get(l) == i:
                    comb[l] = po + seg[l]['C']
                    e0 = comb[l]
                log.append(dict(stage=st['stage'], item=f'experts L{l} x{N} (slots {min(6, N)})', start=s0, end=e0))
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


# ------------------------------------------------------------------------------------------------ build
def build():
    mp = json.loads(MAP.read_text())
    sha = hashlib.sha256(MAP.read_bytes()).hexdigest()
    stages = mp['stages']
    assert mp['verdict']['all_pass'] and len(stages) == mp['stages_count']
    F2 = load(ROOT / 'results/token_pass/cal2_s81_1020/fold_cal2.py', 'fold_cal2')
    r, dags = composed()
    wa = r['workloads']['ar']
    wm = r['workloads']['mtp']
    dag, cyc = dags['ar']
    seg, scan, head_ar, cnode = layer_segments(dag, cyc, F2, wa['extra_terms'])
    # SU add of the partial: priced by analogy with the measured eng.add (an SU vector add), per instance
    eadd = [cnode[n['id']] for n in dag['nodes'] if n.get('op') == 'eng.add']
    add = max(eadd) if eadd else 120.0
    embed = sum(cnode[n['id']] for n in dag['nodes'] if n.get('op') == 'embed')
    win, log, links, chain, legacy = timeline(stages, seg, add, embed)
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
    comp = dict(composer='tools/toksim_s81_compose.py release-partial (results/token_pass/measured_s81_1019/cycles.json)',
                ar=dict(T_composer=wa['T_cycles'], tok_s_composer=wa['tok_s'], pct_measured=wa['pct_measured'],
                        cal2_structural=s_ar, added_hops=dh, forward_x_chain_delta=round(dchain, 1),
                        T=round(T_ar, 1), tok_s=round(F / T_ar, 1)),
                mtp=dict(T_composer=wm['T_cycles'], tok_s_composer=wm['tok_s'], pct_measured=wm['pct_measured'],
                         cal2_structural=s_mtp, added_hops=dh, forward_x_chain_delta=round(dchain, 1),
                         wave_composer=round(wave_old, 1), wave_physical=round(wave_new, 1),
                         T=round(T_mtp, 1), tok_s=round(TAU * F / T_mtp, 1)),
                partial_add_cycles=round(add, 1), partial_add_grade='priced (= measured eng.add SU add instance)')
    recs = {}
    for mode in ('ar', 'mtp'):
        cal = calendar(model, mode)
        n = len(cal['users'])
        neg = calendar(model, mode, n + 1) if n else None
        inj = None
        if n >= 2:
            u = [dict(x) for x in cal['users']]
            u[1]['shift'] = u[0]['shift'] + PHASE_Q          # injected collision: user 1 on top of user 0
            inj = len(check(model, u, cal['P'], cal['col'])[0])
        T = model['T_ar'] if mode == 'ar' else model['T_mtp_step']
        per = (F / max(T, cal['P'])) * (TAU if mode == 'mtp' else 1.0)
        recs[mode] = dict(
            schema=SCHEMA, lane='S81-MUCAL140', mode=mode, map=str(MAP.relative_to(ROOT)), map_sha256=sha,
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
            stage_windows=[{k: s[k] for k in ('stage', 'dense_layer', 'copies', 't', 'occ', 'step')} for s in st_rec],
            composition=comp, grade='node cycles: composer grades; stage split / reservation / forward-x / MTP law: MODEL')
    recs['ar']['layer_segments'] = {f'L{l}': {k: round(v, 1) for k, v in seg[l].items()} for l in range(40)}
    recs['ar']['timeline_log'] = [dict(x, start=round(x['start'], 1), end=round(x['end'], 1)) for x in log]
    return recs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    recs = build()
    rc = 0
    for mode, rec in recs.items():
        f = Path(a.out) / f'calendar_phys140_{mode}.json'
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
