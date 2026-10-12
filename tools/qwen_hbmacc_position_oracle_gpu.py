#!/usr/bin/env python3
"""GPU port of the Qwen3-8B O4 TP2/TP4 position oracle: all 36 layers and the lm_head at a NONZERO position.

tools/qwen_rom_position_oracle_w12.py (the ISA golden over a real prompt, positions < P the golden prefill run as
sequential decode) executes on the CPU in NumPy, about 1.5 s per layer-position: a 36-layer token at P1023 is ~15 h.
This tool runs the SAME ISA machine on the local CUDA GPU (torch), the four TP dies batched along a leading axis:

  * every primitive is the golden's (tools/hdc_golden.py): add/mul are single IEEE binary32 RNE operations with the
    zero result canonicalised to +0 (torch elementwise CUDA kernels round each op; no FMA contraction, no
    flush-to-zero), BF16 rounding, the bit-seeded rsqrt / reciprocal, the Cody-Waite exp, FP8 E4M3 KV rounding, and
    the R-ARITH chunked reduction (chunks of 8 sequential from +0, a pairwise tree padded with +0);
  * dense matrices: the golden contiguous K-split (FastDieMachine.matvec_chunked: each chunk sequential from +0,
    chunk sums by the pairwise tree); KV-sourced ops: hdc_program.Machine.me (interleaved split, past-K skipped),
    vectorised over the split chunks with the identical per-chunk order;
  * stream instructions: hdc_program.Machine.su, the TP all-reduce: hdc_golden.fold in rank order;
  * lm_head: tools/qwen_o4_token_oracle_w12.HeadMachine (chunked running argmax, lower row on ties) and the
    cross-die argmax (np.argmax of the concatenated logits: lowest vocabulary row on ties).

It is checked bit-exactly, before any use, against the CPU golden's committed/retained outputs: the retained TP4
36-layer + head oracle at token 0 position 0 (oracle_tp4, token 50994) and the CPU position oracle at P255/P1023
(layers 0-2: X, kv_pre, kv_at_P).  Outputs use the CPU tool's layout (L<nn>_die<d>_x.hex, kv_pre/, kv_at_P/,
x_preload.hex, embedding_row.json) plus head.json/logits.npy, so tools/qwen_rom_rt_token_w12_rm.py consumes them.

Subcommands:
  --prep   (any host, no torch; file decoding only, no model arithmetic) decode the pinned stage images into
           per-layer/die .npz (codes int8, scales, constant ROM) with every source hex pinned by sha256.
  --run    (local GPU only) the golden prefill to the last --positions entry, recording each listed position.

HA8 (tools/qwen_hbmacc_position_oracle_gpu.py): derived from tools/qwen_rom_position_oracle_gpu.py (realmem
full-token agent, 2026-10-04) with TP taken from QWEN_O4_TP (2 or 4); the arithmetic is unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
LAYERS = 36
TP = int(os.environ.get("QWEN_O4_TP", "4"))   # HA8: TP2 (design point a) or TP4 (b)
HEAD_ROWS = 151936 // TP


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def need_env():
    want = {"QWEN_O4_GROUPS": "6144", "QWEN_O4_TP": str(TP), "HDC_SU_WIDTH": "1024", "HDC_KV_FMT": "fp8"}
    if TP not in (2, 4):
        raise SystemExit("QWEN_O4_TP must be 2 or 4")
    bad = {k: os.environ.get(k) for k, v in want.items() if os.environ.get(k) != v}
    if bad:
        raise SystemExit(f"requires {want}; got {bad}")


# ---------------------------------------------------------------------------------------------------------------
# prep: image decoding (CPU, file conversion only)
# ---------------------------------------------------------------------------------------------------------------
def prep_one(job):
    import qwen_o4_layer0_oracle_w12 as L0
    import qwen_o4_token_oracle_w12 as TO
    kind, n, d, src, man_path, out, pins = job
    src = Path(src)
    got = {name: sha(src / name) for name in ("matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex")}
    for name, want in pins.items():
        if got.get(name) != want:
            raise SystemExit(f"{src}/{name}: sha256 {got.get(name)} != pinned {want}")
    crom = TO.read_crom(src / "crom.hex")
    arrays = {"crom": crom}
    if kind == "layer":
        man = json.loads(Path(man_path).read_text())
        man = dict(man, layer=n)
        obj = types.SimpleNamespace(dir=src, manifest=man, crom=crom)
        for meta in man["matrix_layout"]:
            codes, scales = L0.Image.matrix(obj, meta)
            arrays[f"codes_{meta['name']}"] = codes
            arrays[f"scales_{meta['name']}"] = np.asarray(scales, dtype=np.float32)
        layout = man["matrix_layout"]
    else:
        hm = json.loads(Path(man_path).read_text())
        geo = hm["geometry"]
        meta = {"name": "lm_head", "rows": HEAD_ROWS, "columns": 4096, "split": geo["split"],
                "k_per_split": geo["k_per_split"], "rounds": geo["rounds"], "base": 0,
                "code_span_words": hm["code_words"], "scale_base": 0, "scale_span_words": hm["scale_words"]}
        obj = types.SimpleNamespace(dir=src, manifest=hm, crom=crom)
        codes, scales = L0.Image.matrix(obj, meta)
        arrays["codes_lm_head"], arrays["scales_lm_head"] = codes, np.asarray(scales, dtype=np.float32)
        layout = [meta]
    np.savez(out, **arrays)
    return {"kind": kind, "layer": n, "die": d, "src": str(src), "image_sha256": got, "npz": Path(out).name,
            "npz_sha256": sha(out), "layout": layout}


def cmd_prep(a):
    need_env()
    from concurrent.futures import ProcessPoolExecutor
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    pins = json.loads(a.pins.read_text())             # retained oracle_tp4 oracle.json: layer_image_sha256, head_die*
    stages = {l.split()[0]: l.split()[1:-1] for l in a.stages.read_text().splitlines() if l.strip()}
    jobs = []
    for n in range(LAYERS):
        for d in range(TP):
            p = {k: v for k, v in pins["layer_image_sha256"][f"L{n}"][d].items()
                 if k in ("matrix_int8.hex", "matrix_scale_bf16.hex", "crom.hex")}
            jobs.append(("layer", n, d, stages[f"L{n}"][d], str(a.layout_manifest).format(die=d),
                         str(out / f"L{n:02d}_d{d}.npz"), p))
    for d in range(TP):
        p = {k: v for k, v in pins[f"head_die{d}"]["image_sha256"].items()}
        jobs.append(("head", -1, d, stages["head"][d], str(a.head_manifest).format(die=d), str(out / f"head_d{d}.npz"), p))
    with ProcessPoolExecutor(a.procs) as ex:
        recs = list(ex.map(prep_one, jobs))
    # programs: the golden runs the SU_WIDTH 1024 programs (the stage images' sw programs only re-count chase
    # thresholds, tools/qwen_rom_program_sw.py); layer programs from the layout images, the head regenerated
    progs = {}
    for d in range(TP):
        ld = Path(str(a.layout_manifest).format(die=d)).parent
        progs[f"layer_d{d}"] = {"program": (ld / "program.hex").read_text().split(),
                                "segments": (ld / "segments.hex").read_text().split(),
                                "program_sha256": sha(ld / "program.hex"), "segments_sha256": sha(ld / "segments.hex")}
    rec = {"schema": "opentallas.qwen-rom-position-oracle-gpu-prep.v1", "at": time.strftime("%FT%TZ", time.gmtime()),
           "stages": str(a.stages), "stages_sha256": sha(a.stages), "pins": str(a.pins), "pins_sha256": sha(a.pins),
           "tool_sha256": sha(Path(__file__)), "images": recs, "programs": progs}
    (out / "prep.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"prepared {len(recs)} images in {out}")


# ---------------------------------------------------------------------------------------------------------------
# torch golden primitives (tools/hdc_golden.py, op for op)
# ---------------------------------------------------------------------------------------------------------------
def torch_golden(dev):
    import torch
    T = types.SimpleNamespace(torch=torch, dev=dev)
    f32, i32, i64 = torch.float32, torch.int32, torch.int64
    ZERO = torch.zeros((), dtype=f32, device=dev)

    def c(v):
        return torch.tensor(np.float32(v), dtype=f32, device=dev)

    def z(x):
        return torch.where(x == 0, ZERO, x)

    def add(a, b):
        return z(a + b)

    def mul(a, b):
        return z(a * b)

    def bits(x):
        return x.contiguous().view(i32)

    def from_bits(b):
        return b.to(i32).contiguous().view(f32)

    def neg(a):
        return from_bits(bits(a) ^ torch.tensor(-0x80000000, dtype=i32, device=dev))

    def to_bf16(x):
        b = u32(x)
        r = (b + 0x7FFF + ((b >> 16) & 1)) >> 16
        return from_u32((r << 16) & 0xFFFFFFFF)

    def _u32_to_i32(u):
        u = u.to(i64)
        return torch.where(u >= 0x80000000, u - 0x100000000, u).to(i32)

    def from_u32(u):
        return _u32_to_i32(u).view(f32)

    def u32(x):
        return bits(x).to(i64) & 0xFFFFFFFF

    def rsqrt(v):
        y = from_u32(0x5F3759DF - (u32(v) >> 1))
        half = mul(v, c(0.5))
        for _ in range(3):
            y = mul(y, add(c(1.5), neg(mul(half, mul(y, y)))))
        return y

    def reciprocal(d):
        db = u32(d)
        sat = ((db & 0x80000000) == 0) & ((db & 0x7F800000) != 0x7F800000) & (db > 0x7EF311C7)
        y = from_u32(torch.where(sat, torch.zeros_like(db), 0x7EF311C7 - db) & 0xFFFFFFFF)
        for _ in range(3):
            y = mul(y, add(c(2.0), neg(mul(d, y))))
        return y

    EXP_POLY = [1.0 / 720, 1.0 / 120, 1.0 / 24, 1.0 / 6, 0.5, 1.0, 1.0]

    def exp(x):
        x = torch.clamp(x, c(-87.0), c(88.0))
        t = mul(x, c(1.4426950408889634))
        u = add(t, c(12582912.0))
        n = add(u, neg(c(12582912.0)))
        r = add(add(x, neg(mul(n, c(0.693145751953125)))), neg(mul(n, c(1.428606765330187e-06))))
        p = torch.full_like(r, np.float32(EXP_POLY[0]))
        for k in EXP_POLY[1:]:
            p = add(mul(p, r), c(k))
        e = u32(p) + (n.to(i64) << 23)
        return from_u32(e & 0xFFFFFFFF)

    def to_fp8(x):
        a = torch.abs(x).to(torch.float64)
        _, ex = torch.frexp(a)
        e = torch.clamp(ex.to(i64) - 1, min=-6)
        q = ((e - 3 + 1023) << 52).view(torch.float64)    # 2^(e-3) exactly (torch.ldexp's pow(2, x) is not exact on CUDA)
        r = torch.clamp(torch.round(a / q) * q, max=448.0)
        return z(torch.where(x < 0, -r, r).to(f32))

    def kv_round(x):
        return to_fp8(x)

    def lane_sum_rows(v):
        """reduce_chunked along the last axis (R-ARITH: chunks of 8 sequential from +0, then a +0-padded tree)."""
        n = v.shape[-1]
        nch = max(1, -(-n // 8))
        pad = nch * 8 - n
        if pad:
            v = torch.cat([v, torch.zeros(*v.shape[:-1], pad, dtype=f32, device=dev)], dim=-1)
        v = v.reshape(*v.shape[:-1], nch, 8)
        acc = torch.zeros(v.shape[:-1], dtype=f32, device=dev)
        for i in range(8):                            # padded +0 adds leave acc unchanged (acc is never -0)
            acc = add(acc, v[..., i])
        m = 1
        while m < nch:
            m *= 2
        if m > nch:
            acc = torch.cat([acc, torch.zeros(*acc.shape[:-1], m - nch, dtype=f32, device=dev)], dim=-1)
        while acc.shape[-1] > 1:
            acc = add(acc[..., 0::2], acc[..., 1::2])
        return acc[..., 0]

    def fold(parts):
        acc = parts[0]
        for p in parts[1:]:
            acc = add(acc, p)
        return acc

    T.__dict__.update(z=z, add=add, mul=mul, neg=neg, bits=bits, to_bf16=to_bf16, rsqrt=rsqrt, reciprocal=reciprocal,
                      exp=exp, to_fp8=to_fp8, kv_round=kv_round, lane_sum_rows=lane_sum_rows, fold=fold, c=c,
                      from_u32=from_u32, u32=u32)
    return T


def selftest(T, n=1 << 20, seed=7):
    """Primitive-by-primitive bit equality against tools/hdc_golden.py on adversarial inputs (subnormals, zeros of
    both signs, NaN/Inf, huge/tiny magnitudes, values near the reciprocal saturation and exp clamps)."""
    import hdc_golden as G
    torch = T.torch
    rng = np.random.default_rng(seed)
    raw = rng.integers(0, 1 << 32, size=n, dtype=np.uint64).astype(np.uint32)
    special = np.array([0, 0x80000000, 1, 0x80000001, 0x007FFFFF, 0x00800000, 0x7F7FFFFF, 0x7F800000, 0xFF800000,
                        0x7FC00000, 0x7EF311C7, 0x7EF311C8, 0x3F800000, 0x42B00000, 0xC2AE0000, 0x3B800000],
                       dtype=np.uint32)
    a_np = G.from_bits(np.concatenate([raw, special]))
    b_np = G.from_bits(np.concatenate([rng.integers(0, 1 << 32, size=n, dtype=np.uint64).astype(np.uint32),
                                       special[::-1]]))
    s_np = (rng.standard_normal(n + len(special)) * 30).astype(np.float32)
    small = (rng.standard_normal(n + len(special)) * 1e-3).astype(np.float32)
    a, b, s, sm = (torch.from_numpy(x.copy()).to(T.dev) for x in (a_np, b_np, s_np, small))
    res = {}

    def eq(name, got, want):
        g = got.cpu().numpy().view(np.uint32)
        w = np.asarray(want, dtype=np.float32).view(np.uint32)
        ok = np.array_equal(g, w) or np.array_equal(np.where(np.isnan(got.cpu().numpy()), 0x7FC00000, g),
                                                    np.where(np.isnan(np.asarray(want)), 0x7FC00000, w))
        res[name] = bool(ok)
    with np.errstate(all="ignore"):
        eq("add", T.add(a, b), G.add(a_np, b_np))
        eq("mul", T.mul(a, b), G.mul(a_np, b_np))
        eq("neg", T.neg(a), G.neg(a_np))
        eq("to_bf16", T.to_bf16(a), G.to_bf16(a_np))
        eq("rsqrt", T.rsqrt(torch.abs(s)), G.rsqrt(np.abs(s_np)))
        eq("reciprocal", T.reciprocal(a), G.reciprocal(a_np))
        eq("reciprocal_s", T.reciprocal(s), G.reciprocal(s_np))
        eq("exp", T.exp(s), G.exp(s_np))
        eq("exp_a", T.exp(a), G.exp(a_np))
        eq("to_fp8", T.to_fp8(s), G.to_fp8(s_np))
        eq("to_fp8_small", T.to_fp8(sm), G.to_fp8(small))
        for m in (1, 5, 8, 64, 129, 1024, 4096):
            v = s_np[: 7 * m].reshape(7, m)
            eq(f"lane_sum_{m}", T.lane_sum_rows(torch.from_numpy(v.copy()).to(T.dev)),
               np.array([G.reduce_chunked(r) for r in v], dtype=np.float32))
    return res


# ---------------------------------------------------------------------------------------------------------------
# the ISA machine, four dies batched
# ---------------------------------------------------------------------------------------------------------------
class GpuTP:
    def __init__(self, T, prep_dir: Path, layers, head: bool):
        import hdc_isa as I
        import hdc_program as P
        import hdc_qwen_fullshape_isa_w12 as QI
        import hdc_qwen_fullshape_program_w12 as FP
        import qwen_o4_layer0_oracle_w12 as L0
        self.T, self.I, self.P, self.FP, self.L0 = T, I, P, FP, L0
        torch = T.torch
        self.W, self.IL, self.GROUPS = L0.W, L0.IL, L0.GROUPS
        self.VM, self.VM_ELEMS = L0.VM, L0.VM_ELEMS
        prep = json.loads((prep_dir / "prep.json").read_text())
        self.prep = prep
        self.layouts = {}
        self.prog = [[QI.decode_instruction(int(x, 16)) for x in prep["programs"][f"layer_d{d}"]["program"]] for d in range(TP)]
        self.desc = [QI.decode_descriptor(int(x, 16)) for x in prep["programs"]["layer_d0"]["segments"]]
        for d in range(1, TP):
            if [QI.decode_descriptor(int(x, 16)) for x in prep["programs"][f"layer_d{d}"]["segments"]] != self.desc:
                raise SystemExit("TP descriptor mismatch")
        recs = {(r["kind"], r["layer"], r["die"]): r for r in prep["images"]}
        self.layout = recs[("layer", 0, 0)]["layout"]
        self.lays = [FP.LayerZero(None, d, self.layout) for d in range(TP)]
        self.kv_elems = 2 * self.lays[0].kv_v0
        dev = T.dev
        self.mats, self.crom = [], []
        for n in layers:
            per = {}
            croms = []
            for d in range(TP):
                if recs[("layer", n, d)]["layout"] != self.layout:
                    raise SystemExit(f"L{n} die {d}: matrix layout differs from layer 0")
                z = np.load(prep_dir / f"L{n:02d}_d{d}.npz")
                croms.append(z["crom"])
                for meta in self.layout:
                    nm = meta["name"]
                    codes = z[f"codes_{nm}"]
                    split, kcs = meta["split"], meta["columns"] // meta["split"]
                    wT = np.ascontiguousarray(codes.reshape(codes.shape[0], split, kcs).transpose(2, 1, 0))
                    per.setdefault(nm, ([], []))
                    per[nm][0].append(wT)
                    per[nm][1].append(z[f"scales_{nm}"])
            self.mats.append({nm: (torch.from_numpy(np.stack(w)).to(dev), torch.from_numpy(np.stack(s)).to(dev))
                              for nm, (w, s) in per.items()})
            self.crom.append(torch.from_numpy(np.stack(croms).astype(np.float32)).to(dev))
        self.layer_ids = list(layers)
        self.by_base = {m["base"]: m for m in self.layout}
        self.kv = [torch.zeros((TP, self.kv_elems), dtype=torch.float32, device=dev) for _ in layers]
        self.head = None
        if head:
            hc, hs, hcrom, hprog = [], [], [], []
            for d in range(TP):
                z = np.load(prep_dir / f"head_d{d}.npz")
                hc.append(z["codes_lm_head"]); hs.append(z["scales_lm_head"]); hcrom.append(z["crom"])
            geo = recs[("head", -1, 0)]["layout"][0]
            self.head = {"codes": torch.from_numpy(np.stack(hc)).to(dev), "scales": torch.from_numpy(np.stack(hs)).to(dev),
                         "crom": torch.from_numpy(np.stack(hcrom).astype(np.float32)).to(dev), "geo": geo}

    # -- stream unit ------------------------------------------------------------------------------------
    def stream(self, f, dyn, s, n_out, n_in):
        torch = self.T.torch
        base = f[f"{s}_base"] + dyn[f[f"{s}_d"]]
        o = torch.arange(n_out, device=self.T.dev, dtype=torch.int64)[:, None]
        i = torch.arange(n_in, device=self.T.dev, dtype=torch.int64)[None, :]
        return (base + o * f[f"{s}_so"] + i * f[f"{s}_si"]).reshape(-1)

    def su(self, vm, kv, crom, f, dyn):
        T, I = self.T, self.I
        torch = T.torch
        n_out = f["su_nout"]
        n_in = f["su_nin"] + dyn[f["su_d_nin"]]
        ea, eb, ec = (self.stream(f, dyn, s, n_out, n_in) for s in ("a", "b", "c"))
        if f["a_src"]:
            raise SystemExit("weight-ROM stream operand (a_src) is not used by the Qwen stage programs")
        a = vm[:, ea]
        if f["b_src"]:
            blo, bhi = crom[:, eb, 0], crom[:, eb, 1]
        else:
            blo, bhi = vm[:, eb], torch.zeros((TP, len(eb)), dtype=torch.float32, device=T.dev)
        c = crom[:, ec, 0] if f["c_src"] else vm[:, ec]
        imm1 = T.from_u32(torch.tensor(f["imm1"], dtype=torch.int64, device=T.dev))
        imm2 = T.from_u32(torch.tensor(f["imm2"], dtype=torch.int64, device=T.dev))
        p = {I.MA_BYP: lambda: a, I.MA_AB: lambda: T.mul(a, blo), I.MA_AA: lambda: T.mul(a, a),
             I.MA_AIMM: lambda: T.mul(a, imm1)}[f["ma"]]()
        q = {I.MB_OFF: lambda: None, I.MB_POS: lambda: T.mul(c, bhi), I.MB_NEG: lambda: T.mul(c, T.neg(bhi))}[f["mb"]]()
        r = {I.AD_BYP: lambda: p, I.AD_Q: lambda: T.add(p, q), I.AD_C: lambda: T.add(p, c),
             I.AD_NEGB: lambda: T.add(p, T.neg(blo)), I.AD_IMM: lambda: T.add(p, imm2)}[f["ad"]]()
        s = {I.SFU_NONE: lambda: r, I.SFU_EXP: lambda: T.exp(r), I.SFU_RECIP: lambda: T.reciprocal(r),
             I.SFU_RSQRT: lambda: T.rsqrt(r),
             I.SFU_SIGM: lambda: T.reciprocal(T.add(T.exp(r), T.c(1.0)))}[f["sfu"]]()
        out = T.mul(s, c) if f["mc"] == I.MC_C else s
        if f["md"] == I.MD_B:
            out = T.mul(out, blo)
        if out.dim() == 0 or out.shape[-1] != len(ea):
            out = out.expand(TP, len(ea)).contiguous()
        if f["red"]:
            seg = (T.mul(out, out) if f["red_sq"] else out).reshape(TP, n_out, n_in)
            if f["red"] == I.RED_SUM:
                vals = T.lane_sum_rows(seg)
            else:
                vals = self._max_rows(seg)
            ridx = f["r_base"] + torch.arange(n_out, device=T.dev) * f["r_so"]
            vm[:, ridx] = vals
        if f["dst"]:
            ed = self.stream(f, dyn, "d", n_out, n_in)
            self._check_unique(ed)
            if f["dst"] == I.DST_VM:
                vm[:, ed] = out
            else:
                kv[:, ed] = T.kv_round(out)

    def _max_rows(self, seg):
        """np.max per row: NaN if any NaN; else the maximum (all values are +0-canonical or nonzero)."""
        torch = self.T.torch
        m = torch.amax(seg, dim=-1)
        nan = torch.isnan(seg).any(dim=-1)
        return torch.where(nan, torch.full_like(m, float("nan")), m)

    def _check_unique(self, idx):
        if getattr(self, "_checked", None) is None:
            self._checked = set()
        key = (int(idx[0]), len(idx))
        if key in self._checked:
            return
        if len(self.T.torch.unique(idx)) != len(idx):
            raise SystemExit("duplicate destination indices: NumPy last-write order would be needed")
        self._checked.add(key)

    # -- matrix engine ----------------------------------------------------------------------------------
    def me_dense(self, li, vm, f, dyn):
        T = self.T
        meta = self.by_base[f["me_wbase"]]
        n = f["me_nout"] + dyn[f["me_d_nout"]]
        split = 1 << f["me_split"]
        if n != meta["rows"] or split != meta["split"]:
            raise SystemExit(f"ISA/matrix geometry mismatch: {meta['name']}")
        if not f["me_oen"]:
            raise SystemExit("layer oracle expects each matrix to write VM")
        wT, scales = self.mats[li][meta["name"]]          # [TP, kc, split, n] int8, [TP, n]
        xb = f["me_xbase"] + dyn[f["me_d_xbase"]]
        kcs = wT.shape[1]
        xr = T.to_bf16(vm[:, xb:xb + meta["columns"]]).reshape(TP, split, kcs)
        acc = T.torch.zeros((TP, split, n), dtype=T.torch.float32, device=T.dev)
        for k in range(kcs):
            acc = T.add(acc, T.mul(wT[:, k].to(T.torch.float32), xr[:, :, k, None]))
        while acc.shape[1] > 1:
            acc = T.add(acc[:, 0::2], acc[:, 1::2])
        raw = acc[:, 0]
        out = raw if meta["name"] in ("o", "down") else T.mul(raw, scales)
        ob = f["me_obase"] * self.W
        vm[:, ob:ob + n] = out

    def me_kv(self, vm, kv, f, dyn, pos):
        """hdc_program.Machine.me, KV-sourced (attention) ops, vectorised over the split chunks."""
        T, I, W, IL = self.T, self.I, self.W, self.IL
        torch = T.torch
        GR = self.GROUPS
        n = f["me_nout"] + dyn[f["me_d_nout"]]
        tiles = f["me_tiles"] + dyn[f["me_d_tiles"]]
        K = f["me_k"] + dyn[f["me_d_k"]]
        wb = f["me_wbase"] + dyn[f["me_d_wbase"]]
        xb = f["me_xbase"] + dyn[f["me_d_xbase"]]
        ob = f["me_obase"] + dyn[f["me_d_obase"]]
        split = f["me_split"]
        S = 1 << split
        per_round = GR // S
        if f["me_d_tiles"] == I.DYN_TTILES:
            tiles = f["me_tiles"] + pos // (W * (GR >> split)) + 1
        kc = -(-K // S)
        dev = T.dev
        r, q, j, l = (a.reshape(-1) for a in torch.meshgrid(
            torch.arange(tiles, device=dev), torch.arange(per_round, device=dev), torch.arange(IL, device=dev),
            torch.arange(W, device=dev), indexing="ij"))
        t = r * per_round + q
        nidx = (t * IL + j) * W + l
        keep = (nidx < n) if f["me_mmode"] == 0 else (t * W + l < n)
        r, q, t, j, l, nidx = r[keep], q[keep], t[keep], j[keep], l[keep], nidx[keep]
        cc = torch.arange(S, device=dev)[:, None]
        acc = torch.zeros((TP, S, len(t)), dtype=torch.float32, device=dev)
        for k in range(kc):
            live = (k * S + cc) < K                                       # [S, 1]: past K the element is skipped
            word = wb + t[None] * f["me_ts"] + cc * f["me_wcs"] + k * f["me_ks"] + (j[None] >> f["me_jsh"]) * f["me_js"]
            widx = word * W + l[None]
            widx = torch.where(live, widx, torch.zeros_like(widx))
            w = kv[:, widx]                                               # [TP, S, N]
            xidx = xb + cc * f["me_xcs"] + k * f["me_xks"] + j[None] * f["me_xjs"]
            xidx = torch.where(live, xidx, torch.zeros_like(xidx))
            x = vm[:, xidx]
            if f["me_round"]:
                x = T.to_bf16(x)
            acc = torch.where(live[None], T.add(acc, T.mul(w, x)), acc)
        while acc.shape[1] > 1:
            acc = T.add(acc[:, 0::2], acc[:, 1::2])
        acc = acc[:, 0]
        if f["me_oen"]:
            oidx = (ob + t * f["me_ots"] + j * f["me_ojs"]) * W + l
            self._check_unique(oidx)
            vm[:, oidx] = acc
        if f["me_rmax"]:
            for jj in range(IL):
                sel = acc[:, j == jj]
                if sel.shape[1]:
                    vm[:, f["me_mbase"] + jj] = self._max_rows(sel)
        if f["me_amax"]:
            raise SystemExit("argmax in a layer program")

    # -- one layer, one position --------------------------------------------------------------------------
    def run_layer(self, li, vm, token, pos):
        P, I, T = self.P, self.I, self.T
        kv, crom = self.kv[li], self.crom[li]
        with self.FP.program_geometry(self.VM):
            dyns = [P.dyn_values(lay, token=token, pos=pos) for lay in self.lays]
            if any(dy != dyns[0] for dy in dyns):
                raise SystemExit("dies disagree on dynamic values")
            dyn = dyns[0]
            for idx, seg in enumerate(self.desc):
                first = seg["program_base"]
                end = self.desc[idx + 1]["program_base"] if idx + 1 < len(self.desc) else len(self.prog[0])
                for pc in range(first, end):
                    fs = [self.prog[d][pc] for d in range(TP)]
                    if any(x != fs[0] for x in fs):
                        raise SystemExit(f"die programs differ at pc {pc}")
                    f = fs[0]
                    if f["unit"] == I.UNIT_ME:
                        if f["me_wsrc"]:
                            self.me_kv(vm, kv, f, dyn, pos)
                        else:
                            self.me_dense(li, vm, f, dyn)
                    elif f["unit"] == I.UNIT_SU:
                        self.su(vm, kv, crom, f, dyn)
                if seg["kind"] == P.COLL_ALLREDUCE:
                    lo, hi = seg["vm_word"] * self.W, (seg["vm_word"] + seg["words"]) * self.W
                    summed = T.fold([vm[d, lo:hi].clone() for d in range(TP)])
                    vm[:, lo:hi] = summed[None]
                elif seg["kind"] != P.COLL_END:
                    raise SystemExit("unexpected layer collective")

    # -- lm_head ---------------------------------------------------------------------------------------------
    def run_head(self, vm, token, pos, head_progs):
        """tools/qwen_o4_token_oracle_w12.HeadMachine on every die, then the cross-die argmax."""
        P, I, T = self.P, self.I, self.T
        torch = T.torch
        h = self.head
        geo = h["geo"]
        logits = [None] * TP
        argmax = [None] * TP
        with self.FP.program_geometry(self.VM):
            lays = []
            for d in range(TP):
                lay = self.FP.LayerZero(None, d, self.layout)
                lay.row0 = d * HEAD_ROWS
                lays.append(lay)
            dyn = P.dyn_values(lays[0], token=token, pos=pos)
            kvdummy = torch.zeros((TP, 1), dtype=torch.float32, device=T.dev)
            for pc in range(len(head_progs[0])):
                fs = [head_progs[d][pc] for d in range(TP)]
                f = fs[0]
                if f["unit"] == I.UNIT_SU:
                    if any(x != f for x in fs):
                        raise SystemExit(f"head SU instruction differs between dies at pc {pc}")
                    self.su(vm, kvdummy, h["crom"], f, dyn)
                elif f["unit"] == I.UNIT_ME:
                    if any(x["me_wsrc"] for x in fs):
                        raise SystemExit("head has no KV-sourced op")
                    split = 1 << f["me_split"]
                    if split != geo["split"] or not f["me_round"] or not f["me_amax"]:
                        raise SystemExit("head chunk geometry changed")
                    # chunk fields agree across dies except nothing die-specific; rows from me_row0
                    for d, fd in enumerate(fs):
                        n = fd["me_nout"] + dyn[fd["me_d_nout"]]
                        row0 = fd.get("me_row0", 0)
                        xb = fd["me_xbase"] + dyn[fd["me_d_xbase"]]
                        x = vm[d, xb:xb + 4096]
                        xr = T.to_bf16(x).reshape(split, 4096 // split)
                        w = h["codes"][d, row0:row0 + n].to(torch.float32).reshape(n, split, 4096 // split)
                        acc = torch.zeros((split, n), dtype=torch.float32, device=T.dev)
                        for k in range(4096 // split):
                            acc = T.add(acc, T.mul(w[:, :, k].T, xr[:, k, None]))
                        while acc.shape[0] > 1:
                            acc = T.add(acc[0::2], acc[1::2])
                        out = T.mul(acc[0], h["scales"][d, row0:row0 + n])
                        if fd["me_oen"]:
                            raise SystemExit("head chunk writes VM")
                        logits[d] = torch.cat([logits[d], out]) if (fd["me_amc"] and logits[d] is not None) else out
        res = {}
        all_logits = torch.cat(logits).cpu().numpy().astype(np.float32)
        for d in range(TP):
            lg = logits[d].cpu().numpy()
            am = int(np.argmax(lg))
            res[f"head_die{d}"] = {"argmax_local": am, "row0": d * HEAD_ROWS, "rows": len(lg),
                                   "logit_bits": f"{int(lg[am:am + 1].view(np.uint32)[0]):08x}"}
        tok = int(np.argmax(all_logits))
        top2 = np.sort(all_logits)[-2:]
        res.update(next_token=tok, next_logit_bits=f"{int(all_logits[tok:tok + 1].view(np.uint32)[0]):08x}",
                   top2_margin=float(top2[1] - top2[0]))
        return res, all_logits


def head_programs(prep):
    """The lm_head stage programs at HDC_SU_WIDTH 1024 (FP.profile_lm_head), as tools/qwen_rom_program_sw.py emits
    them at another width; checked against the sw image's recorded source program sha256."""
    import hdc_qwen_fullshape_isa_w12 as QI
    import hdc_qwen_fullshape_program_w12 as FP
    out, shas = [], []
    for d in range(TP):
        rec = next(r for r in prep["images"] if r["kind"] == "head" and r["die"] == d)
        geo = dict(rec["layout"][0])
        g = {"name": "lm_head", "base": 0, "rows": HEAD_ROWS, "columns": 4096, "split": geo["split"],
             "k_per_split": geo["k_per_split"], "rounds": geo["rounds"], "scale_base": 0}
        prog = FP.profile_lm_head(d, g, 0)
        words = prog["program_hex"]
        shas.append(hashlib.sha256(("\n".join(words) + "\n").encode()).hexdigest())
        out.append([QI.decode_instruction(int(x, 16)) for x in words])
    return out, shas


def write_hex(path, arr):
    Path(path).write_text("".join(f"{int(x):08x}\n" for x in np.asarray(arr, dtype=np.float32).view(np.uint32)))


def cmd_run(a):
    need_env()
    import torch
    if not torch.cuda.is_available():
        raise SystemExit("--run executes on the local GPU only")
    dev = torch.device("cuda")
    T = torch_golden(dev)
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    st = selftest(T)
    if not all(st.values()):
        raise SystemExit(f"primitive self-test failed: {st}")
    print("primitive self-test:", "all bit-exact", flush=True)
    prep = json.loads((a.prep_dir / "prep.json").read_text())
    tokens = [int(t) for t in a.tokens.read_text().split()]
    rec_pos = sorted(int(p) for p in a.positions.split(","))
    last = rec_pos[-1]
    nl = a.layers
    t0 = time.time()
    m = GpuTP(T, a.prep_dir, range(nl), head=a.head)
    print(f"loaded {nl} layers{' + head' if a.head else ''} onto {torch.cuda.get_device_name(0)} in {time.time() - t0:.0f} s", flush=True)
    hprogs, hshas = head_programs(prep) if a.head else (None, None)
    z = np.load(a.embedding_npz)
    emb = {int(t): (sc, cd) for t, sc, cd in zip(z["tokens"], z["scales"], z["codes"])}
    if a.check_token0_preload:
        rows = a.check_token0_preload.read_text().split()[1:]
        want0 = np.array([int(x, 16) for x in rows], dtype=np.uint32)
    import hdc_golden as G
    def x_of(tok):
        sc, cd = emb[tok]
        return (cd.view(np.int8).astype(np.float32) * np.float32(G.from_bits(np.uint32(sc) << np.uint32(16)))).astype(np.float32)
    if a.check_token0_preload and not np.array_equal(x_of(0).view(np.uint32), want0):
        raise SystemExit("embedding decode does not reproduce the retained token-0 preload")
    X = m.VM["X"]
    record = {"schema": "opentallas.qwen-tp-position-oracle-gpu.v1", "status": "ISA_golden_only",
              "layers": nl, "head": bool(a.head), "tp": TP, "groups": m.GROUPS, "su_width_arith": 1024, "kv_format": "fp8",
              "device": torch.cuda.get_device_name(0), "torch": torch.__version__,
              "tokens_sha256": sha(a.tokens), "tokens_used": tokens[:last + 1], "positions": rec_pos,
              "embedding_npz_sha256": sha(a.embedding_npz), "prep_sha256": sha(a.prep_dir / "prep.json"),
              "head_program_sha256": hshas, "primitive_selftest": st, "per_position": {},
              "oracle_source_sha256": {p: sha(ROOT / p) for p in (
                  "tools/qwen_hbmacc_position_oracle_gpu.py", "tools/qwen_rom_position_oracle_w12.py",
                  "tools/qwen_o4_layer0_oracle_w12.py", "tools/qwen_o4_token_oracle_w12.py", "tools/hdc_golden.py",
                  "tools/hdc_program.py", "tools/hdc_isa.py", "tools/hdc_qwen_fullshape_isa_w12.py",
                  "tools/hdc_qwen_fullshape_program_w12.py")},
              "claim_boundary": "ISA golden (GPU port, bit-checked against the CPU golden) over a real prompt: positions < P "
                                "are the golden prefill (sequential decode), position P the token under test. Not an RTL verdict."}
    for p in range(last + 1):
        tok = tokens[p]
        x = x_of(tok)
        vm = torch.zeros((TP, m.VM_ELEMS), dtype=torch.float32, device=dev)
        vm[:, X:X + 4096] = torch.from_numpy(x).to(dev)[None]
        recording = p in rec_pos
        if recording:
            pdir = out / f"P{p}"
            (pdir / "kv_pre").mkdir(parents=True, exist_ok=True)
            (pdir / "kv_at_P").mkdir(parents=True, exist_ok=True)
            (pdir / "x_preload.hex").write_text("@1000\n" + "".join(f"{int(v):08x}\n" for v in x.view(np.uint32)))
            sc, cd = emb[tok]
            (pdir / "embedding_row.json").write_text(json.dumps(
                {"token": tok, "scale_bf16": f"{int(sc):04x}", "codes_hex": cd.tobytes().hex()}) + "\n")
            prec = {"token": tok, "x_preload_sha256": sha(pdir / "x_preload.hex"), "layer_x_sha256": {},
                    "kv_pre_sha256": {}, "kv_at_P_sha256": {}}
        for n in range(nl):
            if recording:
                kvh = m.kv[n].cpu().numpy().view(np.uint32)
                for d in range(TP):
                    path = pdir / "kv_pre" / f"L{n}_die{d}.npy"
                    np.save(path, kvh[d].astype(np.uint32))
                    prec["kv_pre_sha256"][f"L{n}_die{d}"] = sha(path)
            m.run_layer(n, vm, tok, p)
            if recording:
                kvh = m.kv[n].cpu().numpy().view(np.uint32)
                vmh = vm.cpu().numpy()
                for d in range(TP):
                    lay = m.lays[d]
                    kel = [lay.k_elem(0, hh, p, dim) for hh in range(lay.KV) for dim in range(lay.HD)]
                    vel = [lay.v_elem(0, hh, p, dim) for hh in range(lay.KV) for dim in range(lay.HD)]
                    path = pdir / "kv_at_P" / f"L{n}_die{d}.json"
                    path.write_text(json.dumps({"k_elem": kel, "k_bits": [f"{int(b):08x}" for b in kvh[d][kel]],
                                                "v_elem": vel, "v_bits": [f"{int(b):08x}" for b in kvh[d][vel]]}) + "\n")
                    prec["kv_at_P_sha256"][f"L{n}_die{d}"] = sha(path)
                    xpath = pdir / f"L{n:02d}_die{d}_x.hex"
                    write_hex(xpath, vmh[d, X:X + 4096])
                    prec["layer_x_sha256"][f"L{n}_die{d}"] = sha(xpath)
        if recording and a.head:
            hres, logits = m.run_head(vm, tok, p, hprogs)
            np.save(pdir / "logits.npy", logits)
            vmh = vm.cpu().numpy()
            for d in range(TP):
                write_hex(pdir / f"head_die{d}_xnorm.hex", vmh[d, 8192:8192 + 4096])
                hres[f"head_die{d}"]["xnorm_sha256"] = sha(pdir / f"head_die{d}_xnorm.hex")
            hres["logits_sha256"] = sha(pdir / "logits.npy")
            (pdir / "head.json").write_text(json.dumps(hres, indent=1, sort_keys=True) + "\n")
            prec["head"] = hres
            print(f"P{p}: next_token {hres['next_token']} logit {hres['next_logit_bits']} margin {hres['top2_margin']:.4f}", flush=True)
        if recording:
            record["per_position"][str(p)] = prec
            (out / "oracle.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        if p % 16 == 0 or recording:
            print(f"position {p} done ({time.time() - t0:.0f} s)", flush=True)
    record["wall_seconds"] = round(time.time() - t0, 1)
    (out / "oracle.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"positions": rec_pos, "wall_seconds": record["wall_seconds"]}))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prep", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--stages", type=Path, help="--prep: stage list (L0..L35, head) of the pinned TP4 images")
    ap.add_argument("--pins", type=Path, help="--prep: the retained oracle_tp4 oracle.json (image sha256 pins)")
    ap.add_argument("--layout-manifest", help="--prep: layer0_rom.json path with {die} (matrix layout, post-TP scale bases)")
    ap.add_argument("--head-manifest", help="--prep: head_rom.json path with {die}")
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--prep-dir", type=Path, help="--run: the --prep output")
    ap.add_argument("--layers", type=int, default=LAYERS)
    ap.add_argument("--head", action="store_true", help="--run: also the lm_head at every recorded position")
    ap.add_argument("--tokens", type=Path)
    ap.add_argument("--positions", default="0")
    ap.add_argument("--embedding-npz", type=Path)
    ap.add_argument("--check-token0-preload", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.prep:
        cmd_prep(a)
    elif a.run:
        cmd_run(a)
    else:
        import torch
        print(json.dumps(selftest(torch_golden(torch.device("cuda"))), indent=1))


if __name__ == "__main__":
    main()
