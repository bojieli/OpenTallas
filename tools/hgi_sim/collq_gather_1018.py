#!/usr/bin/env python3
"""HBM-COLLQ (10-18): compiler model of the per-quadrant COLL gather master (rtl/.../p2p/ot_hgi_coll_gq.sv).

The two-ring x all-gather of d4g plan (b) on the canonical static schedule the master expands from one descriptor:
  global flit i -> ring r = i % R, ring index k = i // R, direction d = k & 1 (0 = CW), ttl 3, tag k % 8;
  issue edge IE(k) = FE + 1 + 3 (k >> 1) + (k & 1)  (FE = descriptor fire edge = launch sample edge + 3 + l*period + t_start)
  ring-A inject edge c(k) = IE(k) + 29; arrivals c + 2h (h = 1..3), src = PREV^h(q) on CW, NEXT^h(q) on CCW.
VM reservations the quadrant calendar must make (bank sample edges, COLL read group / COLL kq write group):
  QBG code flit i: reads src + 4 i + w (w 0..3) at IE + 1;  plain flit i: read src + i at IE + 16
  publish of (src s, flit i) arriving at hop h: write dst + s*stride + i at IE + 34 + 2h
  self-land (QBG / self_land=1): write dst + q*stride + i at IE + 29
  (both include KQ_SHARE_EDGES = 2 of the registered kq share hcollks_<q>, HBM-NSFIX/KQS 10-18; master pins at 32+2h / 27)
Gather span (fire -> last bank write) = 1 + 3 ((K-1) >> 1) + ((K-1) & 1) + 40 edges, K = ceil(F / R).
VM_RT (HBM-BANKLAT-COLL 10-19; RTL ot_hgi_coll_gq_issue #(VM_RT), default 0 = the edges above): the VM read answer
reaches the master V edges after its n+8 capture (faces bank pin + read share BANK_RT excess + die lanes). Read request
edges at the master pins are unchanged; inject c(k) = IE + 29 + V, every write + V, span + V.  --vm-rt V (any command)
or env COLLQ_VM_RT.  The bank SAMPLE edge of a read is the master edge + the die's rq lane (+ faces pin): the quadrant
calendar adds the die's per-bank rq lane depth (padded, equal per bank) to the read reservations it merges.

  python3 tools/hgi_sim/collq_gather_1018.py check            # conflict proof (links, banks) for F < 400, R 1/2
  python3 tools/hgi_sim/collq_gather_1018.py vectors OUTDIR   # QBG golden vectors for the RTL bench
  python3 tools/hgi_sim/collq_gather_1018.py schedule OUT.json  # constants + per-shape spans for the pricer / H-D4G
  python3 tools/hgi_sim/collq_gather_1018.py calendar OUT.json [--merge SCHED.json] [--shape NAME --mode plain|qbg]
          [--q Q] [--R 2] [--fire-index N] [--src W --dst W --stride W]
          # quadrant VM calendar_<q> reservations of one gather (hbm_vm_static_calendar.py schedule form)

ISSUE_AHEAD (HBM-VMEARLY-COLL 10-19; RTL ot_hgi_coll_gq #(ISSUE_AHEAD = N), default 0 = one gather in flight): N + 1
descriptor SLOTS (static field [101 +: SW], gather j -> slot j mod (N + 1)), so gather j+1 fires while gather j drains and
its VM reads issue while j's reads are in flight.  Fire rules (each a static fault in the RTL when violated):
  N = 0      fire(j) >= fire(j-1) + issue_rel(K-1) + ND + 1              ND = 40 + VM_RT (busy = issue + drain)
  N > 0      fire(j) >= fire(j-1) + issue_rel(K-1) + GAP                 GAP = 11 (IA_GAP: every same-tag ring entry pair of two
                                                                         gathers >= 12 edges apart = k, k+8 of one gather);
                                                                         15 for plain -> QBG (reads @16 vs @1 stay in order)
             fire(j) >= fire(j-N-1) + issue_rel(K(j-N-1)-1) + ND + 1     slot reuse (the slot's gather drained)
  RAW        a read of a word an earlier gather writes samples its bank >= 1 edge after that write's bank sample.
  python3 tools/hgi_sim/collq_gather_1018.py [--vm-rt V] ia-check   # cross-gather link/bank/tag proof of IA sequences
  python3 tools/hgi_sim/collq_gather_1018.py [--vm-rt V] ia-plan OUT.json   # fires / exposed edges, DS shapes, N 0..3

VM CALENDAR RESERVATIONS (d4g quadrant VM map results/rtl/hbm_b_rtl1_1017/vm_quadrant_map.json: read group 3 = COLL,
write code WG + 0 = 2 = COLL kq; the gather master shares both with hb_coll_<q> through the static owner splits
hcollrs_<q> / hcollks_<q>, zero latency): every gather read (bank b, sample edge e) needs rslot_v[b] = 1, rslot[3b+:3] =
3 and every publish / self-land write wslot_v[b] = 1, wslot[3b+:3] = 2 on the calendar word that governs bank sample edge
e.  Calendar word index = fire_index + (e - fire) + OWNER_LEAD (bank_static_abi timing: owner_select 1 edge after the
input pin; fire_index = the calendar ordinal of the descriptor fire edge, chosen by the compiler with t_start).
merge() refuses any bank edge already granted to another owner (the calendar is the static arbiter: no runtime arbitration).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

NEXT = {0: 1, 1: 3, 3: 2, 2: 0}
PREV = {v: k for k, v in NEXT.items()}
ISSUE_TO_INJECT = 29
STAGES = {
    "qbg_read_sample": 1, "plain_read_sample": 16, "rr_capture_qbg": 8, "rr_capture_plain": 23,
    "quantiser_s0": 10, "quantiser_out": 22, "payload_P": 24, "self_land_sample": 29, "self_land_kq_pin": 27,
    "ringB_cmd_reg": {"lp": 24, "state_read": 25, "inject": 27, "rx_fwd": "27+2h"},
    "ringA_cmd_reg": {"lp": 25, "state_read": 26, "inject": 28, "rx_fwd": "28+2h"},
    "ring_edge": {"lp": 26, "state_read": 27, "inject": 29, "arrival": "29+2h"},
    "publish_capture": "30+2h", "kq_reg": "31+2h", "publish_kq_pin": "32+2h", "publish_write_sample": "34+2h",
    "kq_share_edges": 2,
}
FIRE_FROM_LAUNCH = 3          # launch_v sampled at L -> fire edge L + 3 + l*period + t_start
ISA_RING_A_EXTRA_EDGES = 2    # every ISA ring-A command and rc_d: +2 edges vs the v5 parent
KQ_SHARE_EDGES = 2            # HBM-NSFIX/KQS 10-18: registered kq share (writer pin flops + vm_kq flops), A and B alike
VM_RT = int(os.environ.get("COLLQ_VM_RT", "0"))   # HBM-BANKLAT-COLL 10-19: ot_hgi_coll_gq_issue #(VM_RT); set by --vm-rt


def src_of(q, d, h):
    s = q
    for _ in range(h):
        s = PREV[s] if d == 0 else NEXT[s]
    return s


def flits(F, R):
    for i in range(F):
        r = i % R
        k = i // R
        yield i, r, k


def issue_rel(k):
    return 1 + 3 * (k >> 1) + (k & 1)


def span(F, R):
    K = (F + R - 1) // R
    return issue_rel(K - 1) + 38 + KQ_SHARE_EDGES + VM_RT


def schedule(q, F, R, qbg, self_land, src, dst, stride, Bs=0):
    """per quadrant: reads [(edge_rel_fire, bank, word)], writes [(edge_rel_fire, bank, word, (s, i))]"""
    reads, writes = [], []
    for i, r, k in flits(F, R):
        ie = issue_rel(k)
        code = (not qbg) or i < Bs
        if qbg and code:
            for w in range(4):
                a = src + 4 * i + w
                reads.append((ie + 1, a % 8, a))
        elif not qbg:
            a = src + i
            reads.append((ie + 16, a % 8, a))
        for h in (1, 2, 3):
            s = src_of(q, k & 1, h)
            a = dst + s * stride + i
            writes.append((ie + 32 + KQ_SHARE_EDGES + VM_RT + 2 * h, a % 8, a, (s, i)))
        if self_land or qbg:
            a = dst + q * stride + i
            writes.append((ie + 27 + KQ_SHARE_EDGES + VM_RT, a % 8, a, (q, i)))
    return reads, writes


def check(maxF=400):
    bad = []
    for R in (1, 2):
        for F in range(1, maxF):
            # directed links: (ring, quadrant, dir, ring edge)
            links = set()
            for i, r, k in flits(F, R):
                c = ISSUE_TO_INJECT + VM_RT + issue_rel(k)
                d = k & 1
                for q in range(4):
                    s = q
                    for h in range(3):
                        key = (r, s, d, c + 2 * h)
                        if key in links:
                            bad.append(("link", R, F, key))
                        links.add(key)
                        s = NEXT[s] if d == 0 else PREV[s]
            for qbg in (0, 1):
                Bs = F - (F + 32) // 33 if qbg else 0
                if qbg and (Bs <= 0 or F != Bs + (Bs + 31) // 32):
                    continue
                for q in range(4):
                    reads, writes = schedule(q, F, R, qbg, 1, 0x40, 0, ((F + 7) // 8) * 8, Bs)
                    for name, ev in (("read", reads), ("write", writes)):
                        seen = set()
                        for e in ev:
                            if (e[0], e[1]) in seen:
                                bad.append((name, R, F, qbg, q, e[:3]))
                            seen.add((e[0], e[1]))
    return bad


# ------------------------------------------------------------------ ISSUE_AHEAD (HBM-VMEARLY-COLL 10-19)
IA_GAP = 11


def nd():
    return 40 + VM_RT


def kring(F, R):
    return (F + R - 1) // R


def last_issue(g):
    return issue_rel(kring(g["F"], g["R"]) - 1)


def ia_gap(p, g):
    """minimum fire(j) - fire(j-1) - issue_rel(K(j-1)-1) at ISSUE_AHEAD > 0: the tag distance (IA_GAP) and the read
    stream order (a QBG gather reads at IE + 1, a plain one at IE + 16: the reads of j start after the reads of j-1)"""
    rel = lambda x: 1 if x["qbg"] else 16
    return max(IA_GAP, rel(p) - rel(g))


def g_schedule(q, g):
    return schedule(q, g["F"], g["R"], g["qbg"], g.get("self", 1), g["src"], g["dst"], g["stride"], g.get("Bs", 0))


def ia_fires(gathers, ia, t0=0, rq_lane=lambda b: 0, raw=True):
    """earliest legal fire edge of every gather (programme order) and the binding rule; rq_lane(b) = read request lane
    edges from the master to bank b's sample (die lanes + faces pin): RAW compares bank SAMPLE edges"""
    fires, why = [], []
    for j, g in enumerate(gathers):
        fe, w = t0, "first"
        if j:
            p = gathers[j - 1]
            if ia == 0:
                fe, w = fires[j - 1] + last_issue(p) + nd() + 1, "busy"
            else:
                fe, w = fires[j - 1] + last_issue(p) + ia_gap(p, g), "serial"
                if j > ia:
                    o = fires[j - ia - 1] + last_issue(gathers[j - ia - 1]) + nd() + 1
                    if o > fe:
                        fe, w = o, "slot"
        if raw:
            for pj in range(j):
                for q in range(4):
                    wr = {}
                    for e in g_schedule(q, gathers[pj])[1]:
                        wr[e[2]] = max(wr.get(e[2], -1), fires[pj] + e[0])
                    for e in g_schedule(q, g)[0]:
                        if e[2] in wr:
                            need = wr[e[2]] + 1 - (e[0] + rq_lane(e[1]))
                            if need > fe:
                                fe, w = need, f"raw:{pj}"
        fires.append(fe)
        why.append(w)
    return fires, why


def ia_check_seq(gathers, fires):
    """absolute link / bank / tag-distance conflicts of a gather sequence (all quadrants)"""
    bad, links, rd, wr, tags = [], {}, {}, {}, {}
    for j, (g, fe) in enumerate(zip(gathers, fires)):
        for i, r, k in flits(g["F"], g["R"]):
            ie = fe + issue_rel(k)
            c = ie + ISSUE_TO_INJECT + VM_RT
            d = k & 1
            for q in range(4):
                s = q
                for h in range(3):
                    key = (r, s, d, c + 2 * h)
                    if key in links and links[key] != j:
                        bad.append(("link", j, links[key], key))
                    links[key] = j
                    s = NEXT[s] if d == 0 else PREV[s]
            key = (r, k % 8)
            if key in tags and tags[key][0] != j and ie - tags[key][1] < 12:
                bad.append(("tag", j, tags[key][0], key, ie - tags[key][1]))
            tags[key] = (j, ie)
        for q in range(4):
            reads, writes = g_schedule(q, g)
            for name, ev, tab in (("read", reads, rd), ("write", writes, wr)):
                for e in ev:
                    key = (q, fe + e[0], e[1])
                    if key in tab and tab[key] != j:
                        bad.append((name, j, tab[key], key))
                    tab[key] = j
    return bad


def ds_gathers(n_each=2):
    """the DS d4g gather shapes (QBG R2: expert_intermediate / o_group / engram_rows; plain R2 / R1), production order mix"""
    out, base = [], 0x0
    for name, n in SHAPES.items():
        s = n // 4
        Bs = s // 32
        F = Bs + (Bs + 31) // 32
        out.append(dict(name=f"{name}_qbg", F=F, R=2, qbg=1, Bs=Bs, self=1, stride=((F + 7) // 8) * 8))
        out.append(dict(name=f"{name}_plain", F=s // 8, R=2, qbg=0, Bs=0, self=1, stride=((s // 8 + 7) // 8) * 8))
    return out


def place(gathers, src0=0x1000, dst0=0x0000):
    """distinct src / dst regions (independent gathers); returns copies with src / dst set"""
    out, src, dst = [], src0, dst0
    for g in gathers:
        g = dict(g)
        g["src"], g["dst"] = src, dst
        src += ((4 * g["F"] if g["qbg"] else g["F"]) + 7) // 8 * 8
        dst += 4 * g["stride"]
        out.append(g)
    return out


def read_edges(q, g, fe):
    return sorted(fe + e[0] for e in g_schedule(q, g)[0])


def exposed(gathers, fires):
    """per consecutive pair: first VM read (master edge) of gather j minus the last VM read of gather j-1 (the operand
    stream gap the consumer sees; the capture is the read + the fixed round trip, so the same gap)"""
    out = []
    for j in range(1, len(gathers)):
        out.append(read_edges(0, gathers[j], fires[j])[0] - read_edges(0, gathers[j - 1], fires[j - 1])[-1])
    return out


def ia_check(seed=20261019, trials=400):
    import random
    rnd = random.Random(seed)
    bad, n = [], 0
    shapes = ds_gathers()
    for ia in (1, 2, 3):
        for t in range(trials):
            seq = []
            for _ in range(rnd.randint(2, 8)):
                if rnd.random() < 0.5:
                    seq.append(dict(rnd.choice(shapes)))
                else:
                    R = rnd.choice((1, 2))
                    F = rnd.randint(1, 120)
                    seq.append(dict(name="rand", F=F, R=R, qbg=0, Bs=0, self=rnd.randint(0, 1), stride=((F + 7) // 8) * 8))
            seq = place(seq)
            fires, _ = ia_fires(seq, ia)
            bad += ia_check_seq(seq, fires)
            n += 1
    return n, bad


def ia_legal(gathers, fires, ia, rq_lane=lambda b: 0):
    """every ISSUE_AHEAD fire rule (ia_fires docstring) holds for these fires; returns the violated rules"""
    bad = []
    for j in range(1, len(gathers)):
        p, g = gathers[j - 1], gathers[j]
        need = fires[j - 1] + last_issue(p) + (nd() + 1 if ia == 0 else ia_gap(p, g))
        if fires[j] < need:
            bad.append(("serial", j, fires[j], need))
        if ia and j > ia and fires[j] < fires[j - ia - 1] + last_issue(gathers[j - ia - 1]) + nd() + 1:
            bad.append(("slot", j))
    for j, g in enumerate(gathers):
        for pj in range(j):
            for q in range(4):
                wr = {}
                for e in g_schedule(q, gathers[pj])[1]:
                    wr[e[2]] = max(wr.get(e[2], -1), fires[pj] + e[0])
                for e in g_schedule(q, g)[0]:
                    if e[2] in wr and fires[j] + e[0] + rq_lane(e[1]) <= wr[e[2]]:
                        bad.append(("raw", j, pj, q, e[2]))
    return bad


def bench_rows():
    """the IA bench programme: 12 rows (a multiple of NB = 2, 3, 4, so the static slot j mod NB repeats every loop), DS
    shapes, row 3 a DEPENDENT plain gather of the words row 2 landed (RAW on its own quadrant's slice 0)"""
    ex = lambda: dict(F=19, R=2, qbg=1, Bs=18, self=1, stride=24, vec=1)
    og = lambda R=2: dict(F=9, R=R, qbg=1, Bs=8, self=1, stride=16, vec=2)
    en = lambda: dict(F=50, R=2, qbg=1, Bs=48, self=1, stride=56, vec=3)
    pl = lambda F, R=2, self=1: dict(F=F, R=R, qbg=0, Bs=0, self=self, stride=((F + 7) // 8) * 8, vec=0)
    rows = [ex(), og(), pl(72), pl(72), en(), pl(19, 1, 0), og(1), pl(1), dict(ex(), R=1), og(), pl(32), ex()]
    src, dst = 0x1000, 0x0000
    for j, g in enumerate(rows):
        g["src"] = src
        src += ((4 * g["Bs"] if g["qbg"] else g["F"]) + 7) // 8 * 8
        g["dst"] = dst
        dst += 4 * g["stride"]
    rows[3]["src"] = rows[2]["dst"]            # = quadrant slice s = 0 of row 2's landing (self-land in q0, publish elsewhere)
    rows[3]["dep"] = 2
    return rows


def ia_bench(out, ia, lanes=False, dep_mutant=False, loops=2):
    """rows.txt for tb_hgi_coll_gq_ia: header 'NR PERIOD LOOPS', then per row 'qbg r2 self t F Bs src dst stride slot vec
    dep'; expected exposed edges (master read stream gaps, rows 1..NR-1 of loop 0 and the loop-boundary pair)"""
    rows = bench_rows()
    lane = (lambda b: 4 + 1 + (b * 23 + 5) % 66) if lanes else (lambda b: 0)
    nb = ia + 1
    if dep_mutant:
        fires, why = ia_fires(rows, ia, raw=False, rq_lane=lane)
    else:
        fires, why = ia_fires(rows, ia, rq_lane=lane)
    period = fires[-1] - fires[0] + 1
    two = rows + rows
    while True:
        f2 = fires + [f + period for f in fires]
        bad = ia_legal(two, f2, ia, lane)
        if dep_mutant:
            bad = [b for b in bad if b[0] != "raw"]
        if not bad:
            break
        period += 1
    lines = [f"{len(rows)} {period} {loops}"]
    for j, (g, t) in enumerate(zip(rows, fires)):
        lines.append(" ".join(str(x) for x in (g["qbg"], int(g["R"] == 2), g["self"], t, g["F"], g["Bs"], g["src"], g["dst"],
                                               g["stride"], j % nb if ia else 0, g["vec"], g.get("dep", -1))))
    seq = rows + [rows[0]]
    exp = exposed(seq, fires + [fires[0] + period])
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "rows.txt").write_text("\n".join(lines) + "\n")
    (Path(out) / "expected_exposed.txt").write_text(" ".join(str(x) for x in exp) + "\n")
    doc = dict(ia=ia, vm_rt=VM_RT, nd=nd(), lanes=lanes, dep_mutant=dep_mutant, period=period, fires=fires, why=why,
               exposed=exp, exposed_sum=sum(exp), rows=rows)
    (Path(out) / "ia_bench.json").write_text(json.dumps(doc, indent=1) + "\n")
    return doc


def ia_plan():
    doc = {"vm_rt": VM_RT, "nd": nd(), "ia_gap": IA_GAP, "per_shape": {}}
    for g in ds_gathers():
        row = {}
        for ia in (0, 1, 2, 3):
            seq = place([dict(g) for _ in range(8)])
            fires, why = ia_fires(seq, ia)
            row[f"ia{ia}"] = dict(fire_period=[b - a for a, b in zip(fires, fires[1:])], exposed=exposed(seq, fires), why=why)
        doc["per_shape"][g["name"]] = dict(F=g["F"], R=g["R"], K=kring(g["F"], g["R"]), issue_edges=last_issue(g), **row)
    return doc


# ------------------------------------------------------------------ QBG golden vectors
SHAPES = {"expert_intermediate": 2304, "o_group": 1024, "engram_rows": 6144}


def e4m3_byte(v):
    import hdc_golden_v41 as G
    pos = {float(G.E4M3[c]): c for c in range(127)}
    out = np.zeros(v.shape, dtype=np.uint8)
    for j, x in enumerate(v.reshape(-1)):
        out.reshape(-1)[j] = pos[abs(float(x))] | (0x80 if np.signbit(x) else 0)
    return out


def word_hex(b):
    """bytes (32, little-endian lanes) -> 256-b hex word (msb first)"""
    return bytes(b[::-1]).hex()


def vectors(outdir, seed=20261018):
    import hdc_golden_v41 as G
    from hdc_golden import F as FT, to_bf16
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    meta = {}
    kinds = ["normal", "heavy", "floor", "large", "bf16", "ties"]
    for ci, (name, n) in enumerate(SHAPES.items()):
        s = n // 4
        Bs = s // 32
        Es = (Bs + 31) // 32
        for q in range(4):
            k = kinds[(ci * 4 + q) % len(kinds)]
            if k == "normal":
                x = rng.standard_normal(s)
            elif k == "heavy":
                x = rng.standard_t(1.5, s) * 10.0 ** rng.integers(-6, 4)
            elif k == "floor":
                x = np.zeros(s)
                x[rng.integers(0, s, 5)] = rng.standard_normal(5) * 1e-6
                x[: s // 2] = rng.standard_normal(s // 2)
            elif k == "large":
                x = rng.standard_normal(s) * 3e4
            elif k == "bf16":
                x = to_bf16(rng.standard_normal(s).astype(FT))
            else:
                e = rng.integers(-8, 8, s)
                x = np.ldexp(1.0 + (rng.integers(0, 16, s) * 2 + 1) / 32.0, e) * rng.choice([-1, 1], s)
            x = np.asarray(x, dtype=FT)
            if k in ("normal", "heavy", "large"):
                x[rng.integers(0, s, 3)] = -0.0
            codes, ex = G.quant_fp8(x, 32)
            cb = e4m3_byte(codes).reshape(Bs, 32)
            src_lines = []
            xb = x.view(np.uint32).reshape(-1, 8)
            for w in xb:
                src_lines.append("".join("%08x" % int(v) for v in w[::-1]))
            rec = [word_hex(cb[b]) for b in range(Bs)]
            for g in range(Es):
                eb = np.zeros(32, dtype=np.uint8)
                for j in range(32):
                    b = 32 * g + j
                    if b < Bs:
                        eb[j] = int(ex[b]) + 127
                rec.append(word_hex(eb))
            (out / f"{name}_q{q}_src.hex").write_text("\n".join(src_lines) + "\n")
            (out / f"{name}_q{q}_rec.hex").write_text("\n".join(rec) + "\n")
        meta[name] = {"n": n, "slice": s, "Bs": Bs, "Es": Es, "F": Bs + Es, "stride": ((Bs + Es + 7) // 8) * 8}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    return meta


COLL_RG = 3            # read group of hb_coll_<q> (and the gather master via hcollrs_<q>) in every d4g quadrant
COLL_WCODE = 2         # wslot code of the COLL kq write port (WG + 0, WG = 2)
OWNER_LEAD = 1         # bank_static_abi.json timing: owner_select = input_pin + 1
RB = WB = 3            # rslot / wslot bits per bank (quadrant_abi params RB / WB)


def reservations(q, F, R, qbg, Bs, src, dst, stride, fire_index=0):
    """{calendar word index: {"r": set(banks), "w": set(banks)}} for one gather of quadrant q"""
    reads, writes = schedule(q, F, R, qbg, 1, src, dst, stride, Bs)
    res = {}
    for kind, ev in (("r", reads), ("w", writes)):
        for e in ev:
            idx = fire_index + e[0] + OWNER_LEAD
            slot = res.setdefault(idx, {"r": set(), "w": set()})
            if e[1] in slot[kind]:
                raise ValueError(f"gather double-books bank {e[1]} ({kind}) at calendar word {idx}")
            slot[kind].add(e[1])
    return res


def merge(cycles, res):
    """overlay reservations onto a calendar schedule's cycle list (hbm_vm_static_calendar.py input form); refuse
    any bank edge already granted to another owner"""
    n = max(res) + 1
    while len(cycles) < n:
        cycles.append({})
    num = lambda v: int(v, 0) if isinstance(v, str) else int(v or 0)
    for idx, slot in sorted(res.items()):
        c = cycles[idx]
        for kind, vf, sf, bits, code in (("r", "rslot_v", "rslot", RB, COLL_RG), ("w", "wslot_v", "wslot", WB, COLL_WCODE)):
            v, sel = num(c.get(vf, 0)), num(c.get(sf, 0))
            for b in sorted(slot[kind]):
                own = (sel >> (bits * b)) & ((1 << bits) - 1)
                if (v >> b) & 1 and own != code:
                    raise ValueError(f"calendar word {idx}: bank {b} {sf} already owned by {own}, gather needs {code}")
                v |= 1 << b
                sel = (sel & ~(((1 << bits) - 1) << (bits * b))) | (code << (bits * b))
            if slot[kind]:
                c[vf], c[sf] = v, sel
    return cycles


def calendar_cmd(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="collq_gather_1018.py calendar")
    ap.add_argument("out", type=Path)
    ap.add_argument("--merge", type=Path, help="existing calendar_<q> schedule JSON {base, loops, cycles}")
    ap.add_argument("--shape", choices=sorted(SHAPES), default="expert_intermediate")
    ap.add_argument("--mode", choices=("plain", "qbg"), default="qbg")
    ap.add_argument("--q", type=int, default=0)
    ap.add_argument("--R", type=int, default=2)
    ap.add_argument("--fire-index", type=int, default=0)
    ap.add_argument("--src", type=int, default=0x40)
    ap.add_argument("--dst", type=int, default=0x200)
    ap.add_argument("--stride", type=int)
    a = ap.parse_args(argv)
    s = SHAPES[a.shape] // 4
    Bs = s // 32 if a.mode == "qbg" else 0
    F = Bs + (Bs + 31) // 32 if a.mode == "qbg" else s // 8
    stride = a.stride if a.stride is not None else ((F + 7) // 8) * 8
    if stride % 8:
        raise SystemExit("slice stride must be a multiple of 8 words (bank-conflict freedom)")
    res = reservations(a.q, F, a.R, a.mode == "qbg", Bs, a.src, a.dst, stride, a.fire_index)
    sched = json.loads(a.merge.read_text()) if a.merge else {"base": 0, "loops": 1, "cycles": []}
    merge(sched["cycles"], res)
    sched["collq_gather"] = dict(shape=a.shape, mode=a.mode, q=a.q, R=a.R, F=F, Bs=Bs, stride=stride, src=a.src, dst=a.dst,
                                 fire_index=a.fire_index, owner_lead=OWNER_LEAD, coll_read_group=COLL_RG,
                                 coll_write_code=COLL_WCODE, words=len(res),
                                 reads=sum(len(v["r"]) for v in res.values()), writes=sum(len(v["w"]) for v in res.values()),
                                 span_fire_to_last_write=span(F, a.R))
    a.out.write_text(json.dumps(sched, indent=1) + "\n")
    print("COLLQ_CALENDAR", json.dumps(sched["collq_gather"]))
    return 0


def main():
    global VM_RT
    if "--vm-rt" in sys.argv:
        j = sys.argv.index("--vm-rt")
        VM_RT = int(sys.argv[j + 1])
        del sys.argv[j:j + 2]
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "ia-check":
        n, bad = ia_check()
        print(f"COLLQ_IA_CHECK vm_rt={VM_RT} N=1..3 sequences={n} (DS shapes + random F<=120, R 1/2) conflicts={len(bad)}", bad[:5])
        return 0 if not bad else 1
    if cmd == "ia-bench":
        ia = int(sys.argv[3])
        doc = ia_bench(sys.argv[2], ia, lanes="--lanes" in sys.argv, dep_mutant="--dep-mutant" in sys.argv)
        print(f"COLLQ_IA_BENCH ia={ia} vm_rt={VM_RT} period={doc['period']} exposed_sum={doc['exposed_sum']} exposed={doc['exposed']} why={doc['why']}")
        return 0
    if cmd == "ia-plan":
        doc = ia_plan()
        Path(sys.argv[2]).write_text(json.dumps(doc, indent=1) + "\n")
        for k, v in doc["per_shape"].items():
            print(k, "K", v["K"], " ".join(f"ia{n}: period {v[f'ia{n}']['fire_period'][-1]} exposed {v[f'ia{n}']['exposed'][-1]}" for n in range(4)))
        return 0
    if cmd == "calendar":
        return calendar_cmd(sys.argv[2:])
    if cmd == "check":
        bad = check()
        print(f"COLLQ_SCHEDULE_CHECK F<400 R=1,2 plain+qbg links/reads/writes conflicts={len(bad)}", bad[:5])
        return 0 if not bad else 1
    if cmd == "vectors":
        print(json.dumps(vectors(sys.argv[2])))
        return 0
    if cmd == "schedule":
        shapes = {}
        for name, n in SHAPES.items():
            s = n // 4
            Bs = s // 32
            Es = (Bs + 31) // 32
            shapes[name] = {
                "plain": {"F": s // 8, "span_R1": span(s // 8, 1), "span_R2": span(s // 8, 2)},
                "qbg": {"Bs": Bs, "F": Bs + Es, "span_R1": span(Bs + Es, 1), "span_R2": span(Bs + Es, 2)},
            }
        doc = {"schema": "opentallas.hbm_d4g.collq_schedule.v1", "lane": "HBM-COLLQ", "rtl": "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv",
               "rule": __doc__.split("\n\n")[1], "stages_after_issue": STAGES, "fire_from_launch": FIRE_FROM_LAUNCH,
               "issue_to_inject": ISSUE_TO_INJECT + VM_RT, "vm_rt": VM_RT, "isa_ring_a_extra_edges": ISA_RING_A_EXTRA_EDGES,
               "span_formula": f"1 + 3((K-1)>>1) + ((K-1)&1) + 40 + VM_RT({VM_RT}), K = ceil(F/R)", "shapes_DS": shapes,
               "conflict_check": "check(): 0 link / read-bank / write-bank conflicts for F < 400, R 1 and 2, plain and QBG"}
        Path(sys.argv[2]).write_text(json.dumps(doc, indent=1))
        print(json.dumps(shapes))
        return 0
    raise SystemExit("usage: check | vectors OUTDIR | schedule OUT.json | calendar OUT.json [...]")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
