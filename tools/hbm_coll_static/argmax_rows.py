#!/usr/bin/env python3
"""COLL.ARGMAX_MERGE P-row static programme for the native V4 q3 SW quadrant (ot_hgi_coll_argmax_static, ARG mode).

One G96 merge a position: the 96 ranks' (value FP32, id U32) candidates, already gathered into this die's VM (the
SW_ARG_NATIVE_JOIN operand placement: one 512-bit line a rank, 4 VM read groups a cycle, pair {2j+1, 2j}), are
folded by the actual native ARGMAX unit (start, 24 four-lane input edges, flush, registered publication flush+6);
the result leaves through its own qslots source to SU delivery lane 0 at the position's output address.

P positions are a software-pipelined loop of the issuer: one 32-row body (II 32 = 24 input edges + flush + 6 +
start) whose loop iteration is the position (iter_vm_step = the per-position operand stride, iter_del_step = the
per-position output stride: real RTL arithmetic). A position's lifetime (VM request -12 .. delivery +35 = 48 edges)
spans two body passes at VM_RT 0 (LEAD 12 + VM_RT, see set_vm_rt), so the compiler peels a 15-row head-only prologue (enters the body at row 15) and a 15-row
tail-only epilogue: 15 + 32 + 16 + halt = 64 programme rows.

    python3 tools/hbm_coll_static/argmax_rows.py OUT --P 6 [--mutant vm_step]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LAYOUT = ROOT / 'rtl/hbm_accel/generic/collective/p2p/static_uop_layout_v4.json'
NPT, G, LANES = 3, 96, 4
M = G // LANES               # 24 input edges a position
II = 32                      # start + 24 inputs + flush + 6 (publish = flush + 6) -> next start
VM_RT = 0                    # HBM-BANKLAT-COLL 10-19: COLL parent VM_RT (VM capture n+10+VM_RT); set by --vm-rt
LEAD = 12                    # VM request of input m at S - LEAD + m (capture +10+VM_RT, sink +11+VM_RT, ARG sees it
                             # +13+VM_RT): LEAD = 12 + VM_RT; the capture/sink/ARG offsets relative to S do not move
VB, VS = 0x0400, 0x0020      # VM operand sector base, per-position stride (32 sectors, 24 used)
OBASE, DSTRIDE = 0x41000000, 0x40
PEEL = 15                    # = W - II, W = LEAD + M + 11 = a position's lifetime in edges (48 - 1 at VM_RT 0):
                             # tail rows (offsets 20..34 of a position) = rows 0..14 of the next body pass
CAP_ROWS = 64                # q3 programme memory (6-bit pc)


def set_vm_rt(v):
    """re-derive LEAD / PEEL for a COLL parent VM_RT. Programme rows = PEEL + II + (PEEL + 1) + halt = 2 W - II + 2 =
    64 + 2 VM_RT: the peeled two-position loop fits the 64-row programme ONLY at VM_RT 0. VM_RT > 0 also stretches a
    position over K = ceil(W / II) > 2 body passes (VM_RT 74: W 121, K 4, PEEL 89 >= II), so no prologue/epilogue peel
    of this ISA fits; it needs per-stage row predicates (kernel-only modulo schedule) or a deeper programme memory."""
    global VM_RT, LEAD, PEEL
    VM_RT, LEAD = v, 12 + v
    W = LEAD + M + 11
    PEEL = W - II
    rows = 2 * PEEL + II + 2
    if PEEL >= II or rows > CAP_ROWS:
        raise SystemExit(f'ARGMAX_ROWS_COMPILE FAIL capacity VM_RT={v} LEAD={LEAD} lifetime={W} passes={-(-W // II)} '
                         f'peel={PEEL} rows={rows} > {CAP_ROWS} (needs stage predicates or a deeper programme)')


def ar_fields(ar):
    return dict(ar_low=ar & ((1 << 31) - 1), ar_high=ar >> 31)


def pos_fields(p, o, rank_pub):
    """fields contributed by position p at offset o = cycle - S_p (S_p = LEAD + II p)."""
    d, ar = {}, 0
    m = o + LEAD
    if 0 <= m < M:                                               # VM request
        s = VB + p * VS + m
        d['vm_rq'] = sum(((1 << 16) | (s & 0xffff)) << (17 * b) for b in range(8))
        d['vm_pair_select'] = sum((((2 * j + 1) << 3) | (2 * j)) << (6 * j) for j in range(4))
        d['vm_meta'] = sum(((1 << 32) | (0xff << 24) | ((4 * m + j) << 16)) << (33 * j) for j in range(4))
    if 0 <= o + 2 < M:                                           # qslots capture of VM0..3 (sources 5..8)
        d['capture_slot'] = 0xf << (2 + NPT)
    if 0 <= o + 1 < M:                                           # sink: ARG lanes 11..14 <- VM sources 5..8
        d['sink_slot'] = 0xf << (NPT + 8)
        d['sink_select'] = sum((2 + NPT + j) << (4 * (NPT + 8 + j)) for j in range(4))
    if o == 0:                                                   # start: G 96, gbase 0, publisher rank
        ar |= 1 << 48
        d.update(tkm_cfg_g=G, tkm_cfg_gbase=0)
    if 1 <= o <= M:
        ar |= 0xf << 51                                          # four-lane input reservation
    if o == M + 1:
        ar |= 1 << 49                                            # flush
    if o == M + 7:
        ar |= 1 << 50                                            # publication = flush + 6
    if o == M + 8:
        d['capture_arg'] = 1
    if o == M + 9:                                               # sink: SU delivery lane 0 <- ARG source 10
        d['sink_slot'] = d.get('sink_slot', 0) | (1 << NPT)
        d['sink_select'] = d.get('sink_select', 0) | ((NPT + 7) << (4 * NPT))
    if o == M + 10:
        d['del_obase'] = OBASE + p * DSTRIDE
    return d, ar


def merge(ds):
    out, ar = {}, (1 << 47) | 0                                  # ARG mode in every row (TKM unused)
    for d, a in ds:
        ar |= a
        for k, v in d.items():
            if k in out and k not in ('sink_slot', 'sink_select', 'capture_slot'):
                raise ValueError(f'field collision {k}')
            out[k] = out.get(k, 0) | v
    return out, ar


def fields_at(c, positions, rank_pub):
    ds = []
    for p in positions:
        o = c - (LEAD + II * p)
        if -LEAD <= o <= M + 10:
            ds.append(pos_fields(p, o, rank_pub))
    d, ar = merge(ds)
    ar |= (rank_pub & 0xff) << 23
    d.update(ar_fields(ar))
    return d


def compile_program(die, P, mutant=None):
    fields = json.loads(LAYOUT.read_text())['fields']
    rank_pub = die
    allp = range(P)
    halt = II * P + PEEL + 1                                     # one edge after S_{P-1} + 35, the last delivery

    def pack(d):
        out = 0
        for k, v in d.items():
            f = fields[k]
            if not 0 <= v < (1 << f['width']):
                raise ValueError((k, v))
            out |= v << f['lsb']
        return out
    words, meta = [], []
    BODY0, END = PEEL, PEEL + II - 1
    for r in range(PEEL):                                        # prologue: position 0 head, cycles 0..14
        words.append(pack(fields_at(r, [0], rank_pub)))
        meta.append((63 << 45) | ((BODY0 + PEEL) if r == PEEL - 1 else r + 1))
    steps = dict(iter_vm_step=0 if mutant == 'vm_step' else VS, iter_del_step=DSTRIDE)
    for r in range(II):                                          # body row r = cycle II i + r, iteration i
        d = fields_at(r, [0, -1], rank_pub)                      # i = 0 bases (tail of p = -1 for rows 0..14)
        d.update(steps)
        pc = BODY0 + r
        nxt = pc + 1
        m = (END << 45) | nxt
        if pc == END:
            m = (END << 45) | (P << 12) | (BODY0 << 6) | (END + 1)
        words.append(pack(d))
        meta.append(m)
    for r in range(PEEL + 1):                                    # epilogue: position P-1 tail (+1 idle edge)
        words.append(pack(fields_at(II * P + r, [P - 1], rank_pub)))
        meta.append((63 << 45) | (len(meta) + 1))
    words.append(pack(fields_at(halt, [], rank_pub)))
    meta.append((63 << 45) | (1 << 44) | (len(meta) << 6) | len(meta))
    if len(words) > 64:
        raise ValueError('programme capacity')
    # independent unroll against the absolute schedule of all P positions
    if mutant is None:
        unroll(words, meta, fields, lambda c: fields_at(c, allp, rank_pub), halt)
    return words, meta, dict(P=P, rows=len(words), halt=halt, last_delivery=II * (P - 1) + LEAD + M + 11,
                             II=II, body_rows=II, prologue=PEEL, epilogue=PEEL)


def unroll(words, meta, fields, sched, halt):
    def get(w, k):
        f = fields[k]
        return (w >> f['lsb']) & ((1 << f['width']) - 1)
    pc, counters, c = 0, [0] * 64, 0
    while True:
        m, w = meta[pc], words[pc]
        it = counters[(m >> 45) & 63]
        exp = sched(c)
        for k in fields:
            if k.startswith('iter_') or k == 'ring':             # ring aliases ar_high / capture_arg / clear
                continue
            v = get(w, k)
            if k == 'vm_rq':
                v = sum((((((v >> (17 * b)) & 0xffff) + it * get(w, 'iter_vm_step')) & 0xffff) | (1 << 16)) << (17 * b)
                        for b in range(8) if (v >> (17 * b + 16)) & 1)
            if k == 'del_obase':
                if 'del_obase' not in exp:
                    continue
                v = ((v & ((1 << 40) - 1)) + it * get(w, 'iter_del_step')) & ((1 << 40) - 1)
            if v != exp.get(k, 0):
                raise AssertionError((c, pc, it, k, hex(v), hex(exp.get(k, 0))))
        if (m >> 44) & 1:
            if c != halt:
                raise AssertionError(('halt', c, halt))
            return
        count, lid = (m >> 12) & 0xffffffff, (m >> 45) & 63
        if count and counters[lid] < count - 1:
            counters[lid] += 1
            pc = (m >> 6) & 63
        else:
            if count:
                counters[lid] = 0
            pc = m & 63
        c += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--P', type=int, default=1)
    ap.add_argument('--mutant', choices=('vm_step',))
    ap.add_argument('--vm-rt', type=int, default=0, help='COLL parent VM_RT (extra VM read edges beyond n+10 capture)')
    a = ap.parse_args()
    set_vm_rt(a.vm_rt)
    a.out.mkdir(parents=True, exist_ok=True)
    man = dict(schema='hcoll.rows.argmax.v1', P=a.P, mutant=a.mutant, vm_rt=a.vm_rt, G=G, II=II, VB=VB, VS=VS, OBASE=OBASE,
               DSTRIDE=DSTRIDE, layout_sha256=hashlib.sha256(LAYOUT.read_bytes()).hexdigest(), parents={})
    halt_only = (1 << 44)
    for die in range(2):
        words, meta, info = compile_program(die, a.P, a.mutant)
        (a.out / f'd{die}q0.rows.hex').write_text(''.join(f'{w:0384x}\n' for w in words))
        (a.out / f'd{die}q0.meta.hex').write_text(''.join(f'{m:016x}\n' for m in meta))
        man['parents'][f'd{die}q0'] = info
        # q2 carries no ARGMAX (it faults by ISA): its programme is the native halt row only
        (a.out / f'd{die}q1.rows.hex').write_text(f'{0:0384x}\n')
        (a.out / f'd{die}q1.meta.hex').write_text(f'{(63 << 45) | halt_only:016x}\n')
        man['parents'][f'd{die}q1'] = dict(rows=1, halt_only=True)
    (a.out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f"ARGMAX_ROWS_COMPILE PASS P={a.P} rows={man['parents']['d0q0']['rows']} II={II} "
          f"last_delivery_instr={man['parents']['d0q0']['last_delivery']} halt={man['parents']['d0q0']['halt']}")


if __name__ == '__main__':
    main()
