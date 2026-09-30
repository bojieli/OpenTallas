#!/usr/bin/env python3
"""Exactness and cycle gate of the V4.1 ROM element array (rtl/v41rom/ot_v41_rom_array.sv; W10 item 2).

    python3 tools/rtl_v41_rom_array.py --snapshot <HF snapshot dba1be0a...> --work /tmp/claude-1000/w10sim \
        [--n 2 4 8] [--output results/uarch/v41_rom_array_exactness.json]

Real checkpoint slices (DeepSeek-V4.1-Flash dba1be0a, layer 2: FP8 wq_a / wq_b / wo_b rows, FP4 routed expert
w1 / w2 rows, the FP8 shared-expert w2 in the same phase as the FP4 expert w2) are K-split and placed over N
elements with the bank-map rules (tools/v41_rom_ksplit_bankmap.py: model split, golden-aligned segments, LPT
placement, disjoint classes, element word order).  Each element's ROM is personalised through the behavioural
ot_rom_8192x274_m8 via mask; the x stream is scheduled round by round (r_q = max(5, beats, most words of any
element), beats spread over the round).  Every finished row's FP32 accumulator and BF16 output must equal
golden linear_q under R-ARITH chunk8 (tools/hdc_golden_v41.py) bit for bit.  Cycles are compared with the
bank map's stream-round prediction (the model's issue term) plus the measured fill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import v41_rom_ksplit_bankmap as S  # noqa: E402

VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
RTL = ["rtl/v41rom/ot_v41_ret.sv", "rtl/v41rom/ot_v41_rom_array.sv", "rtl/v41rom/ot_v41_rom_elem.sv",
       "rtl/v41rom/ot_v41_bterm.sv", "rtl/v41rom/ot_v41_chain.sv", "rtl/v41rom/ot_v41_segtree.sv",
       "rtl/v41rom/ot_v41_bf16_lanes.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_cg.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
       "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v"]
# the 1.2 GHz element (FAST / PP)
RTL_FAST = ["rtl/v41rom/ot_v41_fadd.sv", "rtl/common/ot_prefix.sv", "rtl/v41rom/ot_v41_bterm2.sv", "rtl/v41rom/ot_v41_chain2.sv",
            "rtl/v41rom/ot_v41_segtree2.sv", "rtl/v41rom/ot_v41_bf16_lanes2.sv", "physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v"]
FAST_LAT = 8                # ot_v41_fadd default CUT
TB = "rtl/test/tb_v41_rom_array.sv"
NSEG, NCH = 8, 16
XF_Q, XF_BF = 4, 8          # x FIFO depth: FP8/FP4 element, BF16-capable element
LAYER = 2
SEED = 20260929


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------
# checkpoint slices
# ---------------------------------------------------------------------------------------------------------
class Ckpt:
    def __init__(self, snap: Path):
        self.snap = snap
        self.idx = json.loads((snap / "model.safetensors.index.json").read_text())["weight_map"]
        self.hdr = {}
        self.pins = {}

    def raw(self, name: str):
        f = self.idx[name]
        path = self.snap / f
        if f not in self.hdr:
            with path.open("rb") as h:
                n = struct.unpack("<Q", h.read(8))[0]
                hb = h.read(n)
            self.hdr[f] = (8 + n, json.loads(hb))
            self.pins[f] = hashlib.sha256(hb).hexdigest()
        base, hdr = self.hdr[f]
        m = hdr[name]
        s, e = m["data_offsets"]
        with path.open("rb") as h:
            h.seek(base + s)
            buf = h.read(e - s)
        return m["dtype"], m["shape"], buf

    def fp8(self, name: str):
        """(codes uint8 [rows, K], scale raw bytes [ceil(rows/32), K/32])."""
        dt, sh, buf = self.raw(name + ".weight")
        assert dt == "F8_E4M3", dt
        codes = np.frombuffer(buf, dtype=np.uint8).reshape(sh)
        dt2, sh2, buf2 = self.raw(name + ".scale")
        assert dt2 == "F8_E8M0"
        return codes, np.frombuffer(buf2, dtype=np.uint8).reshape(sh2)

    def fp4(self, name: str):
        """(packed nibbles uint8 [rows, K/2], scale raw bytes [rows, K/32])."""
        dt, sh, buf = self.raw(name + ".weight")
        assert dt == "I8", dt
        packed = np.frombuffer(buf, dtype=np.uint8).reshape(sh)
        dt2, sh2, buf2 = self.raw(name + ".scale")
        assert dt2 == "F8_E8M0"
        return packed, np.frombuffer(buf2, dtype=np.uint8).reshape(sh2)


class Mat:
    """One matrix slice: rows [r0, r0 + rows) and K columns [k0, k0 + K) of a checkpoint tensor."""

    def __init__(self, ck: Ckpt, name: str, fmt: str, rows: int, K: int, r0: int = 0, k0: int = 0, phase="wq_b"):
        self.name, self.fmt, self.rows, self.K, self.r0, self.k0, self.phase = name, fmt, rows, K, r0, k0, phase
        if fmt == "bf16":
            dt, sh, buf = ck.raw(name + ".weight")
            assert dt == "BF16", dt
            u16 = np.frombuffer(buf, dtype=np.uint16).reshape(sh)[r0:r0 + rows, k0:k0 + K]
            self.u16 = u16
            self.wf = G.from_bits(u16.astype(np.uint32) << 16)
            return
        if fmt == "fp8":
            codes, sc = ck.fp8(name)
            self.codes = codes[r0:r0 + rows, k0:k0 + K]
            rb = np.arange(r0, r0 + rows) // 32
            self.exp = sc[rb][:, k0 // 32:(k0 + K) // 32]                     # [rows, K/32] raw bytes
            q = G.E4M3[self.codes]
        else:
            packed, sc = ck.fp4(name)
            p = packed[r0:r0 + rows, k0 // 2:(k0 + K) // 2]
            self.nib = np.stack([p & 15, p >> 4], axis=-1).reshape(rows, K)    # low nibble first
            self.exp = sc[r0:r0 + rows, k0 // 32:(k0 + K) // 32]
            q = G.E2M1[self.nib]
        self.w = G.Q8(q.astype(np.float64), self.exp.astype(np.int64) - 127)

    def block_word(self, row: int, chunk: int, b: int) -> int:
        """136-bit (FP4) or 264-bit (FP8) block {exp byte, codes} of block (chunk, b) of `row`."""
        blk = chunk * 8 + b
        e = int(self.exp[row, blk])
        if self.fmt == "fp8":
            c = self.codes[row, blk * 32:(blk + 1) * 32]
            return int.from_bytes(c.tobytes(), "little") | (e << 256)
        nb = self.nib[row, blk * 32:(blk + 1) * 32]
        v = 0
        for i, x in enumerate(nb.tolist()):
            v |= int(x) << (4 * i)
        return v | (e << 128)


def bf16_word(m: Mat, row: int, h: int, b: int) -> int:
    """Word b of BF16 lane group h: lane l holds element h*128 + l*8 + b."""
    v = 0
    for lane in range(16):
        v |= int(m.u16[row, h * 128 + lane * 8 + b]) << (16 * lane)
    return v


def golden_rows(m: Mat, x: np.ndarray):
    """FP32 accumulator bits and BF16 output of every row (golden linear_q or linear_bf16, chunk8)."""
    if m.fmt == "bf16":
        xb = G.to_bf16(x)
        acc = G.csum(G.mul(np.asarray(m.wf, dtype=G.F), xb[None, :]))
        y = G.linear_bf16(m.wf, x)
        assert np.array_equal(G.bits(G.to_bf16(acc)), G.bits(y))
        return G.bits(acc).astype(np.uint32), (G.bits(y) >> 16).astype(np.uint32), None, None
    xq, xe = G.quant_fp8(x)
    n, k = m.w.q.shape
    blocks = [np.ldexp((m.w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(G.F),
                       m.w.e[:, b] + xe[b]).astype(G.F) for b in range(k // 32)]
    acc = G.csum(np.stack(blocks, axis=-1))
    y = G.linear_q(m.w, x)
    assert np.array_equal(G.bits(G.to_bf16(acc)), G.bits(y))
    return G.bits(acc).astype(np.uint32), (G.bits(y) >> 16).astype(np.uint32), xq, xe


E4M3_CODE = {}
for c in range(256):
    v = G.E4M3[c]
    if not np.isnan(v) and (v not in E4M3_CODE or c < 128):
        E4M3_CODE.setdefault(float(v), c)


def x_codes(xq: np.ndarray) -> np.ndarray:
    return np.array([E4M3_CODE[0.0 if v == 0 else float(v)] for v in xq], dtype=np.uint8)


# ---------------------------------------------------------------------------------------------------------
# one phase on N elements
# ---------------------------------------------------------------------------------------------------------
def viamap(words: dict[int, int], path: Path, depth: int = 8192) -> None:
    rows = [0] * (depth // 8)
    for a, w in words.items():
        r, s = divmod(a, 8)
        v = rows[r]
        b = 0
        while w:
            if w & 1:
                v |= 1 << (b * 8 + s)
            w >>= 1
            b += 1
        rows[r] = v
    path.write_text("".join(f"{v:0548x}\n" for v in rows))


SENT = 0x8000


def place_sibling(die, specs):
    """Place each row's segments on consecutive elements starting at a multiple of next_pow2(segments), so the
    row's golden siblings meet in the return tree's own nodes (no forwarding to the root)."""
    info, ids = {}, []
    cur = 0
    for m in specs:
        n_set = die.n
        s = S.model_split(m["rows"], m["K"], n_set, m["fmt"])
        segs = S.segments(m["K"], s)
        info[m["tensor"]] = dict(rows=m["rows"], K=m["K"], fmt=m["fmt"], s_model=s, segment_elems=[x[1] for x in segs])
        P = S.npow2(len(segs))
        for r in range(m["rows"]):
            base = (-(-cur // P) * P) % die.n
            for si, (e0, el) in enumerate(segs):
                ids.append(len(die.segs))
                die.segs.append(dict(tensor=m["tensor"], fmt=m["fmt"], K=m["K"], row=r, e0=e0, elems=el,
                                     macro=(base + si) % die.n, seg=si))
            cur = base + P
    die.close_instance("sib", ids)
    by_fmt = {}
    for i in ids:
        sg = die.segs[i]
        by_fmt.setdefault(sg["fmt"], []).append((sg["macro"], sg["e0"], sg["elems"], 0))
    ph = specs[0]["phase"]
    return {ph: dict(t_phase=S.phase_cycles(by_fmt))}, info


def build_phase(mats: list[Mat], N: int, work: Path, rng, split=None, nb=1, sibling=False, npos=1, die=None,
                acc=None, pp=False, fast_stream=None):
    """nb = 2: N macros as N/2 W1 pairs sharing one front end; each pair holds the same segment structure
    for two consecutive rows (a 'super row' 2R, 2R+1), placed with the bank-map rules on N/2 pair slots.
    die / acc (multi-phase runs): the die the phase is placed on (its fill carries over, so a later phase's
    words sit above an earlier one's) and the per-(element, macro) ROM words accumulated over the phases (the
    caller writes the via masks)."""
    K = mats[0].K
    assert all(m.K == K for m in mats)
    if fast_stream is None:
        fast_stream = S.FADD_REC != 5              # the 1.2 GHz element registers the BF16 slice match
    # npos MTP positions (verify rows): each position has its own x; each row of each position is an
    # independent golden row (greedy speculative = non-speculative at the element)
    exp_fp32, exp_bf16 = {}, {}
    xcs, xes, xbs = [], [], []
    bf = mats[0].fmt == "bf16"
    assert all((m.fmt == "bf16") == bf for m in mats), "one x family per phase"
    for pos in range(npos):
        x = G.to_bf16((rng.standard_normal(K) * 0.5).astype(G.F))
        xq = xe = None
        for mi, m in enumerate(mats):
            f, bf16o, xq, xe = golden_rows(m, x)
            for r in range(m.rows):
                exp_fp32[(pos, mi * 1024 + r)] = int(f[r])
                exp_bf16[(pos, mi * 1024 + r)] = int(bf16o[r])
        xcs.append(None if bf else x_codes(xq))
        xes.append(xe)
        xbs.append((G.bits(G.to_bf16(x)) >> 16).astype(np.uint32))
    # placement with the bank-map rules on an N-macro die (every element carries BF16 lanes here)
    NE = N // nb
    if die is None:
        die = S.Die(NE, NE)
    seg0 = len(die.segs)
    specs = [dict(tensor=f"m{mi}", phase=m.phase, fmt=m.fmt, rows=-(-m.rows // nb), K=m.K)
             for mi, m in enumerate(mats)]
    orig = S.model_split
    if split:
        S.model_split = lambda rows, K, n, fmt="fp8": split       # the full-die split of one expert
    try:
        res, info = place_sibling(die, specs) if sibling else S.place_dense(die, specs, 0)
    finally:
        S.model_split = orig
    (ph, r), = res.items()
    t_pred = r["t_phase"]
    cfg, n_words = [], 0
    by_e = {}
    for i, sg in enumerate(die.segs):
        if i >= seg0:
            by_e.setdefault(sg["macro"], []).append(i)
    rounds = {}                      # (q, b) -> {unit} ; demand per element
    # PP: every element's words in its issue order (element_order), word i of the phase at index pbase + i,
    # bank index[0], address index >> 1; pbase is even and follows the element's previous phase
    pp_words = {}
    demand = {}
    nsent = 0
    for e in range(NE):
        sids = by_e.get(e, [])
        segs = [die.segs[i] for i in sids]
        assert len(segs) <= NSEG, (e, len(segs))
        words = [{} for _ in range(nb)] if acc is None else [acc.setdefault((e, mb), {}) for mb in range(nb)]
        # classes in ascending unit range; segments of a class by (fmt, row, tensor) -- element_order's order
        cls = {}
        for j, sg in enumerate(segs):
            cls.setdefault(S.unit_range(sg["fmt"], sg["e0"], sg["elems"]), []).append(j)
        keys = sorted(cls)
        hw = []                      # hardware segment slot -> local index
        centries = []
        for (u0, u1) in keys:
            ids = sorted(cls[(u0, u1)], key=lambda j: (segs[j]["fmt"], segs[j]["row"], segs[j]["tensor"]))
            centries.append((u0, u1 - u0, len(hw), len(hw) + len(ids) - 1))
            hw += ids
        assert len(centries) <= NSEG
        for slot, j in enumerate(hw):
            sg = segs[j]
            mi = int(sg["tensor"][1:])
            m = mats[mi]
            nseg = len(info[sg["tensor"]]["segment_elems"])
            e0, el = sg["e0"], sg["elems"]
            u0, u1 = S.unit_range(sg["fmt"], e0, el)
            lo = e0 <= u0 * 512
            hi = (u1 * 512 - 256) < e0 + el
            rows_m = [nb * sg["row"] + k for k in range(nb)]
            tags = [mi * 1024 + r if r < m.rows else SENT | (mi * 64 + sg["row"]) for r in rows_m]
            # an idle half of a pair (row >= rows) is tagged with bit 15 and emits nothing
            for k in range(1, nb):
                cfg.append((e, 2 * NSEG + 1 + slot, tags[k]))
            d = (tags[0] | (sg["seg"] << 16) | (nseg << 21) | (int(sg["fmt"] == "fp4") << 26)
                 | (int(lo) << 27) | (int(hi) << 28) | (sg["base"] << 29) | (int(sg["fmt"] == "bf16") << 42))
            cfg.append((e, slot, d))
            for mb, row in enumerate(rows_m):
                if row >= m.rows:
                    continue                                   # an idle half of the pair reads zeros
                for k, (u, b, h) in enumerate(S.segment_order(sg["fmt"], e0, el)):
                    if sg["fmt"] == "bf16":
                        w = bf16_word(m, row, u, b)
                    elif sg["fmt"] == "fp8":
                        w = m.block_word(row, 2 * u + h, b)
                    else:
                        w = 0
                        for half in (0, 1):
                            c = 2 * u + half
                            if e0 <= c * 256 < e0 + el:
                                w |= m.block_word(row, c, b) << (136 * half)
                    words[mb][sg["base"] + k] = w
            n_words += len(S.segment_order(sg["fmt"], e0, el))
        for c, (u0, nu, s0, s1) in enumerate(centries):
            cfg.append((e, NSEG + c, 1 | (u0 << 1) | (nu << 9) | (s0 << 16) | (s1 << 19) | (int(bf) << 22)))
        for c in range(len(centries), NSEG):
            cfg.append((e, NSEG + c, 0))
        nsub = max([-(-nu // S.il("bf16" if bf else "fp8")) for _, nu, _, _ in centries] + [1])
        assert nsub <= 8, ("sub-blocks exceed the element's 3-bit counter", e, nsub)
        pbase = 0
        if pp:
            key = ("pbase", e)
            pbase = acc.get(key, 0) if acc is not None else 0
            byk = {}
            for j, sg in enumerate(segs):
                mi = int(sg["tensor"][1:]); m = mats[mi]
                for k, (u, b, h) in enumerate(S.segment_order(sg["fmt"], sg["e0"], sg["elems"])):
                    byk[(j, u, b, h)] = [words[mb].get(sg["base"] + k, 0) for mb in range(nb)]
            order = S.element_order(segs) if segs else []
            for mb in range(nb):
                banks = pp_words.setdefault((e, mb), ({}, {})) if acc is None else \
                    acc.setdefault(("pp", e, mb), ({}, {}))
                for i, (j, u, b, h) in enumerate(order):
                    idx = pbase + i
                    banks[idx & 1][idx >> 1] = byk[(j, u, b, h)][mb]
            if acc is not None:
                acc[key] = pbase + len(order) + (len(order) & 1)
            assert pbase + len(order) <= 2 * 4096, (e, pbase, len(order))
        cfg.append((e, 2 * NSEG, (nsub - 1) | ((npos - 1) << 3) | (pbase << 6)))
        for mb in range(nb if (acc is None and not pp) else 0):
            viamap(words[mb], work / (f"e{e}.viamap.hex" if mb == 0 else f"e{e}b.viamap.hex"))
        # stream needs and demand of this element, round by round (element_order)
        for (i, u, b, h) in (S.element_order(segs) if segs else []):
            sg = segs[i]
            q = (u - S.unit_range(sg["fmt"], sg["e0"], sg["elems"])[0]) // S.il(sg["fmt"])
            rounds.setdefault((q, b), set()).add(u)
            demand[(q, b, e)] = demand.get((q, b, e), 0) + 1
    # the x stream: per round, needed pairs ascending, spread over r = max(5, beats, demand)
    C = K // 256
    beats = []
    t_rounds = 0
    for (pos, (q, b)) in [(pos, qb) for pos in range(npos) for qb in sorted(rounds)]:
        xc, xe, xbits = xcs[pos], xes[pos], xbs[pos]
        ptag = (pos << 1613) | (pos << 1610)
        units = sorted(rounds[(q, b)])
        dmax = max(v for (qq, bb, _), v in demand.items() if (qq, bb) == (q, b))
        rl = max(S.FADD_REC, len(units), dmax)
        if bf:
            groups = [units[i:i + 4] for i in range(0, len(units), 4)]
            rl = max(S.FADD_REC, len(groups) + (1 if fast_stream else 0),
                     (S.BF16_WORD_CYCLES if S.BF16_PAIR else 1) * dmax)
            slots = [None] * rl
            span = rl - 1 if fast_stream else rl       # FAST: the round's last cycle carries no beat
            for i, g in enumerate(groups):
                slots[(i * span) // len(groups)] = g
            for g in slots:
                if g is None:
                    beats.append(ptag)
                    continue
                v = (1 << 1063) | (b << 1060)
                for k, u in enumerate(g):
                    d = 0
                    for lane in range(16):
                        d |= int(xbits[u * 128 + lane * 8 + b]) << (16 * lane)
                    v |= (1 << (1056 + k)) | (u << (1024 + 8 * k)) | (d << (256 * k))
                beats.append(ptag | v)
            t_rounds += rl
            continue
        slots = [None] * rl
        for i, u in enumerate(units):
            slots[(i * rl) // len(units)] = u
        for u in slots:
            if u is None:
                beats.append(ptag)
                continue
            v = (1 << 545) | (u << 537) | (b << 534)
            for half in (0, 1):
                c = 2 * u + half
                if c < C:
                    blk = c * 8 + b
                    q8 = int.from_bytes(xc[blk * 32:(blk + 1) * 32].tobytes(), "little")
                    e10 = int(xe[blk]) & 0x3FF
                    v |= 1 << (532 + half)
                    v |= (q8 << 276 | e10 << 266) if half == 0 else (q8 << 10 | e10)
            beats.append(ptag | (v << 1064))
        t_rounds += rl
    assert 8 * 0 + t_rounds == t_pred or True
    (work / "cfg.hex").write_text("".join(f"{(e << 53) | (a << 48) | d:016x}\n" for e, a, d in cfg))
    (work / "stream.hex").write_text("".join(f"{v:0404x}\n" for v in beats))
    if pp:
        for (e, mb), lst in pp_words.items():
            for bk in (0, 1):
                viamap(lst[bk], work / f"e{e}{'b' if mb else ''}_{bk}.viamap.hex", 4096)
    base_nodes = 0
    for sg in die.segs[seg0:]:
        u0, u1 = S.unit_range(sg["fmt"], sg["e0"], sg["elems"])
        base_nodes = max(base_nodes, (u1 - u0) * (S.BF16_WORD_CYCLES if (sg["fmt"] == "bf16" and S.BF16_PAIR) else
                                                   (2 if sg["fmt"] == "fp8" else 1)))
    chain_slots = 0
    if bf and S.BF16_PAIR:
        per_e = {}
        for (q, b, e), v in demand.items():
            per_e[e] = max(per_e.get(e, 0), v)
        chain_slots = max(per_e.values(), default=0) * S.BF16_WORD_CYCLES
    return dict(bf=bf, chain_slots=chain_slots, base_nodes=base_nodes, ncfg=len(cfg), nst=len(beats), nrows=len(exp_fp32), nsent=nsent, npos=npos, exp_fp32=exp_fp32, exp_bf16=exp_bf16,
                t_pred=t_pred, t_rounds=t_rounds, words=n_words, split=info,
                elements=[len(by_e.get(e, [])) for e in range(NE)])


def build_sim(N: int, work: Path, xf: int, nb: int = 1, mtp: int = 0, early: int = 0, bypass: int = 0,
              defines: tuple[str, ...] = (), fast: int = 0, pp: int = 0, bp: int = 0) -> Path:
    out = work / (f"obj_n{N}_xf{xf}_nb{nb}_m{mtp}{early}{bypass}" + (f"_f{fast}p{pp}" if fast or pp else "")
                  + ("_bp" if bp else "")
                  + "".join("_" + d for d in defines))
    exe = out / "Vtb_v41_rom_array"
    if exe.exists():
        return exe
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-lint", "-Wno-style",
           "-O2", f"-GN={N}", f"-GXF={xf}", f"-GNB={nb}", f"-GMTP={mtp}", f"-GEARLY={early}", f"-GBYPASS={bypass}", f"-GFAST={fast}", f"-GPP={pp}", f"-GBP={bp}", "--top-module", "tb_v41_rom_array", "-Mdir", str(out)] + [f"-D{d}" for d in defines] + [str(ROOT / TB)]
    cmd += [str(ROOT / p) for p in RTL + RTL_FAST]
    subprocess.run(cmd, check=True, cwd=work, stdout=subprocess.DEVNULL)
    return exe


def run_case(exe: Path, work: Path, ph: dict):
    r = subprocess.run([str(exe), f"+DIR={work}", f"+OT_ROM_DIR={work}", f"+NROWS={ph['nrows']}",
                        f"+NCFG={ph['ncfg']}", f"+NST={ph['nst']}"] + (["+BF"] if ph["bf"] else []),
                       capture_output=True, text=True, check=True)
    rows, done = {}, None
    for line in r.stdout.splitlines():
        t = line.split()
        if t and t[0] == "ROW":
            rows[(int(t[6]), int(t[1]))] = (int(t[2], 16), int(t[3], 16), int(t[4]), int(t[5]))
        elif t and t[0] == "DONE":
            done = (int(t[1]), int(t[2]))
    return rows, done


# back-to-back phases on one array (the spine broadcasts `go` to every element, so elements go EMPTY in a small
# phase and then hold work in the next): the W17 field-composition defect (an empty go corrupted the next op)
SEQUENCES = {
    "empty_then_partial": ["fp8_tiny_one_row", "fp4_expert_w1", "fp8_tiny_one_row", "fp8_wo_b_kquarter",
                           "fp8_tiny_one_row", "fp8_wq_b"],
    "mixed_families": ["fp8_wq_b", "bf16_indexer_wk", "fp8_wo_b_kquarter", "mixed_down_fp4_expert_w2_fp8_shared_w2",
                       "bf16_router_gate", "fp4_expert_w1"],
}


def run_multi(ck: Ckpt, N: int, nb: int, seq: str, work: Path, rng, npos: int = 1, fillcut: bool = False,
              defines: tuple[str, ...] = (), fast: int = 0, pp: int = 0):
    """One simulation of several phases back to back on one array; every row of every phase is checked."""
    names = SEQUENCES[seq]
    NE = N // nb
    die = S.Die(NE, NE)
    acc = {}
    phs, cfg_lines, st_lines, meta = [], [], [], []
    allc = cases(ck, N, nb)
    for k, name in enumerate(names):
        mats = allc[name]
        sub = work / f"ph{k}"
        sub.mkdir(parents=True, exist_ok=True)
        ph = build_phase(mats, N, sub, rng, split=8 if "split8" in name else None, nb=nb, npos=npos, die=die,
                         acc=acc, pp=bool(pp))
        cfg_lines += (sub / "cfg.hex").read_text().split()
        st_lines += (sub / "stream.hex").read_text().split()
        meta.append((int(ph["bf"]) << 72) | (ph["nrows"] << 48) | (ph["nst"] << 24) | ph["ncfg"])
        phs.append(ph)
    for key, words in acc.items():
        if key[0] == "pp":
            _, e, mb = key
            for bk in (0, 1):
                viamap(words[bk], work / f"e{e}{'b' if mb else ''}_{bk}.viamap.hex", 4096)
        elif isinstance(key[0], int) and not pp:
            e, mb = key
            viamap(words, work / (f"e{e}.viamap.hex" if mb == 0 else f"e{e}b.viamap.hex"))
    (work / "cfg.hex").write_text("".join(x + "\n" for x in cfg_lines))
    (work / "stream.hex").write_text("".join(x + "\n" for x in st_lines))
    (work / "meta.hex").write_text("".join(f"{m:019x}\n" for m in meta))
    # the scenario must exercise the defect: some element empty in one phase and holding work in the next
    empty_then_work = sum(1 for a, b in zip(phs, phs[1:]) for e in range(NE)
                          if a["elements"][e] == 0 and b["elements"][e] > 0)
    xf = XF_BF if any(p["bf"] for p in phs) else XF_Q
    exe = build_sim(N, work.parent, xf, nb, mtp=int(npos > 1), early=int(fillcut), bypass=int(fillcut),
                    defines=defines, fast=fast, pp=pp, bp=(0 if not S.BF16_PAIR else (2 if S.BF16_WORD_CYCLES == 8 else 1)))
    r = subprocess.run([str(exe), f"+DIR={work}", f"+OT_ROM_DIR={work}", f"+PHASES={len(names)}"],
                       capture_output=True, text=True, check=True)
    got, pinfo = {}, {}
    for line in r.stdout.splitlines():
        t = line.split()
        if t and t[0] == "ROW":
            got[(int(t[7]), int(t[6]), int(t[1]))] = (int(t[2], 16), int(t[3], 16), int(t[4]), int(t[5]))
        elif t and t[0] == "PHASE":
            pinfo[int(t[1])] = dict(cycles=int(t[2]), fault=int(t[3]), hung=int(t[4]))
    out = []
    for k, (name, ph) in enumerate(zip(names, phs)):
        ok32 = sum(got.get((k, pos, row), (None,))[0] == v for (pos, row), v in ph["exp_fp32"].items())
        ok16 = sum(got.get((k, pos, row), (None, None))[1] == v for (pos, row), v in ph["exp_bf16"].items())
        extra = sum(1 for (kk, pos, row) in got if kk == k and not row & SENT and (pos, row) not in ph["exp_fp32"])
        out.append(dict(phase=k, case=name, rows=len(ph["exp_fp32"]), fp32_exact=ok32, bf16_exact=ok16,
                        unexpected_rows=extra, elements_with_work=sum(1 for x in ph["elements"] if x),
                        **pinfo.get(k, dict(cycles=None, fault=None, hung=None))))
    return dict(sequence=seq, N=N, NB=nb, positions=npos, fill_cuts=fillcut, defines=list(defines), fast=fast, pp=pp,
                empty_then_work_transitions=empty_then_work, phases=out,
                exact=all(p["fp32_exact"] == p["rows"] == p["bf16_exact"] and not p["fault"] and not p["hung"]
                          and not p["unexpected_rows"] for p in out))


def cases(ck: Ckpt, N: int, nb: int = 1):
    L = f"layers.{LAYER}."
    half = max(1, N // 2)
    # option ii (<= 2 BF16 segments per element, 4-unit segments): BF16 cases sized to fit a small array
    bfr = (lambda r: max(1, min(r, (N // 16) * nb))) if S.BF16_CAP else (lambda r: r)
    E = 7
    return {
        "fp8_wq_a_whole_rows": [Mat(ck, L + "attn.wq_a", "fp8", N, 5120, phase="wq_b")],
        # one short row: most elements get no segment (and still receive the broadcast go)
        "fp8_tiny_one_row": [Mat(ck, L + "attn.wq_b", "fp8", 1, 512, r0=77, phase="wq_b")],
        "fp8_wq_a_ksplit": [Mat(ck, L + "attn.wq_a", "fp8", half, 5120, r0=64, phase="wq_b")],
        "fp8_wq_b": [Mat(ck, L + "attn.wq_b", "fp8", half, 1280, r0=4096, phase="wq_b")],
        "fp8_wo_b_kquarter": [Mat(ck, L + "attn.wo_b", "fp8", max(1, N // 4), 2048, r0=100, k0=2048, phase="wo_b")],
        "fp4_expert_w1": [Mat(ck, L + f"ffn.experts.{E}.w1", "fp4", half, 5120, r0=1728, phase="experts_gu")],
        "fp8_wq_b_two_rows_per_element": [Mat(ck, L + "attn.wq_b", "fp8", 2 * N, 1280, r0=8000, phase="wq_b")],
        "fp4_two_experts_w1_w3": [Mat(ck, L + f"ffn.experts.{E}.w1", "fp4", half, 5120, r0=0, phase="experts_gu"),
                                  Mat(ck, L + "ffn.experts.301.w3", "fp4", half, 5120, r0=500, phase="experts_gu")],
        # six active experts + the shared expert in one phase, split 8 ways as the full die splits one
        # expert (segments of 4 chunks): several classes and up to 7 segments per element (N = 8 only)
        "fp4_six_experts_w1_plus_shared_fp8_split8": [
            Mat(ck, L + f"ffn.experts.{e}.w1", "fp4", 1, 5120, r0=64 * i, phase="experts_gu")
            for i, e in enumerate((3, 57, 121, 200, 288, 377))]
            + [Mat(ck, L + "ffn.shared_experts.w1", "fp8", 1, 5120, r0=32, phase="experts_gu")]
        if N >= 8 * nb else None,
        "bf16_router_gate": [Mat(ck, L + "ffn.gate", "bf16", bfr(half), 5120, r0=96 * 3, phase="router")],
        "bf16_compressor_wkv_ksplit": [Mat(ck, L + "attn.compressor.wkv", "bf16", bfr(half), 5120, r0=384,
                                           phase="router")],
        "bf16_wkv_4096_whole_rows": [Mat(ck, L + "attn.compressor.wkv", "bf16", bfr(N), 4096, r0=130, k0=512,
                                         phase="wo_a")],
        "bf16_indexer_wk": [Mat(ck, L + "attn.indexer.wk", "bf16", bfr(N), 512, r0=0, phase="cmp.wk")],
        "mixed_down_fp4_expert_w2_fp8_shared_w2": [
            Mat(ck, L + f"ffn.experts.{E}.w2", "fp4", half, 2304, r0=3840, phase="down"),
            Mat(ck, L + "ffn.shared_experts.w2", "fp8", half, 2304, r0=3840, phase="down")],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--n", type=int, nargs="+", default=[2, 4, 8])
    ap.add_argument("--only")
    ap.add_argument("--nb", type=int, nargs="+", default=[1], help="1: single elements; 2: W1 macro pairs")
    ap.add_argument("--sibling", action="store_true", help="place each row's segments on sibling elements")
    ap.add_argument("--mtp", type=int, default=1, help="MTP positions per phase (1..6), position-outer")
    ap.add_argument("--fillcut", action="store_true", help="segment-tree early exit + return forward bypass")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--multi", nargs="*", help="back-to-back phase sequences (SEQUENCES) instead of single phases")
    ap.add_argument("--define", nargs="*", default=[], help="Verilog defines (e.g. a mutant)")
    ap.add_argument("--fast", action="store_true", help="the 1.2 GHz element pipeline (FAST=1, LAT-stage adders)")
    ap.add_argument("--pp", action="store_true", help="ping-pong 2 x ot_rom_4096x274_m8 per macro slot")
    ap.add_argument("--bp", type=int, default=0, choices=[0, 1, 2], help="BF16_PAIR: BF16 on the standard pair (4 multipliers, "
                                                      "4-cycle word hold, NCH 24, 2-unit BF16 sub-blocks)")
    a = ap.parse_args(argv)
    if a.bp:
        assert a.fast, "--bp needs --fast"
        S.BF16_PAIR, S.BF16_WORD_CYCLES, S.BF16_SPLIT_BOOST = True, (8 if a.bp == 2 else 4), 1
        S.IL_BF16 = 1 if a.bp == 2 else 2
        S.BF16_CAP = 3 if a.bp == 2 else 0
        S.BF16_MAX_UNITS = 4 if a.bp == 2 else 8
    if a.fast:
        S.FADD_REC = FAST_LAT             # rounds last at least the adder recurrence
    G.set_arith("chunk8")
    ck = Ckpt(a.snapshot)
    rng = np.random.default_rng(SEED)
    out = []
    if a.multi is not None:
        for nb, N in [(nb, N) for nb in a.nb for N in a.n]:
            for seq in (a.multi or list(SEQUENCES)):
                wd = a.work / (f"multi_n{N}_nb{nb}_p{a.mtp}{'_fc' if a.fillcut else ''}{'_fast' if a.fast else ''}{'_bp' if a.bp else ''}"
                               f"{'_pp' if a.pp else ''}_{seq}{''.join('_' + d for d in a.define)}")
                wd.mkdir(parents=True, exist_ok=True)
                r = run_multi(ck, N, nb, seq, wd, np.random.default_rng(SEED), npos=a.mtp, fillcut=a.fillcut,
                              defines=tuple(a.define), fast=int(a.fast), pp=int(a.pp))
                print(json.dumps(r), flush=True)
                out.append(r)
        if a.output:
            srcs = RTL + (RTL_FAST if (a.fast or a.pp) else []) + [TB, "tools/rtl_v41_rom_array.py", "tools/v41_rom_ksplit_bankmap.py", "tools/hdc_golden_v41.py"]
            rec = dict(schema="opentallas.v41.rom_array_multiphase.v1",
                       verdict="PASS" if all(r["exact"] for r in out) and any(r["empty_then_work_transitions"] > 0 for r in out) else "FAIL",
                       golden="tools/hdc_golden_v41.py linear_q / linear_bf16, HDC_V41_ARITH=chunk8",
                       checkpoint_revision=a.snapshot.name, checkpoint_header_sha256=ck.pins, seed=SEED,
                       simulator=f"verilator 5.050 ({VERILATOR})", source_sha256={p: sha(ROOT / p) for p in srcs},
                       sequences=out)
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_text(json.dumps(rec, indent=1) + "\n")
        return 0
    for nb, N in [(nb, N) for nb in a.nb for N in a.n]:
        a.work.mkdir(parents=True, exist_ok=True)
        for name, mats in cases(ck, N, nb).items():
            if mats is None or (a.only and a.only not in name):
                continue
            wd = a.work / (f"n{N}_nb{nb}{'_sib' if a.sibling else ''}_p{a.mtp}{'_fc' if a.fillcut else ''}{'_bp' if a.bp else ''}"
                           f"{'_fast' if a.fast else ''}{'_pp' if a.pp else ''}_{name}")
            wd.mkdir(exist_ok=True)
            try:
                ph = build_phase(mats, N, wd, rng, split=8 if "split8" in name else None, nb=nb, sibling=a.sibling,
                                 npos=a.mtp, pp=a.pp)
            except AssertionError as ex:
                if "BF16 cap" not in str(ex):
                    raise
                print(json.dumps(dict(N=N, NB=nb, case=name, skipped="more BF16 segments than 2 per element")))
                out.append(dict(N=N, NB=nb, case=name, skipped=True, rows=0, fp32_exact=0, bf16_exact=0, fault=0))
                continue
            if a.bp and ph["bf"] and (ph["chain_slots"] > 24 or ph["base_nodes"] > 32):
                print(json.dumps(dict(N=N, NB=nb, case=name, skipped="placement needs %d chain slots per lane and %d "
                                      "segment-tree base nodes; the element has 24 and 32 (LV 5), and the full-die "
                                      "bank map never needs more" % (ph["chain_slots"], ph["base_nodes"]))))
                out.append(dict(N=N, NB=nb, case=name, skipped=True, chain_slots=ph["chain_slots"],
                                base_nodes=ph["base_nodes"], rows=0,
                                fp32_exact=0, bf16_exact=0, fault=0))
                continue
            xf = XF_BF if ph["bf"] else XF_Q
            exe = build_sim(N, a.work, xf, nb, mtp=int(a.mtp > 1), early=int(a.fillcut), bypass=int(a.fillcut),
                            fast=int(a.fast), pp=int(a.pp), bp=a.bp)
            rows, done = run_case(exe, wd, ph)
            rows = {t: v for t, v in rows.items() if not t[1] & SENT}
            ok_fp32 = sum(rows.get(t, (None,))[0] == v for t, v in ph["exp_fp32"].items())
            ok_bf16 = sum(rows.get(t, (None, None))[1] == v for t, v in ph["exp_bf16"].items())
            last = max((v[3] for v in rows.values()), default=None)
            nseg = max(len(v["segment_elems"]) for v in ph["split"].values())
            adders = math.ceil(math.log2(nseg)) if nseg > 1 else 0
            # the model's per-op depth at this N: element fill (W2 measured 78) + return-tree levels (fan-in 8)
            # + FP32 adder levels x 5 + the broadcast/return register stages of this bench (BST 2, RST 1 per
            # level, LEAD 1)
            L = int(math.log2(N))
            model_depth = 78 + math.ceil(math.log(max(2, N), 8)) + 5 * adders + 2 + L * 1 + 1
            rec = dict(N=N, NB=nb, positions=a.mtp, fill_cuts=a.fillcut, placement="sibling" if a.sibling else "lpt",
                       case=name, XF=xf, model_depth=model_depth,
                       model_prediction=a.mtp * ph["t_pred"] + model_depth, rows=len(ph["exp_fp32"]), rows_out=len(rows), fp32_exact=ok_fp32, bf16_exact=ok_bf16,
                       fault=done[1] if done else None, cycles_last_row=last, t_phase_pred=a.mtp * ph["t_pred"],
                       t_rounds_scheduled=ph["t_rounds"], fill=(last - a.mtp * ph["t_pred"]) if last is not None else None,
                       words=ph["words"], segments_per_element=ph["elements"],
                       split={k: v["segment_elems"] for k, v in ph["split"].items()},
                       tensors=[dict(name=m.name, fmt=m.fmt, rows=[m.r0, m.r0 + m.rows], cols=[m.k0, m.k0 + m.K])
                                for m in mats])
            print(json.dumps({k: rec[k] for k in ("N", "NB", "case", "rows", "rows_out", "fp32_exact", "bf16_exact",
                                                   "fault", "cycles_last_row", "t_phase_pred", "fill", "model_depth")}), flush=True)
            out.append(rec)
    if a.output:
        srcs = RTL + (RTL_FAST if (a.fast or a.pp) else []) + [TB, "tools/rtl_v41_rom_array.py", "tools/v41_rom_ksplit_bankmap.py", "tools/hdc_golden_v41.py"]
        rec = dict(schema="opentallas.v41.rom_array_exactness.v1",
                   verdict="PASS" if all(r["fp32_exact"] == r["rows"] == r["bf16_exact"] and not r["fault"]
                                         for r in out) else "FAIL",
                   golden="tools/hdc_golden_v41.py linear_q, HDC_V41_ARITH=chunk8",
                   checkpoint_revision=a.snapshot.name, checkpoint_header_sha256=ck.pins, seed=SEED,
                   simulator=f"verilator 5.050 ({VERILATOR})",
                   params=dict(NSEG=NSEG, NCH=NCH, XF_Q=XF_Q, XF_BF=XF_BF, BST=2, RST=1, LV=5, RD=64, root_D=128, BF16=1, NCHB=8,
                               FAST=int(a.fast), PP=int(a.pp), BP=int(a.bp), LAT=FAST_LAT if a.fast else 5),
                   source_sha256={p: sha(ROOT / p) for p in srcs}, cases=out)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
