#!/usr/bin/env python3
"""S81-SLICE xs lockstep program generator (bench stimulus only).

Builds, for one production stage image (L0 = stage0, L2 = stage3 of
results/rtl/dsrom_recovery_20261004/immutable_fullcatalog), the identical ROM images of both models (phase 0/1, stream
0..3, calendar action/time as ot_rom_4096x72_m8 via maps) and a cycle program:

  REFERENCE  production PQ slot (tb_s81sl_xs_ref): issuer GO / calendar prime+start on fixed edges, the hub VM's x
             responses on the calendar's VM-response rows, the twelve return groups' row counts before each retire.
  XS         ot_s81sl_xs: the same issuer words as is_d (plus the slice offset and gather windows), and the x as ring
             all-gather beats (own / W / E) in a chosen ring-arrival order.

The layer's x consumers in the stage: wq_a (q, tag0, np0), wkv (q, tag1, np1: positions read both buffer parities),
gate (BF16, tag2), shared.w1 (q, tag3, after a second q gather overwrote parity 1).  The xs offset OFF is set so the
latest beat of the first gather arrives on the last legal edge (tight): OFF - 1 must fault.

  xs_program.py --stage-dir DIR --out WORK [--off 37] [--slice 5] [--order near|far|rand] [--seed 1] [--off-load N]
"""
from __future__ import annotations

import argparse
import json
import random
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "s81_static_control"))
from pq_calendar import action_word, viamap  # noqa: E402  (the production 75-b action ABI and ROM via-map codec)

T_START = 60          # reference stage_start iteration
T_PRIME = 40
T_OFFCFG = 24
ADDR_LEAD = 2         # stream ROM address row = request row + 2 (STATE_PINS: raw calendar address, CALCAP +1 capture)
GO_LAT = 3            # timestamp t: calendar action captured by the controller at edge T_START + 3 + t (GO alongside)
VM_LAT = 4            # VM response data at iteration T_START + 4 + t (the controller's captured response edge)
HE_LAT = 9            # stream request t -> stream head (he) loaded at edge T_START + 9 + t
XS_LAG = 3            # xs: is_d pin edge i -> controller GO edge i + OFF + 3 (pin, delay line, output register)
ND = 8                # xs delay-line depth
XS_OUT = 1            # xs output relay stage (frame-word pin flops)


def phase_word(P, ph):
    w = P[2 * ph]
    return dict(ph=ph, bf=w & 1, K=(w >> 1) & 0x1FFF, nb=(w >> 14) & 0xFFFF, sbase=(w >> 30) & 0xFFFF,
                rows=(w >> 46) & 0xFFFF)


def pick_phases(P):
    """the layer x consumers: the two q K5120 phases before the first BF K5120 (gate), gate, the q K5120 after it"""
    ws = [phase_word(P, ph) for ph in range(1024) if P[2 * ph]]
    q = [w for w in ws if not w["bf"] and w["K"] == 5120]
    b = [w for w in ws if w["bf"] and w["K"] == 5120][0]
    d = [w for w in q if w["ph"] > b["ph"]][0]
    a = [w for w in q if w["ph"] < b["ph"]][-2:]       # the layer's wq_a / wkv (the two q K5120 phases before gate)
    return [a[0], a[1], b, d]


def words_beats(S, ph, fam):
    """per stream word: the x beats it reads"""
    out = []
    for w in range(ph["nb"]):
        x = S[ph["sbase"] + w]
        beats = []
        if x & 1:
            if fam:
                b = (x >> 1) & 7
                for k in range(4):
                    if (x >> (4 + k)) & 1:
                        u = (x >> (8 + 8 * k)) & 255
                        beats += [2 * u, 2 * u + 1]
            else:
                u, b, sv = (x >> 1) & 255, (x >> 9) & 7, (x >> 12) & 3
                if sv & 1:
                    beats.append((16 * u + b) >> 1)
                if sv & 2:
                    beats.append((16 * u + 8 + b) >> 1)
        out.append(beats)
    return out


def ring_order(nbeat, slc, order, rng):
    """per source (0 own, 1 W, 2 E): ordered beat list; owner(beat) = beat // 5 over 16 slices"""
    own = [g for g in range(nbeat) if g // 5 == slc]
    W, E = [], []
    for d in range(1, 9):
        W += [g for g in range(nbeat) if g // 5 == (slc - d) % 16]
    for d in range(1, 8):
        E += [g for g in range(nbeat) if g // 5 == (slc + d) % 16]
    lists = [own, W, E]
    if order == "far":
        lists = [own[::-1], W[::-1], E[::-1]]
    elif order == "rand":
        for li in lists:
            rng.shuffle(li)
    return lists


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--off", type=int, default=37)
    ap.add_argument("--off-load", type=int, help="offset value loaded into the xs (default --off; --off - 1 must fault)")
    ap.add_argument("--slice", type=int, default=5)
    ap.add_argument("--order", choices=["near", "far", "rand"], default="near")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    P = [int(l, 16) for l in (a.stage_dir / "spine_phase.hex").read_text().split()]
    S = [int(l, 16) for l in (a.stage_dir / "spine_stream.hex").read_text().split()]
    assert len(P) == 2048 and len(S) == 16384
    # ---- ROM images (identical for both models: INSTANCE names) ----
    (out / "pq_phase0.viamap.hex").write_text(viamap(P[:4096] + [0] * (4096 - len(P))))
    (out / "pq_phase1.viamap.hex").write_text(viamap(P[:4096] + [0] * (4096 - len(P))))
    for b in range(4):
        (out / f"pq_stream{b}.viamap.hex").write_text(viamap(S[4096 * b:4096 * (b + 1)]))
    A, B, C, D = pick_phases(P)
    plan = [dict(p=A, tag=0, np=0, fam=0), dict(p=B, tag=1, np=1, fam=0), dict(p=C, tag=2, np=0, fam=1),
            dict(p=D, tag=3, np=0, fam=0)]
    rows = {}

    def ev(t, **f):
        r = rows.setdefault(t, {})
        for k, v in f.items():
            assert k not in r or r[k] == v, (t, k, r.get(k), v)
            r[k] = v

    # x vectors: gid 0 = x_a (q par 0), 1 = x_b (q par 1), 2 = x_c (BF par 0 and later q par 1)
    xs = []
    for gid in range(3):
        v = []
        for blk in range(160):
            sc = 2.0 ** rng.randint(-12, 6)
            v += [rng.gauss(0.0, 1.0) * sc for _ in range(32)]
        xs.append(v)
        (out / f"x{gid}.hex").write_text("".join(f"{struct.unpack('<I', struct.pack('<f', f))[0]:08x}\n" for f in v))
    # ---- reference VM loads (calendar VM-response rows) ----
    loads = [("q0", 0, 0, 0, 10), ("q1", 1, 0, 1, 100), ("b0", 2, 1, 0, 190)]   # name, gid, fam, par, t0
    ref_vm = []                                                              # (iteration, gid, beat)

    def load(gid, fam, par, t0):
        for j in range(80):
            ev(t0 + j, vm_resp=1, resp_k=64 * j, resp_par=par, resp_fam=fam)
            ref_vm.append((T_START + VM_LAT + t0 + j, gid, j))
    for _, gid, fam, par, t0 in loads:
        load(gid, fam, par, t0)
    # ---- phases ----
    acc = 290
    for i, pl in enumerate(plan):
        pl["accept"] = acc + 4 * i
        pl["cfg"] = acc + 20 + 4 * i
        ev(pl["accept"], accept_tag=pl["tag"])
        ev(pl["cfg"], cfg=1, cfg_tag=pl["tag"])
    t = 340
    reads = {}            # (gather name) -> {beat: first stream timestamp}

    def stream(pl, t0, gather_of_pos):
        p = pl["p"]
        wb = words_beats(S, p, pl["fam"])
        tt = t0
        for pos in range(pl["np"] + 1):
            for w in range(p["nb"]):
                ev(tt, stream_req=1, stream_tag=pl["tag"], stream_pos=pos, stream_fam=pl["fam"],
                   stream_lastpos=int(w == p["nb"] - 1), stream_lastop=int(pos == pl["np"] and w == p["nb"] - 1))
                ev(tt + ADDR_LEAD, stream_addr=p["sbase"] + w)
                g = gather_of_pos[pos]
                for bt in wb[w]:
                    reads.setdefault(g, {}).setdefault(bt, tt)
                tt += 1
        return tt
    A_, B_, C_, D_ = plan
    A_["s0"] = t; t = stream(A_, t, ["q0"]); A_["s1"] = t
    t += 8
    B_["s0"] = t; t = stream(B_, t, ["q1", "q0"]); B_["s1"] = t
    p1_pos0_end = B_["s0"] + B_["p"]["nb"]            # last P1 read of parity 1 (pos 0) is before this timestamp
    t += 8
    C_["s0"] = t; t = stream(C_, t, ["b0"]); C_["s1"] = t
    q1b_t0 = p1_pos0_end + 12                           # reference reload of q parity 1 with x_c
    load(2, 0, 1, q1b_t0)
    t = max(t + 8, q1b_t0 + 80 + 50)
    D_["s0"] = t; t = stream(D_, t, ["q1b"]); D_["s1"] = t
    # launch / retire
    tl = t + 10
    ga = []                                            # (iteration, tag, total rows)
    for pl in plan:
        pl["launch"] = tl
        ev(tl, launch=1, launch_tag=pl["tag"])
        ga.append((T_START + GO_LAT + tl + 4, pl["tag"], pl["p"]["rows"] * (pl["np"] + 1)))
        pl["retire"] = tl + 60
        tl += 4
    for pl in plan:
        ev(pl["retire"], retire_mask=1 << pl["tag"])
    t_end = max(pl["retire"] for pl in plan) + 20
    ev(t_end, phase_end=1)
    ts = sorted(rows)
    assert len(ts) <= 4096
    packed = [(tt << 75) | action_word(rows[tt], action_bits=75) for tt in ts]
    (out / "pq_calendar_action.viamap.hex").write_text(viamap([w & ((1 << 72) - 1) for w in packed]))
    (out / "pq_calendar_time.viamap.hex").write_text(viamap([w >> 72 for w in packed]))
    cal_len = len(ts)
    # ---- the xs ring arrivals ----
    off = a.off
    xs_he = lambda tt: T_START + HE_LAT + tt + off + XS_LAG     # xs stream-head edge of a request at timestamp tt
    gathers = [("q0", 0, 0, 0), ("b0", 2, 1, 0), ("q1", 1, 0, 1), ("q1b", 2, 0, 1)]   # name, gid, fam, par
    busy = set()                                       # (iteration, source)
    arrivals = []                                      # (iteration, src, fam, beat, gid, gather)
    info = {}

    def place(name, gid, fam, R, lists, gaps):
        res = []
        for src, li in enumerate(lists):
            it = R + (0 if src == 0 else 1)
            for bt in li:
                if gaps:
                    while rng.random() < 0.2:
                        it += 1
                while (it, src) in busy:
                    it += 1
                busy.add((it, src))
                res.append((it, src, fam, bt, gid, name))
                it += 1
        return res
    gaps = a.order == "rand"
    # gather q0: tight -- the latest beat (relative to its first read) on the last legal edge
    lists0 = ring_order(80, a.slice, a.order, rng)
    trial = place("q0", 0, 0, 0, lists0, gaps)
    for x in trial:
        busy.discard((x[0], x[1]))
    R0 = min(xs_he(reads["q0"][bt]) - it for (it, _, _, bt, _, _) in trial if bt in reads["q0"])
    arr_q0 = [(it + R0, s, f, bt, g, n) for (it, s, f, bt, g, n) in trial]
    for x in arr_q0:
        busy.add((x[0], x[1]))
    arrivals += arr_q0
    last_q0 = max(x[0] for x in arr_q0)
    # gather b0 (BF16, own window): overlaps q0 on the ring, interleaved per source
    arr_b0 = place("b0", 2, 1, R0 + 7, ring_order(80, a.slice, a.order, rng), gaps)
    arrivals += arr_b0
    # gather q1: after the q0 window closes (one q write parity at a time)
    R1 = last_q0 + 3
    arr_q1 = place("q1", 1, 0, R1, ring_order(80, a.slice, a.order, rng), gaps)
    arrivals += arr_q1
    # gather q1b (x_c, q family, parity 1 again): after P1's last parity-1 read in the xs
    gw_q1b_act = xs_he(p1_pos0_end) + 4
    R3 = gw_q1b_act + 2
    arr_q1b = place("q1b", 2, 0, R3, ring_order(80, a.slice, a.order, rng), gaps)
    arrivals += arr_q1b
    # every beat in time; the q0 bound is tight by construction
    slack = {}
    for name, arr in (("q0", arr_q0), ("b0", arr_b0), ("q1", arr_q1), ("q1b", arr_q1b)):
        sl = min(xs_he(reads[name][bt]) - it for (it, _, _, bt, _, _) in arr if bt in reads[name])
        assert sl >= 0, (name, sl)
        slack[name] = sl
        info[name] = dict(first=min(x[0] for x in arr), last=max(x[0] for x in arr), slack=sl,
                          beats_read=len(reads[name]))
    assert slack["q0"] == 0
    # ---- issuer words (is_d) ----
    is_words = {}

    def isw(it, **f):
        w = is_words.get(it, 0)
        lay = dict(go=(0, 1), ph=(1, 10), np=(11, 3), xbase=(14, 19), xps=(33, 19), obase=(52, 19), ops=(71, 19),
                   fmt=(90, 2), f_fault=(92, 1), prime=(93, 1), start=(94, 1), base=(95, 12), length=(107, 13),
                   gw=(120, 1), gw_fam=(121, 1), gw_par=(122, 1), off_we=(123, 1), off=(124, 8))
        for k, v in f.items():
            lo, wd = lay[k]
            assert 0 <= v < (1 << wd)
            w |= v << lo
        is_words[it] = w
    off_load = a.off if a.off_load is None else a.off_load
    isw(T_OFFCFG, off_we=1, off=off_load)
    isw(T_PRIME, prime=1, base=0, length=cal_len)
    isw(T_START, start=1, base=0, length=cal_len)
    ref_go = []
    for pl in plan:
        it = T_START + GO_LAT + pl["accept"]
        f = dict(go=1, ph=pl["p"]["ph"], np=pl["np"], xbase=64, xps=8192, obase=98304, ops=2048, fmt=0)
        isw(it, **f)
        ref_go.append((it, pl["p"]["ph"], pl["np"]))

    def gw_at(act_edge, fam, par):
        it = act_edge - off - XS_LAG
        while it in is_words:
            it -= 1
        isw(it, gw=1, gw_fam=fam, gw_par=par)
        return it
    gw_at(R0 - 2, 0, 0)
    gw_at(R0 + 5, 1, 0)
    assert R0 + 5 <= min(x[0] for x in arr_b0)
    gw_at(R1 - 1, 0, 1)
    gw_at(R3 - 1, 0, 1)
    # delay-line occupancy (fixed delay OFF + 2: in flight between pin edge and pop)
    its = sorted(is_words)
    for i in its:
        infl = [j for j in its if j <= i < j + off_load + 2]
        assert len(infl) <= ND, ("delay line", i, len(infl))
    # ---- write the program ----
    lines = []
    for it in (T_PRIME,):
        lines.append(f"{it} RPRIME {cal_len}")
    lines.append(f"{T_START} RSTART {cal_len}")
    for it, ph, np_ in ref_go:
        lines.append(f"{it} RGO {ph} {np_} 64 8192 98304 2048 0")
    for it, gid, bt in ref_vm:
        lines.append(f"{it} RVM {gid} {bt}")
    for it, tag, n in ga:
        lines.append(f"{it} RGA {tag} {n}")
    for it, w in is_words.items():
        lines.append(f"{it} XIS {w:040x}")
    for it, src, fam, bt, gid, name in arrivals:
        lines.append(f"{it} XG {src} {fam} {bt} {gid}")
    lines.sort(key=lambda s: int(s.split()[0]))
    end_it = T_START + GO_LAT + t_end + off + 80
    (out / "prog.txt").write_text("\n".join(lines) + "\n")
    meta = dict(stage_dir=str(a.stage_dir), off=off, off_load=off_load, slice=a.slice, order=a.order, seed=a.seed,
                cal_rows=cal_len, end_iter=end_it, t_start=T_START,
                phases=[dict(ph=pl["p"]["ph"], tag=pl["tag"], np=pl["np"], fam=pl["fam"], K=pl["p"]["K"],
                             nb=pl["p"]["nb"], rows=pl["p"]["rows"], accept=pl["accept"], s0=pl["s0"], s1=pl["s1"])
                        for pl in plan],
                gathers=info, expected_xs_minus_ref=off + XS_LAG - 8 + XS_OUT)
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"XS_PROGRAM stage={a.stage_dir.name} phases={[pl['p']['ph'] for pl in plan]} cal_rows={cal_len} "
          f"arrivals={len(arrivals)} off={off} off_load={off_load} order={a.order} slice={a.slice} end={end_it} "
          f"slack={slack}")


if __name__ == "__main__":
    main()
