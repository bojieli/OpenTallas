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
ARG_SOURCE_EXTRA = 0         # opt-in _pr publication delay; engine command issue offsets stay unchanged
VM_RT = 0                    # HBM-BANKLAT-COLL 10-19: COLL parent VM_RT (VM capture n+10+VM_RT); set by --vm-rt
LEAD = 12                    # VM request of input m at S - LEAD + m (capture +10+VM_RT, sink +11+VM_RT, ARG sees it
                             # +13+VM_RT): LEAD = 12 + VM_RT; the capture/sink/ARG offsets relative to S do not move
VB, VS = 0x0400, 0x0020      # VM operand sector base, per-position stride (32 sectors, 24 used)
OBASE, DSTRIDE = 0x41000000, 0x40
PEEL = 15                    # = W - II, W = LEAD + M + 11 = a position's lifetime in edges (48 - 1 at VM_RT 0):
                             # tail rows (offsets 20..34 of a position) = rows 0..14 of the next body pass
CAP_ROWS = 64                # q3 programme memory rows: 64 (6-bit pc, the closed issuer) | 128 | 256 (--rows)
PW = 6                       # programme counter bits (ROWS 64 / 128 / 256 -> 6 / 7 / 8)
START_O = 0                  # ARG start offset: 0; -1 for ot_hgi_coll_argmax_m_tp192 (START_REG=1 registers start +
                             # cfg_g/gbase/rank one edge: the start row moves one edge earlier so the first lane input
                             # stays start+2 raw edges, the TP96 alignment; --start-reg)


def set_arg_pr_source(enabled):
    """Select the actual q3 edge _pr +1 publication contract, before set_vm_rt.

    Only ARG source capture and dependent delivery move. The uniform input
    capture in the engine already delays execution; its instruction rows stay.
    II32 remains valid. The extra lifetime costs two peeled programme rows.
    """
    global ARG_SOURCE_EXTRA
    ARG_SOURCE_EXTRA = int(bool(enabled))


def set_vm_rt(v):
    """re-derive LEAD / PEEL for a COLL parent VM_RT. A position's lifetime W = LEAD + M + 11 spans K = ceil(W / II)
    body passes; the compiler peels a straight-line prologue of PEEL = W - II rows (the cycles in which a modulo body would
    reference positions < 0) and an epilogue of PEEL + 1 rows (positions >= P), the body enters at row PEEL mod II of
    iteration PEEL // II. Programme rows = PEEL + II + (PEEL + 1) + halt = 64 + 2 VM_RT (VM_RT 0: 64, the closed issuer;
    VM_RT 74: 212 -> the 256-row issuer, coordinator HANDOFF 0kj)."""
    global VM_RT, LEAD, PEEL
    VM_RT, LEAD = v, 12 + v
    W = LEAD + M + 11 + ARG_SOURCE_EXTRA
    PEEL = W - II
    rows = 2 * PEEL + II + 2
    if rows > CAP_ROWS:
        raise SystemExit(f'ARGMAX_ROWS_COMPILE FAIL capacity VM_RT={v} LEAD={LEAD} lifetime={W} passes={-(-W // II)} '
                         f'peel={PEEL} rows={rows} > {CAP_ROWS} (--rows 256 = the deeper q3 programme memory)')


def set_rows(r):
    global CAP_ROWS, PW
    if r not in (64, 128, 256):
        raise SystemExit(f'ARGMAX_ROWS_COMPILE FAIL rows {r} (64 | 128 | 256)')
    CAP_ROWS, PW = r, {64: 6, 128: 7, 256: 8}[r]


def set_npt(n):
    global NPT
    NPT = n


LIDS = {}                                                        # ROWS 256: loop id -> dense id (issuer v7 NL 32)
NL_256 = 32


def enc_meta(nxt, tgt=0, count=0, lid=63, halt=0):
    """issuer row metadata (ot_hgi_coll_static_issuer_v6): next[5:0] target[11:6] count[43:12] halt[44] lid[50:45];
    ROWS 128 adds next[6]/target[6]/lid[6] at [51]/[52]/[53], ROWS 256 next[7]/target[7]/lid[7] at [54]/[55]/[56].
    ROWS 256 (HBM-COLL256-KITS, issuer v7: loop counters by id, NL 32): loop ids are mapped densely in order of first
    use (an injective rename: the loop semantics and every iteration value are unchanged); > 32 ids is a compile error."""
    if PW == 8:
        lid = LIDS.setdefault(lid, len(LIDS))
        if lid >= NL_256:
            raise SystemExit(f'ARGMAX_ROWS_COMPILE FAIL {len(LIDS)} loop ids > {NL_256} (256-row issuer v7)')
    for x in (nxt, tgt, lid):
        if not 0 <= x < (1 << PW):
            raise ValueError(('pc field', x, PW))
    m = ((lid & 63) << 45) | (halt << 44) | (count << 12) | ((tgt & 63) << 6) | (nxt & 63)
    if PW >= 7:
        m |= (((nxt >> 6) & 1) << 51) | (((tgt >> 6) & 1) << 52) | (((lid >> 6) & 1) << 53)
    if PW >= 8:
        m |= (((nxt >> 7) & 1) << 54) | (((tgt >> 7) & 1) << 55) | (((lid >> 7) & 1) << 56)
    return m


def dec_meta(m):
    nxt, tgt, lid = m & 63, (m >> 6) & 63, (m >> 45) & 63
    if PW >= 7:
        nxt, tgt, lid = nxt | (((m >> 51) & 1) << 6), tgt | (((m >> 52) & 1) << 6), lid | (((m >> 53) & 1) << 6)
    if PW >= 8:
        nxt, tgt, lid = nxt | (((m >> 54) & 1) << 7), tgt | (((m >> 55) & 1) << 7), lid | (((m >> 56) & 1) << 7)
    return dict(next=nxt, target=tgt, lid=lid, count=(m >> 12) & 0xffffffff, halt=(m >> 44) & 1)


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
    if o == START_O:                                             # start: G 96, gbase 0, publisher rank
        ar |= 1 << 48
        d.update(tkm_cfg_g=G, tkm_cfg_gbase=0)
    if 1 <= o <= M:
        ar |= 0xf << 51                                          # four-lane input reservation
    if o == M + 1:
        ar |= 1 << 49                                            # flush
    if o == M + 7:
        ar |= 1 << 50                                            # publication = flush + 6
    if o == M + 8 + ARG_SOURCE_EXTRA:
        d['capture_arg'] = 1
    if o == M + 9 + ARG_SOURCE_EXTRA:                                               # sink: SU delivery lane 0 <- ARG source 10
        d['sink_slot'] = d.get('sink_slot', 0) | (1 << NPT)
        d['sink_select'] = d.get('sink_select', 0) | ((NPT + 7) << (4 * NPT))
    if o == M + 10 + ARG_SOURCE_EXTRA:
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
        if -LEAD <= o <= M + 10 + ARG_SOURCE_EXTRA:
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
    i0, entry = divmod(PEEL, II)                                 # body entered at row `entry` of iteration i0
    K = -(-(LEAD + M + 11 + ARG_SOURCE_EXTRA) // II) + 1                            # positions a body row can reference (filtered)
    steps = dict(iter_vm_step=0 if mutant == 'vm_step' else VS, iter_del_step=DSTRIDE)
    if P > i0:
        for r in range(PEEL):                                    # prologue: cycles 0..PEEL-1 (no position < 0)
            words.append(pack(fields_at(r, allp, rank_pub)))
            meta.append(enc_meta(BODY0 + entry if r == PEEL - 1 else r + 1))
        for r in range(II):                                      # body row r = cycle II (i0 + it) + r, it = iteration
            d = fields_at(II * i0 + r, range(i0 - K + 1, i0 + 1), rank_pub)
            d.update(steps)
            pc = BODY0 + r
            words.append(pack(d))
            meta.append(enc_meta(END + 1, BODY0, P - i0, END) if pc == END else enc_meta(pc + 1, lid=END))
        c0 = II * P                                              # epilogue: cycles II P .. halt-1 (no position >= P)
    else:
        c0 = 0                                                   # P <= i0: no steady state, straight-line
    for c in range(c0, halt):
        words.append(pack(fields_at(c, allp, rank_pub)))
        meta.append(enc_meta(len(meta) + 1))
    words.append(pack(fields_at(halt, [], rank_pub)))
    meta.append(enc_meta(len(meta), len(meta), halt=1))
    if len(words) > CAP_ROWS:
        raise ValueError('programme capacity')
    # independent unroll against the absolute schedule of all P positions
    if mutant is None:
        unroll(words, meta, fields, lambda c: fields_at(c, allp, rank_pub), halt)
    return words, meta, dict(P=P, rows=len(words), halt=halt, last_delivery=II * (P - 1) + LEAD + M + 11 + ARG_SOURCE_EXTRA,
                             II=II, body_rows=II, prologue=PEEL, epilogue=PEEL)


def unroll(words, meta, fields, sched, halt):
    def get(w, k):
        f = fields[k]
        return (w >> f['lsb']) & ((1 << f['width']) - 1)
    pc, counters, c = 0, [0] * (1 << PW), 0
    while True:
        m, w = meta[pc], words[pc]
        f = dec_meta(m)
        it = counters[f['lid']]
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
        if f['halt']:
            if c != halt:
                raise AssertionError(('halt', c, halt))
            return
        count, lid = f['count'], f['lid']
        if count and counters[lid] < count - 1:
            counters[lid] += 1
            pc = f['target']
        else:
            if count:
                counters[lid] = 0
            pc = f['next']
        c += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('out', type=pathlib.Path)
    ap.add_argument('--P', type=int, default=1)
    ap.add_argument('--mutant', choices=('vm_step',))
    ap.add_argument('--vm-rt', type=int, default=0, help='COLL parent VM_RT (extra VM read edges beyond n+10 capture)')
    ap.add_argument('--rows', type=int, default=64, help='q3 issuer programme rows (ROWS 64 | 128 | 256)')
    ap.add_argument('--start-reg', action='store_true', help='ARG unit registers start (argmax_m_tp192, d4g SW TP 192)')
    ap.add_argument('--arg-pr-source', action='store_true', help='actual q3 edge _pr ARG publication +1: capture and dependent delivery shift, II32 unchanged; needs >=66 rows at VM_RT0')
    ap.add_argument('--npt', type=int, default=3, help='parent link ports NPT (v4 q3 / v8x NLINK 3: 3; d4g SW v8x NLINK 2: 2)')
    a = ap.parse_args()
    set_rows(a.rows)
    set_npt(a.npt)
    global START_O
    START_O = -1 if a.start_reg else 0
    set_arg_pr_source(a.arg_pr_source)
    set_vm_rt(a.vm_rt)
    a.out.mkdir(parents=True, exist_ok=True)
    man = dict(schema='hcoll.rows.argmax.v1', P=a.P, mutant=a.mutant, vm_rt=a.vm_rt, G=G, II=II, VB=VB, VS=VS, OBASE=OBASE,
               DSTRIDE=DSTRIDE, layout_sha256=hashlib.sha256(LAYOUT.read_bytes()).hexdigest(), parents={})
    if a.rows != 64 or a.npt != 3 or a.start_reg:                # default manifest byte-identical
        man.update(rows=a.rows, npt=a.npt, start_reg=a.start_reg)
    if a.arg_pr_source:
        man.update(arg_source_publication_extra=1, source_contract='ot_hgi_coll_argmax_m_tp192_pr', source_adoption='compiler_only_actual_native_caller_pending')
    halt_only = (1 << 44)
    for die in range(2):
        words, meta, info = compile_program(die, a.P, a.mutant)
        (a.out / f'd{die}q0.rows.hex').write_text(''.join(f'{w:0384x}\n' for w in words))
        (a.out / f'd{die}q0.meta.hex').write_text(''.join(f'{m:016x}\n' for m in meta))
        man['parents'][f'd{die}q0'] = info
        # q2 carries no ARGMAX (it faults by ISA): its programme is the native halt row only
        (a.out / f'd{die}q1.rows.hex').write_text(f'{0:0384x}\n')
        (a.out / f'd{die}q1.meta.hex').write_text(f'{enc_meta(0) | halt_only:016x}\n')
        man['parents'][f'd{die}q1'] = dict(rows=1, halt_only=True)
    (a.out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f"ARGMAX_ROWS_COMPILE PASS P={a.P} rows={man['parents']['d0q0']['rows']} II={II} "
          f"last_delivery_instr={man['parents']['d0q0']['last_delivery']} halt={man['parents']['d0q0']['halt']}")


if __name__ == '__main__':
    main()
