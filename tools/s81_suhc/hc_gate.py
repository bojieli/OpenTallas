#!/usr/bin/env python3
"""Exact gate + throughput bench of the S81 HC die master dsfd_sp_hc (stream s81-suhc-1011, 2026-10-11).

One RUN drives the master through its dsfd_sp_ctrl engine adapter (controller-clock command pulses, QD 8 credits,
the stage sequencer's decoupled issue) with a 20-job program over two job slots (two users' layers interleaved):

    GAIN_LOAD x4 (attn / ffn gain of each chain)
    H_LOAD   slot 0, slot 1               (stage entry: h from the VM, BF16 packed)
    COEF + NORM(QUANT) attn, slot 0 / 1   (hc_pre -> RMSNorm -> FP8 act-quant = attn.quant)
    POST attn, slot 0 / 1                 (hc_post in place, y on the direct collective bus)
    COEF + NORM(QUANT + Y) ffn, slot 0 / 1(= ffn.norm.scale + ffn.quant)
    POST ffn, slot 0 / 1
    H_STORE slot 0 / 1                    (stage exit)

The expected VM image is the CPU golden (tools/hdc_golden_v41: hc_pre mix, rmsnorm_bf16, quant_fp8 / qdq_fp8 through
rtl_hdc_v41_blockdot_campaign.aq_expect, the hc_post lowering order of tools/dsrom_su_hcpost.golden) chained across
the two blocks: the FFN block reads the h the attention hc_post produced, and H_STORE returns the h of the next
layer.  Golden runs use the 1M token's real operands (su_cases pickle: L0 / L2 attn + ffn hc_pre_norm and hc_post
cases; the chain replay is asserted equal to every check the pickle holds); stress runs use random operands with
signed zeros, subnormals and wide exponents.

    python3 tools/s81_suhc/hc_gate.py prep --cases su_cases.pkl --out DIR [--ng 256]
    python3 tools/s81_suhc/hc_gate.py run  --out DIR [--ng 256] [--mut M] [--amut A] [--fp dpi|rtl]
    python3 tools/s81_suhc/hc_gate.py record --out DIR --rec results/rtl/s81_suhc_20261011/hc_gate.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
F = np.float32
D, HC = 5120, 4
K_HLOAD, K_HSTORE, K_COEF, K_POST, K_NORM, K_GAIN = 0, 1, 2, 3, 4, 5
# VM map (rows)
G_BASE, H_BASE, C_BASE, O_BASE, S_BASE = 0, 1280, 2560, 3072, 6144
HROWS = HC * D * 16 // 512          # 640
GROWS = D // 16                     # 320

RTL = ["rtl/dsrom_sys/s81_suhc/ot_s81_hc_core.sv", "rtl/dsrom_sys/s81_suhc/dsfd_sp_hc.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cpin.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_comb.sv", "rtl/link/ot_fifo_sram_fwft.sv",
       "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
       "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_croot.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crooty.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crootr.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_stree.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_hroot.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cseq.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crx.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_caq.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cntree.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccr.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cpad.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctile.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_pad_split.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_xp.sv",
       "rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv", "rtl/lib/ot_async_fifo.sv", "rtl/lib/ot_reset_sync.sv",
       "rtl/lib/ot_skid_buffer.sv",
       "rtl/hdc/v41x/ot_dsrom_su_hcpost.sv", "rtl/hdc/v41x/ot_dsrom_su_add6.sv", "rtl/hdc/v41x/ot_dsrom_su_norm.sv",
       "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv",
       "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41/ot_hdc_softplus.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv",
       "rtl/hdc/v41/ot_hdc_actquant.sv", "rtl/hdc/v41x/ot_dsrom_aq12.sv", "rtl/hdc/v41x/ot_dsrom_divc.sv"]
FP = dict(
    rtl=["rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
         "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv"],
    dpi=["rtl/test/sim_hdc_v41x_fastfp_dpi.sv", "rtl/test/sim_hdc_v41x_fastfp_wrap.sv",
         "rtl/test/sim_hdc_v41x_fastfp_dpi.cpp", "rtl/test/sim_hdc_fp32_f12_dpi_tops.sv",
         "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv", "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp",
         "rtl/test/sim_hdc_fp32_lat_tops.sv", "rtl/test/sim_hdc_prefix_beh.sv", "rtl/test/sim_dsrom_fp32_add_l6_dpi.sv"])
TB = "rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_master.sv"
VL = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
VERILATOR = str(VL) if VL.exists() else "verilator"


def dpi_rest(obj):
    """The RTL helpers the DPI float models do not replace (f12 cuts / l6 / l7 variants, lzc / ksa / mul24 rows):
    rtl/hdc/ot_hdc_fp32_f12.sv and rtl/hdc/ot_hdc_fastfp.sv minus every module a DPI source defines."""
    dpi_mods = set()
    for s_ in FP["dpi"]:
        if s_.endswith(".sv"):
            dpi_mods |= set(re.findall(r"^module\s+(\w+)", (ROOT / s_).read_text(), re.M))
    out = []
    for src in ("rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fastfp.sv"):
        keep = []
        for blk in re.split(r"(?m)^(?=module\s)", (ROOT / src).read_text()):
            m_ = re.match(r"module\s+(\w+)", blk)
            if not m_ or m_.group(1) not in dpi_mods:
                keep.append(blk)
        f = obj / ("rest_" + Path(src).name)
        f.write_text("".join(keep))
        out.append(f)
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def u32(x):
    return np.asarray(x, F).view(np.uint32)


def f32(b):
    return np.asarray(b, np.uint32).view(F)


def bf16bits(x):
    return (u32(x) >> 16).astype(np.int64)


def pack(vals, width):
    acc = 0
    for i, v in enumerate(vals):
        acc |= (int(v) & ((1 << width) - 1)) << (width * i)
    return acc


# ---------------------------------------------------------------------------------------------------------------- golden
def g_norm(h, pre, w, eps):
    import hdc_golden_v41 as V
    x = V.to_bf16(V.seqsum([V.mul(F(pre[k]), h[k]) for k in range(HC)]))
    return V.rmsnorm_bf16(x, np.asarray(w, F), F(eps))


def g_post(res, y, comb, post):
    import dsrom_su_hcpost as P
    return P.golden(res, y, comb, post).reshape(HC, D)


def g_quant(y):
    import rtl_hdc_v41_blockdot_campaign as BC
    out = []
    for b in np.asarray(y, F).reshape(-1, 32):
        f_, e, codes, _yy = BC.aq_expect(b, False)
        assert f_ == 0
        out.append((e & 0x3FF, codes))
    return out


# ---------------------------------------------------------------------------------------------------------------- image
class Run:
    def __init__(self, ng):
        self.ng, self.n = ng, 4 * ng
        self.nv = D // self.n
        self.vm, self.exp, self.prog, self.y = {}, {}, [], []

    def h_rows(self, h):
        """BF16-packed h: row q = elements 8q .. 8q+7, copy k of element e at 16*((e%8)*4+k)."""
        hb = bf16bits(h)                                       # [4][D]
        assert np.array_equal((u32(h) & 0xFFFF), np.zeros_like(u32(h))), "h not BF16"
        return [pack([hb[k][e] for e in range(8 * q, 8 * q + 8) for k in range(HC)], 16) for q in range(HROWS)]

    def job(self, kind, slot, base, gsel=0, quant=0, yout=0):
        op = len(self.prog)
        arg = (kind << 20) | (gsel << 18) | (yout << 15) | (quant << 14) | base
        self.prog.append((slot << 83) | (arg << 7) | op)

    def norm_rows(self, base, y, quant, yout):
        n, nv = self.n, self.nv
        crows, erows, yrows = n // 64, (n + 1023) // 1024, n // 32
        q = g_quant(y) if quant else None
        for v in range(nv):
            if quant:
                blk = q[v * (n // 32):(v + 1) * (n // 32)]
                for r in range(crows):
                    self.exp[base + v * crows + r] = pack([c for b in blk[2 * r:2 * r + 2] for c in b[1]], 8)
                for r in range(erows):
                    self.exp[base + nv * crows + v * erows + r] = pack([b[0] for b in blk[32 * r:32 * r + 32]], 16)
            if yout:
                yb = bf16bits(y)
                off = base + (nv * (crows + erows) if quant else 0)
                for r in range(yrows):
                    self.exp[off + v * yrows + r] = pack(yb[v * n + 32 * r: v * n + 32 * r + 32], 16)

    def build(self, chains):
        """chains[c] = dict(h, attn=(pre, w, eps, comb, post, y), ffn=(...))"""
        ng = self.ng
        for c, ch in enumerate(chains):
            for b, blk in enumerate(("attn", "ffn")):
                w = u32(ch[blk][1])
                for r in range(GROWS):
                    self.vm[G_BASE + (2 * c + b) * GROWS + r] = pack(w[16 * r:16 * r + 16], 32)
                pre, _w, eps, comb, post, _y = ch[blk]
                self.vm[C_BASE + 4 * c + 2 * b] = pack(u32(np.asarray(comb, F).reshape(-1)), 32)
                self.vm[C_BASE + 4 * c + 2 * b + 1] = pack(list(u32(pre)) + list(u32(post)) + [int(u32([eps])[0])], 32)
            for q, row in enumerate(self.h_rows(ch["h"])):
                self.vm[H_BASE + c * HROWS + q] = row
        for g in range(4):
            self.job(K_GAIN, 0, G_BASE + g * GROWS, gsel=g)
        for c in range(len(chains)):
            self.job(K_HLOAD, c, H_BASE + c * HROWS)
        h = [np.asarray(ch["h"], F).reshape(HC, D) for ch in chains]
        for b, blk in enumerate(("attn", "ffn")):
            for c, ch in enumerate(chains):
                pre, w, eps, comb, post, y = ch[blk]
                quant, yout = 1, (1 if blk == "ffn" else 0)
                base = O_BASE + (2 * c + b) * 512
                self.job(K_COEF, c, C_BASE + 4 * c + 2 * b)
                self.job(K_NORM, c, base, gsel=2 * c + b, quant=quant, yout=yout)
                yn = g_norm(h[c], pre, w, eps)
                ch.setdefault("norm_out", {})[blk] = yn
                self.norm_rows(base, yn, quant, yout)
            for c, ch in enumerate(chains):
                pre, w, eps, comb, post, y = ch[blk]
                self.job(K_POST, c, 0)
                yv = u32(y)
                for bt in range(D // ng):
                    self.y.append(pack(yv[bt * ng:(bt + 1) * ng], 32))
                h[c] = g_post(h[c], np.asarray(y, F), np.asarray(comb, F).reshape(HC, HC), np.asarray(post, F))
                ch.setdefault("h_out", {})[blk] = h[c]
        for c in range(len(chains)):
            self.job(K_HSTORE, c, S_BASE + c * HROWS)
            for q, row in enumerate(self.h_rows(h[c])):
                self.exp[S_BASE + c * HROWS + q] = row

    def build_x(self, chains, h2, y2):
        """POST express epoch program (hier 4): the 20-job program with the POSTs issued straight behind the jobs whose
        beats they depend on or share the bus with -- COEF (a decoy coefficient set, then the real one) -> POST,
        GAIN -> POST, and a second stage entry HLOAD (fresh h) -> POST -> HSTORE."""
        ng = self.ng
        H2_BASE, S2_BASE, CBAD = 8192, 9216, C_BASE + 32
        for c, ch in enumerate(chains):
            for b, blk in enumerate(("attn", "ffn")):
                w = u32(ch[blk][1])
                for r in range(GROWS):
                    self.vm[G_BASE + (2 * c + b) * GROWS + r] = pack(w[16 * r:16 * r + 16], 32)
                pre, _w, eps, comb, post, _y = ch[blk]
                self.vm[C_BASE + 4 * c + 2 * b] = pack(u32(np.asarray(comb, F).reshape(-1)), 32)
                self.vm[C_BASE + 4 * c + 2 * b + 1] = pack(list(u32(pre)) + list(u32(post)) + [int(u32([eps])[0])], 32)
            for q, row in enumerate(self.h_rows(ch["h"])):
                self.vm[H_BASE + c * HROWS + q] = row
        pre0, _w0, eps0, comb0, post0, _y0 = chains[0]["attn"]
        self.vm[CBAD] = pack(u32(np.asarray(comb0, F).reshape(-1) * F(-3.0) + F(0.5)), 32)
        self.vm[CBAD + 1] = pack(list(u32(np.asarray(pre0, F) + F(1.0))) + list(u32(np.asarray(post0, F) * F(7.0) + F(1.0))) +
                                 [int(u32([eps0])[0])], 32)
        for q, row in enumerate(self.h_rows(h2)):
            self.vm[H2_BASE + q] = row
        for g in range(4):
            self.job(K_GAIN, 0, G_BASE + g * GROWS, gsel=g)
        for c in range(len(chains)):
            self.job(K_HLOAD, c, H_BASE + c * HROWS)
        h = [np.asarray(ch["h"], F).reshape(HC, D) for ch in chains]

        def post(c, blk):
            pre, w, eps, comb, post_, y = chains[c][blk]
            self.job(K_POST, c, 0)
            yv = u32(y)
            for bt in range(D // ng):
                self.y.append(pack(yv[bt * ng:(bt + 1) * ng], 32))
            h[c] = g_post(h[c], np.asarray(y, F), np.asarray(comb, F).reshape(HC, HC), np.asarray(post_, F))

        for b, blk in enumerate(("attn", "ffn")):
            for c, ch in enumerate(chains):
                pre, w, eps, comb, post_, y = ch[blk]
                quant, yout = 1, (1 if blk == "ffn" else 0)
                base = O_BASE + (2 * c + b) * 512
                self.job(K_COEF, c, C_BASE + 4 * c + 2 * b)
                self.job(K_NORM, c, base, gsel=2 * c + b, quant=quant, yout=yout)
                self.norm_rows(base, g_norm(h[c], pre, w, eps), quant, yout)
            if b == 0:
                self.job(K_COEF, 0, CBAD)                       # decoy set into slot 0 ...
                self.job(K_COEF, 0, C_BASE)                     # ... replaced by the real one, POST straight behind
                post(0, blk)
                self.job(K_GAIN, 0, G_BASE, gsel=0)             # gain beats on the bus the POST y beats use
                post(1, blk)
            else:
                post(0, blk)
                post(1, blk)
        for c in range(len(chains)):
            self.job(K_HSTORE, c, S_BASE + c * HROWS)
            for q, row in enumerate(self.h_rows(h[c])):
                self.exp[S_BASE + c * HROWS + q] = row
        # second stage entry on slot 0: fresh h, POST straight behind its HLOAD
        self.job(K_COEF, 0, C_BASE)
        self.job(K_HLOAD, 0, H2_BASE)
        self.job(K_POST, 0, 0)
        yv = u32(y2)
        for bt in range(D // ng):
            self.y.append(pack(yv[bt * ng:(bt + 1) * ng], 32))
        hx = g_post(np.asarray(h2, F).reshape(HC, D), np.asarray(y2, F), np.asarray(comb0, F).reshape(HC, HC),
                    np.asarray(post0, F))
        self.job(K_HSTORE, 0, S2_BASE)
        for q, row in enumerate(self.h_rows(hx)):
            self.exp[S2_BASE + q] = row

    def write(self, d: Path, meta):
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "vm.mem", "w") as f:
            for a in sorted(self.vm):
                f.write(f"@{a:x}\n{self.vm[a]:0128x}\n")
        with open(d / "expa.mem", "w") as fa, open(d / "expd.mem", "w") as fd:
            for a in sorted(self.exp):
                fa.write(f"{a:04x}\n")
                fd.write(f"{self.exp[a]:0128x}\n")
        (d / "prog.mem").write_text("".join(f"{p:021x}\n" for p in self.prog))
        (d / "y.mem").write_text("".join(f"{v:0{self.ng * 8}x}\n" for v in self.y))
        (d / "n.mem").write_text(f"{len(self.prog):08x}\n{len(self.exp):08x}\n{len(self.y):08x}\n")
        (d / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")


def chains_golden(cases):
    by = {c["name"]: c for c in cases["cases"]}
    out = []
    for L in ("L0", "L2"):
        pn = {b: by[f"{L}.hc_pre_norm.{b}"] for b in ("attn", "ffn")}
        hp = {b: by[f"{L}.hc_post.{b}"] for b in ("attn", "ffn")}
        h0 = dict(pn["attn"]["init"])[64].reshape(HC, D)
        ch = dict(h=h0, src=L)
        for b in ("attn", "ffn"):
            c = pn[b]
            img = dict(c["init"])
            pre = img[20544]
            ro_, so = c["ops"][3], c["ops"][4]
            eps = f32([ro_["imm2"]])[0]
            w = f32(c["cr_lo"][so["cbase"]:so["cbase"] + D])
            pimg = dict(hp[b]["init"])
            ch[b] = (pre, w, eps, pimg[25664].reshape(HC, HC), pimg[25680], pimg[20544])
            ch[b + "_checks"] = (c["checks"], hp[b]["checks"], img[64].reshape(HC, D), pimg[64].reshape(HC, D))
        out.append(ch)
    return out


def chains_stress(rng, kinds):
    import hdc_golden_v41 as V
    out = []
    for t in kinds:
        h = V.to_bf16((rng.standard_normal((HC, D)) * [1.0, 37.0, 1e-3, 0.5][t % 4]).astype(F))
        m = rng.random((HC, D))
        h[m < 0.04] = F(0.0)
        h[(m > 0.04) & (m < 0.06)] = F(-0.0)
        if t >= 2:
            h = V.to_bf16((h * F(2.0) ** rng.integers(-60, 40, size=(HC, D)).astype(F)).astype(F))
        ch = dict(h=h, src=f"stress{t}")
        for b in ("attn", "ffn"):
            pre = (rng.random(HC) * 1.5).astype(F)
            w = V.to_bf16((rng.standard_normal(D) * 0.3 + 1.0).astype(F))
            y = V.to_bf16((rng.standard_normal(D) * [0.5, 8.0, 0.01, 2.0][t % 4]).astype(F))
            y[rng.random(D) < 0.03] = F(-0.0)
            comb = rng.random((HC, HC)).astype(F)
            post = (rng.random(HC) * 2).astype(F)
            ch[b] = (pre, w, F(1e-6), comb, post, y)
        out.append(ch)
    return out


def cmd_prep(a):
    out = Path(a.out)
    rows = []
    cases = pickle.loads(Path(a.cases).read_bytes())
    gold = chains_golden(cases)
    runs = [("golden_L0_L2", gold)]
    rng = np.random.default_rng(20261011)
    runs += [(f"stress_{i}", chains_stress(rng, [2 * i, 2 * i + 1])) for i in range(2)]
    for name, chs in runs:
        r = Run(a.ng)
        r.build(chs)
        # golden runs: the chain replay equals every check the 1M case set holds
        checked = 0
        for ch in chs:
            if "attn_checks" not in ch:
                continue
            for b in ("attn", "ffn"):
                nck, pck, h_in_norm, h_in_post = ch[b + "_checks"]
                (_l, _a, bits, _k), = nck
                assert np.array_equal(u32(ch["norm_out"][b]), np.asarray(bits, np.uint32)), (ch["src"], b, "norm")
                (_l, _a, bits, _k), = pck
                assert np.array_equal(u32(ch["h_out"][b]).reshape(-1), np.asarray(bits, np.uint32)), (ch["src"], b, "post")
                checked += 2
            # the chain is the token's own: the ffn norm's h == the attn hc_post output, next layer's h == ffn output
            ch["chain_consistent_attn_to_ffn"] = bool(np.array_equal(u32(ch["h_out"]["attn"]), u32(ch["ffn_checks"][2])))
        meta = dict(run=name, ng=a.ng, jobs=len(r.prog), exp_rows=len(r.exp), y_beats=len(r.y), golden_checks=checked,
                    chains=[dict(src=c["src"], attn_to_ffn_consistent=c.get("chain_consistent_attn_to_ffn")) for c in chs],
                    cases_sha256=sha(a.cases))
        r.write(out / "runs" / name, meta)
        rows.append(meta)
        print(name, meta["jobs"], "jobs", meta["exp_rows"], "rows", "checks", checked, meta["chains"])
    (out / "runs.json").write_text(json.dumps(dict(runs=rows), indent=1) + "\n")
    return 0


def cmd_prepx(a):
    """Add the POST express epoch run (random operands, no case pickle) to an existing fixture."""
    import hdc_golden_v41 as V
    out = Path(a.out)
    rng = np.random.default_rng(20261013)
    chs = chains_stress(rng, [0, 3])
    h2 = V.to_bf16((rng.standard_normal((HC, D)) * 2.0).astype(F))
    y2 = V.to_bf16((rng.standard_normal(D) * 0.7).astype(F))
    r = Run(a.ng)
    r.build_x(chs, h2, y2)
    meta = dict(run="express_epoch", ng=a.ng, jobs=len(r.prog), exp_rows=len(r.exp), y_beats=len(r.y), golden_checks=0,
                chains=[dict(src=c["src"], attn_to_ffn_consistent=None) for c in chs], cases_sha256=None,
                program="COEF decoy -> COEF -> POST, GAIN -> POST, HLOAD -> POST adjacency")
    r.write(out / "runs" / "express_epoch", meta)
    rj = out / "runs.json"
    rows = json.loads(rj.read_text())["runs"] if rj.exists() else []
    rows = [x for x in rows if x["run"] != "express_epoch"] + [meta]
    rj.write_text(json.dumps(dict(runs=rows), indent=1) + "\n")
    print("express_epoch", meta["jobs"], "jobs", meta["exp_rows"], "rows", meta["y_beats"], "y beats")
    return 0


# ---------------------------------------------------------------------------------------------------------------- run
HCG = re.compile(r"HCG jobs=(\d+) done=(\d+) err=(\d+) rows=(\d+) fault=(\d+) code=(\d+) cyc=(\d+) bad_tag=(\d+)")
JOB = re.compile(r"HCJ op=(\d+) kind=(\d+) start=(\d+) done=(\d+)")


def build(out: Path, ng, fp, mut, amut, lvm, hier=0, cnl_pin=0, chain_step=4, lane_specialize=0, xmut=0):
    # hier: 1 = root split + column chains of octet sub-tiles; 2 = the structural variant (half-octet sub-tiles, split
    # column roots)
    # 4 = hier 2 + the POST express (accept point at the corridor midpoint, head / corridor / tail as hier 3)
    tag = f"ng{ng}_{fp}_m{mut}_a{amut}" + {0: "", 1: "_hier", 2: "_hier2", 3: "_hier3tail", 4: "_hier4xp"}[hier]
    tag += f"_cp{cnl_pin}_cs{chain_step}_ls{lane_specialize}" + (f"_x{xmut}" if hier == 4 else "")
    obj = out / f"build_{tag}"
    exe = obj / "Vtb_s81_hc_master"
    if not exe.exists():
        obj.mkdir(parents=True, exist_ok=True)
        srcs = [ROOT / s for s in FP[fp] + RTL + [TB]]
        if fp == "dpi":
            srcs = dpi_rest(obj) + srcs
        cmd = [VERILATOR, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module", "tb_s81_hc_master",
               "-Mdir", str(obj), "-j", "16", "--unroll-count", "4", "-fno-dfg", f"-GNG={ng}", f"-GMUT={mut}",
               f"-GLANE_SPECIALIZE={lane_specialize}", f"-GCNL_PIN={cnl_pin}", f"-GCHAIN_STEP={chain_step}", f"-GAMUT={amut}", f"-GLVM={lvm}", f"-GHIER={min(hier, 1)}", f"-GHALF={int(hier >= 2)}", f"-GCSPLIT={int(hier >= 2)}", f"-GTAIL_SPLIT={2 if hier == 3 else 0}", f"-GXP={int(hier == 4)}", f"-GXMUT={xmut}", f"-GHEAD_ROWS={10 if ng == 256 else 2}", *map(str, srcs), "-CFLAGS", "-O1"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"build_{tag}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr)
        if r.returncode != 0:
            sys.exit(f"build failed: {out}/build_{tag}.log")
    return exe, tag


def cmd_run(a):
    out = Path(a.out).resolve()
    exe, tag = build(out, a.ng, a.fp, a.mut, a.amut, a.lvm, a.hier, a.cnl_pin, a.chain_step, a.lane_specialize, a.xmut)
    res = []
    for meta in json.loads((out / "runs.json").read_text())["runs"]:
        d = out / "runs" / meta["run"]
        r = subprocess.run([str(exe)] + a.plusarg, cwd=d, capture_output=True, text=True)
        if a.plusarg:
            (out / f"log_{tag}_{meta['run']}.txt").write_text(r.stdout + r.stderr)
        m = HCG.search(r.stdout)
        jobs = [dict(op=int(x[0]), kind=int(x[1]), start=int(x[2]), done=int(x[3])) for x in JOB.findall(r.stdout)]
        if not m:
            res.append(dict(run=meta["run"], ok=False, tail=(r.stdout + r.stderr)[-3000:]))
            print(meta["run"], "NO RESULT", flush=True)
            continue
        g = list(map(int, m.groups()))
        row = dict(run=meta["run"], jobs=g[0], done=g[1], err_rows=g[2], rows=g[3], fault=g[4], fault_code=g[5],
                   cycles=g[6], bad_tag=g[7], ok=("HCG PASS" in r.stdout), job_cycles=jobs,
                   mismatches=[x for x in r.stdout.splitlines() if "mismatch" in x][:5])
        res.append(row)
        print(meta["run"], "PASS" if row["ok"] else "FAIL", row["err_rows"], "/", row["rows"], "fault", row["fault"],
              "cyc", row["cycles"], flush=True)
    rec = dict(schema="opentallas.s81_suhc.hc_gate.run.v1", generated_utc=datetime.datetime.utcnow().isoformat() + "Z",
               ng=a.ng, fp=a.fp, mut=a.mut, amut=a.amut, lvm=a.lvm, hier=a.hier, xmut=a.xmut, cnl_pin=a.cnl_pin, chain_step=a.chain_step, lane_specialize=a.lane_specialize, runs=res,
               status="pass" if res and all(x["ok"] for x in res) else "fail",
               simulator=subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={s: sha(ROOT / s) for s in FP[a.fp] + RTL + [TB]})
    (out / f"run_{tag}.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("RUN", tag, rec["status"])
    return 0 if rec["status"] == "pass" else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prep")
    p.add_argument("--cases", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ng", type=int, default=256)
    p = sp.add_parser("prepx")
    p.add_argument("--out", required=True)
    p.add_argument("--ng", type=int, default=256)
    p = sp.add_parser("run")
    p.add_argument("--out", required=True)
    p.add_argument("--ng", type=int, default=256)
    p.add_argument("--fp", default="dpi")
    p.add_argument("--mut", type=int, default=0)
    p.add_argument("--amut", type=int, default=0)
    p.add_argument("--lvm", type=int, default=10)
    p.add_argument("--hier", type=int, default=0, help="1: hierarchical slab (root tile + 3 column chains of 1-octet sub-tiles)")
    p.add_argument("--cnl-pin", type=int, default=0)
    p.add_argument("--chain-step", type=int, default=4)
    p.add_argument("--lane-specialize", type=int, default=0)
    p.add_argument("--xmut", type=int, default=0, help="POST express negative control (hier 4)")
    p.add_argument("--plusarg", action="append", default=[], help="simulator plusarg, e.g. +HC_XGEOM")
    a = ap.parse_args()
    return dict(prep=cmd_prep, prepx=cmd_prepx, run=cmd_run)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
