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

  python3 tools/hgi_sim/collq_gather_1018.py check            # conflict proof (links, banks) for F < 400, R 1/2
  python3 tools/hgi_sim/collq_gather_1018.py vectors OUTDIR   # QBG golden vectors for the RTL bench
  python3 tools/hgi_sim/collq_gather_1018.py schedule OUT.json  # constants + per-shape spans for the pricer / H-D4G
  python3 tools/hgi_sim/collq_gather_1018.py calendar OUT.json [--merge SCHED.json] [--shape NAME --mode plain|qbg]
          [--q Q] [--R 2] [--fire-index N] [--src W --dst W --stride W]
          # quadrant VM calendar_<q> reservations of one gather (hbm_vm_static_calendar.py schedule form)

VM CALENDAR RESERVATIONS (d4g quadrant VM map results/rtl/hbm_b_rtl1_1017/vm_quadrant_map.json: read group 3 = COLL,
write code WG + 0 = 2 = COLL kq; the gather master shares both with hb_coll_<q> through the static owner splits
hcollrs_<q> / hcollks_<q>, zero latency): every gather read (bank b, sample edge e) needs rslot_v[b] = 1, rslot[3b+:3] =
3 and every publish / self-land write wslot_v[b] = 1, wslot[3b+:3] = 2 on the calendar word that governs bank sample edge
e.  Calendar word index = fire_index + (e - fire) + OWNER_LEAD (bank_static_abi timing: owner_select 1 edge after the
input pin; fire_index = the calendar ordinal of the descriptor fire edge, chosen by the compiler with t_start).
merge() refuses any bank edge already granted to another owner (the calendar is the static arbiter: no runtime arbitration).
"""
import json
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
    return issue_rel(K - 1) + 38 + KQ_SHARE_EDGES


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
            writes.append((ie + 32 + KQ_SHARE_EDGES + 2 * h, a % 8, a, (s, i)))
        if self_land or qbg:
            a = dst + q * stride + i
            writes.append((ie + 27 + KQ_SHARE_EDGES, a % 8, a, (q, i)))
    return reads, writes


def check(maxF=400):
    bad = []
    for R in (1, 2):
        for F in range(1, maxF):
            # directed links: (ring, quadrant, dir, ring edge)
            links = set()
            for i, r, k in flits(F, R):
                c = ISSUE_TO_INJECT + issue_rel(k)
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
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
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
               "issue_to_inject": ISSUE_TO_INJECT, "isa_ring_a_extra_edges": ISA_RING_A_EXTRA_EDGES,
               "span_formula": "1 + 3((K-1)>>1) + ((K-1)&1) + 40, K = ceil(F/R)", "shapes_DS": shapes,
               "conflict_check": "check(): 0 link / read-bank / write-bank conflicts for F < 400, R 1 and 2, plain and QBG"}
        Path(sys.argv[2]).write_text(json.dumps(doc, indent=1))
        print(json.dumps(shapes))
        return 0
    raise SystemExit("usage: check | vectors OUTDIR | schedule OUT.json | calendar OUT.json [...]")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(main())
