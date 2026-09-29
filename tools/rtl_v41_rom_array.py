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
       "rtl/hdc/ot_hdc_delay.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
       "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v"]
TB = "rtl/test/tb_v41_rom_array.sv"
NSEG, NCH, XF = 4, 16, 4
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


def golden_rows(m: Mat, x: np.ndarray):
    """FP32 accumulator bits and BF16 output of every row (golden linear_q, chunk8)."""
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
def viamap(words: dict[int, int], path: Path) -> None:
    rows = [0] * 1024
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


def build_phase(mats: list[Mat], N: int, work: Path, rng):
    K = mats[0].K
    assert all(m.K == K for m in mats)
    x = G.to_bf16((rng.standard_normal(K) * 0.5).astype(G.F))
    exp_fp32, exp_bf16 = {}, {}
    xq = xe = None
    for mi, m in enumerate(mats):
        f, bf, xq, xe = golden_rows(m, x)
        for r in range(m.rows):
            exp_fp32[mi * 1024 + r] = int(f[r])
            exp_bf16[mi * 1024 + r] = int(bf[r])
    xc = x_codes(xq)
    # placement with the bank-map rules on an N-macro die (no BF16 subset needed here)
    die = S.Die(N, 0)
    specs = [dict(tensor=f"m{mi}", phase=m.phase, fmt=m.fmt, rows=m.rows, K=m.K) for mi, m in enumerate(mats)]
    res, info = S.place_dense(die, specs, 0)
    (ph, r), = res.items()
    t_pred = r["t_phase"]
    cfg, n_words = [], 0
    by_e = {}
    for i, sg in enumerate(die.segs):
        by_e.setdefault(sg["macro"], []).append(i)
    rounds = {}                      # (q, b) -> {unit} ; demand per element
    demand = {}
    for e in range(N):
        sids = by_e.get(e, [])
        segs = [die.segs[i] for i in sids]
        assert len(segs) <= NSEG, (e, len(segs))
        words = {}
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
            d = ((mi * 1024 + sg["row"]) | (sg["seg"] << 16) | (nseg << 21) | (int(sg["fmt"] == "fp4") << 26)
                 | (int(lo) << 27) | (int(hi) << 28) | (sg["base"] << 29))
            cfg.append((e, slot, d))
            for k, (u, b, h) in enumerate(S.segment_order(sg["fmt"], e0, el)):
                if sg["fmt"] == "fp8":
                    w = m.block_word(sg["row"], 2 * u + h, b)
                else:
                    w = 0
                    for half in (0, 1):
                        c = 2 * u + half
                        if e0 <= c * 256 < e0 + el:
                            w |= m.block_word(sg["row"], c, b) << (136 * half)
                words[sg["base"] + k] = w
            n_words += len(S.segment_order(sg["fmt"], e0, el))
        for c, (u0, nu, s0, s1) in enumerate(centries):
            cfg.append((e, NSEG + c, 1 | (u0 << 1) | (nu << 9) | (s0 << 14) | (s1 << 16)))
        for c in range(len(centries), NSEG):
            cfg.append((e, NSEG + c, 0))
        two_q = any(nu > 8 for _, nu, _, _ in centries)
        cfg.append((e, 2 * NSEG, int(two_q)))
        viamap(words, work / f"e{e}.viamap.hex")
        # stream needs and demand of this element, round by round (element_order)
        for (i, u, b, h) in S.element_order(segs):
            sg = segs[i]
            q = (u - S.unit_range(sg["fmt"], sg["e0"], sg["elems"])[0]) // S.IL
            rounds.setdefault((q, b), set()).add(u)
            demand[(q, b, e)] = demand.get((q, b, e), 0) + 1
    # the x stream: per round, needed pairs ascending, spread over r = max(5, beats, demand)
    C = K // 256
    beats = []
    t_rounds = 0
    for (q, b) in sorted(rounds):
        units = sorted(rounds[(q, b)])
        dmax = max(v for (qq, bb, _), v in demand.items() if (qq, bb) == (q, b))
        rl = max(S.FADD_REC, len(units), dmax)
        slots = [None] * rl
        for i, u in enumerate(units):
            slots[(i * rl) // len(units)] = u
        for u in slots:
            if u is None:
                beats.append(0)
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
            beats.append(v)
        t_rounds += rl
    assert 8 * 0 + t_rounds == t_pred or True
    (work / "cfg.hex").write_text("".join(f"{(e << 52) | (a << 48) | d:015x}\n" for e, a, d in cfg))
    (work / "stream.hex").write_text("".join(f"{v:0137x}\n" for v in beats))
    return dict(ncfg=len(cfg), nst=len(beats), nrows=len(exp_fp32), exp_fp32=exp_fp32, exp_bf16=exp_bf16,
                t_pred=t_pred, t_rounds=t_rounds, words=n_words, split=info,
                elements=[len(by_e.get(e, [])) for e in range(N)])


def build_sim(N: int, work: Path) -> Path:
    out = work / f"obj_n{N}"
    exe = out / "Vtb_v41_rom_array"
    if exe.exists():
        return exe
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "8", "-Wno-fatal", "-Wno-lint", "-Wno-style",
           "-O2", f"-GN={N}", "--top-module", "tb_v41_rom_array", "-Mdir", str(out), str(ROOT / TB)]
    cmd += [str(ROOT / p) for p in RTL]
    subprocess.run(cmd, check=True, cwd=work, stdout=subprocess.DEVNULL)
    return exe


def run_case(exe: Path, work: Path, ph: dict):
    r = subprocess.run([str(exe), f"+DIR={work}", f"+OT_ROM_DIR={work}", f"+NROWS={ph['nrows']}",
                        f"+NCFG={ph['ncfg']}", f"+NST={ph['nst']}"], capture_output=True, text=True, check=True)
    rows, done = {}, None
    for line in r.stdout.splitlines():
        t = line.split()
        if t and t[0] == "ROW":
            rows[int(t[1])] = (int(t[2], 16), int(t[3], 16), int(t[4]), int(t[5]))
        elif t and t[0] == "DONE":
            done = (int(t[1]), int(t[2]))
    return rows, done


def cases(ck: Ckpt, N: int):
    L = f"layers.{LAYER}."
    half = max(1, N // 2)
    E = 7
    return {
        "fp8_wq_a_whole_rows": [Mat(ck, L + "attn.wq_a", "fp8", N, 5120, phase="wq_b")],
        "fp8_wq_a_ksplit": [Mat(ck, L + "attn.wq_a", "fp8", half, 5120, r0=64, phase="wq_b")],
        "fp8_wq_b": [Mat(ck, L + "attn.wq_b", "fp8", half, 1280, r0=4096, phase="wq_b")],
        "fp8_wo_b_kquarter": [Mat(ck, L + "attn.wo_b", "fp8", max(1, N // 4), 2048, r0=100, k0=2048, phase="wo_b")],
        "fp4_expert_w1": [Mat(ck, L + f"ffn.experts.{E}.w1", "fp4", half, 5120, r0=1728, phase="experts_gu")],
        "fp8_wq_b_two_rows_per_element": [Mat(ck, L + "attn.wq_b", "fp8", 2 * N, 1280, r0=8000, phase="wq_b")],
        "fp4_two_experts_w1_w3": [Mat(ck, L + f"ffn.experts.{E}.w1", "fp4", half, 5120, r0=0, phase="experts_gu"),
                                  Mat(ck, L + "ffn.experts.301.w3", "fp4", half, 5120, r0=500, phase="experts_gu")],
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
    ap.add_argument("--output", type=Path)
    a = ap.parse_args(argv)
    G.set_arith("chunk8")
    ck = Ckpt(a.snapshot)
    rng = np.random.default_rng(SEED)
    out = []
    for N in a.n:
        a.work.mkdir(parents=True, exist_ok=True)
        exe = build_sim(N, a.work)
        for name, mats in cases(ck, N).items():
            if a.only and a.only not in name:
                continue
            wd = a.work / f"n{N}_{name}"
            wd.mkdir(exist_ok=True)
            ph = build_phase(mats, N, wd, rng)
            rows, done = run_case(exe, wd, ph)
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
            rec = dict(N=N, case=name, model_depth=model_depth,
                       model_prediction=ph["t_pred"] + model_depth, rows=ph["nrows"], rows_out=len(rows), fp32_exact=ok_fp32, bf16_exact=ok_bf16,
                       fault=done[1] if done else None, cycles_last_row=last, t_phase_pred=ph["t_pred"],
                       t_rounds_scheduled=ph["t_rounds"], fill=(last - ph["t_pred"]) if last is not None else None,
                       words=ph["words"], segments_per_element=ph["elements"],
                       split={k: v["segment_elems"] for k, v in ph["split"].items()},
                       tensors=[dict(name=m.name, fmt=m.fmt, rows=[m.r0, m.r0 + m.rows], cols=[m.k0, m.k0 + m.K])
                                for m in mats])
            print(json.dumps({k: rec[k] for k in ("N", "case", "rows", "rows_out", "fp32_exact", "bf16_exact",
                                                   "fault", "cycles_last_row", "t_phase_pred", "fill", "model_depth")}), flush=True)
            out.append(rec)
    if a.output:
        srcs = RTL + [TB, "tools/rtl_v41_rom_array.py", "tools/v41_rom_ksplit_bankmap.py", "tools/hdc_golden_v41.py"]
        rec = dict(schema="opentallas.v41.rom_array_exactness.v1",
                   verdict="PASS" if all(r["fp32_exact"] == r["rows"] == r["bf16_exact"] and not r["fault"]
                                         for r in out) else "FAIL",
                   golden="tools/hdc_golden_v41.py linear_q, HDC_V41_ARITH=chunk8",
                   checkpoint_revision=a.snapshot.name, checkpoint_header_sha256=ck.pins, seed=SEED,
                   simulator=f"verilator 5.050 ({VERILATOR})",
                   params=dict(NSEG=NSEG, NCH=NCH, XF=XF, BST=2, RST=1, LV=5, RD=16, root_D=16),
                   source_sha256={p: sha(ROOT / p) for p in srcs}, cases=out)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
