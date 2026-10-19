#!/usr/bin/env python3
"""HBM-NEXT-UNITS-SUDMA2 2026-10-19: REDUCER / RF ROW CLASS of an N-row norm-style SU.VOP record, on the four d4g SU
quarter cores (ot_hbm_su_static_qcore: RF replica + reducer, RTL unchanged) behind the row stage ot_hnx_su_rowr, with
the top's RF relay routes (RF_RELAY stages, all four replicas commit on one edge).

    su_red_rows_compile.py OUT --n N [--m 128] [--absolute] [--seed 0] [--s-red 32] [--s-rf 32] [--lat 1]

Per row r (N rows), the reduction a norm row needs (su_top_compile's REDUCE section, row-stepped):
  quarter q: m lane partials (one lane ro_x an edge, lane c % 128, slice (lane >> 4) & 3), NCH = 10 interleaved FP32
  chains (LOAD, then ADD_EXT) in scratch [0, 10) + row, a left-to-right pairwise tree (ADD_TREE) into scratch [10, 19) +
  row, EXPORT to RF word 8 q + row (tag[8] = RF write, relayed to every replica);
  reducer 0: (((q0 + q1) + q2) + q3) from RF class-4 reads of those words into scratch 20 + row, EXPORT to RF word 2 + row;
  every quarter: class-1 broadcast read of the row scalar (checked at rf_bword), class-5 drains of the row's 4 RF sectors
  (checked at rf_dsec, replica coherence).
Row-relative image (default): every red / rf word is row 0's; the per-edge 8-b row code rc2 = {RF row, reducer row} and
the record strides s_red (scratch words) / s_rf (RF words) are applied by ot_hnx_su_rowr. --absolute: the unrolled d4g
image (absolute scratch / RF words, rc2 = 0, strides 0) -> the SAME expected files (d4g qcore bit for bit).
Schedule (static, every edge compiler-fixed; one reducer command a quarter an edge; collision = assert here, FAULT in
the RTL): rows in order; a row's lane stream starts on the first free command slot after the previous row's stream, its
tree / export / cross-quarter ops take the earliest free slot at or after operand ready (DEP = 10), so row r + 1's chains
fill the slots while row r's tree waits on the 10-edge add -- legal only because the rows' scratch is disjoint (s_red).
One RF row code an edge per quarter: an RF read whose row clashes with the edge's code moves to the next edge.
Edge rules (qcore / top headers; programme edge e reaches the qcore at e + L): reducer scalar held e + L + 11 (checked
e + L + 12), RF word readable by a read at programme edge >= export + 13 + RF_RELAY, class read data at rf_bword /
rf_dsec checked at e + L + 4, slice_x for a command at e is sampled at e + L + 1, the RF drain bit (slice-0 port-0 vmw
src 1) one edge after its class-5 read.
Golden: hdc_golden add (NumPy FP32 RNE, canonical +0) in the compiled order, independent of the DUT.
Outputs: prog.mem (4 x 128 b {rf54, red74} an edge), rc2.mem (4 x 8 b), st2.mem ({s_rf8, s_red10}), xs.mem (4 x 4 x
32 b slice_x a bench cycle), drn.mem (4 x 2 b rf_drain_cmd), exps.mem / expb.mem / expd.mem, programme.json (cycles(N),
row II, reducer slot use, dictionary words of the red / rf fields for the row-relative and the absolute image).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from hdc_golden import add  # noqa: E402

RLAT, DEP, NCH, R = 9, 10, 10, 8          # reducer r3 latency, dependent distance, chains, RF_RELAY (bench)
SC_CH, SC_TR, SC_X = 0, NCH, 20           # scratch: chains, tree nodes, cross-quarter accumulator (row 0)
RF_G = 2                                  # RF word of the row scalar (row 0); quarter sums at 8 q
LEAD = 8                                  # first command edge (reset settles)


def f32(u): return np.uint32(u).view(np.float32)
def u32(x): return int(np.float32(x).view(np.uint32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--n', type=int, required=True); ap.add_argument('--m', type=int, default=128)
    ap.add_argument('--absolute', action='store_true'); ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--s-red', type=int, default=32); ap.add_argument('--s-rf', type=int, default=32)
    ap.add_argument('--lat', type=int, default=1)
    ap.add_argument('--ovf', action='store_true', help='fail witness: scratch stride that carries out of 1,024 words '
                    '(rowr must FAULT)')
    a = ap.parse_args()
    N, M, L, rel = a.n, a.m, a.lat, not a.absolute
    srd, srf = a.s_red, a.s_rf
    assert 1 <= N <= 15 and 1 <= M <= 512 and srf % 8 == 0
    assert SC_X + srd * (N - 1) < 1024 or a.ovf
    assert 24 + 8 + srf * (N - 1) <= 256, 'RF words of the last row leave the 256-word RF'
    rng = np.random.default_rng(a.seed)
    V = (rng.standard_normal((N, 4, M)) * np.float32(2.0) ** rng.integers(-6, 6, (N, 4, M))).astype(np.float32)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    red, rf, rcd, rcf, xs, drn = {}, {}, {}, {}, {}, {}
    exps, expb, expd = [], [], []
    rfv = {}                                   # absolute RF word -> value
    rfrdy = {}                                 # absolute RF word -> first readable programme edge
    commits = set()

    def red_free(e, q): return (e, q) not in red

    def put_red(e, q, row, op, a_=0, b=0, d=0, tag=0, osel=0, lane=0):
        assert red_free(e, q)
        off = 0 if rel else srd * row
        toff = 0 if rel else srf * row
        A, B, D = a_ + (off if op in (1, 2, 3, 4, 5) else 0), b + (off if op in (2, 5) else 0), d + (off if op in (0, 1, 2, 3, 5) else 0)
        T = tag + (toff if (op == 4 and tag & 0x100) else 0)
        red[(e, q)] = (1 << 73) | (op << 70) | (A << 60) | (B << 50) | (D << 40) | (T << 8) | (osel << 7) | lane
        if rel: rcd[(e, q)] = row

    def rf_ok(e, q, c, row):
        if e < 0 or (e, q, c) in rf: return False
        cur = rcf.get((e, q))
        return cur is None or cur == row

    def put_rf(e, q, c, row, addr):
        assert rf_ok(e, q, c, row)
        rf[(e, q, c)] = (1 << 8) | (addr + (0 if rel else srf * row))
        rcf[(e, q)] = row          # schedule identical in both modes (the clash rule applies to both)

    def export(e, q, row, src, word0, val):
        put_red(e, q, row, 4, a_=src, tag=0x100 | word0)
        exps.append((e + L + 12, q, 0x100 | ((word0 + srf * row) & 0xff), val))
        w = word0 + srf * row
        ce = e + RLAT + 3
        assert (ce, w & 63) not in commits, 'RF bank write collision'
        commits.add((ce, w & 63))
        rfv[w] = val; rfrdy[w] = e + 13 + R

    lane_e = [LEAD - 1] * 4                          # last lane command edge a quarter (row r + 1's stream follows it)
    rows_first = []
    slot_use = [0] * 4
    for r in range(N):
        roots = {}
        first = None
        for q in range(4):
            ready = {}
            acc = [None] * NCH
            le = lane_e[q]
            for c in range(M):
                k = c % NCH
                e = max(le + 1, ready.get(SC_CH + k, 0))
                while not red_free(e, q): e += 1
                ln = c % 128
                v = u32(V[r, q, c])
                if c < NCH:
                    put_red(e, q, r, 0, d=SC_CH + k, lane=ln); acc[k] = v
                else:
                    put_red(e, q, r, 1, a_=SC_CH + k, d=SC_CH + k, lane=ln); acc[k] = u32(add(f32(acc[k]), f32(v)))
                xs[(e + L + 1, q, (ln >> 4) & 3)] = v
                ready[SC_CH + k] = e + DEP; le = e
                if first is None or e < first: first = e
            qlast = le
            vv = {SC_CH + i: acc[i] for i in range(min(NCH, M))}
            level = sorted(vv); nxt = SC_TR
            while len(level) > 1:
                nl = []
                for i in range(0, len(level) - 1, 2):
                    x, y = level[i], level[i + 1]
                    e = max(ready[x], ready[y])
                    while not red_free(e, q): e += 1
                    put_red(e, q, r, 2, a_=x, b=y, d=nxt)
                    vv[nxt] = u32(add(f32(vv[x]), f32(vv[y]))); ready[nxt] = e + DEP; nl.append(nxt); nxt += 1
                if len(level) % 2: nl.append(level[-1])
                level = nl
            assert nxt <= SC_X
            root = level[0]
            e = ready[root]
            while not red_free(e, q): e += 1
            export(e, q, r, root, 8 * q, vv[root]); roots[q] = vv[root]
            lane_e[q] = qlast
        rows_first.append(first)
        # reducer 0: (((q0 + q1) + q2) + q3) from RF class-4 reads (read at e - 2, operand at e + 1)
        e = 0; acc = None; xr = 0
        for i in range(4):
            e = max(e, rfrdy[8 * i + srf * r] + 2, xr)
            while not (red_free(e, 0) and rf_ok(e - 2, 0, 4, r)): e += 1
            put_rf(e - 2, 0, 4, r, 8 * i)
            put_red(e, 0, r, 0 if i == 0 else 1, a_=SC_X, d=SC_X, osel=1)
            acc = roots[0] if i == 0 else u32(add(f32(acc), f32(roots[i])))
            xr = e + DEP
        e = xr
        while not red_free(e, 0): e += 1
        export(e, 0, r, SC_X, RF_G, acc)
        gw = RF_G + srf * r
        # every quarter: class-1 broadcast of the row scalar, then class-5 drains of the row's sectors 0..3
        for q in range(4):
            e = rfrdy[gw]
            while not rf_ok(e, q, 1, r): e += 1
            put_rf(e, q, 1, r, RF_G)
            expb.append((e + L + 4, q, 1, acc))
            for g in range(4):
                base = 8 * g + srf * r
                e = max(rfrdy[w] for w in range(base, base + 8) if w in rfv)
                while not (rf_ok(e, q, 5, r) and (e + L + 1, q) not in drn): e += 1
                put_rf(e, q, 5, r, 8 * g)
                drn[(e + L + 1, q)] = 3
                mask = sum(1 << k for k in range(8) if base + k in rfv)
                expd.append((e + L + 4, q, mask, [rfv.get(base + k, 0) for k in range(8)]))
    for (e, q) in red: slot_use[q] += 1
    NE = max([e for (e, _) in red] + [e for (e, _, _) in rf]) + 1
    NT = NE + L + 24
    # files
    with open(out / 'prog.mem', 'w') as f:
        for e in range(NE):
            v = 0
            for q in range(4):
                w = red.get((e, q), 0)
                for c in range(6): w |= rf.get((e, q, c), 0) << (74 + 9 * c)
                v |= w << (128 * q)
            f.write(f'{v:0128x}\n')
    with open(out / 'rc2.mem', 'w') as f:
        for e in range(NE):
            f.write(''.join(f'{(rcf.get((e, q), 0) << 4 | rcd.get((e, q), 0)) if rel else 0:02x}' for q in (3, 2, 1, 0)) + '\n')
    stv = ((srf if rel else 0) << 10) | ((srd if rel else 0) & 1023)
    (out / 'st2.mem').write_text(f'{stv:05x}\n')
    with open(out / 'xs.mem', 'w') as f:
        for t in range(NT):
            v = 0
            for q in range(4):
                for g in range(4): v |= xs.get((t, q, g), 0) << (128 * q + 32 * g)
            f.write(f'{v:0128x}\n')
    with open(out / 'drn.mem', 'w') as f:
        for t in range(NT): f.write(f'{sum(drn.get((t, q), 0) << (2 * q) for q in range(4)):02x}\n')
    exps.sort(); expb.sort(); expd.sort(key=lambda x: (x[0], x[1]))
    (out / 'exps.mem').write_text(''.join(f'{e:08x}{q:08x}{t:08x}{v:08x}\n' for e, q, t, v in exps))
    (out / 'expb.mem').write_text(''.join(f'{e:08x}{q:02x}{c:02x}{v:08x}\n' for e, q, c, v in expb))
    with open(out / 'expd.mem', 'w') as f:
        for e, q, mk, ws in expd:
            dd = 0
            for k, w in enumerate(ws): dd |= w << (32 * k)
            f.write(f'{e:08x}{q:02x}{mk:02x}{dd:064x}\n')
    # dictionary words of the red74 / rf54 fields over (edge, quarter): the image as written, and the other mode
    def dic():
        return len(set(red.values())), len(set((c, w) for (e, q, c), w in rf.items()))
    last_ev = max([x[0] for x in exps] + [x[0] for x in expb] + [x[0] for x in expd])
    first_cmd = min(e for (e, _) in red)
    span = last_ev - (first_cmd + L) + 1
    lane_per_row = [rows_first[i + 1] - rows_first[i] for i in range(N - 1)]
    nr, nf = dic()
    man = dict(schema='opentallas.hbm_next.su_red_rows.v1', n=N, m=M, row_relative=rel, lat=L, s_red=srd, s_rf=srf,
               edges=NE, bench_cycles=NT, first_cmd_edge=first_cmd, last_event_cycle=last_ev, cycles=span,
               row_start_edges=rows_first, row_start_pitch=lane_per_row,
               reducer_slots_per_quarter=slot_use, reducer_slots_per_row_q0=slot_use[0] / N,
               red_dict_words=nr, rf_dict_words=nf,
               expected_scalars=len(exps), expected_bcast=len(expb), expected_drains=len(expd), seed=a.seed,
               golden='hdc_golden add NumPy FP32 RNE in the compiled chain / tree / cross-quarter order')
    (out / 'programme.json').write_text(json.dumps(man, indent=1) + '\n')
    print(f'NE={NE} NT={NT} NS={len(exps)} NB={len(expb)} ND={len(expd)} cycles={span} pitch={lane_per_row} '
          f'red_dict={nr} rf_dict={nf}')


if __name__ == '__main__':
    main()
