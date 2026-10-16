#!/usr/bin/env python3
"""COLL.ROW_GATHER P-row static programme for the native V4 quadrant (q3 SW / q2).

Lowers one die's per-quadrant share of the DS-V4.1 MTP-verify ROW_GATHER as the model prices it (hgi_sim
ds_native_timing.NativeCost.row_gather, the bypass form the native programme runs: every owner pads its selected
rows to the group maximum M = 13 (bit-exact 1M run), one exact gather of 96 x M compressed-KV rows of 288 B (9 x 32 B
sectors) into every die) to the ACTUAL native issuer ISA (static_uop_layout_v4.json) for
ot_hfd_coll_q{3,2}_static_host_v4: 13 x 288 B = 59 64-byte flits a rank, 95 remote ranks = 5,605 flits a position
into every die over its 9 rails.

Every rail carries R flits a position (R = ceil(5605 / 9 rails) = 623, 1/cycle; this assumes the G96 route
calendar fills every rail of the receiving die, which this quadrant-level bench does not prove); the P positions
are rows of ONE stream: the issuer's loop iteration is the RTL row/flit counter (iter_inj_idx_step, iter_inj_addr_step,
iter_vm_step, iter_del_step, iter_link_slot_step are real RTL arithmetic in ot_hgi_coll_q_static_ctl_v4).
Inside a position the lane's delivery addresses are dense (step 64 B); between positions the destination
jumps by the compile-time position stride RS (each position's gathered-row store is its own region), so the
compiler splits the delivery-address stage's loop row at every position boundary.  All link sequence slots
(0 .. P*R-1 per rail, one epoch) are reserved at compile time; there is no ready/credit wait on the die.

Sources: rails 0/1 <- SU inject ports 0/1 (INJLAT 12, data from the declared SU boundary model: the SU-side
inj_d is unbound in the die, gap G-CIL-INJ); q3 rail 2 <- VM read group 0 (bank pair 1:0, P+10 capture).
Sinks: RX rail k -> SU delivery lane k (del_valid/del_flit/hgi_del_obase).

Mechanism compiler at the quadrant boundary, not the normative HGI record compiler.

    python3 tools/hbm_coll_static/row_gather_rows.py OUT --P 6 [--R 623] [--wire 453] [--mutant row_stride|link_step]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
LAYOUT = ROOT / 'rtl/hbm_accel/generic/collective/p2p/static_uop_layout_v4.json'

G, M_OWNED, ROW_BYTES, RAILS_DIE = 96, 13, 288, 9   # bypass ROW_GATHER: G ranks x M padded rows of 288 B
RANK_FLITS = math.ceil(M_OWNED * ROW_BYTES / 64)    # 59 flits a rank (13 x 288 B = 3,744 B)
FLITS_POS = (G - 1) * RANK_FLITS                     # 5,605 remote flits a position into every die
R_PROD = math.ceil(FLITS_POS / RAILS_DIE)            # 623 flits a rail a position
FLIT_B = 64
OBASE = 0x40000000                                   # list-order selected-row store (position 0)
RS = 0x60000                                         # position stride: 96 x 59 flits x 64 B = 0x58800 fits
IDX0 = (0x0100, 0x4100)                              # SU inject list bases, ports 0 / 1
ADDR0 = (0x2000000, 0x3000000)                       # SU inject address bases (byte), ports 0 / 1
VM_S0 = 0x0200                                       # VM sector base of the q3 rail-2 rows
EPOCH = 0x5a

# instruction-cycle offsets of the pipeline stages, relative to the stream index's SU request cycle
REQ, CAP = 0, 12                                     # INJLAT 12: request P -> qslots SU capture P+12
REQV = CAP - 10                                      # VM request P -> qslots VM capture P+10
SINK = CAP + 1                                       # sink instruction C+1 selects source captured C
WR = CAP + 3                                         # registered sink C+2 visible C+3 = link write reservation
DRD = 4                                              # read reservation after the native SRAM write (E+4)
RD = WR + DRD
TXLAT = 7                                            # rd sampled E -> registered TX pin E+6, visible E+7


def stages(npt, wire):
    rxe = RD + TXLAT + wire                          # instruction cycle the RX pin is driven = rx_expect edge
    st = dict(REQ=REQ, CAP=CAP, SINK=SINK, WRSEQ=WR - 1, WR=WR, RDSEQ=RD - 1, RD=RD,
              RXSEQ=rxe - 1, RXE=rxe, RXCAP=rxe + 3, DSINK=rxe + 4, DADDR=rxe + 5)
    if npt == 3:
        st['REQV'] = REQV
    return st


def gidx(qid, k):
    """die-global rail number of quadrant qid rail k (q3 rails 0..2, q2 quadrants 1..3 rails 0..1)."""
    return k if qid == 0 else 3 + 2 * (qid - 1) + k


def su_meta(die, idx):
    return (1 << 32) | (0xff << 24) | ((die & 0xff) << 16) | (idx & 0xffff)


def vm_meta(die):
    return (1 << 32) | (0xff << 24) | ((die & 0xff) << 16) | 0xa5a5


def compile_program(die, qid, P, R, wire, mutant=None):
    fields = json.loads(LAYOUT.read_text())['fields']
    npt = 3 if qid == 0 else 2
    N = P * R
    st = stages(npt, wire)
    DEL = st['DADDR'] + 1
    last = DEL + N - 1                               # last delivery-visible instruction cycle
    halt = last + 1

    def pack(d):
        out = 0
        for k, v in d.items():
            f = fields[k]
            if not 0 <= v < (1 << f['width']):
                raise ValueError((k, v))
            out |= v << f['lsb']
        return out

    def daddr(qk, j):
        p, f = divmod(j, R)
        if mutant == 'row_stride':
            p = 0                                    # the row step dropped: every position lands on row 0
        return OBASE + gidx(qid, qk) * R * FLIT_B + p * RS + f * FLIT_B

    def fields_at(c):
        """field values of logical instruction cycle c (absolute values, no iteration)."""
        d = {}
        if c == 0:
            d.update(lk_epoch_begin=(1 << npt) - 1, lk_epoch=EPOCH)

        def j_of(o):
            j = c - o
            return j if 0 <= j < N else None
        cap = sinks = sel = 0
        su = 2 if npt == 3 else npt                  # SU-fed rails
        if (j := j_of(st['REQ'])) is not None:
            idx = [IDX0[k] + j for k in range(2)]
            d.update(inj_rd=3, inj_idx=idx[0] | (idx[1] << 16),
                     inj_meta=sum(su_meta(die, idx[k]) << (33 * k) for k in range(2)),
                     inj_addr=sum((ADDR0[k] + j * FLIT_B + 32 * h) << (80 * k + 40 * h) for k in range(2) for h in range(2)))
        if npt == 3 and (j := j_of(st['REQV'])) is not None:
            s = VM_S0 + j
            d.update(vm_rq=((1 << 16) | s) | (((1 << 16) | s) << 17), vm_pair_select=(1 << 3) | 0,
                     vm_meta=vm_meta(die))
        if j_of(st['CAP']) is not None:
            cap |= 3 | ((1 << (2 + npt)) if npt == 3 else 0)
        if j_of(st['SINK']) is not None:
            for k in range(npt):
                sinks |= 1 << k
                sel |= (k if k < su else 2 + npt) << (4 * k)
        seqs = {}
        for key, sname, vname in (('lk_wr', 'WRSEQ', 'WR'), ('lk_rd', 'RDSEQ', 'RD'), ('lk_rx', 'RXSEQ', 'RXE')):
            if (j := j_of(st[sname])) is not None:
                seqs[key] = j
            if j_of(st[vname]) is not None:
                d['lk_rx_expect' if key == 'lk_rx' else key + '_v'] = (1 << npt) - 1
        for key, j in seqs.items():
            if j >= 65536:
                raise ValueError('link sequence beyond one epoch')
            d[key + '_slot'] = sum((j & 63) << (6 * k) for k in range(npt))
            d[key + '_seq_high'] = sum((j >> 6) << (10 * k) for k in range(npt))
        if j_of(st['RXCAP']) is not None:
            cap |= sum(1 << (2 + k) for k in range(npt))
        if j_of(st['DSINK']) is not None:
            for k in range(npt):
                sinks |= 1 << (npt + k)
                sel |= (2 + k) << (4 * (npt + k))
        if (j := j_of(st['DADDR'])) is not None:
            d['del_obase'] = sum(daddr(k, j) << (40 * k) for k in range(npt))
        if cap:
            d['capture_slot'] = cap
        if sinks:
            d.update(sink_slot=sinks, sink_select=sel)
        return d

    steps = dict(iter_inj_idx_step=1, iter_inj_addr_step=FLIT_B, iter_del_step=FLIT_B,
                 iter_link_slot_step=0 if mutant == 'link_step' else 1)
    if npt == 3:
        steps['iter_vm_step'] = 1
    # segment boundaries: every stage start/end, the epoch row, every position boundary of the delivery-address
    # stage (the position stride is not the in-row step), the halt row
    bounds = {0, 1, halt}
    for o in st.values():
        bounds |= {o, o + N}
    bounds |= {st['DADDR'] + p * R for p in range(1, P)}
    bounds = sorted(b for b in bounds if 0 <= b <= halt)
    segs = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)] + [(halt, halt + 1)]
    words, meta, plan = [], [], []
    for pc, (s, e) in enumerate(segs):
        d = fields_at(s)
        L = e - s
        if s == halt:
            m = (63 << 45) | (1 << 44) | (pc << 6) | pc
        elif L > 1:
            d.update(steps)
            m = (pc << 45) | (L << 12) | (pc << 6) | ((pc + 1) & 63)
        else:
            m = (63 << 45) | ((pc + 1) & 63)
        if s == 0:
            m = (63 << 45) | 1                       # epoch row: single visit
        words.append(pack(d))
        meta.append(m)
        plan.append(dict(pc=pc, start=s, visits=L if s != halt else 1))
    if len(words) > 64:
        raise ValueError(f'programme capacity: {len(words)} rows > 64')
    # independent unroll of the issuer metadata ISA against a fresh per-cycle schedule (iteration arithmetic as
    # ot_hgi_coll_q_static_ctl_v4 computes it); the row_stride mutant is checked against its own schedule
    unroll(words, meta, fields, fields_at, halt, npt)
    cfg = []
    return words, meta, plan, dict(N=N, P=P, R=R, wire=wire, stages=st, DEL=DEL, last_delivery=last, halt=halt,
                                   rows=len(words))


def unroll(words, meta, fields, fields_at, halt, npt):
    def get(w, k):
        f = fields[k]
        return (w >> f['lsb']) & ((1 << f['width']) - 1)
    pc, counters, c = 0, [0] * 64, 0
    while True:
        m, w = meta[pc], words[pc]
        it = counters[(m >> 45) & 63]
        exp = fields_at(c)
        for k in fields:
            if k.startswith('iter_') or k in ('ar_high', 'capture_arg', 'reduce_clear'):
                continue
            v = get(w, k)
            if it:
                if k == 'inj_idx':
                    v = sum((((v >> (16 * j)) & 0xffff) + it * get(w, 'iter_inj_idx_step') & 0xffff) << (16 * j) for j in range(2))
                elif k == 'inj_meta':
                    v = sum(((((v >> (33 * j)) & ((1 << 33) - 1)) & ~0xffff) | ((((v >> (33 * j)) & 0xffff) + it * get(w, 'iter_inj_idx_step')) & 0xffff)) << (33 * j) for j in range(2))
                elif k == 'inj_addr':
                    v = sum(((((v >> (40 * j)) & ((1 << 40) - 1)) + it * get(w, 'iter_inj_addr_step')) & ((1 << 40) - 1)) << (40 * j) for j in range(4))
                elif k == 'del_obase':
                    v = sum(((((v >> (40 * j)) & ((1 << 40) - 1)) + it * get(w, 'iter_del_step')) & ((1 << 40) - 1)) << (40 * j) for j in range(npt))
                elif k == 'vm_rq':
                    v = sum((((((v >> (17 * b)) & 0xffff) + it * get(w, 'iter_vm_step')) & 0xffff) | (((v >> (17 * b + 16)) & 1) << 16)) << (17 * b) for b in range(8))
                elif k in ('lk_wr_slot', 'lk_rd_slot', 'lk_rx_slot', 'lk_wr_seq_high', 'lk_rd_seq_high', 'lk_rx_seq_high'):
                    continue                          # checked as full sequences below
            # inactive request/address lanes carry the iteration term harmlessly (valid 0): compare valid lanes only
            if k in ('inj_idx', 'inj_meta', 'inj_addr') and not get(w, 'inj_rd'):
                continue
            if k == 'vm_rq':
                v = sum(((v >> (17 * b)) & 0x1ffff) << (17 * b) for b in range(8) if (v >> (17 * b + 16)) & 1)
            if k == 'del_obase' and 'del_obase' not in exp:
                continue
            if v != exp.get(k, 0):
                raise AssertionError((c, pc, it, k, hex(v), hex(exp.get(k, 0))))
        for key in ('lk_wr', 'lk_rd', 'lk_rx'):
            if key + '_slot' in exp:
                for r in range(npt):
                    base = (((get(w, key + '_seq_high') >> (10 * r)) & 1023) << 6) | ((get(w, key + '_slot') >> (6 * r)) & 63)
                    full = base + it * get(w, 'iter_link_slot_step')
                    want = ((exp[key + '_seq_high'] >> (10 * r)) & 1023) << 6 | ((exp[key + '_slot'] >> (6 * r)) & 63)
                    if full != want and get(w, 'iter_link_slot_step') != 0:
                        raise AssertionError((c, pc, key, r, full, want))
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
    ap.add_argument('--R', type=int, default=R_PROD)
    ap.add_argument('--wire', type=int, default=453)
    ap.add_argument('--mutant', choices=('row_stride', 'link_step'))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    man = dict(schema='hcoll.rows.row_gather.v1', P=a.P, R=a.R, wire=a.wire, mutant=a.mutant,
               shape=dict(G=G, max_owned_rows=M_OWNED, row_bytes=ROW_BYTES, rank_flits=RANK_FLITS, flits_per_position=FLITS_POS, rails_die=RAILS_DIE,
                          R_production=R_PROD, flit_bytes=FLIT_B, obase=OBASE, position_stride=RS),
               layout_sha256=hashlib.sha256(LAYOUT.read_bytes()).hexdigest(), parents={})
    for die in range(2):
        for qid in (0, 1):
            words, meta, plan, info = compile_program(die, qid, a.P, a.R, a.wire, a.mutant)
            name = f'd{die}q{qid}'
            (a.out / f'{name}.rows.hex').write_text(''.join(f'{w:0384x}\n' for w in words))
            (a.out / f'{name}.meta.hex').write_text(''.join(f'{m:016x}\n' for m in meta))
            man['parents'][name] = dict(info, plan=plan)
    (a.out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    p = man['parents']
    print(f"ROW_GATHER_ROWS_COMPILE PASS P={a.P} R={a.R} wire={a.wire} rows q3={p['d0q0']['rows']} "
          f"q2={p['d0q1']['rows']} last_delivery_instr={p['d0q0']['last_delivery']} halt={p['d0q0']['halt']}")


if __name__ == '__main__':
    main()
