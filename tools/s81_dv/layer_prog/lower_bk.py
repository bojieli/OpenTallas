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
        p[7:0] uid, p[10:8] op, p[18:11] n, p[26:19] d.  The SAME beat reaches the S-tier slices (s_4S re-injects V CTL
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
from pathlib import Path

import numpy as np

OPS = [r'^attn\.idx\.(topk_local|topk_final)$', r'^attn\.cand\.(topk_local|merge|final)$']

INST = 'u_bk_sel'
LW = 7                    # dsdv_bk_vout: CTL vo edge -> first window vo edge = LW + d
RELAY = 1                 # dsdv_bk_sel u_rs / u_rn: +1 flop per direction
FWD = 2                   # ot_dsdv_vstop forward: 2 flops (input, output)
PIN_TO_PIN = RELAY + FWD - 1   # bench edge convention (value sampled at edge e -> vo after edge e + 2), measured
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


def ingress_schedule(lanes, t0, ik=4):
    """lane words -> [(edge, beat)] on vi_s: HDRs first (one per lane), then the lanes' words round-robin, each word's
    beats in consecutive slots, one V beat per edge"""
    beats = []
    q = [list(ws) for ws in lanes]
    order = []
    for l in range(4):
        order.append((l, q[l].pop(0)))
    while any(q):
        for l in range(4):
            if q[l]:
                order.append((l, q[l].pop(0)))
    t = t0
    for l, w in order:
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


def plan_select(keys_lanes, pos_lanes, bases, k, tag, t0, sparse=False, boot_done=True, ik=4, ek=5, uid=0x5B):
    """the whole bk_sel job: ingress beats, drain CTL, expected egress beats at vo_s (bench / replay timing)"""
    lanes = []
    for q in range(4):
        if sparse:
            lanes.append(lane_words_sparse(keys_lanes[q], pos_lanes[q], bases[q], k, q, tag))
        else:
            lanes.append(lane_words_dense(keys_lanes[q], bases[q], len(keys_lanes[q]), k, q, tag))
    ins = ingress_schedule(lanes, t0, ik)
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


# ================================================================================================= fixtures -> jobs
def load_op(fx, name):
    meta = json.loads((Path(fx) / 'ops.json').read_text())[name]
    return np.fromfile(Path(fx) / 'ops' / f'{name}.bin', dtype=meta['dtype']).reshape(meta['shape'])


def job_topk_local(fx, rank=0, t0=100, tag=0x21, boot_done=True, mut=None):
    s = load_op(fx, 'attn.idx.score')
    n = s.size
    q4 = n // 4
    keys = bf16_key(s[rank * q4:(rank + 1) * q4])
    qs = quarters_dense(rank * q4, q4)
    kl = [keys[b - rank * q4:b - rank * q4 + m] for b, m in qs]
    pl = [np.arange(b, b + m) for b, m in qs]
    if mut:
        kl = mut(kl, pl, np.sort(load_op(fx, 'attn.idx.topk_local')[rank * min(K_MAX, q4):(rank + 1) * min(K_MAX, q4)]))
    k = min(K_MAX, q4)
    plan = plan_select(kl, pl, [b for b, _ in qs], k, tag, t0, boot_done=boot_done)
    gold = np.sort(load_op(fx, 'attn.idx.topk_local')[rank * k:(rank + 1) * k])
    plan['golden_ok'] = bool(np.array_equal(np.asarray(plan['selection']), gold))
    plan['golden'] = 'attn.idx.topk_local rank %d (sorted)' % rank
    return plan


def job_topk_final(fx, t0=100, tag=0x22, boot_done=False, mut=None):
    s = load_op(fx, 'attn.idx.score')
    n = s.size
    q4 = n // 4
    loc = load_op(fx, 'attn.idx.topk_local')
    k = min(K_MAX, q4)
    kl, pl, bases = [], [], []
    for r in range(4):
        p = np.sort(loc[r * k:(r + 1) * k])
        pl.append(p)
        kl.append(bf16_key(s[p]))
        bases.append(int(p[0]) // 16 * 16 if p.size else r * q4)
    if mut:
        kl = mut(kl, pl, np.sort(load_op(fx, 'attn.idx.topk_final')))
    plan = plan_select(kl, pl, bases, k, tag, t0, sparse=True, boot_done=boot_done)
    gold = np.sort(load_op(fx, 'attn.idx.topk_final'))
    plan['golden_ok'] = bool(np.array_equal(np.asarray(plan['selection']), gold))
    plan['golden'] = 'attn.idx.topk_final (sorted)'
    return plan


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
    try:
        plan = job_topk_local(fx, t0=t_issue) if name.endswith('topk_local') else \
            job_topk_final(fx, t0=t_issue, boot_done=False)
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
        golden_ok=plan['golden_ok'], golden=plan['golden'], tail_budget=TAIL_BUDGET,
        span_edges=plan['egress'][-1][0] - plan['ingress'][0][0] + 1, price_cycles=round(op['end'] - op['start'], 1)),
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
    # the drain CTL itself is forwarded southbound: vi_n pin -> relay (+1) -> vstop (+2) -> vo_s
    exp[plan['drain']['vi_n_edge'] + PIN_TO_PIN] = plan['drain']['beat']
    with open(out / 'exp.txt', 'w') as f:
        for e in sorted(exp):
            f.write(f'{e} {exp[e]:069x}\n')
    ncyc = max(max(exp), max(stim)) + 200
    (out / 'meta.json').write_text(json.dumps(dict(ncyc=ncyc, mutant=mutant, t_first_in=ins[0][0],
                                                   t_last_in=plan['t_last_in'], window=plan['window'],
                                                   drain=dict((k, v) for k, v in plan['drain'].items() if k != 'beat'),
                                                   words=len(plan['words']), sel_per_quarter=plan['sel_per_quarter'],
                                                   golden_ok=plan['golden_ok'], golden=plan['golden']), indent=1) + '\n')
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
    g.add_argument('--job', choices=('topk_local', 'topk_final'), default='topk_local')
    g.add_argument('--out', required=True)
    g.add_argument('--mutant', default=None, choices=(None, 'corrupt', 'early'))
    g.add_argument('--t0', type=int, default=100)
    c = sub.add_parser('check')
    c.add_argument('--run', required=True)
    c.add_argument('--dir', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'gen':
        job = (lambda **k: job_topk_local(a.fixtures, t0=a.t0, **k)) if a.job == 'topk_local' else \
            (lambda **k: job_topk_final(a.fixtures, t0=a.t0, boot_done=True, **k))
        plan = job()
        mplan = job(mut=mut_drop_selected) if a.mutant == 'corrupt' else None
        n = write_bench(plan, a.out, a.mutant, mplan)
        print(json.dumps(dict(ncyc=n, ingress=len(plan['ingress']), t_last_in=plan['t_last_in'], window=plan['window'],
                              words=len(plan['words']), golden_ok=plan['golden_ok'], sel=plan['sel_per_quarter'])))
    else:
        r = check_bench(a.run, a.dir)
        (Path(a.dir) / 'check_result.json').write_text(json.dumps(r, indent=1) + '\n')
        print(('BK_LAYER PASS' if r['pass_'] else 'BK_LAYER FAIL'), json.dumps(r)[:600])
        raise SystemExit(0 if r['pass_'] else 1)


if __name__ == '__main__':
    main()
