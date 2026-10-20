#!/usr/bin/env python3
"""MU-S81 (10-18, owner MU.DECIDE option A): the S81 multi-user STATIC calendar compiler.

Owner configuration (HANDOFF 0is/0ir): B3 index sharding + MTP read sharing, and the 8 index-attention stage groups
S029 S020 S011 S002 S034 S040 S046 S052 duplicated (copy A / copy B) = 520 dies + 520 HBM stacks.

What it emits (one JSON record per mode, results/arch/mu_s81_1018/calendar_<mode>.json):
  slots        the N-slot calendar: slot k = user k, shift delta_k, kind (latency / ar / mtp / filler)
  copies       per duplicated group, the copy (A / B) every user uses; the latency user (user 0) is always on copy A
  tables       per stage group, per slot: {user, pos0, pos_stride, copy, local index on the copy, HBM bases}
               (pos of user k at pass p = pos0_k + p * pos_stride; bases = the per-user region bases the compiler
               writes into the svc job words: WB window ring, SB compressed rows, IKB index keys)
  lemma        the shift-lemma assertion, by construction AND by brute force:
                 (1) every window of a non-replicated resource <= its slot spacing (the lemma's premise);
                 (2) every pair of users on every resource (stage group copy, stage-hop link, host plane), windows
                     expanded modulo the period: no overlap.  A collision is a COMPILE FAULT (never a stall, owner
                     rule: static schedule, no credit / back-pressure);
                 (3) the latency user's windows are exactly the single-user schedule (shift 0, copy A everywhere).
The stage model (per-position occupancy, span, MTP step occupancy) is the S81-BALANCE model of record
(results/arch/s81_balance_1018/compute.py: 10-09 stage classes x K to the 10-18 composition + SCANCHK 1 stack/die),
imported, not re-derived.  Grade of every number here: modelled (the calendar is exact arithmetic on modelled windows;
the multi-user bench MU.TOK measures it on RTL).

  dv_mu_calendar.py --mode ar  [--users N] [--out DIR]       # N omitted = the largest N that passes the lemma
  dv_mu_calendar.py --mode mtp [--users N] [--fillers F] [--out DIR]
  dv_mu_calendar.py --check                                    # recompute and compare with the committed records
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BAL = ROOT / 'results/arch/s81_balance_1018/compute.py'
OUT = ROOT / 'results/arch/mu_s81_1018'
SCHEMA = 'opentallas.s81_dv.mu_calendar.v1'
DUP = ('S029', 'S020', 'S011', 'S002', 'S034', 'S040', 'S046', 'S052')   # owner config (coordinator 0ir)
# the layer whose attention / index state each duplicated group owns (configs/models/candidates/deepseek-v4.1-flash.json
# kv_source_layer_ids [2, 8, 14, 20], index_source_layer_ids [2, 8, 14, 20, 24, 28, 32, 36]; brief 0is)
DUP_LAYER = dict(S002=2, S011=8, S020=14, S029=20, S034=24, S040=28, S046=32, S052=36)
H_MSG = 652            # stage h message serialisation on the stage-hop link, cycles (ROM-MULTIUSER (3) "link serialisation")
HOST_TOK = 134         # host plane cycles a token a user (133.5, ROM-MULTIUSER item 6), rounded up
COPIES = ('A', 'B')
# MU-S81/TOK 10-19: the start-phase quantum of ot_dsdv_fixed_issue (dsdv_seq_host u_iss): a job is accepted only on the
# edge where the free-running 2-bit phase_q + 1 == the sealed start_phase (else fault code 5), so on every die user k's
# start must sit a multiple of 4 edges after user 0's: every shift AND the period (pass p + 1 = pass p + P) must be
# multiples of PHASE_Q.  --phase-q 4 (DEFAULT, the record calendar_<mode>.json; calendar_<mode>_q4.json = TOK's bench copy, same content)
# --phase-q 1 = the original 1-cycle grid (calendar_<mode>_q1.json, NOT issuer-feasible: fault 5).  Witness: results/rtl/s81_mu_1018 (raw shift 21313 ->
# fault 5).
PHASE_Q = 4            # MU-S81 10-19: the issuer-feasible grid is the record (calendar_<mode>.json)


def qup(x):
    return -(-x // PHASE_Q) * PHASE_Q
D_CTX = 1048576
# per-user HBM regions (modelled default until results/arch/mu_s81_1018/svc_bases.json (lane MU-S81/SVC) exists):
#   KV window ring: dsdv_svc_att WB + 68 u sectors (built: 64 code sectors + 4 scale sectors a user, 128-slot ring)
#   compressed rows (owner layers): D_CTX / ratio rows, 9 sectors a 16-row block, spread over the 16 slices x 2 PCs of
#     the die and the 4 dies of the TP4 stage (svc_att header: block g >> 8 on PC g[8] at SB + 9 (g >> 9))
#   index keys: 68 B a key (FP4 128-d + E8M0 / 32), sharded over the layer's dies (B2: 10 full-scan / 8 reindex)
SECTOR_B = 32
DEFAULT_BASES = dict(wb_sectors_per_user=68,
                     note='modelled default (svc_att header); replaced by svc_bases.json when lane MU-S81/SVC commits it')


def load_model():
    spec = importlib.util.spec_from_file_location('s81_balance', BAL)
    m = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(m)     # deterministic; rewrites its own summary.json byte-identically
    return m


# ------------------------------------------------------------------------------------------------ L20 split (0li)
# S81-L20SPLIT (coordinator 0li, 10-19): the L20 index window (group S029) is split over 2x the dies: its keys sit on
# the HBM stacks of S029's own 10 dies + 10 dies of the neighbouring non-scan group S030 (shard 20, no new silicon).
# The S029 scan term is the MEASURED reader law (dsdv_idx_rg P = 3, S81-IDXRD sweep_1019: cycles = 3 N / 16 + 511) on
# the per-die keys.  The helper dies' HBM / svc time is a NEW resource window per user on S030's svc (index reader +
# bk_sel): it must not collide with any other user's helper window, nor with S030's own svc windows (its own HBM +
# select, placed by the compiler at an offset inside S030's stage window: the check returns the feasible offsets).
# Copies: both S029 copies use the same S030 dies (S030 is not duplicated).  Links: the query goes out on the S029 ->
# S030 stage link (Q_WORDS edges), the helper top-512 comes back on the S030 -> S029 return link (2 beats a word).
SPLIT_L20 = dict(group='S029', helper='S030', shard=20, helper_dies=10,
                 reader_p=3, reader_t0=511, select_tail=286, q_words=64, topk_words=36)


def reader_cycles(n, sp=SPLIT_L20):
    return math.ceil(sp['reader_p'] * n / 16 + sp['reader_t0'])


def apply_split(m, sp=SPLIT_L20):
    """patch the stage model in place: S029 keys over sp['shard'] dies, its scan term = the measured reader law"""
    m.sh_all = dict(m.sh_all, **{sp['group']: sp['shard']})
    orig = m.group_occ
    BPC = m.BPC_STACK

    def occ(g, shard=4, stacks_per_die=1, **kw):
        if g['id'] != sp['group'] or g['idx_score_cycles'] <= 0:
            return orig(g, shard=shard, stacks_per_die=stacks_per_die, **kw)
        keys_die = m.SCAN_BYTES[g['idx_score_cycles']] / m.IDX_B / (shard * stacks_per_die)
        meas = reader_cycles(keys_die, sp) / m.K           # group_occ multiplies its classes by K
        m.BPC_STACK = m.SCAN_BYTES[g['idx_score_cycles']] / (shard * stacks_per_die * meas)
        try:
            return orig(g, shard=shard, stacks_per_die=stacks_per_die, **kw)
        finally:
            m.BPC_STACK = BPC
    m.group_occ = occ
    m.split_l20 = sp
    return m


def helper_windows(m, st, sp=SPLIT_L20):
    """per-user window lengths on the helper die's svc (AR / MTP step) and on the links, + the helper's own svc use"""
    g = next(x for x in m.groups if x['id'] == sp['group'])
    h = next(x for x in m.groups if x['id'] == sp['helper'])
    idx = g['idx_score_cycles']
    keys_die = math.ceil(m.D_CTX / sp['shard']) if idx == 5937.0 else m.SCAN_BYTES[idx] / m.IDX_B / sp['shard']
    scan = reader_cycles(keys_die, sp)
    score = idx * 4.0 / sp['shard'] * m.K
    sel_local = g['by_class'].get('select', 0.0) * m.SELECT_LOCAL * 4.0 / sp['shard'] * m.K
    own = (h['by_class'].get('hbm', 0.0) + h['by_class'].get('select', 0.0)) * m.K
    sg = {x['id']: x for x in st}
    ar = math.ceil(max(scan, score) + sel_local + sp['select_tail'])
    mtp = math.ceil(max(scan, 6 * score) + 6 * sel_local + 6 * sp['select_tail'])
    # a compiled helper occupancy (S81-L20SPLIT split.json: the rank-tree bk_sel jobs on RTL) overrides the model when
    # it is longer: the helper die's svc + bk_sel are held from the query's arrival to its last egress word
    ar = max(ar, sp.get('helper_window_ar') or 0)
    mtp = max(mtp, sp.get('helper_window_mtp') or 0)
    return dict(keys_die=keys_die, scan=scan, score=round(score, 1), sel_local=round(sel_local, 1), ar=ar, mtp=mtp,
                own_ar=math.ceil(own), own_mtp=math.ceil(6 * own),
                q_at=math.ceil(m.HOP), helper_occ=sg[sp['helper']]['occ'], helper_step=sg[sp['helper']]['step'],
                t_group=sg[sp['group']]['t'], t_helper=sg[sp['helper']]['t'], link_q=sp['q_words'],
                link_topk=2 * sp['topk_words'])


def _bad_offsets(starts_own, starts_help, Lo, Lh, P):
    """o-space (mod P) intervals where an own window [so + o, + Lo) overlaps a helper window [sh, + Lh)"""
    out = []
    for so in starts_own:
        for sh in starts_help:
            a = (sh - so - Lo + 1) % P                         # o in [a, a + Lo + Lh - 1) collides
            out.append((a, Lo + Lh - 1))
    return out


def split_check(m, st, users, P, col, mode, sp=SPLIT_L20):
    """the helper-die HBM time in the calendar: (1) helper windows of all users never overlap each other; (2) the
    feasible offsets for the helper's own svc window inside its stage window; (3) query / top-k link windows"""
    hw = helper_windows(m, st, sp)
    Lh = hw['ar'] if mode == 'ar' else hw['mtp']
    Lo = hw['own_ar'] if mode == 'ar' else hw['own_mtp']
    span_h = hw['helper_occ'] if mode == 'ar' else hw['helper_step']
    hs, own_s, links = [], [], []
    for u in users:
        s0 = u['shift'] + hw['t_group'] + hw['q_at']
        hs.append((s0, u['user']))
        own_s.append(u['shift'] + hw['t_helper'])
        cp = col.get(sp['group'], {}).get(u['user'], 'A')
        links.append((f"link.{sp['group']}.{cp}.q", u['shift'] + hw['t_group'], hw['link_q']))
        links.append((f"rlink.{sp['helper']}.{sp['group']}.{cp}", s0 + Lh, hw['link_topk']))
    # (1) helper vs helper
    bad = []
    lst = sorted((s % P, u) for s, u in hs)
    for i in range(len(lst)):
        s, u = lst[i]
        s2, u2 = lst[(i + 1) % len(lst)]
        gap = (s2 - s) % P or (P if len(lst) == 1 else 0)
        if len(lst) > 1 and gap < Lh:
            bad.append(dict(resource=f"svc.{sp['helper']}.scan", users=[u, u2], overlap=Lh - gap))
    # (3) link windows (q on the S029 -> S030 link next to the stage message; top-k on the return link)
    base_links = {}
    for u in users:
        for r, a, e in windows(st, u['user'], u['shift'], u['kind'], col):
            if r.startswith('link.'):
                base_links.setdefault(r, []).append((a, e - a))
    by = {}
    for r, a, L in links:
        key = r[:-2] if r.endswith('.q') else r
        by.setdefault(key, []).append((a, L))
    for r, lst2 in by.items():
        allw = sorted(((a % P, L) for a, L in lst2 + base_links.get(r, [])))
        for i in range(len(allw)):
            a, L = allw[i]
            a2, _ = allw[(i + 1) % len(allw)]
            if len(allw) > 1 and (a2 - a) % P < L:
                bad.append(dict(resource=r, overlap=L - (a2 - a) % P))
    # (2) own-window offsets
    iv = _bad_offsets(own_s, [s for s, _ in hs], Lo, Lh, P)
    hi = max(0, span_h - Lo)
    free, o = [], 0
    marks = sorted(iv)
    # sweep [0, hi] for the first feasible offset and the feasible measure (exact on the integer grid of interval ends)
    pts = sorted({0, hi} | {a % P for a, _ in marks if 0 <= a % P <= hi} | {(a + L) % P for a, L in marks
                                                                               if 0 <= (a + L) % P <= hi})

    def blocked(x):
        return any((x - a) % P < L for a, L in marks)
    feas = [x for x in pts if not blocked(x)]
    return dict(helper=sp['helper'], group=sp['group'], shard=sp['shard'], keys_die=round(hw['keys_die']),
                helper_window=Lh, helper_own_window=Lo, helper_stage_window=span_h, period=P, users=len(users),
                helper_busy_pct=round(100 * (len(users) * (Lh + Lo)) / P, 1), windows=hw,
                collisions=bad[:20], n_collisions=len(bad),
                own_offset_first_feasible=feas[0] if feas else None, own_offset_any=not any(blocked(x) for x in pts),
                own_offset_feasible_points=len(feas),
                result='PASS' if not bad and feas else 'FAULT',
                note='own_offset: the compiler places the helper stage\'s own svc/HBM window (Lo) at an offset inside '
                     'its stage window; PASS needs one feasible offset (first_feasible), any = every offset is free')


SPLIT_JSON = ROOT / 'results/arch/s81_l20_1019/split/split.json'


def split_config():
    """SPLIT_L20 + the COMPILED helper windows (split.json mu_helper_windows, the rank-tree bk_sel occupancy on RTL)"""
    sp = dict(SPLIT_L20)
    if SPLIT_JSON.exists():
        w = json.loads(SPLIT_JSON.read_text()).get('mu_helper_windows') or {}
        sp.update(helper_window_ar=w.get('ar'), helper_window_mtp=w.get('mtp'),
                  helper_window_source=f"{SPLIT_JSON.relative_to(ROOT)} mu_helper_windows: {w.get('source')}")
    return sp


def stage_windows(m):
    """per stage group: span (single-user, cycles), occ (one position held, 1 job context), step (one MTP step,
    6 verify positions with the shared index read), start offset t in the reference pass, copies"""
    out, t = [], 0
    for g in m.groups:
        o = m.group_occ(g, shard=m.sh_all.get(g['id'], 4), mtp_share=True, expert_imb=m.IMB_BAL)
        # integer cycles (a calendar is integer): windows rounded UP, offsets accumulate rounded-up spans + hop
        span, occ, step = (math.ceil(o[k]) for k in ('span', 'occ', 'step'))
        out.append(dict(id=g['id'], label=g['label'], t=t, span=span, occ=occ, step=step,
                        copies=2 if g['id'] in DUP else 1, idx=g['idx_score_cycles'] > 0))
        t += span + math.ceil(m.HOP)
    return out


def design(m):
    d = m.s81_design('MU-S81 owner config: B3 + 8 duplicated index-attention groups', shard=m.sh_all,
                     expert_imb=m.IMB_BAL, mtp_share=True, repl={g: 2 for g in DUP})
    return d


# ------------------------------------------------------------------------------------------------ copy assignment
def assign_copies(shifts, P, win, latency=0):
    """2-colour the users of one duplicated group so that, on each copy, every circular gap between consecutive users
    is >= the window.  shifts sorted ascending; returns {user: 'A'|'B'} or None if no colouring exists."""
    n = len(shifts)
    order = sorted(range(n), key=lambda k: shifts[k])
    # alternate along the circle starting at the latency user on A; an odd cycle forces one same-copy adjacency,
    # placed where the elementary gap is largest (it must then be >= win)
    pos = order.index(latency)
    seq = order[pos:] + order[:pos]
    col = {u: COPIES[i % 2] for i, u in enumerate(seq)}
    if n % 2 == 1:
        # the adjacency (seq[-1] -> seq[0] around the wrap) is A -> A; try every rotation point for the clash
        best = None
        for j in range(1, n + 1):
            c = {}
            for i, u in enumerate(seq):
                c[u] = COPIES[i % 2] if i < j else COPIES[(i + 1) % 2]
            if c[latency] != 'A':
                continue
            if copy_ok(shifts, P, win, c):
                best = c
                break
        return best
    return col if copy_ok(shifts, P, win, col) else None


def copy_ok(shifts, P, win, col):
    for cp in COPIES:
        us = sorted((shifts[u] for u in col if col[u] == cp))
        for i, s in enumerate(us):
            nxt = us[(i + 1) % len(us)] + (P if i + 1 == len(us) else 0)
            if len(us) > 1 and nxt - s < win:
                return False
            if len(us) == 1 and P < win:
                return False
    return True


# ------------------------------------------------------------------------------------------------ brute-force lemma
def windows(st, user, shift, kind, col):
    """every resource window of one user in one period: (resource, start, end)"""
    ws = []
    for g in st:
        L = g['occ'] if kind in ('ar', 'latency', 'filler') else g['step']
        cp = col.get(g['id'], {}).get(user, 'A') if g['copies'] > 1 else 'A'
        s = shift + g['t']
        ws.append((f"{g['id']}.{cp}", s, s + L))
        ws.append((f"link.{g['id']}.{cp}", s + g['span'], s + g['span'] + H_MSG * (6 if kind == 'mtp' else 1)))
    end = shift + st[-1]['t'] + st[-1]['span']
    ws.append(('host', end, end + HOST_TOK * (6 if kind == 'mtp' else 1)))
    return ws


def collisions(st, users, P, col):
    by_res = {}
    for u in users:
        for r, s, e in windows(st, u['user'], u['shift'], u['kind'], col):
            by_res.setdefault(r, []).append((s % P, e - s, u['user']))
    bad = []
    for r, lst in by_res.items():
        lst.sort()
        n = len(lst)
        for i in range(n):
            s, L, u = lst[i]
            for j in range(1, n):
                s2, L2, u2 = lst[(i + j) % n]
                gap = (s2 - s) % P
                if gap >= L:
                    break
                bad.append(dict(resource=r, users=[u, u2], overlap=round(L - gap, 1)))
    return bad, {r: len(v) for r, v in by_res.items()}


# ------------------------------------------------------------------------------------------------ calendars
def calendar_ar(m, st, d, N=None):
    P = qup(math.ceil(d['T_ar']))
    S_nr = max(g['occ'] for g in st if g['copies'] == 1)
    dup_w = {g['id']: g['occ'] for g in st if g['copies'] > 1}
    nmax = math.floor(P / S_nr)
    tried = []
    for n in ([N] if N else range(nmax, 0, -1)):
        S = P / n                         # uniform spacing over the period (>= S_nr when n <= nmax)
        shifts = [(k * (P // PHASE_Q)) // n * PHASE_Q for k in range(n)]   # integer shifts on the phase grid; every
        # gap is floor(S) or ceil(S) on that grid
        col, why = {}, None
        if min(b - a for a, b in zip(shifts, shifts[1:] + [P])) < S_nr:
            why = f'slot {S:.1f} < non-replicated window {S_nr:.1f}'
        else:
            for gid, w in dup_w.items():
                c = assign_copies(shifts, P, w)
                if c is None:
                    why = f'{gid}: no A/B colouring with per-copy gap >= {w:.1f} (odd N needs one same-copy ' \
                          f'adjacency of {S:.1f} < {w:.1f})'
                    break
                col[gid] = c
        tried.append(dict(users=n, slot=round(S, 1), result='PASS' if why is None else 'FAIL', why=why))
        if why is None:
            users = [dict(user=k, shift=shifts[k], kind='latency' if k == 0 else 'ar') for k in range(n)]
            return dict(P=P, S=S, S_nonrep=S_nr, users=users, col=col, tried=tried, n_model=d['users_ar'])
    return dict(P=P, S=None, users=[], col={}, tried=tried, n_model=d['users_ar'])


def calendar_mtp(m, st, d, N=None, F=None):
    P = qup(math.ceil(d['T_mtp']))
    Sm = qup(max(g['step'] for g in st if g['copies'] == 1))
    dup_w = {g['id']: g['step'] for g in st if g['copies'] > 1}
    n = N or math.floor(P / Sm)
    shifts = [k * Sm for k in range(n)]
    col = {}
    for gid, w in dup_w.items():
        c = assign_copies(shifts, P, w)
        if c is None:
            return dict(P=P, S=Sm, users=[], col={}, why=f'{gid} no colouring', n_model=d['users_mtp'])
        col[gid] = c
    users = [dict(user=k, shift=shifts[k], kind='latency' if k == 0 else 'mtp') for k in range(n)]
    # AR fillers in the gap after the last MTP slot: greedy, each placed at the earliest shift (1-cycle grid of the
    # non-replicated AR window) where it collides with nothing on any copy (it may take either copy)
    S_ar = qup(math.ceil(max(g['occ'] for g in st if g['copies'] == 1)))
    fills, k = [], n
    t = n * Sm
    limit = F if F is not None else 64
    while len(fills) < limit and t + S_ar <= P + 1e-6:
        ok = dict(col)
        base = users + fills + [dict(user=k, shift=t, kind='filler')]
        for gid in col:                       # each duplicated group picks a free copy for the filler
            for cp in COPIES:
                trial = dict(ok, **{gid: {**ok[gid], k: cp}})
                bad, _ = collisions(st, base, P, trial)
                if not any(b['resource'].split('.')[-2:-1] == [gid] or b['resource'].startswith(gid + '.')
                           for b in bad):
                    ok = trial
                    break
            else:
                ok = None
                break
        if ok is not None and collisions(st, base, P, ok)[0]:
            ok = None
        if ok:
            col = ok
            fills.append(dict(user=k, shift=t, kind='filler'))
            k += 1
            t += S_ar
        else:
            t += 256
    return dict(P=P, S=Sm, S_ar=S_ar, users=users + fills, col=col, fillers=len(fills), n_model=d['users_mtp'],
                fillers_model=d['fillers'])


def bases(st, users, col, svc=None):
    """per stage group, per user: local index on its copy and the HBM region bases (sector units)"""
    sb = dict(DEFAULT_BASES)
    if svc:
        sb.update(svc)
    tabs = {}
    for g in st:
        cp_of = col.get(g['id'], {})
        loc, rows = {c: 0 for c in COPIES}, []
        for u in sorted(users, key=lambda x: x['shift']):
            cp = cp_of.get(u['user'], 'A') if g['copies'] > 1 else 'A'
            li = loc[cp]
            loc[cp] += 1
            r = dict(user=u['user'], kind=u['kind'], copy=cp, local=li, start=round(u['shift'] + g['t'], 1),
                     wb=li * sb['wb_sectors_per_user'])
            if 'sb_sectors_per_user' in sb:
                r['sb'] = li * sb['sb_sectors_per_user']
            if 'ikb_sectors_per_user' in sb and g['idx']:
                r['ikb'] = li * sb['ikb_sectors_per_user']
            rows.append(r)
        tabs[g['id']] = dict(label=g['label'], copies=g['copies'], users_per_copy=loc, rows=rows)
    return tabs, sb


def record(mode, m, st, d, cal, svc=None):
    users = cal['users']
    bad, nres = collisions(st, users, cal['P'], cal['col'])
    tabs, sb = bases(st, users, cal['col'], svc)
    lat_ok = all(c.get(0, 'A') == 'A' for c in cal['col'].values()) and users and users[0]['shift'] == 0
    nonrep_max = max(g['occ' if mode == 'ar' else 'step'] for g in st if g['copies'] == 1)
    lemma = dict(
        premise=dict(rule='every non-replicated window <= slot spacing; every duplicated window <= per-copy spacing',
                     nonrep_window_max=round(nonrep_max, 1), slot=round(cal['S'], 1) if cal['S'] else None,
                     holds=bool(cal['S']) and nonrep_max <= cal['S'] + 1e-6),
        brute_force=dict(resources=len(nres), windows=sum(nres.values()), collisions=bad[:20], n_collisions=len(bad),
                         result='PASS' if not bad and users else 'FAULT'),
        latency_user=dict(shift=0, copy='A on every duplicated group', result='PASS' if lat_ok else 'FAIL',
                          note='user 0 runs the single-user schedule unshifted on copy A: its windows are the '
                               'single-user windows, and no other user touches them (brute_force) -> its rate and '
                               'cycle trace are the single-user ones'))
    n_main = len([u for u in users if u['kind'] != 'filler'])
    per_user = (m.F / cal['P']) * (m.S81['tau'] if mode == 'mtp' else 1.0)
    agg = n_main * per_user + (cal.get('fillers', 0) * m.F / cal['P'] if mode == 'mtp' else 0.0)
    rec = dict(schema=SCHEMA, lane='MU-S81', mode=mode, grade='modelled (exact calendar arithmetic on the S81-BALANCE '
               'stage model of record; measured by MU.TOK)',
               config=dict(dup_groups=list(DUP), dup_layers=DUP_LAYER, dies=d['dies'], stacks=d['stacks'],
                           total_mm2=d['total_mm2'], model_users=cal['n_model'], model_agg_ar=d['agg_ar'],
                           model_agg_mtp=d['agg_mtp']),
               period=round(cal['P'], 1), slot=round(cal['S'], 1) if cal['S'] else None, users=n_main,
               fillers=cal.get('fillers', 0), per_user_tok_s=round(per_user, 1),
               filler_tok_s=round(m.F / cal['P'], 1) if mode == 'mtp' else None, aggregate_tok_s=round(agg),
               search=cal.get('tried'),
               slots=[dict(slot=i, user=u['user'], kind=u['kind'], shift=round(u['shift'], 1),
                           copy={gid: c.get(u['user'], 'A') for gid, c in cal['col'].items()})
                      for i, u in enumerate(sorted(users, key=lambda x: x['shift']))],
               pos=dict(rule='pos of user k at pass p = pos0_k + p * stride; AR stride 1, MTP stride 6 verify '
                             'positions a step (accepted count varies, the calendar does not)',
                        stride=6 if mode == 'mtp' else 1),
               bases=dict(units=f'HBM sectors ({SECTOR_B} B) relative to the group copy region base', **sb),
               tables=tabs, lemma=lemma,
               stage_model=dict(source='results/arch/s81_balance_1018/compute.py group_occ (B3, IMB_BAL)',
                                sha256=hashlib.sha256(BAL.read_bytes()).hexdigest(),
                                stages=[{k: (round(v, 1) if isinstance(v, float) else v) for k, v in g.items()}
                                        for g in st]))
    return rec


def build(mode, users=None, fillers=None, split=False):
    """split: False | True (SPLIT_L20) | a SPLIT_L20-shaped dict (e.g. with compiled helper windows)"""
    sp = (split if isinstance(split, dict) else SPLIT_L20) if split else None
    m = load_model()
    if sp:
        apply_split(m, sp)
    st = stage_windows(m)
    d = design(m)
    svc = None
    p = OUT / 'svc_bases.json'
    if p.exists():
        svc = {k: v for k, v in json.loads(p.read_text()).items() if k.endswith('_per_user')}
    cal = calendar_ar(m, st, d, users) if mode == 'ar' else calendar_mtp(m, st, d, users, fillers)
    rec = record(mode, m, st, d, cal, svc)
    if split:
        rec['l20_split'] = dict(config=sp, decision='coordinator 0li (HANDOFF 10-19 ~15:45)',
                                check=split_check(m, st, cal['users'], cal['P'], cal['col'], mode, sp))
        if rec['l20_split']['check']['result'] != 'PASS':
            rec['lemma']['brute_force']['result'] = 'FAULT'
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--mode', choices=('ar', 'mtp'))
    ap.add_argument('--users', type=int)
    ap.add_argument('--fillers', type=int)
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--phase-q', type=int, default=4, help='shift / period quantum (4 = ot_dsdv_fixed_issue start phase)')
    ap.add_argument('--l20-split', action='store_true', help='S81-L20SPLIT (0li): S029 keys over 20 dies (+ S030 '
                    'helpers, measured reader) -> calendar_<mode>_l20split.json with the helper-die check')
    a = ap.parse_args(argv)
    global PHASE_Q
    PHASE_Q = a.phase_q
    modes = [a.mode] if a.mode else ['ar', 'mtp']
    rc = 0
    for mode in modes:
        rec = build(mode, a.users, a.fillers, split=split_config() if a.l20_split else False)
        f = Path(a.out) / (f'calendar_{mode}.json' if PHASE_Q == 4 else f'calendar_{mode}_q{PHASE_Q}.json')
        if a.l20_split:
            f = f.with_name(f.stem + '_l20split.json')
        txt = json.dumps(rec, indent=1) + '\n'
        if a.check:
            same = f.exists() and f.read_text() == txt
            print(f'{mode}: {"SAME" if same else "DIFFERS"} {f}')
            rc |= 0 if same else 1
        else:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(txt)
        lm = rec['lemma']
        print(f"{mode}: users {rec['users']} (+{rec['fillers']} fillers) x {rec['per_user_tok_s']} tok/s = "
              f"{rec['aggregate_tok_s']} agg; slot {rec['slot']} period {rec['period']}; lemma "
              f"{lm['brute_force']['result']} ({lm['brute_force']['windows']} windows, "
              f"{lm['brute_force']['n_collisions']} collisions), latency user {lm['latency_user']['result']}; "
              f"model said {rec['config']['model_users']}")
        if 'l20_split' in rec:
            c = rec['l20_split']['check']
            print(f"  L20 split helper {c['helper']}: {c['result']} window {c['helper_window']} own {c['helper_own_window']}"
                  f" busy {c['helper_busy_pct']}% collisions {c['n_collisions']} own offset first {c['own_offset_first_feasible']}"
                  f" any {c['own_offset_any']}")
        if lm['brute_force']['result'] != 'PASS':
            rc = 2
    return rc


if __name__ == '__main__':
    sys.exit(main())
