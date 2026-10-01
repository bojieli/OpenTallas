#!/usr/bin/env python3
"""ROM-field images for the experimental W17/W10 FAST/PP runtime baseline.

FAST/PP/BP default off; FRONT_PAR remains zero. No adoption or headline-clock claim.
Library used by the runtime-composition gate (tools/w17_w10_field_rt_gate.py) only; it does not enable full-shape runtime adoption.

A PHASE is one or more weight matrices sharing one x vector and one x family (FP8/FP4 = the FP8-quantised x of
golden linear_q; BF16 = the BF16 x of golden mv / linear_bf16), as in tools/v41_rom_ksplit_bankmap.py.  For a
field of NP element PAIRS (ot_v41_pair_w17w10, NB = 2: each pair slot holds one segment structure for the two rows
2R, 2R + 1 of a "super row" R) cut into R_REG return regions (ot_v41_field_w17w10), a phase is placed with W10's
rules -- golden-aligned K segments (model split), element read order, disjoint classes, LPT by words -- plus
one W17 rule the multi-root return needs: ALL segments of a super row lie in ONE region (region = super row
mod R_REG), so each row finishes in its region's root.

Outputs per phase:
  cfg[pair]      the 25 configuration words (ot_v41_rom_elem cfg_a 0 .. 3*NSEG) of every pair;
  words[macro]   ROM words appended at each macro's fill pointer (segments contiguous, element read order);
  stream         the static x schedule (ot_v41_spine stream ROM words, one per cycle of one position);
  rows           the phase's row tags: matrix mi's rows are tags off_mi .. off_mi + rows_mi - 1.
The stream is W10's (tools/rtl_v41_rom_array.py build_phase): per round (q, b) the needed units ascending,
spread over r = max(5, beats, most words any element reads in the round).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import v41_rom_ksplit_bankmap as S  # noqa: E402
from rtl_v41_rom_array import Mat, bf16_word, viamap  # noqa: E402,F401

NSEG = 8
NCH, NCHB = 16, 8
CW = 3 * NSEG + 1
SENT = 0x8000


def bf16_pairs(np_: int, nbf: int) -> np.ndarray:
    return np.unique((np.arange(nbf, dtype=np.int64) * np_) // nbf)


class Field:
    """NP pair slots (a power of two: the return tree's leaves), R return regions, of which `active` slots hold an
    element (None: all; the die floorplan's pair count); BF16 lanes on `nbf` active pairs, spread evenly over each
    region's active pairs; per-macro ROM depth `depth` words (a parameter: the macro may become 4,096 deep)."""

    def __init__(self, np_: int, r: int, nbf: int, depth: int = 8192, active: int | None = None, pp: bool = False, fast: bool = False):
        assert np_ & (np_ - 1) == 0 and r & (r - 1) == 0 and 2 * np_ >= 2 * r
        self.np, self.r, self.nbf, self.depth = np_, r, nbf, depth
        self.pp, self.fast = pp, fast
        self.add_latency = 8 if fast else S.FADD_REC
        per = np_ // r
        self.act = np.ones(np_, dtype=bool)
        if active is not None and active < np_:
            # region j keeps its first a_j slots; the remainder spread one per region from region 0
            base, extra = divmod(active, r)
            self.act[:] = False
            for j in range(r):
                self.act[j * per: j * per + base + (1 if j < extra else 0)] = True
        self.bf = np.zeros(np_, dtype=bool)
        if active is None or active >= np_:
            self.bf[bf16_pairs(np_, nbf)] = True
        else:
            bper, bext = divmod(nbf, r)
            for j in range(r):
                a = np.flatnonzero(self.act[j * per:(j + 1) * per]) + j * per
                k = bper + (1 if j < bext else 0)
                self.bf[a[(np.arange(k) * len(a)) // k]] = True
        self.fill = np.zeros(np_, dtype=np.int64)          # pair slot fill (both macros share the structure)
        self.words = [dict() for _ in range(2 * np_)]      # macro -> {address: word}
        self.cfg = []                                      # per phase: [pair][25] words
        self.stream = []                                   # stream ROM words (all phases)
        self.phases = []                                   # per phase: dict(meta)

    def region_pairs(self, reg: int) -> np.ndarray:
        n = self.np // self.r
        a = np.arange(reg * n, (reg + 1) * n)
        return a[self.act[a]]


def _place(field: Field, mats: list[Mat]):
    """Region-constrained LPT placement of every super row's segments.  Returns segment dicts."""
    load = np.zeros(field.np, dtype=np.int64)
    items = []
    off = 0
    info = []
    for mi, m in enumerate(mats):
        srows = -(-m.rows // 2)
        # every super row lives in one region (its rows' VM group), so the K split is chosen per region: the
        # region's super rows share its (BF16-capable) pairs, as the model splits a matrix over the field
        per_reg = len(field.region_pairs(0))
        if m.fmt == "bf16":
            per_reg = int(field.bf[field.region_pairs(0)].sum())
        rows_reg = -(-srows // field.r)
        s = S.model_split(rows_reg, m.K, per_reg, m.fmt)
        segs = S.segments(m.K, s)
        info.append(dict(off=off, srows=srows, s=s, segs=segs))
        for si, (e0, el) in enumerate(segs):
            items.append((S.seg_words(m.fmt, e0, el), mi, si, e0, el))
        off += m.rows
    items.sort(key=lambda t: (-t[0], t[1], t[2]))
    out = []
    held = {}                                     # (family, u0, u1) -> set(pairs)
    for w, mi, si, e0, el in items:
        m = mats[mi]
        rng = (S.family(m.fmt),) + S.unit_range(m.fmt, e0, el)
        for R_ in range(info[mi]["srows"]):
            reg = R_ % field.r
            allowed = field.region_pairs(reg)
            if m.fmt == "bf16":
                allowed = allowed[field.bf[allowed]]
            ok = []
            for p in allowed:
                bad = False
                for (f2, a0, a1), ps in held.items():
                    if p in ps and f2 == rng[0] and (a0, a1) != rng[1:] and a0 < rng[2] and rng[1] < a1:
                        bad = True
                        break
                if not bad:
                    ok.append(p)
            assert ok, ("no legal pair", m.name, R_, si)
            ok = np.array(ok)
            order = np.lexsort((ok, field.fill[ok], load[ok]))
            p = int(ok[order[0]])
            load[p] += w
            held.setdefault(rng, set()).add(p)
            out.append(dict(mi=mi, tensor=mi, fmt=m.fmt, K=m.K, row=R_, e0=e0, elems=el, pair=p, seg=si,
                            nseg=len(info[mi]["segs"])))
    return out, info, int(load.max())


def add_phase(field: Field, mats: list[Mat], fmt_fp32=(False, False), rsplit: int = 0) -> dict:
    """Place one phase, append its ROM words, configuration and stream.  Returns the phase meta."""
    bf = mats[0].fmt == "bf16"
    assert all((m.fmt == "bf16") == bf for m in mats), "one x family per phase"
    K = mats[0].K
    assert all(m.K == K for m in mats)
    segs, info, t_read = _place(field, mats)
    by_p = {}
    for i, sg in enumerate(segs):
        by_p.setdefault(sg["pair"], []).append(i)
    # addresses: each pair's segments contiguous from its fill pointer, in element read order
    cfg = [[0] * CW for _ in range(field.np)]
    rounds, demand = {}, {}
    for p in range(field.np):
        sids = by_p.get(p, [])
        if not sids:
            continue
        if field.pp:
            field.fill[p] += int(field.fill[p]) & 1
        phase_start = int(field.fill[p])
        ps = [segs[i] for i in sids]
        cls = {}
        for j, sg in enumerate(ps):
            cls.setdefault(S.unit_range(sg["fmt"], sg["e0"], sg["elems"]), []).append(j)
        keys = sorted(cls)
        hw, centries = [], []
        for (u0, u1) in keys:
            ids = sorted(cls[(u0, u1)], key=lambda j: (ps[j]["fmt"], ps[j]["row"], ps[j]["mi"]))
            centries.append((u0, u1 - u0, len(hw), len(hw) + len(ids) - 1))
            hw += ids
        assert len(hw) <= NSEG and len(centries) <= NSEG, ("element over capacity", p, len(hw), len(centries))
        for slot, j in enumerate(hw):
            sg = ps[j]
            m = mats[sg["mi"]]
            sg["base"] = int(field.fill[p])
            order = S.segment_order(sg["fmt"], sg["e0"], sg["elems"])
            field.fill[p] += len(order)
            assert field.fill[p] <= field.depth, ("ROM depth", p)
            u0, u1 = S.unit_range(sg["fmt"], sg["e0"], sg["elems"])
            lo = sg["e0"] <= u0 * 512
            hi = (u1 * 512 - 256) < sg["e0"] + sg["elems"]
            off = info[sg["mi"]]["off"]
            tags = []
            for k in range(2):
                r = 2 * sg["row"] + k
                tags.append(off + r if r < m.rows else SENT | (sg["mi"] * 64 + sg["row"]))
            cfg[p][2 * NSEG + 1 + slot] = tags[1]
            cfg[p][slot] = (tags[0] | (sg["seg"] << 16) | (sg["nseg"] << 21) | (int(sg["fmt"] == "fp4") << 26)
                            | (int(lo) << 27) | (int(hi) << 28) | (sg["base"] << 29)
                            | (int(sg["fmt"] == "bf16") << 42))
            for mb in range(2):
                row = 2 * sg["row"] + mb
                if row >= m.rows:
                    continue
                wd = field.words[2 * p + mb]
                for k, (u, b, h) in enumerate(order):
                    if sg["fmt"] == "bf16":
                        w = bf16_word(m, row, u, b)
                    elif sg["fmt"] == "fp8":
                        w = m.block_word(row, 2 * u + h, b)
                    else:
                        w = 0
                        for half in (0, 1):
                            c = 2 * u + half
                            if sg["e0"] <= c * 256 < sg["e0"] + sg["elems"]:
                                w |= m.block_word(row, c, b) << (136 * half)
                    wd[sg["base"] + k] = w
        for c, (u0, nu, s0, s1) in enumerate(centries):
            cfg[p][NSEG + c] = 1 | (u0 << 1) | (nu << 9) | (s0 << 16) | (s1 << 19) | (int(bf) << 22)
        nsub = max([-(-nu // 8) for _, nu, _, _ in centries] + [1])
        cfg[p][2 * NSEG] = nsub - 1
        if field.pp:
            # Reorder only this phase; snapshot before overwriting overlapping addresses.
            by_key = {}
            for j, sg in enumerate(ps):
                for k, (u, b, h) in enumerate(S.segment_order(sg["fmt"], sg["e0"], sg["elems"])):
                    by_key[(j, u, b, h)] = [field.words[2*p+mb].get(sg["base"] + k, 0) for mb in range(2)]
            order_pp = S.element_order(ps)
            assert phase_start + len(order_pp) <= 8192
            for i, key in enumerate(order_pp):
                for mb in range(2):
                    field.words[2*p+mb][phase_start+i] = by_key[key][mb]
            cfg[p][2*NSEG] |= phase_start << 6
        for (i, u, b, h) in S.element_order(ps):
            sg = ps[i]
            q = (u - S.unit_range(sg["fmt"], sg["e0"], sg["elems"])[0]) // S.IL
            rounds.setdefault((q, b), set()).add(u)
            demand[(q, b, p)] = demand.get((q, b, p), 0) + 1
    # element round capacity (W10 frozen interface): an element reads at most NCH (FP8/FP4) or NCHB (BF16)
    # words per round -- one chain register per word position of the round
    cap = NCHB if bf else NCH
    over = {k: v for k, v in demand.items() if v > cap}
    assert not over, ("element round capacity exceeded (words per round > %d)" % cap, sorted(over.items())[:4])
    # stream (one position)
    C = K // 256
    beats = []
    for (q, b) in sorted(rounds):
        units = sorted(rounds[(q, b)])
        dmax = max(v for (qq, bb, _), v in demand.items() if (qq, bb) == (q, b))
        if bf:
            groups = [units[i:i + 4] for i in range(0, len(units), 4)]
            rl = max(field.add_latency, len(groups) + int(field.fast), dmax)
            slots = [None] * rl
            for i, g in enumerate(groups):
                slots[(i * (rl - int(field.fast))) // len(groups)] = g
            for g in slots:
                if g is None:
                    beats.append(0)
                    continue
                v = 1 | (b << 1)
                for k, u in enumerate(g):
                    v |= (1 << (4 + k)) | (u << (8 + 8 * k))
                beats.append(v)
        else:
            rl = max(field.add_latency, len(units), dmax)
            slots = [None] * rl
            for i, u in enumerate(units):
                slots[(i * rl) // len(units)] = u
            for u in slots:
                if u is None:
                    beats.append(0)
                    continue
                sv = sum(1 << h for h in (0, 1) if 2 * u + h < C)
                beats.append(1 | (u << 1) | (b << 9) | (sv << 12))
    sbase = len(field.stream)
    field.stream += beats
    nrows = sum(m.rows for m in mats)
    ph = dict(index=len(field.phases), bf=bf, K=K, nbeat=len(beats), sbase=sbase, nrows=nrows,
              fmt_fp32=list(fmt_fp32), rsplit=rsplit, t_read=t_read,
              t_phase_model=S.phase_cycles({f: [(sg["pair"], sg["e0"], sg["elems"], 0) for sg in segs
                                                 if sg["fmt"] == f] for f in {sg["fmt"] for sg in segs}}),
              matrices=[dict(name=m.name, fmt=m.fmt, rows=[m.r0, m.r0 + m.rows], cols=[m.k0, m.k0 + m.K],
                             off=info[i]["off"], split=info[i]["s"], segment_elems=[x[1] for x in info[i]["segs"]])
                        for i, m in enumerate(mats)],
              segments_per_pair_max=max(len(v) for v in by_p.values()))
    field.cfg.append(cfg)
    field.phases.append(ph)
    return ph


def phase_words(ph: dict) -> tuple[int, int]:
    w0 = (int(ph["bf"]) | (ph["K"] << 1) | (ph["nbeat"] << 14) | (ph["sbase"] << 30) | (ph["nrows"] << 46)
          | (int(ph["fmt_fp32"][0]) << 62) | (int(ph["fmt_fp32"][1]) << 63))
    assert ph["K"] < (1 << 13) and ph["nbeat"] < (1 << 16) and ph["sbase"] < (1 << 16) and ph["nrows"] < (1 << 16)
    return w0, ph["rsplit"]


def golden_phase(mats: list[Mat], x: np.ndarray):
    """Per row tag: (FP32 accumulator bits, BF16 bits) under R-ARITH chunk8, exactly as the element array
    must produce them (golden linear_q / csum of mul(w, bf16(x)))."""
    out = {}
    off = 0
    for m in mats:
        if m.fmt == "bf16":
            xb = G.to_bf16(x)
            acc = G.csum(G.mul(np.asarray(m.wf, dtype=G.F), xb[None, :]))
            y = G.linear_bf16(m.wf, x)
        else:
            xq, xe = G.quant_fp8(x)
            n, k = m.w.q.shape
            blocks = [np.ldexp((m.w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(G.F),
                               m.w.e[:, b] + xe[b]).astype(G.F) for b in range(k // 32)]
            acc = G.csum(np.stack(blocks, axis=-1))
            y = G.linear_q(m.w, x)
        assert np.array_equal(G.bits(G.to_bf16(acc)), G.bits(y))
        for r in range(m.rows):
            out[off + r] = (int(G.bits(acc)[r]), int(G.bits(y)[r]) >> 16)
        off += m.rows
    return out


def write_field(field: Field, out: Path, phw: int, flat_viamaps: bool = True) -> None:
    """Image files: per pair e<p>.cfg.hex (phases x 25 words, 2^PHW slots), per macro e<p>[b].words.hex
    (address word pairs for the runtime host) and e<p>[b].viamap.hex (the via ROM of the flat build);
    spine_phase.hex, spine_stream.hex."""
    out.mkdir(parents=True, exist_ok=True)
    act = [int(p) for p in np.flatnonzero(field.act)]
    (out / "field.txt").write_text(f"np {field.np}\nr {field.r}\nactive {' '.join(map(str, act))}\n"
                                   f"bf16 {' '.join(str(int(p)) for p in np.flatnonzero(field.bf))}\n")
    for p in act:
        lines = []
        for ph in range(1 << phw):
            ws = field.cfg[ph][p] if ph < len(field.cfg) else [0] * CW
            lines += [f"{w:012x}" for w in ws]
        (out / f"e{p}.cfg.hex").write_text("\n".join(lines) + "\n")
        for mb in range(2):
            name = f"e{p}" + ("b" if mb else "")
            wd = field.words[2 * p + mb]
            (out / f"{name}.words.hex").write_text("".join(f"{a:04x} {w:069x}\n" for a, w in sorted(wd.items())))
            if flat_viamaps:
                if field.pp:
                    for parity in (0, 1):
                        bank = {a // 2: w for a, w in wd.items() if a % 2 == parity}
                        # Existing writer uses 1024 rows; a 4096 macro consumes 512.
                        target = out / f"{name}_{parity}.viamap.hex"
                        viamap(bank, target)
                        target.write_text("".join(target.read_text().splitlines(keepends=True)[:512]))
                else:
                    viamap(wd, out / f"{name}.viamap.hex")
    pw = []
    for i in range(1 << phw):
        if i < len(field.phases):
            w0, w1 = phase_words(field.phases[i])
        else:
            w0, w1 = 0, 0
        pw += [f"{w0:016x}", f"{w1:016x}"]
    (out / "spine_phase.hex").write_text("\n".join(pw) + "\n")
    (out / "spine_stream.hex").write_text("".join(f"{w:012x}\n" for w in field.stream) or "0\n")
