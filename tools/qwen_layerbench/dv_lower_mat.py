#!/usr/bin/env python3
"""dv_lower_mat: DV slice lowering of the matrix-side command families (QLB-C4b/3b 10-18, layer-bench gap G-C4).

dv_lower.py (QLB-C4) lowered the slice map, row ownership, the PROG image and the RMSNorm sum of squares.  This module
lowers the families that move matvec results through the qfd_dv_slice2 chain (rtl/qwen_dv/qfd_dv_slice2.sv), and
splices the lowered entries into the ctlm decode calendar.  The vector families (norm apply, residual, QK-norm, RoPE,
SiLU) are tools/qwen_layerbench/dv_lower_vec.py (QLB-C4b/3a); this module allocates its VM regions from the TOP of the
16,384-element slice VM and refuses any overlap with dv_lower.vm_map.

 1. STN (every matvec: qkv, o, gate/up, down, LM head): ONE STN command per slice per round (the station's dbase is read
    at r_v time, j / sbase at the finished word: a mid-op cfg would re-address in-flight words, so a round's STN lands
    after the previous round's last result and before its first finished word).  mode by split level (L7 0 / L8 1 / L9
    receiver 2 + sender 3), wsrc 0 (BF16 row scale from BTAB at sbase + j), nwords = the round's 16-row words,
    destination: qkv / gate-up -> slice-local VM (QKV / GU regions; GU = gate block then up block = the PC19 SiLU
    operand layout), o / down -> AR with dbase = 128 b = the global row element address (the AR word tag), LM head ->
    none (amax 1, dbase = die row0 + 128 b = the vocabulary row: the argmax index).
    BTAB map: one per-slice layout (qkv 0, o 8, gu 32, down 48, lm_head 72 .. 271 of 512 words) + its kind-2 stream
    table words built from the matrices' BF16 row scales -- EXCEPT o / down (AR destinations): the ISA all-reduces the
    RAW o / down partials and applies the post-TP scale in the residual (PC19 / PC28 = the DV residual's pscale), so
    their station row scale is BF16 1.0 (station_row_scales; QW-ODSCALE 10-19, exact vs the TP8 ISA gold partials).
    TILE-DELIVERY CONTRACT (output, the schedule the ME / xhead calendar must deliver): the edge of every round's far
    cluster word at each slice's rs pins.  For AR destinations the AR words of all 12 slices share ONE outbound lane
    (2 edges a hop, a pass word and an own word on one edge is a port fault) and io_collective takes one word an edge
    at c + 1 + w: the lowering staggers the deliveries so word w of the message (global row order: block b, word j ->
    w = 8 b + j) leaves dvs_W5 on edge M0 + w -- slice s receives block b's far words at M0 + 8 b + j - l8_ar - 2 s.
    The as-built hr chain delivers every slice the same go 1 edge a hop apart; that delivery collides (mutant
    'nostagger').
 2. XC: the collective command of a message addressed to dvs_W5 ONLY (dst 0: the only slice whose cc_o reaches
    io_collective), on the edge that puts word 0 on io_collective's in pins at the command's c + 1 (cmd pin register +
    1): cc_o at W5 on edge M0 - 2 (cc and ar lanes have equal relay ages, 2 / 2).  Reduce: words = message words,
    mode 0; gather (LM-head token): words 1, mode 1.  Today's ctlm XC is dst 15 (12 cc words; mutant 'xc_bc').
 3. LM-head AMAX: AMAX clear (dst 15), ROOT cfg (root dvs_W5, amnb = the 6 L9 receivers, the RMSNorm fields kept),
    ARX arm on the root, 25 rounds of amax STN, one AMAX emit per receiver with a collision-free AMI / AMV schedule on
    the downward scalar chain, the root's TOK, the ARX AR word, XC gather, AMAX GATHER (dst 15) before the 8 rank
    returns (io_collective all-gather timing out = c + LU + LS + 8 + k, LU / LS = the die's OT_QFDS_LU / LS).
 4. Stage 0 (embedding em_base): the embedding row's 256 words arrive on the D2D return chain at the provider's slots
    (one an edge, word w = elements 16 w ..); each slice lands exactly its residual blocks into its X region: per owned
    block a PORTS arm (em_base = X + 128 i, em_en) entering at t_b - s - 1 and a disarm entering at t_b + 7 - s
    (exact: em_en and em_k reset on the PORTS edge; derived from the slice2 registers, checked by the bench).
 5. LM-head ME programme lowering (token_source_plan head_profiles: SSQ, rsqrt, apply, 4 amax chunks, END): the
    head-side rows {cycle, pc, unit, last} of a PER-SEGMENT fixed-issue calendar at the LM-head segment base, with
    round deliveries tied to the DV-side STN schedule.  DEPENDENCY: the current RTL (ot_qfd_tt_ctlm_head_static_rk /
    split_static) arms u_fixed_issue only at prog_base 0 with one 8-row calendar per image (QLB-C4b item 2,
    claude/qlb-c4b-lmh-1018, fixes it); the DV slice side of the LM head runs on the current RTL and is benched.
 6. SPLICE into the ctlm decode calendar (ctlm_image.py plan): the SU PC0 / PC15 / PC23 broadcast commands are replaced
    by dv_lower's per-slice SSQ entries, the XC by the dst-0 command, and the matvec STN commands are added at their ME
    issue (the first-round STN lands with the go at the slice); the result is re-checked with ctlm_image's cmd_cal
    model.

RTL constants are MEASURED (rtl/test/qwen_dv/dv_lower_mat_bench.py --calibrate, Verilator 5.050):
results/rtl/qlb_c4b_1018/dv_lower_mat/stn_ages.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import dv_lower as D

# ROOT4-QWMERGE 10-19: STN kc (k steps per (round, j); dv_lower.cmd_stn kc is mandatory since MU-DQ-SLICEKC adc266442) =
# tools/qwen_static_schedule/mu_tok_cases.MATVEC_KC under this lowering's op names (o = o_proj, gu = gate_up)
STN_KC = {'qkv': 8, 'o': 2, 'gu': 32, 'down': 6, 'lm_head': 8}

ROOT = D.ROOT
STN_AGES = 'results/rtl/qlb_c4b_1018/dv_lower_mat/stn_ages.json'
N, BLOCK, VM_EL = D.NSLICE, D.BLOCK, D.VM_EL
MODE = {7: 0, 8: 1, 9: 2}
DST_VM, DST_AR = 1, 2
BT = dict(qkv=0, o=8, gu=32, down=48, lm_head=72)      # BTAB word base per matrix (one layout for every slice)
BT_WORDS = 512
# Bound stations reject config overlapping ANY producer word, including the near half
# which arrives SKEW=14 edges before far. Pre-arm before that half and its config fanout.
STN_LEAD = 20 if D.SLICE_RTL == 's8' else 6
# l8_ar already includes the local result latency plus the outward register stages.
# The bound ctl own_ch and fdn ch_dn_o are two outgoing registers, so its
# local station result precedes the measured AR pin edge by two. Reconfigure
# after that local result; legacy slice2 keeps its historical sixteen-edge guard.
RV_SLACK = -2 if D.SLICE_RTL == 's8' else 16
XC_TO_WORD0 = 2         # cc_o at W5 on edge X -> io_collective cmd pin X + a, internal c = X + a + 1, word 0 at in pins
                        # c + 1 = X + a + 2 (a = 2 on both the cc and the ar lanes: dv2f14bq relay ages)
LU, LS = 53, 376        # qfd_io_collective_static OT_QFDS_LU / OT_QFDS_LS defaults (die params; Q-COLLCAL: LS 377 open)
RET_AGE = 2             # io_collective.out_* -> dvs_W5.r*_wi age edges (relay table)
LM_PERIOD = 80          # DV-side minimum LM-head round spacing used by the bench (the ROM tiles' priced round rate rules)
AMNB = 6


class LowerError(D.LowerError):
    pass


def load_ages(path=None):
    path = path or STN_AGES
    p = ROOT / path
    if not p.exists():
        raise LowerError(f'{path} missing: measure it (rtl/test/qwen_dv/dv_lower_mat_bench.py --calibrate)')
    a = json.loads(p.read_text())
    for k in ('l8_ar', 'ar_hop', 'amax_ami', 'arx_after_amv', 'xc_cc'):
        if k not in a:
            raise LowerError(f'{path}: no {k}')
    if a['ar_hop'] != 2:
        raise LowerError(f'measured AR outbound hop {a["ar_hop"]} != 2 (slice2 chu_q pin + ch_dn_o register)')
    return a


# ------------------------------------------------------------------------------------------------ VM regions
def vm_regions(own):
    """matrix-side slice-local regions, allocated from the top of the VM (dv_lower_vec allocates from the bottom)."""
    regs = [('GU', 2 * BLOCK, 'gate/up results: gate block (lower pair, j 0..7) then up block (j 8..15) = PC19 a / a + 128'),
            ('QKV', BLOCK, 'qkv results on the L9 receiver slices (one 128-row block)')]
    out, top = {}, VM_EL
    for n, size, what in regs:
        top -= size
        out[n] = dict(base=top, size=size, what=what)
    low = D.vm_map(own)
    hi = max(r['base'] + r['size'] for r in low.values())
    if hi > min(r['base'] for r in out.values()):
        raise LowerError(f'matrix regions {out} overlap dv_lower.vm_map (top {hi})')
    return out


# ------------------------------------------------------------------------------------------------ cmd chain
class Chain:
    """dvs_W5.cmd_wi takes one command an edge; a command for slice s lands cmd_arrival[s] edges after its entry."""

    def __init__(self, smap):
        self.arr = smap['cmd_arrival']
        self.used = {}

    def put(self, land, dst, cmd, label, earliest=None):
        """enter as late as possible for a landing on or before `land` (dst 15: land = entry)"""
        a = 0 if dst == 15 else self.arr[dst]
        e = land - a
        while e in self.used:
            e -= 1
        if earliest is not None and e + a < earliest:
            raise LowerError(f'{label}: no free chain edge in [{earliest}, {land}] at the slice')
        self.used[e] = (cmd, label)
        return e

    def commands(self):
        return [dict(edge=e, cmd=f'{c:029x}', label=l) for e, (c, l) in sorted(self.used.items())]


# ------------------------------------------------------------------------------------------------ STN
def rounds_of(own, name):
    """per round: [(slice, [blocks in finishing order], role)]  role 'fin' (finishing slice) / 'snd' (L9 sender)"""
    m = own[name]
    out = []
    for r in range(m['rounds']):
        units = {}
        for b in m['blocks']:
            if b['round'] == r:
                units.setdefault(b['slice'], []).append(b)
        lst = []
        for s in sorted(units):
            bl = sorted(units[s], key=lambda b: (b['pair'] or 0, b['block']))
            lst.append((s, bl, 'fin'))
            if m['level'] == 9:
                lst.append((s ^ 1, bl, 'snd'))
        out.append(lst)
    return out


def words_of(b):
    return math.ceil((b['rows'][1] - b['rows'][0]) / 16)


def btab_layout(own):
    """per matrix per slice: sbase of each finishing block (8 words a block, round order)"""
    lay = {}
    for name, base in BT.items():
        per = {}
        for rl in rounds_of(own, name):
            for s, bl, role in rl:
                if role != 'fin':
                    continue
                for b in bl:
                    k = len(per.setdefault(s, []))
                    per[s].append(dict(block=b['block'], sbase=base + 8 * k, words=words_of(b)))
        nxt = min([v for v in BT.values() if v > base] + [BT_WORDS])
        for s, lst in per.items():
            if lst[-1]['sbase'] + 8 > nxt:
                raise LowerError(f'BTAB {name} slice {s}: {len(lst)} blocks overflow [{base}, {nxt})')
        lay[name] = per
    return lay


AR_UNSCALED = ('o', 'down')     # ISA: AR of RAW partials, post-TP scale in the residual (pscale) -> station scale 1.0


def station_row_scales(name, matrix_scales):
    """the BF16 row scale the DV station applies (BTAB) for matrix `name`, from the matrix's own row scales: o / down
    (AR destinations) -> 1.0 (the post-TP scale belongs to the residual, after the all-reduce); others = the matrix's."""
    import numpy as np
    sc = np.asarray(matrix_scales, dtype=np.float32)
    return np.ones(len(sc), dtype=np.float32) if name in AR_UNSCALED else sc


def btab_stream(lay, scales, mutant=None):
    """{slice: [(word0, payload)]} kind-2 table words (4 BTAB words = 64 BF16 a stream word) from {matrix: FP32 BF16-valued
    MATRIX row scales} (station_row_scales applied: o / down emit 1.0); rows of a partial block pad with 0.
    mutant 'rawscale' = the pre-QW-ODSCALE lowering (o / down BTAB = the matrix scales)."""
    import numpy as np
    out = {}
    for name, sc in scales.items():
        sc = np.asarray(sc, dtype=np.float32) if mutant == 'rawscale' else station_row_scales(name, sc)
        hw = (sc.view(np.uint32) >> 16).astype(np.uint64)
        if np.any((sc.view(np.uint32) & 0xFFFF) != 0):
            raise LowerError(f'{name}: scales are not BF16 values')
        for s, lst in lay[name].items():
            words = {}
            for e in lst:
                r0 = BLOCK * e['block']
                for w in range(8):
                    vals = [int(hw[r]) if r < len(hw) else 0 for r in range(r0 + 16 * w, r0 + 16 * w + 16)]
                    words[e['sbase'] + w] = sum(v << (16 * i) for i, v in enumerate(vals))
            for w0 in sorted({w // 4 * 4 for w in words}):
                pay = sum(words.get(w0 + i, 0) << (256 * i) for i in range(4))
                out.setdefault(s, []).append((w0, pay))
    return out


def lower_matvec(name, t0, ages, chain, own=None, regions=None, row0=0, period=LM_PERIOD, mutant=None, running_k=False):
    """the STN commands of one matvec op + the tile-delivery contract + the expected results.
    t0: AR destinations -> the edge AR word 0 leaves dvs_W5 (S0AR); otherwise the first round's far-word edge."""
    own = own or D.ownership()
    regions = regions or vm_regions(own)
    m = own[name]
    lv = m['level']
    lay = btab_layout(own)[name]
    dst = {'qkv': DST_VM, 'gu': DST_VM, 'o': DST_AR, 'down': DST_AR, 'lm_head': 0}[name]
    amax = int(name == 'lm_head')
    LAR = ages['l8_ar']
    rv = LAR + (7 if lv == 9 else 0) - (7 if lv == 7 else 0)   # far word -> own AR word (L8 measured; L9 +1 add, L7 -1)
    kc = STN_KC[name]
    prefix_edges = (kc - 1) * 8 if running_k else 0
    if running_k and dst != DST_AR:
        # All input k blocks must follow cfg, after the previous round drains.
        period = max(period, prefix_edges + rv + RV_SLACK + STN_LEAD + 8)
    deliveries, stn, exp_ar, exp_vm, last_far = [], [], [], {}, {}
    for r, rl in enumerate(rounds_of(own, name)):
        for s, bl, role in rl:
            if dst == DST_AR:
                if mutant == 'nostagger':
                    far = [t0 + 96 * r - LAR + j for j in range(words_of(bl[0]))]
                else:
                    far = [t0 + 8 * bl[0]['block'] + j - LAR - 2 * s for j in range(words_of(bl[0]))]
            else:
                far = [t0 + r * period + j for j in range(sum(words_of(b) for b in bl) if lv != 7 else words_of(bl[0]))]
            nw = sum(words_of(b) for b in bl)
            land = far[0] - prefix_edges - STN_LEAD
            lo = last_far.get(s, -10 ** 9) + rv + RV_SLACK
            if land < lo:
                raise LowerError(f'{name} round {r} slice {s}: STN window empty (land {land} < previous results {lo})')
            if role == 'snd':
                c = D.cmd_stn(s, 3, 0, nw, 0, 0, 0, kc=STN_KC[name])
            else:
                k = [e['block'] for e in lay[s]].index(bl[0]['block'])
                sb = lay[s][k]['sbase'] + (1 if mutant == 'sbase1' else 0)
                if dst == DST_VM:
                    reg = regions['GU' if name == 'gu' else 'QKV']
                    db = reg['base'] + (BLOCK * k if name == 'qkv' else 0)
                elif dst == DST_AR:
                    db = BLOCK * bl[0]['block']
                else:
                    db = 0 if mutant == 'amax_local' else row0 + BLOCK * bl[0]['block']
                c = D.cmd_stn(s, MODE[lv], 0, nw, sb, dst, db, kc=STN_KC[name], amax=amax)
                for j in range(nw):
                    b = bl[j // 8] if lv == 7 else bl[0]
                    jj = j % 8 if lv == 7 else j
                    if dst == DST_AR:
                        exp_ar.append(dict(edge=t0 + 8 * b['block'] + jj, tag=db + 16 * j, last=int(j == nw - 1),
                                           row=BLOCK * b['block'] + 16 * jj))
                    elif dst == DST_VM:
                        exp_vm.setdefault(s, {})[db + 16 * j] = BLOCK * b['block'] + 16 * jj
            e = chain.put(land, s, c, f'STN {name} r{r} s{s} {role}', earliest=lo)
            stn.append(dict(slice=s, round=r, role=role, entry=e, land=e + chain.arr[s], cmd=f'{c:029x}', nwords=nw,
                            blocks=[b['block'] for b in bl]))
            # far-word deliveries: L7 lower pair (rs_s) = bl[0], upper pair (rs_n) = bl[1], same edges
            deliveries.append(dict(slice=s, round=r, role=role, far=far, blocks=[b['block'] for b in bl],
                                   words=[words_of(b) for b in bl]))
            last_far[s] = far[-1]
    return dict(name=name, level=lv, mode=MODE[lv], dst=dst, kc=kc, running_k=running_k,
                k_block_words=8, period=period, prefix_edges=prefix_edges,
                stn=stn, deliveries=deliveries, expected_ar=exp_ar,
                expected_vm=exp_vm, btab=lay)


def ar_collisions(low, ages):
    """outbound AR lane occupancy {(slice, edge at its ch_dn_o)}: one word a slice an edge (a pass + an own word faults)"""
    occ = {}
    for d in low['deliveries']:
        if d['role'] != 'fin':
            continue
        s = d['slice']
        for f in d['far']:
            out0 = f + ages['l8_ar']          # leaves W5 (slice 0) this edge when s = 0
            for m in range(s, -1, -1):
                occ.setdefault((m, out0 + 2 * s - 2 * m), []).append(s)
    return sorted((k, v) for k, v in occ.items() if len(v) > 1)


def lower_xc(chain, ages, word0_at_w5, words, tag, mode=0, mutant=None):
    x = word0_at_w5 - XC_TO_WORD0               # cc_o of W5 valid (S0CC) on this edge
    entry = x - ages['xc_cc']
    dst = 15 if mutant == 'xc_bc' else 0
    c = D.cmd_xc(dst, mode, words, tag)
    if entry in chain.used:
        raise LowerError(f'XC tag {tag}: chain edge {entry} taken (the XC edge is exact)')
    chain.used[entry] = (c, f'XC tag {tag} words {words} mode {mode} dst {dst}')
    return dict(entry=entry, cc_edge=x, cmd=f'{c:029x}', cc_word=(1 << 49) | (mode << 48) | (words << 32) | tag, dst=dst)


def ar_framed(expected_ar, xc):
    """QW-LAYERGAP 10-20: the AR words of one message as the qfd_dv_slice2 ARF 1 framer stamps them at dvs_W5 (the
    io_collective in-pin contract): tag = the XC tag on every word, last only on the message's last word.  Fails closed
    unless the XC (cc edge) precedes word 0 by XC_TO_WORD0 and the message has exactly `words` words."""
    words = (xc['cc_word'] >> 32) & 0xFFFF
    tag = xc['cc_word'] & 0xFFFFFFFF
    ex = sorted(expected_ar, key=lambda e: e['edge'])
    if len(ex) != words:
        raise LowerError(f'XC tag {tag:#x}: {len(ex)} AR words, XC says {words}')
    if ex and ex[0]['edge'] - xc['cc_edge'] < XC_TO_WORD0:
        raise LowerError(f'XC tag {tag:#x}: cc edge {xc["cc_edge"]} not {XC_TO_WORD0} edges before word 0 ({ex[0]["edge"]})')
    return [dict(e, tag=tag, last=int(i == len(ex) - 1)) for i, e in enumerate(ex)]


def ar_framer_order(messages):
    """messages [(xc, expected_ar)]: the single-message framer needs XC n + 1 at / after the last word of message n"""
    m = sorted(messages, key=lambda t: t[0]['cc_edge'])
    for (xa, ea), (xb, _) in zip(m, m[1:]):
        if xb['cc_edge'] < max(e['edge'] for e in ea):
            raise LowerError(f'XC {xb["cc_word"] & 0xFFFFFFFF:#x} arms before the last word of the previous message')
    return True


# ------------------------------------------------------------------------------------------------ LM head (DV side)
def lower_lm(t0, ages, chain, row0=0, period=LM_PERIOD, die_rank=0, mutant=None, running_k=False):
    """the LM-head DV schedule: clear / ROOT / ARX before the rounds, the amax STN rounds from t0 (first far word),
    collision-free emits, the token, ARX + XC gather, GATHER, the 8 rank returns' edges."""
    own = D.ownership()
    smap = D.slice_map()
    lw = D.lower()                               # the RMSNorm ROOT fields (one ROOT cfg serves the norm and the head)
    rt = lw['root']
    pre = t0 - 60
    if D.SLICE_RTL == 's8':
        # Pair-head senders have no local candidate and never emit. Opening them
        # would leave MU state open and make the next token's clear fault.
        receivers = sorted({b['slice'] for b in own['lm_head']['blocks']})
        for i, s in enumerate(receivers):
            chain.put(pre + i + smap['cmd_arrival'][s], s, D.cmd_amax(s, clear=1), f'AMAX clear s{s}')
    else:
        c = D.cmd_amax(15, clear=1)
        chain.put(pre, 15, c, 'AMAX clear (all)')
    for s in range(N):
        c = D.cmd_root(s, int(s == 0), rt['nb'], rt['ss'], fuse=int(s == 0), rx=rt['rx'], eps=rt['eps'] if s == 0 else 0,
                       k=rt['k'] if s == 0 else 0, amnb=(AMNB - (1 if mutant == 'amnb5' else 0)) if s == 0 else 0)
        chain.put(pre + 8 + s, s, c, f'ROOT s{s}' + (' (root, amnb 6)' if s == 0 else ''))
    chain.put(pre + 30, 0, D.cmd_amax(0, arx=1), 'AMAX ARX arm (root)')
    mv = lower_matvec('lm_head', t0, ages, chain, own=own, row0=row0, period=period, mutant=mutant, running_k=running_k)
    rv = ages['l8_ar'] + 7
    last = {d['slice']: d['far'][-1] for d in mv['deliveries'] if d['role'] == 'fin'}
    recv = sorted(last)
    if len(recv) != AMNB:
        raise LowerError(f'{len(recv)} LM-head receivers (amnb {AMNB})')
    ready = {s: last[s] + rv + 8 for s in recv}       # + the 5-edge compare tree and the running best
    # the root emits first (its candidate merges locally); far receivers next, collision-free on the dn chain
    occ, emits = {}, {}
    if 0 in ready:
        e0 = chain.put(ready[0], 0, D.cmd_amax(0, emit=1), 'AMAX emit s0 (root)', earliest=ready[0] - 40)
        emits[0] = e0 + smap['cmd_arrival'][0]
    t = max(ready.values())
    for s in sorted((x for x in recv if x), reverse=True):
        while True:
            land = t
            ami = land + ages['amax_ami']
            keys = [(m, ami + b + D.SC_HOP * (s - m)) for b in (0, 1) for m in range(s, 0, -1)]
            if not any(k in occ for k in keys) and (land - smap['cmd_arrival'][s]) not in chain.used:
                break
            t += 1
        for k in keys:
            occ[k] = s
        e = chain.put(land, s, D.cmd_amax(s, emit=1), f'AMAX emit s{s}')
        emits[s] = e + smap['cmd_arrival'][s]
        t += 1
    last_amv_s1 = max(emits[s] + ages['amax_ami'] + 1 + D.SC_HOP * (s - 1) for s in recv if s)
    arx_at_w5 = last_amv_s1 + ages['arx_after_amv']
    xc = lower_xc(chain, ages, arx_at_w5, 1, 0x4C4D0000 | die_rank, mode=1)
    g0 = xc['cc_edge'] + LU + LS + 13            # word k of the all-gather at the dvs_W5 return pin (TB ret0)
    eg = chain.put(arx_at_w5 + 4, 15, D.cmd_amax(15, gather=1), 'AMAX GATHER arm (all)')
    if eg + 2 * (N - 1) + 2 >= g0:
        raise LowerError('GATHER arm lands after the first gather return')
    return dict(matvec=mv, emits=emits, arx_at_w5=arx_at_w5, xc=xc, gather_first=g0, die_rank=die_rank, row0=row0,
                amnb=AMNB, scalar_occupancy=len(occ))


# ------------------------------------------------------------------------------------------------ stage 0 embedding
def lower_embed(t0, chain, mutant=None):
    """word w of the embedding row at the dvs_W5 D2D return pin on edge t0 + w; each slice lands its residual blocks."""
    own = D.ownership()
    vm = D.vm_map(own)
    res = own['residual']['blocks_per_slice']
    sh = 1 if mutant == 'emb_late' else 0
    land = {}
    for s in range(N):
        for i, b in enumerate(res[s]):
            tb = t0 + 8 * b
            for e, cmd, lab in ((tb - s - 1 + sh, D.cmd_ports(s, em_base=vm['X']['base'] + BLOCK * i, em_en=1), 'arm'),
                                (tb + 7 - s + sh, D.cmd_ports(s, em_base=vm['X']['base'] + BLOCK * i, em_en=0), 'disarm')):
                if e in chain.used:
                    raise LowerError(f'embedding PORTS {lab} s{s} b{b}: chain edge {e} taken (the edge is exact)')
                chain.used[e] = (cmd, f'PORTS em {lab} s{s} block {b}')
            for j in range(8):
                land.setdefault(s, {})[vm['X']['base'] + BLOCK * i + 16 * j] = BLOCK * b + 16 * j
    return dict(word0=t0, words=4096 // 16, expected_vm=land, x_base=vm['X']['base'],
                rule='arm enters t_b - s - 1, disarm t_b + 7 - s (t_b = word 8 b at the W5 return pin)')


# ------------------------------------------------------------------------------------------------ 5. LM-head ME programme
def lm_programme():
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import hdc_qwen_fullshape_isa_w12 as ISA
    p = json.loads((ROOT / D.PLAN).read_text())
    hp = p['head_profiles']
    out = []
    for h in hp:
        ops = [ISA.decode_instruction(int(w, 16)) for w in h['program_hex']]
        me = [(pc, o) for pc, o in enumerate(ops) if o['unit'] == 1]
        if [o['me_amax'] for _, o in me] != [1] * len(me) or any(o['me_split'] != 9 for _, o in me):
            raise LowerError(f'LM-head die {h["die"]}: ME ops are not all split-9 amax chunks')
        rows = sum(o['me_nout'] for _, o in me)
        if rows != p['head_geometry']['rows']:
            raise LowerError(f'LM-head die {h["die"]}: chunk rows {rows} != {p["head_geometry"]["rows"]}')
        out.append(dict(die=h['die'], row0=h['row0'], ops=ops, me=me, words=h['program_hex']))
    return out


def lm_calendar(lm, ages, tile_first, seg_base_pc=0):
    """per-segment ME8 rows of the LM-head programme: ME chunk c issues so that its first round's far words reach the
    slices at the DV schedule's round edge (tile_first = ME issue edge -> first far word, the xhead delivery constant
    no tool compiles yet).  Cycles are relative to the LM-head segment start (the per-segment calendar of item 2)."""
    die = lm_programme()[0]
    rnd = 0
    rows = []
    for pc, o in die['me']:
        nblk = math.ceil(o['me_nout'] / BLOCK)
        first_far = lm['matvec']['deliveries'][2 * 6 * rnd]['far'][0] if rnd < 25 else None
        rows.append(dict(pc=pc + seg_base_pc, unit=1, edge=first_far - tile_first, round0=rnd, blocks=nblk))
        rnd += math.ceil(nblk / 6)
    end_pc = next(pc for pc, o in enumerate(die['ops']) if o['unit'] == 0)
    rows.append(dict(pc=end_pc + seg_base_pc, unit=0, edge=lm['gather_first'] + 8 + 8, round0=None, blocks=0))
    s0 = rows[0]['edge'] - 2
    for n, r in enumerate(rows):
        r['cycle'] = r['edge'] - s0
        r['hex'] = f"{r['cycle'] | (r['pc'] << 32) | (r['unit'] << 44) | (int(n == len(rows) - 1) << 46):012x}"
    for a, b in zip(rows, rows[1:]):
        if b['cycle'] <= a['cycle']:
            raise LowerError('LM-head calendar rows not strictly increasing')
    return dict(rows=rows, segment_start_edge=s0, tile_first=tile_first,
                dependency='per-segment fixed-issue calendar armed at a nonzero prog_base: QLB-C4b item 2 '
                           '(claude/qlb-c4b-lmh-1018); current RTL arms u_fixed_issue only at prog_base 0')


# ------------------------------------------------------------------------------------------------ 6. splice
def splice(tile_first=40, ctlm_args=None, ages=None):
    """the ctlm decode calendar with the lowered entries: per-slice SSQ (dv_lower) in place of the SU PC0/15/23
    broadcasts, XC dst 0, STN of every matvec at its ME issue.  Returns the event list at the tt_ctlm.cmd output and the
    cmd_cal model check."""
    import argparse
    import ctlm_image as CI
    a = argparse.Namespace(program=CI.DEF_PROGRAM, lowering=CI.DEF_LOWERING, token_path=CI.DEF_TOKEN_PATH,
                           relay=CI.DEF_RELAY, lane_ages=None, stage=1, sys_face_events=CI.DEF_SF_EVENTS, period=None,
                           lead_margin=2, xpf_transport_edges=None, me_observe_edges=1, su_first_write=12, dv_lower=False,
                           tload=False, lm_head=False, head_plan=CI.HEAD_PLAN)
    if ctlm_args:
        for k, v in ctlm_args.items():
            setattr(a, k, v)
    image, rec = CI.compile_image(a)
    R, C = rec['relay'], rec['constants']
    lw = D.lower()
    ssq_pcs = set(lw['isa']['ssq_pcs'])
    ssq_cmds = [c for c in lw['commands'] if c['label'].startswith('SSQ')]
    e_min = min(c['edge'] for c in ssq_cmds)
    ages = ages or load_ages()
    own = D.ownership()
    ev, notes, overrun = [], [], []
    mat_of = {1: 'qkv', 12: 'o', 16: 'gu', 20: 'down'}
    taken = set()
    xc_plan, xc_low = [], []

    def put(edge, cmd, label):
        while edge in taken:
            edge -= 1
        taken.add(edge)
        ev.append((edge, cmd, label))
        return edge
    for p in rec['plan']:
        if p['kind'] == 'SU' and p['pc'] in ssq_pcs:
            for c in ssq_cmds:
                put(p['at'] - R['R_CMD'] + c['edge'] - e_min, int(c['cmd'], 16) & ~(0x1FF << 4) | (p['pc'] << 4),
                    f'SU PC{p["pc"]} {c["label"]}')
            span = max(c['edge'] for c in ssq_cmds) - e_min + lw['ages']['ssq_psum_out'][-1] + D.SC_HOP * (N - 1) + 61
            if p['at'] + span > p['done']:
                overrun.append(dict(pc=p['pc'], priced_done=p['done'], lowered_done=p['at'] + span))
        elif p['kind'] == 'SU':
            put(p['at'] - R['R_CMD'], CI.cmdw(1, 1, p['pc'], 15), f'SU PC{p["pc"]} (broadcast: not lowered here)')
        elif p['kind'] == 'XC':
            xc_plan.append(dict(tag=p['tag'], ctlm_at_w5=p['at'], ctlm_words=p['words']))
        elif p['kind'] == 'SEG':
            put(p['at'] - C['LOC_EDGES'], CI.cmdw(1, 2, p['base'], 14), f'SEG base {p["base"]}')
        elif p['kind'] == 'ME' and p['pc'] in mat_of:
            name = mat_of[p['pc']]
            go_w5 = p['at'] + C['ISSUE_TO_ROM'] + R['R_HR']
            ch = Chain(D.slice_map())
            t0 = go_w5 + tile_first + (ages['l8_ar'] + 2 * (N - 1) if own[name]['level'] == 8 else 0)
            if own[name]['level'] == 8:              # AR message: the XC edge is exact, reserved before the STN
                tag = len(xc_low)
                x = lower_xc(ch, ages, t0, 4096 // 16, tag)
                xc_low.append(dict(tag=tag, pc=p['pc'], entry_at_w5=x['entry'], words=4096 // 16))
                if put(x['entry'] - R['R_CMD'], int(x['cmd'], 16), f'XC tag {tag} dst 0 ({name})') != x['entry'] - R['R_CMD']:
                    notes.append(f'XC tag {tag}: its exact edge was taken by an earlier entry (moved: FIX the splice)')
            low = lower_matvec(name, t0, ages, ch, own=own)
            for d in low['stn']:
                put(d['entry'] - R['R_CMD'], int(d['cmd'], 16), f'PC{p["pc"]} {name} STN r{d["round"]} s{d["slice"]} {d["role"]}')
            notes.append(f'PC{p["pc"]} {name}: {len(low["stn"])} STN commands, first far word at go + {tile_first} '
                         f'(tile-delivery contract)')
    dec = CI.cal_entries([(e, c, l) for e, c, l in ev], C['CAL_S'], C)
    try:
        issue = CI.cal_model(dec, C['CAL_S'])
        model = dict(ok=True, entries=len(dec), last_issue=issue[-1])
    except CI.CompileError as e:
        model = dict(ok=False, entries=len(dec), error=str(e))
    return dict(events=[dict(edge=e, cmd=f'{c:029x}', label=l) for e, c, l in sorted(ev)], cal_model=model,
                ssq_overrun=overrun, notes=notes, xc_ctlm_plan=xc_plan, xc_lowered=xc_low,
                boot_events=[c for c in lw['commands'] if c['label'].startswith(('SETID', 'ROOT'))], tile_first=tile_first, period=rec['period'],
                ctlm_decode_entries=len(rec['cal']['decode']), spliced_entries=len(dec),
                pending=['PC15 / PC23 PROG words (residual add + SSQ, pidx = PC): dv_lower_vec (QLB-C4b/3a)',
                         'tile_first: the ME issue -> first far cluster word delivery constant (xhead / ROM tiles) is not '
                         'compiled by any tool; the STN entries move with it'])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--splice', help='write the spliced decode calendar JSON here')
    ap.add_argument('--lm-calendar', help='write the LM-head programme lowering (DV schedule + per-segment ME rows) here')
    ap.add_argument('--tile-first', type=int, default=40)
    a = ap.parse_args()
    if a.lm_calendar:
        ages = load_ages()
        ch = Chain(D.slice_map())
        lm = lower_lm(200, ages, ch)
        cal = lm_calendar(lm, ages, a.tile_first)
        rec = dict(schema='opentallas.qwen.dv-lm-head-lowering.v1', tool='tools/qwen_layerbench/dv_lower_mat.py',
                   programme=[dict(die=d['die'], row0=d['row0'], me_pcs=[pc for pc, _ in d['me']]) for d in lm_programme()],
                   calendar=cal, dv=dict(stn=len(lm['matvec']['stn']), emits=lm['emits'], arx_at_w5=lm['arx_at_w5'],
                                          xc=lm['xc'], gather_first=lm['gather_first'], commands=ch.commands()))
        Path(a.lm_calendar).parent.mkdir(parents=True, exist_ok=True)
        Path(a.lm_calendar).write_text(json.dumps(rec, indent=1) + '\n')
        print(json.dumps(dict(rows=[r['hex'] for r in cal['rows']], commands=len(ch.used))))
    if a.splice:
        r = splice()
        Path(a.splice).parent.mkdir(parents=True, exist_ok=True)
        Path(a.splice).write_text(json.dumps(r, indent=1) + '\n')
        print(json.dumps(dict(cal_model=r['cal_model'], overrun=r['ssq_overrun'], entries=r['spliced_entries'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
