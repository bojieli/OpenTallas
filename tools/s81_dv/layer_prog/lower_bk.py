#!/usr/bin/env python3
"""TOK-S81-GAPS/IDX (10-18): lowering of the indexer select ops onto the S81-DV bk selector (dsdv_bk_sel, die u_bk_sel,
column-4 V rung between u_s_4S and u_seqhost) and the gap record of the other indexer / sparse-gather ops.

Ops claimed (dv_layer_price names):
  attn.idx.topk_local   bk_sel exact streaming top-k over the die's score quarter (4 sel quarters = 4 contiguous
                        sub-ranges), drained to s_4S in one compiled egress window          -> PARTIAL (see gaps)
  attn.idx.topk_final   bk_sel again over the TP4-merged candidates (sparse positions: REBASE + lane masks)  -> PARTIAL
  attn.cand.(topk_local|merge|final)   L20 candidate-block select (same unit, block maxima as scores)       -> PARTIAL
  attn.idx.(newkey|score), attn.gather, eng.rows_allgather are NOT lowerable on the p4l3 die: GAP records below.

Every encoding is read from the RTL of record (byte-identical on claude/tok-s81-gaps-1018):
  BK V beat (ingress kind = strap ik)   dsdv_bk_v.sv:7-15   [0] 1, [3:1] ik, [5:4] lane, [6] part, [7] single,
                                        part 0: [19:8] data[511:500], [275:20] data[255:0]; part 1: [8] lane fault,
                                        [275:20] data[511:256]; single (data[499:256] == 0): data = {[19:8], 244'b0, [275:20]}
  sel lane word (data 512)              ot_s81ph_sel.sv:8-17, :88-123 (decode)   [511:508] type, [507:500] tag
        1 HDR    [19:0] base position, [29:20] k (<= 512), [31:30] qslot         (single beat)
        2 BEAT   [255:0] 16 BF16 scores (lane i [16i +: 16]), [271:256] lane valid, [272] last of the quarter (2 beats)
        6 REBASE [19:0] position of the next beat's lane 0 (forward jump)          (single beat)
  egress words (vd)                     ot_s81ph_sel_tile.sv:415-433
        3 IDX    {3, tag, 145'b0, last, qslot 2, ninf 16, lv 16, idx 16 x 20}
        4 DONE   {4, tag, 484'b0, fault 5, ovf_seen, count 10}; ONE DONE is also emitted after reset (count 0, tag 0)
  egress beats                          dsdv_bk_v.sv:150-153   part 0 {qlo, qhi[255:244], 0, 0, 00, ek, 1};
                                        part 1 {qhi, 12'b0, 0, 1, 00, ek, 1}   (qlo = data[255:0], qhi = data[511:256])
  drain CTL (kind 0, tapped not sunk)   dsdv_bk_v.sv:17-21   [28:21] uid, [31:29] op 1, [39:32] n, [47:40] d; window =
        n slots of vo (eg_n 0: vo_s) from (CTL vo edge) + LW 7 + d.  In CTL-payload terms (p = beat[21 +: 186]):
        p[7:0] uid, p[10:8] op, p[18:11] n, p[26:19] d.  CANONICAL 10-24: the BK stop consumes it (addressed-drain
        sink); the d[1:0] rule below only guards legacy (forwarding) builds.  Legacy: the SAME beat reached the S-tier slices (s_4S re-injects V CTL
        on its line): ot_s81sl_xr reads p[15:0] as its slice mask and p[20:16] = {d[1:0], n[7:5]} as the target, so
        d[1:0] != 0 is REQUIRED (target >= 8: no slice action; targets 0..5 would be live commands).  Asserted here.
  straps (die.v u_bk_sel)               tap_k 0x11 (CTL + kind 4 delivered), sink_k 0x10 (kind 4 sunk), ik 4, ek 5,
                                        uid 0x5B, eg_n 0; rung relays u_rs / u_rn = +1 edge per direction (dsdv_bk_sel.sv)

Static plan (no ready / credit at any unit port): the four lanes' words arrive on vi_s (the only BK producer side, the
S slice) one V beat a cycle; each lane word is part 0 + part 1 in consecutive slots (HDR / REBASE singles); the drain
window opens after the WORST-CASE select tail (TAIL_BUDGET, measured by the bench on this RTL and asserted there) and
reserves the worst-case word count (32 + 4 IDX + DONE (+ the boot DONE once)); words not produced leave
their slots empty.  The calendar must keep the window slots of vo_s free of forwarded southbound CTL beats.

RATE FINDING (measured in RTL, tools/s81_dv/layer_prog/bk/run_bk_layer.sh): a 16-score BEAT word costs 2 V beats, so
the 276-b rung carries 8 scores / cycle (one direction) vs the 64 scores / cycle (4 x 512-b die lanes) the hub-era
price of attn.idx.topk_local assumes (2,177 cycles): the die's 131,072-score quarter needs >= 16,388 ingress edges.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

OPS = [r'^attn\.idx\.(topk_local|topk_final)$', r'^attn\.cand\.(topk_local|merge|final)$']

INST = 'u_bk_sel'
LW = 7                    # dsdv_bk_vout: CTL vo edge -> first window vo edge = LW + d
RELAY = 1                 # dsdv_bk_sel u_rs / u_rn: +1 flop per direction
FWD = 2                   # ot_dsdv_vstop forward: 2 flops (input, output)
PIN_TO_PIN = RELAY + FWD - 1   # bench edge convention (value sampled at edge e -> vo after edge e + 2), measured
# COORD ruling 2026-10-24 18:55: the BK addressed-drain sink is canonical (ot_dsdv_vstop BK_DRAIN_SINK=1): u_bk_sel's
# rung stop consumes the drain CTL addressed to its uid, it is NOT forwarded to vo_s / the slices.  The legacy
# transparent-forwarding expectation is retired; OT_BK_LEGACY_FWD=1 reproduces it for the old records only.
import os as _os
BK_DRAIN_SINK = _os.environ.get('OT_BK_LEGACY_FWD', '0') != '1'
K_MAX = 512
TAIL_BUDGET = 640         # edges from the last ingress beat at the vi pin to the drain window's first slot (bench-asserted)
MAX_WORDS = 512 // 16 + 4 + 1   # worst-case egress words of one segment: sum_q ceil(sel_q / 16) <= 32 + 4, + DONE
D_DRAIN = 1               # drain CTL extra delay d: d[1:0] != 0 keeps the slices' target field >= 8
BENCH = 'results/rtl/s81_layer_tput_1018/compiler/bench_bk'
T_HDR, T_BEAT, T_IDX, T_DONE, T_REBASE = 1, 2, 3, 4, 6
M276 = (1 << 276) - 1


# ================================================================================================= encoders (bit exact)
def hdr_word(base, k, qslot, tag):
    return T_HDR << 508 | (tag & 0xFF) << 500 | (qslot & 3) << 30 | (k & 0x3FF) << 20 | (base & 0xFFFFF)


def rebase_word(pos, tag):
    return T_REBASE << 508 | (tag & 0xFF) << 500 | (pos & 0xFFFFF)


def beat_word(keys16, lv, last, tag):
    d = 0
    for i, k in enumerate(keys16):
        d |= (int(k) & 0xFFFF) << (16 * i)
    return T_BEAT << 508 | (tag & 0xFF) << 500 | int(bool(last)) << 272 | (lv & 0xFFFF) << 256 | d


def idx_word(idx16, lv, ninf, qslot, last, tag):
    d = 0
    for i, x in enumerate(idx16):
        d |= (int(x) & 0xFFFFF) << (20 * i)
    return T_IDX << 508 | (tag & 0xFF) << 500 | int(bool(last)) << 354 | (qslot & 3) << 352 | (ninf & 0xFFFF) << 336 \
        | (lv & 0xFFFF) << 320 | d


def done_word(count, tag, ovf=0, fault=0):
    return T_DONE << 508 | (tag & 0xFF) << 500 | (fault & 0x1F) << 11 | int(bool(ovf)) << 10 | (count & 0x3FF)


def is_single(w):
    return (w >> 256) & ((1 << 244) - 1) == 0


def bk_beats(lane, w, ik=4, fault=0):
    """one lane word -> its V beats (dsdv_bk_v.sv:7-15)"""
    lo = w & ((1 << 256) - 1)
    hi = w >> 256
    top = (w >> 500) & 0xFFF
    h = 1 | (ik & 7) << 1 | (lane & 3) << 4
    if is_single(w):
        return [h | 1 << 7 | top << 8 | lo << 20]
    return [h | top << 8 | lo << 20, h | 1 << 6 | (fault & 1) << 8 | hi << 20]


def egress_beats(w, ek=5):
    """one vd word -> its 2 egress V beats on vo (dsdv_bk_vout o_b)"""
    qlo = w & ((1 << 256) - 1)
    qhi = w >> 256
    h = 1 | (ek & 7) << 1
    return [h | ((qhi >> 244) & 0xFFF) << 8 | qlo << 20, h | 1 << 6 | qhi << 20]


def drain_payload(uid, n, d):
    """drain CTL as a 186-b CTL template payload (seq_host puts it at beat[21 +: 186]); asserts the slice-target rule"""
    assert 0 < n <= 255 and 0 <= d <= 255
    p = (uid & 0xFF) | 1 << 8 | (n & 0xFF) << 11 | (d & 0xFF) << 19
    tgt = (p >> 16) & 0x1F
    assert tgt >= 6, f'drain CTL n {n} d {d}: slice target {tgt} would be a live xr command (need d[1:0] != 0)'
    return p


def ctl_beat(payload186, src=4, hops=0):
    return 1 | (hops & 0x1F) << 4 | (src & 0xF) << 9 | payload186 << 21


# ================================================================================================= select model
def bf16_key(v):
    """BF16 bits of a float64 holding a BF16 value"""
    b = np.asarray(v, dtype=np.float64).astype(np.float32).view(np.uint32)
    assert np.all(b & 0xFFFF == 0), 'scores are not BF16 values'
    return (b >> 16).astype(np.uint32)


def ordkey(k16):
    """order-preserving key of BF16 bits (-0 == +0)"""
    k = np.asarray(k16, dtype=np.int64)
    neg = (k & 0x8000) != 0
    o = np.where(neg, 0x7FFF - (k & 0x7FFF), 0x8000 | (k & 0x7FFF))
    o = np.where((k & 0x7FFF) == 0, 0x8000, o)      # -0 == +0
    return o


def topk_lowest_index(keys, pos, k):
    """the golden rule: k largest values, ties to the lower position; returned ascending by position"""
    o = ordkey(keys)
    order = np.lexsort((pos, -o))
    sel = np.sort(pos[order[:k]])
    return sel


# ================================================================================================= plan
def quarters_dense(base, n):
    """4 contiguous sub-ranges of [base, base + n) (sizes multiple of 16 where possible)"""
    q = [n // 4 // 16 * 16] * 3
    q.append(n - sum(q))
    out, b = [], base
    for s in q:
        out.append((b, s))
        b += s
    return out


def lane_words_dense(keys, base, n, k, qslot, tag):
    """HDR + BEATs of one dense quarter (all lanes valid, the last beat partial-masked)"""
    ws = [hdr_word(base, k, qslot, tag)]
    nb = max(1, math.ceil(n / 16))
    for b in range(nb):
        seg = keys[16 * b:16 * b + 16]
        lv = (1 << len(seg)) - 1
        seg = list(seg) + [0] * (16 - len(seg))
        ws.append(beat_word(seg, lv, b == nb - 1, tag))
    if n == 0:
        ws[-1:] = [ws[0], beat_word([0] * 16, 0, True, tag)]
    return ws


def lane_words_sparse(keys, pos, base, k, qslot, tag):
    """HDR + (REBASE + BEAT)* of one sparse ascending position set: positions grouped by 16-aligned windows"""
    ws = [hdr_word(base, k, qslot, tag)]
    pos = np.asarray(pos, dtype=np.int64)
    if pos.size == 0:
        return ws + [beat_word([0] * 16, 0, True, tag)]
    cur = base
    groups = []
    i = 0
    while i < pos.size:
        w0 = int(pos[i]) // 16 * 16
        j = i
        while j < pos.size and pos[j] < w0 + 16:
            j += 1
        groups.append((w0, i, j))
        i = j
    for g, (w0, i, j) in enumerate(groups):
        if w0 != cur:
            assert w0 > cur
            ws.append(rebase_word(w0, tag))
        lv, seg = 0, [0] * 16
        for t in range(i, j):
            off = int(pos[t]) - w0
            lv |= 1 << off
            seg[off] = int(keys[t])
        ws.append(beat_word(seg, lv, g == len(groups) - 1, tag))
        cur = w0 + 16
    return ws


def lane_words_indexed13(keys, pos, base, k, qslot, tag):
    """Type 8: 13 x (BF16 score + ORIGINAL 20-bit index), mask [480:468], last [481].
    Requires RTL OT_S81PH_SEL_INDEXED13; off by default until physical closure.
    Quarter positions must be strictly ascending, so native output order is unchanged.
    """
    assert len(keys) == len(pos)
    assert all(0 <= int(p) < (1 << 20) for p in pos)
    assert all(int(a) < int(b) for a, b in zip(pos, pos[1:]))
    ws = [hdr_word(base, k, qslot, tag)]
    nb = max(1, math.ceil(len(pos) / 13))
    for b in range(nb):
        pp, kk = pos[13*b:13*b+13], keys[13*b:13*b+13]
        w = 8 << 508 | (tag & 255) << 500 | int(b == nb-1) << 481 | ((1 << len(pp))-1) << 468
        for i, (p, key) in enumerate(zip(pp, kk)):
            w |= (int(key) & 0xffff) << (36*i) | int(p) << (36*i+16)
        ws.append(w)
    return ws


def ingress_schedule(lanes, t0, ik=4, avail=None):
    """lane words -> [(edge, beat)] on vi_s: HDRs first (one per lane), then the lanes' words round-robin, each word's
    beats in consecutive slots, one V beat per edge.  avail(lane, word index, word) -> earliest edge of that word or None
    (static pacing: the reader's key rate, a child die's candidates after its egress + leg); the order never changes."""
    beats = []
    q = [list(enumerate(ws)) for ws in lanes]
    order = []
    for l in range(4):
        order.append((l,) + q[l].pop(0))
    while any(q):
        for l in range(4):
            if q[l]:
                order.append((l,) + q[l].pop(0))
    t = t0
    for l, i, w in order:
        a = avail(l, i, w) if avail else None
        if a is not None and a > t:
            t = a
        for b in bk_beats(l, w, ik):
            beats.append((t, b))
            t += 1
    return beats


def expected_words(sel_per_q, keys_of, tag, boot_done=True):
    """egress vd words in order: [boot DONE], per quarter its IDX words (16 a word, last flagged), DONE"""
    out = []
    if boot_done:
        out.append(done_word(0, 0))
    total = 0
    for q, (sel, keys) in enumerate(zip(sel_per_q, keys_of)):
        nw = max(1, math.ceil(len(sel) / 16))
        for w in range(nw):
            s = list(sel[16 * w:16 * w + 16])
            kk = list(keys[16 * w:16 * w + 16])
            lv = (1 << len(s)) - 1
            ninf = sum(1 << i for i, x in enumerate(kk) if (int(x) & 0x7FFF) == 0x7F80 and int(x) & 0x8000)
            out.append(idx_word(s + [0] * (16 - len(s)), lv, ninf, q, w == nw - 1, tag))
        total += len(sel)
    out.append(done_word(total, tag))
    return out


def plan_select(keys_lanes, pos_lanes, bases, k, tag, t0, sparse=False, boot_done=True, ik=4, ek=5, uid=0x5B,
                lanes=None, avail=None):
    """the whole bk_sel job: ingress beats, drain CTL, expected egress beats at vo_s (bench / replay timing).
    lanes: pre-built lane words (append jobs); avail: ingress pacing (see ingress_schedule)"""
    if lanes is None:
        lanes = []
        for q in range(4):
            if sparse:
                lanes.append(lane_words_sparse(keys_lanes[q], pos_lanes[q], bases[q], k, q, tag))
            else:
                lanes.append(lane_words_dense(keys_lanes[q], bases[q], len(keys_lanes[q]), k, q, tag))
    ins = ingress_schedule(lanes, t0, ik, avail)
    t_last = ins[-1][0]
    allk = np.concatenate([np.asarray(x, dtype=np.int64) for x in keys_lanes])
    allp = np.concatenate([np.asarray(x, dtype=np.int64) for x in pos_lanes])
    sel = topk_lowest_index(allk, allp, k)
    kmap = dict(zip(allp.tolist(), allk.tolist()))
    sel_q, key_q = [], []
    for q in range(4):
        lo = int(min(pos_lanes[q])) if len(pos_lanes[q]) else None
        hi = int(max(pos_lanes[q])) if len(pos_lanes[q]) else None
        s = [int(x) for x in sel if lo is not None and lo <= x <= hi]
        sel_q.append(s)
        key_q.append([kmap[x] for x in s])
    words = expected_words(sel_q, key_q, tag, boot_done)
    n = 2 * (MAX_WORDS + (1 if boot_done else 0))
    assert n <= 255
    # window: first slot at the vo_s pin edge W0 = t_last + TAIL_BUDGET; the CTL leaves vo_s at W0 - LW - d
    w0 = t_last + TAIL_BUDGET
    c_vo = w0 - LW - D_DRAIN
    c_vi = c_vo - PIN_TO_PIN                      # the CTL beat at the vi_n pin (southbound: relay u_rn + vstop)
    p = drain_payload(uid, n, D_DRAIN)
    outs = []
    for i, w in enumerate(words):
        for j, b in enumerate(egress_beats(w, ek)):
            outs.append((w0 + 2 * i + j, b))
    return dict(ingress=ins, t_last_in=t_last, drain=dict(vi_n_edge=c_vi, vo_edge=c_vo, payload=p, n=n, d=D_DRAIN,
                                                          beat=ctl_beat(p)),
                window=(w0, w0 + n - 1), words=words, egress=outs, selection=[int(x) for x in sel],
                sel_per_quarter=[len(s) for s in sel_q])


# ================================================================================================= key sharding (record)
# S81-SCAND option D (coordinator 0iq) shards each full-scan layer's rank keys over k adjacent TP4 stages (one HBM stack a
# die): L2 / L8 / L14 k = 3 (43,691 keys a die), L20 k = 3 -> 87,382.  S81-L20SPLIT (coordinator 0li, 10-19): the L20
# window is split over 2x the dies (k = 6: the record's 3 stages + 3 helper stages, no new silicon) -> 43,691 a die.
# Before 10-19 lower_bk fed the UNSHARDED 262,144 rank keys a die into bk_sel (TOK cut L20 44,256 cycles): wrong design.
SHARD_K = {'L2': 3, 'L8': 3, 'L14': 3, 'L20': 6}
SHARD_K_RECORD_D = {'L2': 3, 'L8': 3, 'L14': 3, 'L20': 3}     # option D before the L20 split (comparison only)


def shard_k(layer, default=1):
    return SHARD_K.get(str(layer), default)


def shard_range(n, k, j):
    """die j of k: contiguous [lo, lo + m) of a rank's n keys; ceil(n / k) a die, the last die the remainder"""
    assert 0 <= j < k
    m = -(-n // k)
    lo = min(n, j * m)
    return lo, min(n, lo + m) - lo


# ================================================================================================= fixtures -> jobs
def load_op(fx, name):
    meta = json.loads((Path(fx) / 'ops.json').read_text())[name]
    return np.fromfile(Path(fx) / 'ops' / f'{name}.bin', dtype=meta['dtype']).reshape(meta['shape'])


def job_topk_local(fx, rank=0, t0=100, tag=0x21, boot_done=True, mut=None, k_dies=1, die=0):
    """the bk_sel job of die `die` of the k_dies dies that hold rank `rank`'s keys (k_dies 1 = the unsharded rank).
    Golden: k_dies 1 = attn.idx.topk_local rank (fixture); k_dies > 1 = the golden rule on the die's own shard (the
    shard closure -- the k dies' selections contain the rank's fixture top-k -- is checked by job_topk_final)."""
    s = load_op(fx, 'attn.idx.score')
    n = s.size
    q4 = n // 4
    lo, m = shard_range(q4, k_dies, die)
    b0 = rank * q4 + lo
    keys = bf16_key(s[b0:b0 + m])
    qs = quarters_dense(b0, m)
    kl = [keys[b - b0:b - b0 + mm] for b, mm in qs]
    pl = [np.arange(b, b + mm) for b, mm in qs]
    k = min(K_MAX, m)
    if k_dies == 1:
        gold = np.sort(load_op(fx, 'attn.idx.topk_local')[rank * min(K_MAX, q4):(rank + 1) * min(K_MAX, q4)])
        gname = 'attn.idx.topk_local rank %d (sorted)' % rank
    else:
        gold = topk_lowest_index(keys, np.arange(b0, b0 + m), k)
        gname = 'golden rule on the die shard rank %d die %d/%d [%d, %d)' % (rank, die, k_dies, b0, b0 + m)
    if mut:
        kl = mut(kl, pl, gold)
    plan = plan_select(kl, pl, [b for b, _ in qs], k, tag, t0, boot_done=boot_done)
    plan['golden_ok'] = bool(np.array_equal(np.asarray(plan['selection']), gold))
    plan['golden'] = gname
    plan['shard'] = dict(k_dies=k_dies, die=die, rank=rank, base=int(b0), keys=int(m))
    return plan


def shard_candidates(fx, k_dies):
    """the die-local selections of every (rank, die): {rank: sorted positions of the rank's k_dies x 512 candidates}
    + the shard-closure proof: the top-512 of the union == the fixture attn.idx.topk_local of the rank"""
    s = load_op(fx, 'attn.idx.score')
    n = s.size
    q4 = n // 4
    loc = load_op(fx, 'attn.idx.topk_local')
    kr = min(K_MAX, q4)
    cand, closure = {}, {}
    for r in range(4):
        ps = []
        for j in range(k_dies):
            lo, m = shard_range(q4, k_dies, j)
            b0 = r * q4 + lo
            ps.append(topk_lowest_index(bf16_key(s[b0:b0 + m]), np.arange(b0, b0 + m), min(K_MAX, m)))
        p = np.sort(np.concatenate(ps))
        cand[r] = p
        merged = topk_lowest_index(bf16_key(s[p]), p, kr)
        closure[r] = bool(np.array_equal(merged, np.sort(loc[r * kr:(r + 1) * kr])))
    return cand, closure


def job_topk_final(fx, t0=100, tag=0x22, boot_done=False, mut=None, k_dies=1, indexed13=False):
    """the final select over the 4 ranks' candidates: k_dies 1 = 4 x 512 (the ranks' topk_local, TP4 merge);
    k_dies > 1 = 4 x k_dies x 512 die-local selections (option D / L20 split: the all-gather widens, one select)."""
    s = load_op(fx, 'attn.idx.score')
    n = s.size
    q4 = n // 4
    loc = load_op(fx, 'attn.idx.topk_local')
    k = min(K_MAX, q4)
    closure = None
    if k_dies > 1:
        cand, closure = shard_candidates(fx, k_dies)
    kl, pl, bases = [], [], []
    for r in range(4):
        p = np.sort(loc[r * k:(r + 1) * k]) if k_dies == 1 else cand[r]
        pl.append(p)
        kl.append(bf16_key(s[p]))
        bases.append(int(p[0]) // 16 * 16 if p.size else r * q4)
    if mut:
        kl = mut(kl, pl, np.sort(load_op(fx, 'attn.idx.topk_final')))
    lanes = [lane_words_indexed13(kl[q], pl[q], bases[q], k, q, tag) for q in range(4)] if indexed13 else None
    plan = plan_select(kl, pl, bases, k, tag, t0, sparse=True, boot_done=boot_done, lanes=lanes)
    plan['indexed13'] = bool(indexed13)
    gold = np.sort(load_op(fx, 'attn.idx.topk_final'))
    plan['golden_ok'] = bool(np.array_equal(np.asarray(plan['selection']), gold)) and \
        (closure is None or all(closure.values()))
    plan['golden'] = 'attn.idx.topk_final (sorted)' + ('' if k_dies == 1 else
                                                       ' over 4 x %d x 512 die-local candidates; shard closure %s' %
                                                       (k_dies, closure))
    plan['shard'] = dict(k_dies=k_dies, candidates=[int(len(x)) for x in pl], closure=closure)
    return plan


# ================================================================================================= L20 split: rank tree
# S81-L20SPLIT (coordinator 0li): the rank's keys sit on k_dies dies (SHARD_K); every die scans its own shard (the
# measured reader law: one key every READER_P cycles in each of 16 regions + READER_T0) into its bk_sel, and the rank's
# top-512 is merged up a static tree over the existing die links: a parent's job is its OWN shard (4 dense quarters)
# followed, on lane 3, by its children's merged 512-candidate sets (REBASE + sparse BEAT words; the children own the
# higher key ranges, so every appended position is above the parent's own).  No credit / ready: every child's
# candidates reach the parent's vi_s at a compiled edge (child's last egress beat + LEG), and the parent's lane-3 tail
# is scheduled at that edge.  The root die's selection is the rank's topk_local (fixture) -- the shard closure.
READER_P, READER_T0 = 3, 511       # dsdv_idx_rg P = 3 (S81-IDXRD sweep_1019: 87,382 keys 16,895 / 43,691 keys 8,702)
LEG = 729                          # S81 cross-die idx_topk_merge leg (measured, S81-SCAND scand.json legs)


def reader_cycles(n, p=READER_P):
    return math.ceil(p * n / 16 + READER_T0)


def shard_tree(k_dies):
    """{die: [children]} -- die a roots [a, b): children = the roots of [a + 1, mid) and [mid, b) (depth ~log2 k)"""
    ch = {}

    def build(a, b):
        ch[a] = []
        rest = b - (a + 1)
        if rest <= 0:
            return
        if rest == 1:
            ch[a].append(a + 1)
            build(a + 1, b)
            return
        mid = a + 1 + rest // 2
        for lo, hi in ((a + 1, mid), (mid, b)):
            ch[a].append(lo)
            build(lo, hi)
    build(0, k_dies)
    return ch


def subtree(ch, d):
    out = [d]
    for c in ch[d]:
        out += subtree(ch, c)
    return sorted(out)


def lane3_append(own_keys, base, n, ext, k, tag):
    """lane 3: HDR + the own dense quarter (not last) + the appended (keys, positions) sets as REBASE + sparse BEATs"""
    ws = lane_words_dense(own_keys, base, n, k, 3, tag)
    if not ext:
        return ws
    ek = np.concatenate([np.asarray(x[0], dtype=np.int64) for x in ext])
    ep = np.concatenate([np.asarray(x[1], dtype=np.int64) for x in ext])
    o = np.argsort(ep, kind='stable')
    ek, ep = ek[o], ep[o]
    nb = max(1, math.ceil(n / 16))
    cur = base + 16 * nb
    # the last own BEAT loses its 'last' flag (the lane continues)
    w = ws[-1]
    ws[-1] = w & ~(1 << 272)
    assert ep.size == 0 or ep[0] >= base + n
    # appended positions inside the own last BEAT's 16-position window join that word (lane-valid bit + key)
    i = 0
    if n > 0:
        w = ws[-1]
        w0l = cur - 16
        while i < ep.size and ep[i] < cur:
            off = int(ep[i]) - w0l
            w = (w & ~(0xFFFF << (16 * off))) | (int(ek[i]) & 0xFFFF) << (16 * off) | 1 << (256 + off)
            i += 1
        ws[-1] = w
    groups = []
    while i < ep.size:
        w0 = int(ep[i]) // 16 * 16
        if w0 < cur:
            w0 = int(ep[i])           # aligned window starts below the stream position: start it at the position
        j = i
        while j < ep.size and ep[j] < w0 + 16:
            j += 1
        groups.append((w0, i, j))
        i = j
    if not groups:
        ws[-1] |= 1 << 272
    for g, (w0, i, j) in enumerate(groups):
        if w0 != cur:
            assert w0 > cur
            ws.append(rebase_word(w0, tag))
        lv, seg = 0, [0] * 16
        for t in range(i, j):
            off = int(ep[t]) - w0
            lv |= 1 << off
            seg[off] = int(ek[t])
        ws.append(beat_word(seg, lv, g == len(groups) - 1, tag))
        cur = w0 + 16
    return ws


def job_rank_tree(fx, rank=0, k_dies=None, layer='L20', t_q=0, tag0=0x30, boot_done=True, pace=True, mut=None,
                  mut_die=None):
    """the static rank tree: one bk_sel job a die.  t_q = the edge the query reaches every die's reader (the compiled
    fan-out); returns {die: plan} (plan['avail_children'] = the edges the children's candidates are scheduled at) and
    the rank result (root selection == fixture topk_local of the rank, the shard closure)"""
    kd = k_dies or shard_k(layer)
    s = load_op(fx, 'attn.idx.score')
    q4 = s.size // 4
    ch = shard_tree(kd)
    depth = {0: 0}
    for d in sorted(ch):
        for c in ch[d]:
            depth[c] = depth[d] + 1
    plans = {}

    def run(d):
        for c in ch[d]:
            run(c)
        lo, m = shard_range(q4, kd, d)
        b0 = rank * q4 + lo
        keys = bf16_key(s[b0:b0 + m])
        qs = quarters_dense(b0, m)
        kl = [keys[b - b0:b - b0 + mm] for b, mm in qs]
        pl = [np.arange(b, b + mm) for b, mm in qs]
        ext, arr = [], []
        for c in ch[d]:
            pc = plans[c]
            sel = np.asarray(pc['selection'], dtype=np.int64)
            ext.append((bf16_key(s[sel]), sel))
            arr.append(pc['egress'][-1][0] + LEG)
        if mut is not None and d == mut_die:
            kl = mut(kl, pl, np.asarray(topk_lowest_index(keys, np.arange(b0, b0 + m), min(K_MAX, m))))
        k = K_MAX
        tag = tag0 + d
        lanes = [lane_words_dense(kl[q], qs[q][0], qs[q][1], k, q, tag) for q in range(3)]
        lanes.append(lane3_append(kl[3], qs[3][0], qs[3][1], ext, k, tag))
        n_dense3 = max(1, math.ceil(qs[3][1] / 16))
        cnt = {'g': 0}
        tq_d = t_q + depth[d] * LEG               # the query reaches die d down the same tree (one leg an edge)
        t_ext = max(arr) if arr else None

        def avail(l, i, w):
            if (w >> 508) == T_HDR:
                return None
            if l == 3 and i > n_dense3:
                return t_ext                       # appended candidates: the latest child's arrival (static)
            if (w >> 508) != T_BEAT or not pace:
                return None
            cnt['g'] += 1                         # the reader delivers 16 keys a word, P cycles a key / region
            return tq_d + READER_T0 + READER_P * cnt['g']
        allk = [kl[0], kl[1], kl[2], np.concatenate([kl[3]] + [e[0] for e in ext])]
        allp = [pl[0], pl[1], pl[2], np.concatenate([pl[3]] + [e[1] for e in ext])]
        plan = plan_select(allk, allp, None, k, tag, tq_d, boot_done=boot_done, lanes=lanes, avail=avail)
        sub = subtree(ch, d)
        lo_s, _ = shard_range(q4, kd, sub[0])
        lo_e, m_e = shard_range(q4, kd, sub[-1])
        a0, a1 = rank * q4 + lo_s, rank * q4 + lo_e + m_e
        gold = topk_lowest_index(bf16_key(s[a0:a1]), np.arange(a0, a1), K_MAX)
        plan['golden_ok'] = bool(np.array_equal(np.asarray(plan['selection']), gold))
        plan['golden'] = 'golden rule over the subtree keys [%d, %d) (dies %s)' % (a0, a1, sub)
        plan['shard'] = dict(k_dies=kd, die=d, rank=rank, base=int(b0), keys=int(m), children=ch[d],
                             child_arrival=arr, t_q=tq_d, depth=depth[d])
        plans[d] = plan
    run(0)
    loc = load_op(fx, 'attn.idx.topk_local')
    kr = min(K_MAX, q4)
    closure = bool(np.array_equal(np.asarray(plans[0]['selection']), np.sort(loc[rank * kr:(rank + 1) * kr])))
    return plans, dict(k_dies=kd, tree=ch, closure=closure, root_last_egress=plans[0]['egress'][-1][0],
                       per_die=[dict(die=d, keys=plans[d]['shard']['keys'], first_in=plans[d]['ingress'][0][0],
                                     last_in=plans[d]['t_last_in'], last_egress=plans[d]['egress'][-1][0],
                                     t_q=plans[d]['shard']['t_q'],
                                     reader_done=plans[d]['shard']['t_q'] + reader_cycles(plans[d]['shard']['keys']),
                                     children=ch[d], golden_ok=plans[d]['golden_ok']) for d in sorted(plans)])


# ================================================================================================= L20 die: reader tree
# S81-L20DIE (10-19): the rank tree as the DIE RTL runs it (supersedes the job_rank_tree lane-3 append, which modelled
# the children's candidates as arriving with their scores although the selector's IDX egress carries none).
#   * own shard: the 16 regional readers (dsdv_idx_rg) put the WHOLE shard on lane 0 (HDR 16 j0, one BEAT a 16-position
#     word, part 0 at E + 10 + P w, part 1 + 1); lanes 1..3: HDR + empty last BEAT unless OPEN (spec om).
#   * children: child i of a die owns lane CHILD_LANES[i] at the parent (om bit set, the reader leaves it open).  The
#     child's dsdv_idx_tx re-encodes its own selection with the scores its selector ingested (score store) as
#     HDR(HB = subtree low & ~15, k, lane) + (REBASE + BEAT)* (16-aligned windows) + last, tagged with the PARENT's tag,
#     and emits it on a reserved slot grid (TX_SM slots, pitch TX_R) from a compiled first slot; the link adds LEG.
#   * the parent's drain waits for the RESERVED end of every child grid (static: data never moves a compiled edge).
CHILD_LANES = (2, 3)
TX_UID, TX_OP = 0x5C, 2
TX_SM = 1600             # worst-case tx beats: HDR + 512 x (REBASE + 2 BEAT) = 1,537 + the first-IDX lead (~15) + margin
TX_R = 1
# MU.S81.CAL booking (STW-S81c-DIE4 10-22): TOPK TX x (dsdv_idx_tx_n32 RIL+RDL, RTL 100457dd6 / census b7b57b3d4) has the
# TX lookup pipe LP 4 = reference dsdv_idx_tx LP 2 + LPX 2 (x == reference LPX=2 cycle-exact, 55,734 checks).  Effect at
# the tx pins: beats 1-3 unchanged, beat 4 onward and done one 4-cycle beat slot later (+4 edges, once a job).  The
# compiled slot grid absorbs it: the FIRST slot (checked edge-exact) is unchanged and the parent waits for the RESERVED
# grid end (TX_SM slots), so the worst-case stream + the shift must fit TX_SM.  TX_LPX = the bound TX's LPX (0 = today's
# die, dsdv_idx_tx_n32 v; 2 = TOPK TX x/y once bound); the tree bench builds the reference with it (run_idx_tree.sh LPX=).
TX_LPX = 0
TX_LPX_BOOKED = 2
TX_WORST = 1537 + 15     # HDR + 512 x (REBASE + 2 BEAT) + the first-IDX lead
TX_LPX_SHIFT = {0: 0, 1: 0, 2: 4}   # measured at the tx pins (LPX 1 invisible, LPX 2 = one 4-cycle beat slot)
assert TX_WORST + max(TX_LPX_SHIFT[TX_LPX], TX_LPX_SHIFT[TX_LPX_BOOKED]) <= TX_SM * TX_R, 'TX grid cannot absorb LPX'
TX_OFF = 5               # tx-job CTL at the bk_sel vi_n pin edge c -> first grid slot printed (lo) at c + TX_OFF + DLY
TX_LINK = 3              # tx lo printed at t -> parent bk_sel vi_s ingress edge t + TX_LINK + leg (vmux 2 + pin 1)
VMUX_LAT = 2             # dsdv_idx_vmux pin -> pin
TX_CTL_LEAD = 16         # the tx-job CTL enters vi_n this many edges before the drain CTL


def reader_beats(keys, b0, n, k, tag, om, e0, p=READER_P, ik=4):
    """the readers' compiled emission at the bk_sel vi_s pin (dsdv_idx_rg.sv emission): [(edge, beat)]"""
    j0, j1 = b0 >> 4, (b0 + n - 1) >> 4
    nw = j1 - j0 + 1
    out = [(e0, bk_beats(0, hdr_word(16 * j0, k, 0, tag), ik)[0])]
    for l in (1, 2, 3):
        if om >> (l - 1) & 1:
            continue
        t = e0 + 1 + 3 * (l - 1)
        out.append((t, bk_beats(l, hdr_word(16 * (j1 + 1), k, l, tag), ik)[0]))
        for i, b in enumerate(bk_beats(l, beat_word([0] * 16, 0, True, tag), ik)):
            out.append((t + 1 + i, b))
    for w in range(nw):
        lv, seg = 0, [0] * 16
        for i in range(16):
            pos = 16 * (j0 + w) + i
            if b0 <= pos < b0 + n:
                lv |= 1 << i
                seg[i] = int(keys[pos - b0])
        for i, b in enumerate(bk_beats(0, beat_word(seg, lv, w == nw - 1, tag), ik)):
            out.append((e0 + 10 + p * w + i, b))
    return out


def tx_payload(lane, ptag, k, hb, otag, dly, r, sm):
    assert 0 <= dly < 1 << 16 and 1 <= r < 8 and 0 < sm < 1 << 12 and hb % 16 == 0
    return (TX_UID | TX_OP << 8 | 31 << 16 | (lane & 3) << 21 | (ptag & 0xFF) << 23 | (k & 0x3FF) << 31 |
            (hb & 0xFFFFF) << 41 | (otag & 0xFF) << 61 | dly << 69 | r << 85 | sm << 88)


def drain_for(t_last, n_words_max):
    w0 = t_last + TAIL_BUDGET
    c_vo = w0 - LW - D_DRAIN
    return w0, c_vo, c_vo - PIN_TO_PIN


def job_rank_tree_rd(fx, rank=0, k_dies=None, layer='L20', t_q=0, tag0=0x30, boot_done=True, leg=LEG, mut=None,
                     mut_die=None):
    """the static rank tree on the die RTL (reader + vmux + bk_sel + tx); t_q = the edge the query's reader beats start
    at the root's bk_sel vi_s (E of the root); a die at depth h starts at t_q + h leg (query fan-out over the same
    links, qf pin -> pin = the link's).  Returns {die: plan}, summary (root selection == fixture topk_local)."""
    kd = k_dies or shard_k(layer)
    s = load_op(fx, 'attn.idx.score')
    q4 = s.size // 4
    ch = shard_tree(kd)
    depth = {0: 0}
    for d in sorted(ch):
        for c in ch[d]:
            depth[c] = depth[d] + 1
    par = {c: (d, i) for d in ch for i, c in enumerate(ch[d])}
    plans = {}

    def sub_lo(d):
        sub = subtree(ch, d)
        return rank * q4 + shard_range(q4, kd, sub[0])[0]

    def run(d):
        for c in ch[d]:
            run(c)
        lo_, m = shard_range(q4, kd, d)
        b0 = rank * q4 + lo_
        keys = bf16_key(s[b0:b0 + m])
        if mut is not None and d == mut_die:
            keys = mut(keys, b0)
        tag = tag0 + d
        om = 0
        for i, c in enumerate(ch[d]):
            om |= 1 << (CHILD_LANES[i] - 1)
        e0 = t_q + depth[d] * leg
        rb = reader_beats(keys, b0, m, K_MAX, tag, om, e0)
        pos_l = {0: np.arange(b0, b0 + m)}
        key_l = {0: keys}
        t_last = rb[-1][0]
        arr = []
        free_from = t_last + 1
        for i, c in enumerate(ch[d]):
            pc = plans[c]
            sel = np.asarray(pc['selection'], dtype=np.int64)
            ks = np.asarray(pc['sel_keys'], dtype=np.int64)
            L = CHILD_LANES[i]
            pos_l[L], key_l[L] = sel, ks
            # the child's grid: first slot >= its egress window start, and its arrival window after the previous one
            first = max(pc['window'][0], free_from - TX_LINK - leg)
            a0 = first + TX_LINK + leg
            a1 = a0 + TX_SM * TX_R
            free_from = a1 + 1
            c_tx = pc['drain']['vi_n_edge'] - TX_CTL_LEAD
            dly = first - (c_tx + TX_OFF)
            assert dly >= 1, (d, c, dly)
            hb = sub_lo(c) // 16 * 16
            pc['tx'] = dict(lane=L, parent=d, ptag=tag, hb=hb, ctl_vi_n=c_tx, dly=dly, first=first, r=TX_R, sm=TX_SM,
                            arrive=[a0, a1], payload=tx_payload(L, tag, K_MAX, hb, pc['tag'], dly, TX_R, TX_SM),
                            words=lane_words_sparse(ks, sel, hb, K_MAX, L, tag))
            pc['tx']['beat'] = ctl_beat(pc['tx']['payload'])
            arr.append([a0, a1])
            t_last = max(t_last, a1)
        allk = np.concatenate([np.asarray(key_l[l], dtype=np.int64) for l in sorted(key_l)])
        allp = np.concatenate([np.asarray(pos_l[l], dtype=np.int64) for l in sorted(pos_l)])
        k = K_MAX
        sel = topk_lowest_index(allk, allp, k)
        kmap = dict(zip(allp.tolist(), allk.tolist()))
        sel_q, key_q = [], []
        for q in range(4):
            pq = set(int(x) for x in pos_l.get(q, []))
            sq = [int(x) for x in sel if int(x) in pq]
            sel_q.append(sq)
            key_q.append([kmap[x] for x in sq])
        words = expected_words(sel_q, key_q, tag, boot_done)
        n = 2 * (MAX_WORDS + (1 if boot_done else 0))
        w0, c_vo, c_vi = drain_for(t_last, n)
        p = drain_payload(0x5B, n, D_DRAIN)
        egress = []
        for i, w in enumerate(words):
            for j, b in enumerate(egress_beats(w)):
                egress.append((w0 + 2 * i + j, b))
        sub = subtree(ch, d)
        a0_ = sub_lo(d)
        lo_e, m_e = shard_range(q4, kd, sub[-1])
        a1_ = rank * q4 + lo_e + m_e
        gold = topk_lowest_index(bf16_key(s[a0_:a1_]), np.arange(a0_, a1_), K_MAX)
        plans[d] = dict(die=d, tag=tag, om=om, e0=e0, reader=rb, t_last_in=t_last, children=ch[d], child_arrive=arr,
                        drain=dict(vi_n_edge=c_vi, vo_edge=c_vo, payload=p, n=n, d=D_DRAIN, beat=ctl_beat(p)),
                        window=(w0, w0 + n - 1), words=words, egress=egress, selection=[int(x) for x in sel],
                        sel_keys=[kmap[int(x)] for x in sel], sel_per_quarter=[len(x) for x in sel_q],
                        golden_ok=bool(np.array_equal(np.asarray(sel), gold)), keys=int(m), base=int(b0), depth=depth[d])
    run(0)
    loc = load_op(fx, 'attn.idx.topk_local')
    kr = min(K_MAX, q4)
    closure = bool(np.array_equal(np.asarray(plans[0]['selection']), np.sort(loc[rank * kr:(rank + 1) * kr])))
    return plans, dict(k_dies=kd, tree=ch, par=par, closure=closure, root_last_egress=plans[0]['egress'][-1][0],
                       per_die=[dict(die=d, keys=plans[d]['keys'], e0=plans[d]['e0'], t_last_in=plans[d]['t_last_in'],
                                     window=plans[d]['window'], last_egress=plans[d]['egress'][-1][0],
                                     child_arrive=plans[d]['child_arrive'], golden_ok=plans[d]['golden_ok'],
                                     tx=({k_: v for k_, v in plans[d]['tx'].items() if k_ not in ('words', 'beat', 'payload')}
                                         if 'tx' in plans[d] else None)) for d in sorted(plans)])


def write_tree_bench(fx, out, k_dies, t_q=200, leg=LEG, mutant=None, layer='L20'):
    """stim.txt '<edge> <die> s|n <hex>' (s = vmux i_s at edge - VMUX_LAT, n = bk_sel vi_n), exp.json, args.txt
    (plusargs).  Mutants (stimulus only; the expectation stays golden): corrupt = the root's lowest selected own key
    -> -inf; early_tx = a child's tx grid one slot early relative to its reserved window is NOT a stimulus mutant (tx
    RTL mutants are build-time: TX_MUT)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    plans, summ = job_rank_tree_rd(fx, k_dies=k_dies, t_q=t_q, leg=leg, layer=layer)
    sp = plans
    if mutant == 'corrupt':
        tgt = [x for x in plans[0]['selection'] if plans[0]['base'] <= x < plans[0]['base'] + plans[0]['keys']][0]

        def m(keys, b0):
            k2 = keys.copy()
            k2[tgt - b0] = 0xFF80
            return k2
        sp, _ = job_rank_tree_rd(fx, k_dies=k_dies, t_q=t_q, leg=leg, layer=layer, mut=m, mut_die=0)
    lines = []
    for d, p in sp.items():
        for e, b in p['reader']:
            lines.append((e - VMUX_LAT, d, 's', b))
        lines.append((p['drain']['vi_n_edge'], d, 'n', p['drain']['beat']))
        if 'tx' in p:
            lines.append((p['tx']['ctl_vi_n'], d, 'n', p['tx']['beat']))
    lines.sort()
    keys_ = [(e, d, k) for e, d, k, _ in lines]
    assert len(set(keys_)) == len(keys_), 'two stimulus beats on one port / edge'
    with open(out / 'stim.txt', 'w') as f:
        for e, d, k, b in lines:
            f.write(f'{e} {d} {k} {b:069x}\n')
    exp = {}
    for d, p in plans.items():
        eg = {e: b for e, b in p['egress']}
        if not BK_DRAIN_SINK:     # legacy record only: the drain CTL forwarded southbound
            eg[p['drain']['vi_n_edge'] + PIN_TO_PIN] = p['drain']['beat']
        if 'tx' in p:
            eg[p['tx']['ctl_vi_n'] + PIN_TO_PIN] = p['tx']['beat']
        exp[d] = dict(vo={str(e): f'{b:x}' for e, b in sorted(eg.items())},
                      tx=(dict(beats=[f'{b:x}' for w in p['tx']['words'] for b in bk_beats(p['tx']['lane'], w)],
                               first=p['tx']['first'], last_slot=p['tx']['first'] + TX_SM * TX_R - 1) if 'tx' in p else None))
    ncyc = max(max(int(e) for e in exp[d]['vo']) for d in exp) + 300
    args = [f'+NCYC={ncyc}', f'+LEG={leg}'] + [f'+PAR{c}={pd} +PIN{c}={i}' for c, (pd, i) in summ['par'].items()]
    (out / 'args.txt').write_text(' '.join(args) + '\n')
    (out / 'exp.json').write_text(json.dumps(dict(exp=exp, mutant=mutant, summary=summ), indent=0) + '\n')
    return dict(ncyc=ncyc, closure=summ['closure'], root_last_egress=summ['root_last_egress'],
                golden=[p['golden_ok'] for p in plans.values()])


def idx_tree_frame(plans, tag, user=0, uids=None, kb=0, t0=READER_T0, p=READER_P, ik=4):
    """the IDX job source (S81-L20DIE): the type-10 TREE FRAME the root's dsdv_idx_qf receives (header + NS spec words;
    the 64 query words follow, produced by the slice's index-q op) -- every die's reader spec (B, N, k, KB, T0, P, ik,
    om) keyed by the die's tree uid (uids[d], default d).  Returns the header + spec words (512-b ints)."""
    ent = []
    for d in sorted(plans):
        pl = plans[d]
        spec = (pl['base'] & 0xFFFFF) | (pl['keys'] & 0x1FFFFF) << 20 | (K_MAX & 0x3FF) << 41 | (kb & 0x3FFFFFFF) << 51 \
            | (t0 & 0xFFFF) << 81 | (p & 0xF) << 97 | (ik & 7) << 101 | (pl['om'] & 7) << 104
        u = (uids or {}).get(d, d)
        ent.append(1 << 127 | (u & 0xFF) << 119 | spec)
    ns = -(-len(ent) // 4)
    hdr = 10 << 508 | (tag & 0xFF) << 495 | (64 + ns) << 480 | (user & 0x3FF) << 449 | ns
    words = [hdr]
    for i in range(ns):
        w = 0
        for e, x in enumerate(ent[4 * i:4 * i + 4]):
            w |= x << (128 * e)
        words.append(w)
    return words



def check_tree_bench(run_log, out_dir):
    out_dir = Path(out_dir)
    X = json.loads((out_dir / 'exp.json').read_text())
    got_vo, got_tx, faults = defaultdict(dict), defaultdict(list), []
    for ln in Path(run_log).read_text().split('\n'):
        m = re.match(r'VO (\d+) (\d+) ([0-9a-f]+)', ln)
        if m:
            got_vo[int(m.group(1))][int(m.group(2))] = int(m.group(3), 16)
        m = re.match(r'TX (\d+) (\d+) ([0-9a-f]+)', ln)
        if m:
            got_tx[int(m.group(1))].append((int(m.group(2)), int(m.group(3), 16)))
        if ln.startswith('FAULT'):
            faults.append(ln.strip())
    bad = []
    for d, ex in X['exp'].items():
        d = int(d)
        ev = {int(e): int(v, 16) for e, v in ex['vo'].items()}
        for e, v in sorted(ev.items()):
            if got_vo[d].get(e) != v:
                bad.append(dict(die=d, kind='vo', edge=e, exp=f'{v:x}'[:20], got=f'{got_vo[d].get(e, 0):x}'[:20]))
        for e, v in sorted(got_vo[d].items()):
            if e not in ev:
                bad.append(dict(die=d, kind='vo-extra', edge=e, got=f'{v:x}'[:20]))
        if ex['tx']:
            gb = [v for _, v in got_tx[d]]
            eb = [int(v, 16) for v in ex['tx']['beats']]
            if gb != eb:
                i = next((i for i, (a, b) in enumerate(zip(gb, eb)) if a != b), min(len(gb), len(eb)))
                bad.append(dict(die=d, kind='tx-seq', n_got=len(gb), n_exp=len(eb), first_diff=i))
            if got_tx[d] and (got_tx[d][0][0] != ex['tx']['first'] or got_tx[d][-1][0] > ex['tx']['last_slot']):
                bad.append(dict(die=d, kind='tx-window', got=[got_tx[d][0][0], got_tx[d][-1][0]],
                                exp=[ex['tx']['first'], ex['tx']['last_slot']]))
        elif got_tx[d]:
            bad.append(dict(die=d, kind='tx-unexpected', n=len(got_tx[d])))
    tx_span = {d: [v[0][0], v[-1][0], len(v)] for d, v in got_tx.items() if v}
    return dict(pass_=not bad and not faults, mismatches=len(bad), first=bad[:8], faults=faults[:8], tx_span=tx_span)


# ================================================================================================= compiler hook
GAPS = {
    'producer': dict(module='DV die: no index-score unit (u_rsv_* = dsdv_svc_rs has no indexer scan; hub-era dsfd_svc_idx '
                            'is not instantiated in bind_p4l3_g8) + ot_s81sl_xr / rstop V send',
                     port='u_bk_sel.vi_s (tvN_s_4S) BK ingress beats {lane, part, single, type/tag, data}',
                     missing='nothing on the die produces BK-format ingress beats: the slice V send emits xr RD beats '
                             '([8:4] hops, [12:9] src, [21 +: 16] mask, payload at [52]), whose header bits collide with '
                             'the BK lane / part / single / type fields; the scores themselves (attn.idx.score) have no '
                             'DV unit.  The bk_sel job is proven in RTL with the stimulus at its pin (bench_bk)'),
    'consumer': dict(module='u_s_4S (ot_s81sl_rstop V receive) -> TP4 collective (topk_merge, cross-die)',
                     port='u_bk_sel.vo_s (tvS_bk_sel) egress kind 5 beats (IDX / DONE words, 2 beats each)',
                     missing='the rstop delivers V kind 5 (SC) to the control plane only as router scores (SC relay); no '
                             'path forwards the IDX words to an end-slice lep for the TP4 merge or to the svc for the '
                             'gather -- checked at the bk_sel pin only'),
}


_TREE_DONE = {}      # (fixtures, layer) -> the rank tree root's last egress edge (topk_final issues after it + merge)


def lower(die, op, ctx):
    name = op['op']
    fx = ctx.get('fixtures')
    t_issue = int(math.floor(op['start']))
    res = dict(status='PARTIAL', unit='dsdv_bk_sel (u_bk_sel)', insts=[INST, 'u_seqhost'], rows=[], templates=[],
               gunit_rows=[], svc_jobs=[], files={}, events=[], bench=BENCH, deps=[],
               gap=GAPS['producer'])
    uid = die.strap(INST, 'uid') if hasattr(die, 'strap') else 0x5B
    ik = die.strap(INST, 'ik') or 4
    ek = die.strap(INST, 'ek') or 5
    assert (uid, ik, ek) == (0x5B, 4, 5), f'bk_sel straps changed: uid {uid} ik {ik} ek {ek}'
    if name.startswith('attn.cand.'):
        res['gap'] = dict(module='lower_bk', port='attn.cand.* block-maxima select',
                          missing='candidate-block select (L20) maps onto the same bk_sel job (block maxima as scores, '
                                  'k = candidate_topk_blocks); the block-max pool producer is a slice vs / svc op with no '
                                  'DV encoder -- not emitted')
        return res
    if fx is None or not (Path(fx) / 'ops.json').exists() or name.split('.')[-1] not in ('topk_local', 'topk_final'):
        res['gap'] = dict(module='lower_bk', port='fixtures', missing='no layer fixture dir in ctx: the job words '
                          '(scores, positions) come from attn.idx.score / attn.idx.topk_local')
        return res
    kd = int(ctx.get('shard_k') or shard_k(ctx.get('layer')))
    sd = int(ctx.get('shard_die') or 0)
    ops = {o['op']: o for o in (ctx.get('sched') or {}).get('ops', [])}
    key = (str(fx), str(ctx.get('layer')))
    try:
        if name.endswith('topk_local') and kd > 1 and ctx.get('idx_tree') == 'rd':
            # S81-L20DIE: the die-RTL tree (readers + vmux + bk_sel + tx); plan shaped like plan_select's
            t_q = int(math.floor(ops['attn.idx.score']['start'])) if 'attn.idx.score' in ops else t_issue
            plans, tree = job_rank_tree_rd(fx, k_dies=kd, layer=ctx.get('layer'), t_q=t_q + READER_T0)
            pr = plans[sd]
            plan = dict(pr, ingress=sorted(pr['reader']), golden=f'golden rule over the subtree of die {sd}',
                        shard=dict(k_dies=kd, die=sd, children=pr['children'], child_arrive=pr['child_arrive']))
            res['rank_tree'] = {k: v for k, v in tree.items() if k not in ('tree', 'par')}
            res['idx_frame'] = [f'{w:x}' for w in idx_tree_frame(plans, tag=0x30)]
            if 'tx' in pr:
                res['tx_job'] = {k: v for k, v in pr['tx'].items() if k not in ('words', 'beat')}
            _TREE_DONE[key] = plans[0]['egress'][-1][0]
        elif name.endswith('topk_local') and kd > 1:
            # S81-L20SPLIT: this die's job in the static rank tree (default die 0 = the rank's home / tree root:
            # its own shard + the children's merged candidates; the root's selection is the rank's topk_local).
            # The tree's readers ARE attn.idx.score: the query reaches the home die at the score op's start.
            t_q = int(math.floor(ops['attn.idx.score']['start'])) if 'attn.idx.score' in ops else t_issue
            plans, tree = job_rank_tree(fx, k_dies=kd, layer=ctx.get('layer'), t_q=t_q)
            plan = plans[sd]
            res['rank_tree'] = {k: v for k, v in tree.items() if k != 'tree'}
            _TREE_DONE[key] = plans[0]['egress'][-1][0]
        elif name.endswith('topk_local'):
            plan = job_topk_local(fx, t0=t_issue)
            _TREE_DONE[key] = plan['egress'][-1][0]
        else:
            # the TP4 final select over the 4 ranks' tree roots (4 x 512: unchanged by the shard), issued once the
            # roots' 512-sets are all-gathered: root egress + the topk_merge window (static, no ready)
            mg = ops.get('attn.idx.topk_merge')
            ready = _TREE_DONE.get(key)
            t0 = t_issue if ready is None else max(t_issue, ready + 1 + int(math.ceil(mg['end'] - mg['start']) if mg else 0))
            plan = job_topk_final(fx, t0=t0, boot_done=False, indexed13=bool(ctx.get('bk_indexed13')))
    except KeyError as x:
        res['gap'] = dict(module='lower_bk', port='fixtures', missing=f'fixture op {x} missing')
        return res
    tpl = drain_payload(uid, plan['drain']['n'], plan['drain']['d'])
    res['templates'] = [(f'{name}.drain', tpl)]
    # the VS calendar row whose CTL beat reaches u_bk_sel.vi_n at the plan edge (seq_host vo_s + tvS_seqhost age)
    L = die.links.get('tvS_seqhost')
    age = L['age_edges'] if L else 0
    v_cmd_to_vo = 11      # dv_layer_compile SEQ['v_cmd_to_vo'] (calendar issue -> seq_host vo pin), checked below
    issue = plan['drain']['vi_n_edge'] - v_cmd_to_vo - int(math.ceil(age))
    res['rows'] = [dict(eng=1, issue=issue, arg=0, what=f'{name}: bk_sel drain CTL n {plan["drain"]["n"]} d {D_DRAIN}')]
    if res.get('tx_job'):
        tj = res['tx_job']
        res['templates'].append((f'{name}.tx', tj['payload']))
        res['rows'].append(dict(eng=1, issue=tj['ctl_vi_n'] - v_cmd_to_vo - int(math.ceil(age)), arg=0,
                                what=f'{name}: dsdv_idx_tx job CTL lane {tj["lane"]} -> die {tj["parent"]} DLY {tj["dly"]}'))
    hexw = lambda b: f'{b:x}'
    res['events'].append(dict(cycle=plan['ingress'][0][0], inst=INST, port='vi_s', ports=['vi_s'], dir='in', kind='BK',
                              tag=f'{name}.ingress', valid_bit=0, payload=f'{len(plan["ingress"])} BK beats',
                              words=[[e, hexw(b), hexw(M276)] for e, b in plan['ingress']]))
    res['events'].append(dict(cycle=plan['window'][0], inst=INST, port='vo_s', ports=['vo_s'], dir='out', kind='BKOUT',
                              tag=f'{name}.egress', valid_bit=0, payload=f'{len(plan["words"])} vd words',
                              words=[[e, hexw(b), hexw(M276)] for e, b in plan['egress']]))
    res['files'][f'prog/bk/{name}.plan.json'] = json.dumps(dict(
        op=name, t_issue=t_issue, t_first_in=plan['ingress'][0][0], t_last_in=plan['t_last_in'],
        ingress_beats=len(plan['ingress']), window=plan['window'], drain=dict((k, v) for k, v in plan['drain'].items()
                                                                              if k != 'beat'),
        calendar_issue=issue, words=len(plan['words']), sel_per_quarter=plan['sel_per_quarter'],
        golden_ok=plan['golden_ok'], golden=plan['golden'], tail_budget=TAIL_BUDGET, shard=plan.get('shard'),
        indexed13=plan.get('indexed13', False), span_edges=plan['egress'][-1][0] - plan['ingress'][0][0] + 1, price_cycles=round(op['end'] - op['start'], 1)),
        indent=1) + '\n'
    res['deps'] += ['BK ingress producer (scores at vi_s, see gap)', 'IDX egress consumer (s_4S -> TP4 merge)',
                    'calendar: no southbound V CTL may land in the drain window slots on vo_s']
    res['note'] = (f'span {plan["egress"][-1][0] - plan["ingress"][0][0] + 1} edges at the rung rate vs price '
                   f'{round(op["end"] - op["start"], 1)}')
    return res


# ================================================================================================= bench files
def mut_drop_selected(kl, pl, gold):
    """mutant 'corrupt': the score of the lowest selected position becomes -inf (it must drop out of the selection)"""
    kl = [np.array(k, copy=True) for k in kl]
    tgt = int(gold[0])
    for q in range(4):
        hit = np.nonzero(np.asarray(pl[q]) == tgt)[0]
        if hit.size:
            kl[q][hit[0]] = 0xFF80
            return kl
    raise AssertionError('selected position not in any lane')


def write_bench(plan, out, mutant=None, mplan=None):
    """stim.txt: '<edge> <vi_s hex> <vi_n hex>' for every edge with traffic; exp.txt: '<edge> <vo_s hex>' for every
    expected non-zero vo_s beat (egress words + the forwarded drain CTL); meta.json.  Mutants: corrupt (the lowest
    selected position's score -> -inf in the stimulus: the selection must change), early (drain CTL 400 edges earlier:
    the window moves, every egress beat misses its compiled edge)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ins = list(plan['ingress'])
    drain = plan['drain']['vi_n_edge']
    if mutant == 'corrupt':
        assert mplan is not None and len(mplan['ingress']) == len(ins)
        ins = list(mplan['ingress'])          # stimulus from the corrupted scores, expectation from the golden plan
        assert ins != list(plan['ingress'])
    elif mutant == 'early':
        drain -= 400
    stim = {}
    for e, b in ins:
        stim.setdefault(e, [0, 0])[0] = b
    stim.setdefault(drain, [0, 0])[1] = plan['drain']['beat']
    with open(out / 'stim.txt', 'w') as f:
        for e in sorted(stim):
            f.write(f'{e} {stim[e][0]:069x} {stim[e][1]:069x}\n')
    exp = {e: b for e, b in plan['egress']}
    # canonical sink: the addressed drain CTL is consumed at the BK stop (never on vo_s).  Legacy record only
    # (OT_BK_LEGACY_FWD=1): it was forwarded southbound, vi_n pin -> relay (+1) -> vstop (+2) -> vo_s
    if not BK_DRAIN_SINK:
        exp[plan['drain']['vi_n_edge'] + PIN_TO_PIN] = plan['drain']['beat']
    with open(out / 'exp.txt', 'w') as f:
        for e in sorted(exp):
            f.write(f'{e} {exp[e]:069x}\n')
    ncyc = max(max(exp), max(stim)) + 200
    (out / 'meta.json').write_text(json.dumps(dict(ncyc=ncyc, mutant=mutant, t_first_in=ins[0][0],
                                                   t_last_in=plan['t_last_in'], window=plan['window'],
                                                   drain=dict((k, v) for k, v in plan['drain'].items() if k != 'beat'),
                                                   words=len(plan['words']), sel_per_quarter=plan['sel_per_quarter'],
                                                   golden_ok=plan['golden_ok'], golden=plan['golden'],
                                                   shard=plan.get('shard'), indexed13=plan.get('indexed13', False)), indent=1) + '\n')
    return ncyc


def check_bench(run_log, out_dir):
    """compare the bench's vo_s dump with exp.txt: every expected beat at its edge, no other non-zero beat, fault 0"""
    out_dir = Path(out_dir)
    exp = {}
    for ln in (out_dir / 'exp.txt').read_text().split('\n'):
        if ln.strip():
            e, v = ln.split()
            exp[int(e)] = int(v, 16)
    got, fault, first_eg = {}, None, None
    for ln in Path(run_log).read_text().split('\n'):
        m = re.match(r'VO (\d+) ([0-9a-f]+)', ln)
        if m:
            got[int(m.group(1))] = int(m.group(2), 16)
        m = re.match(r'FAULT (\d+)', ln)
        if m and fault is None:
            fault = int(m.group(1))
    bad = []
    for e, v in sorted(exp.items()):
        if got.get(e) != v:
            bad.append(dict(edge=e, exp=f'{v:x}'[:24], got=f'{got.get(e, 0):x}'[:24]))
    for e, v in sorted(got.items()):
        if e not in exp and v:
            bad.append(dict(edge=e, exp='0', got=f'{v:x}'[:24], extra=True))
    return dict(pass_=not bad and fault is None, mismatches=len(bad), first=bad[:8], fault_edge=fault,
                expected_beats=len(exp), got_beats=len(got))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('gen')
    g.add_argument('--fixtures', required=True)
    g.add_argument('--job', choices=('topk_local', 'topk_final', 'tree'), default='topk_local')
    g.add_argument('--out', required=True)
    g.add_argument('--mutant', default=None, choices=(None, 'corrupt', 'early'))
    g.add_argument('--indexed13', action='store_true', help='opt-in type8 explicit-index candidate packing')
    g.add_argument('--t0', type=int, default=100)
    g.add_argument('--k-dies', type=int, default=1, help='dies holding a rank\'s keys (record: SHARD_K[layer])')
    g.add_argument('--die', type=int, default=0, help='topk_local: which die of --k-dies')
    t = sub.add_parser('tree-rd', help='S81-L20DIE: the reader / tx rank-tree compose bench (tb_idx_tree)')
    t.add_argument('--fixtures', required=True)
    t.add_argument('--out', required=True)
    t.add_argument('--k-dies', type=int, default=6)
    t.add_argument('--t0', type=int, default=200)
    t.add_argument('--leg', type=int, default=LEG)
    t.add_argument('--mutant', default=None, choices=(None, 'corrupt'))
    tc = sub.add_parser('tree-rd-check')
    tc.add_argument('--run', required=True)
    tc.add_argument('--dir', required=True)
    c = sub.add_parser('check')
    c.add_argument('--run', required=True)
    c.add_argument('--dir', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'tree-rd':
        print(json.dumps(write_tree_bench(a.fixtures, a.out, a.k_dies, t_q=a.t0, leg=a.leg, mutant=a.mutant)))
        return
    if a.cmd == 'tree-rd-check':
        r = check_tree_bench(a.run, a.dir)
        (Path(a.dir) / 'check_result.json').write_text(json.dumps(r, indent=1) + '\n')
        print(('TREE_RD PASS' if r['pass_'] else 'TREE_RD FAIL'), json.dumps(r)[:900])
        raise SystemExit(0 if r['pass_'] else 1)
    if a.cmd == 'gen':
        if a.job == 'tree':
            # one die of the static rank tree (S81-L20SPLIT); the corrupt mutant drops the die's lowest SELECTED own key
            plans, _ = job_rank_tree(a.fixtures, k_dies=a.k_dies, t_q=a.t0)
            plan = plans[a.die]
            mplan = None
            if a.mutant == 'corrupt':
                own = set(range(plan['shard']['base'], plan['shard']['base'] + plan['shard']['keys']))
                tgt = np.asarray([min(x for x in plan['selection'] if x in own)])
                mplan = job_rank_tree(a.fixtures, k_dies=a.k_dies, t_q=a.t0, mut_die=a.die,
                                      mut=lambda kl, pl, g: mut_drop_selected(kl, pl, tgt))[0][a.die]
        else:
            job = (lambda **k: job_topk_local(a.fixtures, t0=a.t0, k_dies=a.k_dies, die=a.die, **k)) \
                if a.job == 'topk_local' else \
                (lambda **k: job_topk_final(a.fixtures, t0=a.t0, boot_done=True, k_dies=a.k_dies, indexed13=a.indexed13, **k))
            plan = job()
            mplan = job(mut=mut_drop_selected) if a.mutant == 'corrupt' else None
        n = write_bench(plan, a.out, a.mutant, mplan)
        print(json.dumps(dict(ncyc=n, ingress=len(plan['ingress']), t_last_in=plan['t_last_in'], window=plan['window'],
                              words=len(plan['words']), golden_ok=plan['golden_ok'], sel=plan['sel_per_quarter'],
                              shard=plan.get('shard'))))
    else:
        r = check_bench(a.run, a.dir)
        (Path(a.dir) / 'check_result.json').write_text(json.dumps(r, indent=1) + '\n')
        print(('BK_LAYER PASS' if r['pass_'] else 'BK_LAYER FAIL'), json.dumps(r)[:600])
        raise SystemExit(0 if r['pass_'] else 1)


if __name__ == '__main__':
    main()
