#!/usr/bin/env python3
"""DS-ROM recovery lever su_norm: the fused 1.2 GHz RMSNorm chains (rtl/hdc/v41x/ot_dsrom_su_norm.sv) measured on
the golden 1M operands of every representative layer (the SU case set of tools/dsrom_1m_su.py: L0 / L3 / L20 / L24
and the head) plus random stress rows, bit-exact against the golden (tools/hdc_golden_v41, R-ARITH chunk8).

Variants (dedicated units, one per chain; the q and kv chains run in parallel after a_allgather, so they are separate
units):
  hc  N 1,024  D 5,120  HC 1  QUANT 1          attn|ffn|head: hc_pre -> norm.{sumsq,rsqrt,scale} -> quant
  q   N   256  D 1,280  HC 0  QUANT 1          attn.q_norm.* -> q_quant
  kv  N   512  D   512  HC 0  RD 64  QUANT 1   attn.kv_norm.* -> kv_rope_qdq (RoPE tail + FP8 QDQ)
The lane counts are the ones that minimise each chain's latency (stream + tree + vector levels).  Wire: the hub
traverse is charged once a chain, HUB_IN 33 / HUB_OUT 23 fast stages (22 / 15 slow stages x 748/504 um reach),
plus RW 9 result-wire and BW 9 broadcast-wire stages between the lanes' tree and the scalar tail.

    python3 tools/dsrom_su_norm.py prep   --cases su_cases.pkl --out DIR
    python3 tools/dsrom_su_norm.py run    --out DIR --variant hc|q|kv --fp dpi|rtl [--n N]
    python3 tools/dsrom_su_norm.py record --out DIR [--record results/rtl/dsrom_recovery_20261004/su_norm/measure.json]
    python3 tools/dsrom_su_norm.py divc   --out DIR      # exhaustive check of the constant divider
    python3 tools/dsrom_su_norm.py screen --work DIR [--top T] [--sources a,b] [--param K=V ...]
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

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
F = np.float32
FAST = 1.2e9
HUB_IN, HUB_OUT, RW, BW = 33, 23, 9, 9
VARIANTS = dict(hc=dict(N=1024, D=5120, HC=1, RD=0, QUANT=1), q=dict(N=256, D=1280, HC=0, RD=0, QUANT=1),
                kv=dict(N=512, D=512, HC=0, RD=64, QUANT=1))
RTL = ROOT / "rtl/hdc/v41x/ot_dsrom_su_norm.sv"
TB = ROOT / "rtl/test/tb_dsrom_su_norm.sv"
COMMON = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
          "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv",
          "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41/ot_hdc_softplus.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv",
          "rtl/hdc/v41/ot_hdc_actquant.sv", "rtl/hdc/v41x/ot_dsrom_aq12.sv",
          "rtl/hdc/v41x/ot_dsrom_divc.sv"]
FP_L6 = dict(rtl="rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv", dpi="rtl/test/sim_dsrom_fp32_add_l6_dpi.sv")
FP_SRC = dict(
    rtl=["rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
         "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv"],
    dpi=["rtl/test/sim_hdc_v41x_fastfp_dpi.sv", "rtl/test/sim_hdc_v41x_fastfp_wrap.sv",
         "rtl/test/sim_hdc_v41x_fastfp_dpi.cpp", "rtl/test/sim_hdc_fp32_f12_dpi_tops.sv",
         "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv", "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp",
         "rtl/test/sim_hdc_fp32_lat_tops.sv", "rtl/test/sim_hdc_prefix_beh.sv"])
VL = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
VERILATOR = str(VL) if VL.exists() else "verilator"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def u32(x):
    return np.asarray(x, dtype=F).reshape(-1).view(np.uint32)


def f32(b):
    return np.asarray(b, dtype=np.uint32).view(F)


def wmem(path, words, bits=32):
    with open(path, "w") as f:
        for w in words:
            f.write(f"{int(w):0{bits // 4}x}\n")


def hexw(ints, width):
    acc = 0
    for i, v in enumerate(ints):
        acc |= (int(v) & ((1 << width) - 1)) << (width * i)
    return acc


# ---------------------------------------------------------------------------------------------------------------------
def golden_row(kind, x, pre, w, eps, cs=None):
    """(normalised row, RoPE row or None) by the golden's own functions."""
    import hdc_golden_v41 as V
    D = len(w)
    if kind == "hc":
        h = np.asarray(x, F).reshape(4, D)
        xr = V.to_bf16(V.seqsum([V.mul(F(pre[k]), h[k]) for k in range(4)]))
    else:
        xr = np.asarray(x, F)
    y = V.rmsnorm_bf16(xr, np.asarray(w, F), F(eps))
    ro = V.rope_tail(y, cs) if cs is not None else None
    return y, ro


def write_case(d: Path, kind, x, pre, w, eps, y, ro, meta):
    import rtl_hdc_v41_blockdot_campaign as BC
    d.mkdir(parents=True, exist_ok=True)
    D = len(w)
    wmem(d / "x.mem", u32(x))
    wmem(d / "w.mem", u32(w))
    cfg = list(u32(np.asarray(pre, F))) + [u32([F(D)])[0], u32([F(eps)])[0]]
    wmem(d / "cfg.mem", cfg)
    wmem(d / "ey.mem", u32(y))
    qsrc = y
    if ro is not None:
        wmem(d / "er.mem", u32(ro))
        wmem(d / "cs.mem", list(u32(meta["cos"])) + list(u32(meta["sin"])))
        qsrc = ro
    qc, qe, qy = [], [], []
    for b in np.asarray(qsrc, F).reshape(-1, 32):
        f_, e, codes, yy = BC.aq_expect(b, False)
        assert f_ == 0
        qc.append(hexw(codes, 8))
        qe.append(e & 0xFFFF)
        qy.append(hexw(yy, 16))
    wmem(d / "eqc.mem", qc, 256)
    wmem(d / "eqe.mem", qe, 16)
    wmem(d / "eqy.mem", qy, 512)


def cmd_prep(a):
    import hdc_golden_v41 as V
    out = Path(a.out)
    d = pickle.loads(Path(a.cases).read_bytes())
    rows = []
    for c in d["cases"]:
        fn, name = c["meta"]["fn"], c["name"]
        if fn not in ("hc_pre_norm", "q_norm", "kv_norm_rope"):
            continue
        ops = c["ops"]
        if fn == "hc_pre_norm":
            kind = "hc"
            x, pre = c["init"][0][1], c["init"][1][1]
            ro_, so = ops[3], ops[4]
        else:
            kind = "q" if fn == "q_norm" else "kv"
            x, pre = c["init"][0][1], np.zeros(4, F)
            ro_, so = ops[1], ops[2]
        eps = f32([ro_["imm2"]])[0]
        n = f32([ro_["imm1"]])[0]
        D = len(x) // (4 if kind == "hc" else 1)
        assert n == F(D), (name, n, D)
        w = f32(c["cr_lo"][so["cbase"]:so["cbase"] + D])
        cs = None
        meta = {}
        if kind == "kv":
            rp = ops[3]
            cos = f32(c["cr_lo"][rp["bbase"]:rp["bbase"] + 32])
            sin = f32(c["cr_hi"][rp["bbase"]:rp["bbase"] + 32])
            cs = (cos, sin)
            meta = dict(cos=cos, sin=sin)
        y, ro = golden_row(kind, x, pre, w, eps, cs)
        want = {lab: f32(bits) for lab, _ad, bits, _k in c["checks"]}
        lab0 = list(want)[0]
        assert np.array_equal(u32(y), u32(want[lab0])), (name, "golden replay != SU case check")
        if kind == "kv":
            assert np.array_equal(u32(ro[-64:]), u32(want[list(want)[1]])), (name, "rope")
        write_case(out / "cases" / name, kind, x, pre, w, eps, y, ro, meta)
        rows.append(dict(case=name, kind=kind, layer=c["meta"]["layer"], D=D, source="golden 1M (su_cases.pkl)",
                         check_label=lab0))
    # random stress rows: specials (zeros, subnormals, negative zero, wide magnitudes), reduction-order sensitivity
    rng = np.random.default_rng(20261004)
    for kind, nrow in (("hc", 6), ("q", 6), ("kv", 6)):
        D = VARIANTS[kind]["D"]
        for t in range(nrow):
            scale = [1.0, 1e-3, 37.0, 1e-20, 3e3, 0.5][t]
            xs = (rng.standard_normal(D * (4 if kind == "hc" else 1)) * scale).astype(F)
            m = rng.random(len(xs))
            xs[m < 0.05] = F(0.0)
            xs[(m > 0.05) & (m < 0.08)] = F(-0.0)
            xs[(m > 0.08) & (m < 0.10)] = f32(rng.integers(1, 1 << 23, int(((m > 0.08) & (m < 0.10)).sum()), dtype=np.uint32))
            if kind != "hc":
                xs = V.to_bf16(xs)          # q / kv latents are BF16 values
            pre = (rng.standard_normal(4) * 0.7).astype(F) if kind == "hc" else np.zeros(4, F)
            w = (rng.standard_normal(D) * 0.3 + 1.0).astype(F)
            if kind == "hc":
                w = V.to_bf16(w)
            eps = F(1e-6)
            cs, meta = None, {}
            if kind == "kv":
                ang = rng.random(32) * 6.28
                cs = (np.cos(ang).astype(F), np.sin(ang).astype(F))
                meta = dict(cos=cs[0], sin=cs[1])
            y, ro = golden_row(kind, xs, pre, w, eps, cs)
            if not np.all(np.isfinite(y)):
                continue
            name = f"stress.{kind}.{t}"
            write_case(out / "cases" / name, kind, xs, pre, w, eps, y, ro, meta)
            rows.append(dict(case=name, kind=kind, layer="stress", D=D, source=f"random seed 20261004 row {t} scale {scale}"))
    (out / "cases.json").write_text(json.dumps(dict(cases=rows, cases_pkl_sha256=sha(a.cases)), indent=1) + "\n")
    print("cases", len(rows))
    return 0


# ---------------------------------------------------------------------------------------------------------------------
SUN = re.compile(r"SUN go=(-?\d+) y_last=(-?\d+) r=(-?\d+) ro_last=(-?\d+) q_last=(-?\d+) ey=(\d+) er=(\d+) eq=(\d+) "
                 r"checked_y=(\d+) checked_r=(\d+) checked_q=(\d+) fault=(\d+)")


def build(out: Path, variant, fp, n, rxs=0, la=4, sxc=0):
    p = dict(VARIANTS[variant], N=n or VARIANTS[variant]["N"])
    if rxs:
        p["RXS"] = rxs
    if la != 4:
        p["LA"] = la
    if sxc:
        p["SXC"] = sxc
    tag = (f"{variant}_{fp}_N{p['N']}" + (f"_rxs{rxs}" if rxs else "") + (f"_la{la}" if la != 4 else "")
           + (f"_sxc{sxc}" if sxc else ""))
    obj = out / f"build_{tag}"
    exe = obj / "Vtb_dsrom_su_norm"
    if not exe.exists():
        srcs = [ROOT / s for s in COMMON + FP_SRC[fp] + [FP_L6[fp]]] + [RTL, TB]
        cmd = [VERILATOR, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module", "tb_dsrom_su_norm",
               "-Mdir", str(obj), "-j", "16", "--unroll-count", "4", "-fno-dfg",
               *[f"-G{k}={v}" for k, v in p.items()], f"-GRW={RW}", f"-GBW={BW}", f"-GHUB_IN={HUB_IN}",
               f"-GHUB_OUT={HUB_OUT}", *map(str, srcs), "-CFLAGS", "-O1"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"build_{tag}.log").write_text(r.stdout + r.stderr)
        if r.returncode != 0:
            sys.exit(f"build failed: {out}/build_{tag}.log")
    return exe, p, tag


def cmd_run(a):
    out = Path(a.out)
    exe, p, tag = build(out, a.variant, a.fp, a.n, a.rxs, a.la, a.sxc)
    cases = [c for c in json.loads((out / "cases.json").read_text())["cases"] if c["kind"] == a.variant]
    rows = []
    for c in cases:
        r = subprocess.run([str(exe)], cwd=out / "cases" / c["case"], capture_output=True, text=True)
        m = SUN.search(r.stdout)
        if not m:
            rows.append(dict(c, ok=False, stdout=r.stdout[-2000:], stderr=r.stderr[-2000:]))
            print(c["case"], "NO RESULT", flush=True)
            continue
        g = list(map(int, m.groups()))
        row = dict(c, y_last=g[1], r=g[2], ro_last=g[3], q_last=g[4], err_y=g[5], err_ro=g[6], err_q=g[7],
                   checked_y=g[8], checked_ro=g[9], checked_q=g[10], fault=g[11], ok="PASS" in r.stdout,
                   mismatches=[x for x in r.stdout.splitlines() if "mismatch" in x][:5])
        rows.append(row)
        print(c["case"], row["ok"], row["y_last"], row["ro_last"], row["q_last"], flush=True)
    res = dict(schema="opentallas.dsrom-recovery.su-norm.run.v1", generated_utc=now(), variant=a.variant, fp=a.fp,
               params=dict(p, RW=RW, BW=BW, HUB_IN=HUB_IN, HUB_OUT=HUB_OUT), rows=rows,
               status="pass" if rows and all(r["ok"] for r in rows) else "fail",
               simulator=subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={str(Path(s)): sha(ROOT / s) for s in COMMON + FP_SRC[a.fp] + [FP_L6[a.fp]] +
                              [str(RTL.relative_to(ROOT)), str(TB.relative_to(ROOT))]})
    (out / f"run_{tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    print("RUN", tag, res["status"])
    return 0 if res["status"] == "pass" else 1


# ---------------------------------------------------------------------------------------------------------------------
def vector_levels(nv, la=4):
    """Cycles from the FIRST vector sum to the row's sum: the golden's top tree over nv vector sums (one a cycle)
    padded to a power of two; a node whose right subtree is padding passes (x + 0 = x), an add costs la."""
    t = {i: float(i) for i in range(nv)}
    width = 1
    while width < nv:
        width *= 2
    level = [t.get(i) for i in range(width)]
    while len(level) > 1:
        level = [(max(a, b) + la if b is not None else a) if a is not None else None
                 for a, b in zip(level[0::2], level[1::2])]
    return int(level[0])


def floor_terms(v, la=4, rxs=0, sxc=0):
    """The fused chain's floor in 1.2 GHz cycles: the golden op DAG's longest path on dedicated f12 units at the
    variant's lane count (the stream and vector-level terms are the width trade), plus the wire charged once and the
    vector-memory read (accept) cycle."""
    p = VARIANTS[v]
    LM, LA = 5, la
    LAV = LA if LA >= 5 else LA + 1
    nv = -(-p["D"] // p["N"])
    lt = (p["N"] // 8).bit_length() - 1
    t = dict(vm_read=1, hub_in=HUB_IN)
    if p["HC"]:
        t["mix_4mul_3add_rnd"] = LM + 3 * LA + 1
    t.update(square=LM, chunk_chain_7add=7 * LA, tree_in_vector=lt * LA,
             stream_and_vector_levels=vector_levels(nv, LAV), result_wire=RW, divide_by_D_divc=9, add_eps=LA,
             rsqrt=1 + 3 * (3 * LM + LA), broadcast_wire=BW, scale_stream=nv - 1, scale_mul_mul_rnd=2 * (LM + sxc) + 1)
    if p["RD"]:
        t["rope_mul6_add5_rnd"] = rxs + (LM + 1) + LAV + 1
    if p["QUANT"]:
        t["actquant_aq12"] = 18
    t["hub_out"] = HUB_OUT
    return t


NODES = {   # variant -> [(graph node key, event, covers)]
    "hc": [("*.attn.quant", "q_last", ["*.attn.hc_pre", "*.attn.norm.sumsq", "*.attn.norm.rsqrt", "*.attn.norm.scale"]),
           ("*.ffn.norm.scale", "y_last", ["*.ffn.hc_pre", "*.ffn.norm.sumsq", "*.ffn.norm.rsqrt"]),
           ("*.ffn.quant", "q_after_y", []),
           ("head.norm.scale", "y_last", ["head.hc_pre", "head.norm.sumsq", "head.norm.rsqrt"])],
    "q": [("*.attn.q_quant", "q_last", ["*.attn.q_norm.sumsq", "*.attn.q_norm.rsqrt", "*.attn.q_norm.scale"])],
    "kv": [("*.attn.kv_rope_qdq", "q_last", ["*.attn.kv_norm.sumsq", "*.attn.kv_norm.rsqrt", "*.attn.kv_norm.scale"])],
}


def cmd_record(a):
    out = Path(a.out)
    runs = {}
    for f in sorted(out.glob("run_*.json")):
        r = json.loads(f.read_text())
        if (r["params"].get("LA", 4), r["params"].get("RXS", 0), r["params"].get("SXC", 0)) != (a.la, a.rxs, a.sxc):
            continue
        runs[f"{r['variant']}_{r['fp']}_N{r['params']['N']}"] = r
    meas = {}
    for v, p in VARIANTS.items():
        full = runs[f"{v}_dpi_N{p['N']}"]
        rtl = runs[f"{v}_rtl_N64"]
        ok = full["status"] == "pass" and rtl["status"] == "pass"
        gold = [r for r in full["rows"] if r["layer"] != "stress"]
        cyc = {k: sorted({r[k] for r in full["rows"]}) for k in ("y_last", "q_last", "ro_last", "r")}
        assert all(len(x) == 1 for x in cyc.values()), (v, cyc)   # fixed pipeline: data-independent latency
        c = {k: x[0] for k, x in cyc.items()}
        ft = floor_terms(v, a.la, a.rxs, a.sxc)
        meas[v] = dict(params=full["params"], exact=ok, cases_full_shape=len(full["rows"]), golden_cases=len(gold),
                       golden_layers=sorted({r["layer"] for r in gold}), cases_rtl_N64=len(rtl["rows"]),
                       checked_elements_full=sum(r["checked_y"] for r in full["rows"]),
                       checked_quant_blocks_full=sum(r["checked_q"] for r in full["rows"]),
                       cycles=dict(c, q_after_y=c["q_last"] - c["y_last"]),
                       us={k: round(x / FAST * 1e6, 5) for k, x in dict(c, q_after_y=c["q_last"] - c["y_last"]).items()},
                       floor_cycles=sum(ft.values()), floor_terms=ft,
                       residual_over_floor=c["q_last"] - sum(ft.values()) if p["QUANT"] else None)
    res = dict(schema="opentallas.dsrom-recovery.su-norm.measure.v1", generated_utc=now(),
               clock_hz=FAST, add_latency=a.la, wire=dict(HUB_IN=HUB_IN, HUB_OUT=HUB_OUT, RW=RW, BW=BW,
                                        basis="hub traverse once a chain: 22 / 15 slow stages x 748/504 um reach; "
                                              "RW / BW: the reducer's 6 slow cross-lane result stages x 1.5, each way"),
               variants=meas, runs={k: dict(status=r["status"], params=r["params"], fp=r["fp"], rows=len(r["rows"]),
                                            simulator=r["simulator"]) for k, r in runs.items()},
               source_sha256=next(iter(runs.values()))["source_sha256"], tool_sha256=sha(__file__))
    Path(a.record).parent.mkdir(parents=True, exist_ok=True)
    Path(a.record).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({v: dict(cycles=m["cycles"], floor=m["floor_cycles"], exact=m["exact"]) for v, m in meas.items()},
                     indent=1))
    return 0


# ---------------------------------------------------------------------------------------------------------------------
KEEP = "ot_hdc_fp32_add_f12_l4 ot_hdc_fp32_add_f12_l5x ot_hdc_fp32_mul_f12_l5 ot_hdc_fp32_mul_f12_l6"
SCREEN_SRC = [s for s in COMMON + FP_SRC["rtl"]] + [FP_L6["rtl"], str(RTL.relative_to(ROOT))]


def cmd_screen(a):
    """tools/dsrom_reindex_screen.py (pre-layout SS setup 60 ps / FF hold 25 ps at 833 ps) with the 1.2 GHz FP unit
    tops kept as their own hierarchy (ORFS SYNTH_KEEP_MODULES): ABC maps each unit as the standalone unit that closes
    (rtl/hdc/ot_hdc_fp32_f12.sv), instead of re-rippling its keep-prefix adders inside the flattened block.  The
    route (run_abi3_physical --orfs-var SYNTH_KEEP_MODULES=...) uses the same setting."""
    import dsrom_reindex_screen as SC
    orig = SC.cs.CaseSpec

    def spec(*args, **kw):
        kw["extra"] = dict(kw.get("extra", {}), SYNTH_KEEP_MODULES=KEEP)
        return orig(*args, **kw)
    SC.cs.CaseSpec = spec
    argv = ["--top", a.top, "--period-ps", "833", "--work", a.work]
    for x in (a.sources.split(",") if a.sources else SCREEN_SRC):
        argv += ["--source", x]
    for p in a.param or []:
        argv += ["--param", p]
    SC.main(argv)
    return 0


def cmd_divc(a):
    """Exhaustive ot_dsrom_divc check for every D the chains use: all positive finite binary32 x (+ a stride of
    negatives, +-inf, NaN) against C++ float division (rtl/test/tb_dsrom_divc.cpp)."""
    out = Path(a.out)
    rows = []
    for D in (5120, 1280, 512):
        k = (D & -D).bit_length() - 1
        f = D >> k
        obj = out / f"divc_D{D}"
        exe = obj / "Vot_dsrom_divc"
        if not exe.exists():
            r = subprocess.run([VERILATOR, "--cc", "--exe", "--build", "-O3", "-Wno-fatal", "-Wno-WIDTH", "--top-module",
                                "ot_dsrom_divc", f"-GF={f}", f"-GK={k}", "-Mdir", str(obj),
                                str(ROOT / "rtl/hdc/ot_hdc_sfu.sv"), str(ROOT / "rtl/hdc/ot_hdc_delay.sv"),
                                str(ROOT / "rtl/hdc/ot_hdc_fastfp_lat_f12.sv"), str(ROOT / "rtl/hdc/ot_hdc_fp32_f12.sv"),
                                str(ROOT / "rtl/hdc/ot_hdc_fastfp.sv"), str(ROOT / "rtl/hdc/ot_hdc_fp32_mul_lat.sv"),
                                str(ROOT / "rtl/hdc/ot_hdc_fp32_add_lat.sv"), str(ROOT / "rtl/hdc/ot_hdc_prefix.sv"),
                                str(ROOT / "rtl/hdc/v41x/ot_dsrom_divc.sv"), str(ROOT / "rtl/test/tb_dsrom_divc.cpp"),
                                "-CFLAGS", "-O2"], capture_output=True, text=True)
            if r.returncode:
                sys.exit(r.stdout + r.stderr)
        r = subprocess.run([str(exe), str(D)], capture_output=True, text=True)
        m = re.search(r"checked=(\d+) errors=(\d+) faults_ok=(\d+) faults_bad=(\d+)", r.stdout)
        rows.append(dict(D=D, F=f, K=k, checked=int(m.group(1)), errors=int(m.group(2)), faults_ok=int(m.group(3)),
                         faults_bad=int(m.group(4)), passed="PASS" in r.stdout, mismatches=r.stdout.splitlines()[:5]))
        print(rows[-1], flush=True)
    res = dict(schema="opentallas.dsrom-recovery.su-norm.divc.v1", generated_utc=now(), rows=rows,
               scope="every positive finite binary32 x (0 .. 0x7F7FFFFF) + every 4,099th negative + +-inf + NaN",
               status="pass" if all(r["passed"] for r in rows) else "fail",
               simulator=subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={p: sha(ROOT / p) for p in ("rtl/hdc/v41x/ot_dsrom_divc.sv", "rtl/test/tb_dsrom_divc.cpp")})
    (out / "divc.json").write_text(json.dumps(res, indent=1) + "\n")
    print("DIVC", res["status"])
    return 0 if res["status"] == "pass" else 1


def cmd_lever(a):
    """levers/su_norm.json (opentallas.dsrom-recovery.lever.v1) from measure.json and the physical records under
    su_norm/route/ (corner_sta_<unit>.json, routed) and su_norm/screen/ (screen_<unit>.json, pre-layout)."""
    base = ROOT / "results/rtl/dsrom_recovery_20261004"
    m = json.loads((base / "su_norm/measure.json").read_text())
    assert m.get("add_latency") == 6, "lever uses the LA6 (ot_dsrom_fp32_add_f12_l6) measurement"
    V = m["variants"]
    us = lambda c: round(c / FAST * 1e6, 5)                                             # noqa: E731
    src = ("ot_dsrom_su_norm {v} (N {N}, D {D}): {what} {c} cycles at 1.2 GHz from the vector-memory read to the last "
           "{ev} landing at its consumer (hub in 33 / out 23, result + broadcast wire 9 + 9 stages included); bit-exact "
           "on the L0/L3/L20/L24{hd} golden 1M operands + 6 stress rows (Verilator, full shape with DPI FP stand-ins and "
           "N 64 with the bit-level FP RTL); equals its floor")
    nodes = {}

    def put(k, c, text):
        nodes[k] = dict(us=us(c), source=text, cls="measured", kind="fused_fast")

    def cov(ks, by):
        for k in ks:
            nodes[k] = dict(us=0.0, source=f"covered by {by} (one fused ot_dsrom_su_norm pipeline)", cls="measured",
                            kind="fused_fast")
    hc, q, kv = V["hc"], V["q"], V["kv"]
    cov(["*.attn.hc_pre", "*.attn.norm.sumsq", "*.attn.norm.rsqrt", "*.attn.norm.scale"], "attn.quant")
    put("*.attn.quant", hc["cycles"]["q_last"], src.format(v="hc", N=1024, D=5120, what="hc_pre -> RMSNorm -> FP8 "
        "act-quant", c=hc["cycles"]["q_last"], ev="quantised block", hd=""))
    cov(["*.ffn.hc_pre", "*.ffn.norm.sumsq", "*.ffn.norm.rsqrt"], "ffn.norm.scale")
    put("*.ffn.norm.scale", hc["cycles"]["y_last"], src.format(v="hc", N=1024, D=5120, what="hc_pre -> RMSNorm",
        c=hc["cycles"]["y_last"], ev="normalised vector", hd=""))
    put("*.ffn.quant", hc["cycles"]["q_after_y"], "ot_dsrom_su_norm hc: the FP8 act-quant behind the normalised vector "
        f"(ffn.norm.scale): {hc['cycles']['q_after_y']} cycles at 1.2 GHz (ot_dsrom_aq12, 32 instances), exact")
    cov(["head.hc_pre", "head.norm.sumsq", "head.norm.rsqrt"], "head.norm.scale")
    put("head.norm.scale", hc["cycles"]["y_last"], src.format(v="hc", N=1024, D=5120, what="hc_pre -> RMSNorm",
        c=hc["cycles"]["y_last"], ev="normalised vector", hd=" + head"))
    cov(["*.attn.q_norm.sumsq", "*.attn.q_norm.rsqrt", "*.attn.q_norm.scale"], "attn.q_quant")
    put("*.attn.q_quant", q["cycles"]["q_last"], src.format(v="q", N=256, D=1280, what="q RMSNorm -> FP8 act-quant",
        c=q["cycles"]["q_last"], ev="quantised block", hd=""))
    cov(["*.attn.kv_norm.sumsq", "*.attn.kv_norm.rsqrt", "*.attn.kv_norm.scale"], "attn.kv_rope_qdq")
    put("*.attn.kv_rope_qdq", kv["cycles"]["q_last"], src.format(v="kv", N=512, D=512, what="kv RMSNorm -> RoPE tail "
        "-> FP8 QDQ", c=kv["cycles"]["q_last"], ev="QDQ block", hd=""))
    phys = {}
    for f in sorted((base / "su_norm/route").glob("corner_sta_*.json")):
        d = json.loads(f.read_text())
        phys[f.stem[len("corner_sta_"):]] = dict(record=str(f.relative_to(ROOT)), ss_setup_ps=d["setup_ss"]["worst_slack_ps"],
                                                 ff_hold_ps=d["hold_ff"]["worst_slack_ps"])
    scr = {}
    for f in sorted((base / "su_norm/screen").glob("screen_*.json")):
        d = json.loads(f.read_text())
        scr[f.stem[len("screen_"):]] = dict(record=str(f.relative_to(ROOT)), ss_setup_ps=d["ss_setup_wns_ps"],
                                            ff_hold_ps=d["ff_hold_wns_ps"])
    closes = bool(phys) and all(x["ss_setup_ps"] >= 0 and x["ff_hold_ps"] >= 0 for x in phys.values())
    rec = dict(schema="opentallas.dsrom-recovery.lever.v1", lever="su_norm", verdict=a.verdict,
               exact=all(v["exact"] for v in V.values()) and json.loads((base / "su_norm/divc.json").read_text())["status"] == "pass",
               ss_ff=dict(period_ps=833.0, routed=phys, prelayout_screen=scr, closes=closes,
                          basis="routed minimum components (run_abi3_physical asap7, 0.833 ns, SS setup 60 ps / FF hold "
                                "25 ps, FP unit tops kept as hierarchy) + tools/w18/corner_sta.py; pre-layout screens "
                                "listed for reference"),
               nodes=nodes,
               measurement=dict(record="results/rtl/dsrom_recovery_20261004/su_norm/measure.json",
                                old_us_per_occurrence={"attn hc_pre+norm.*+quant": 0.7554, "ffn hc_pre+norm.*": 0.5221,
                                                       "q_norm.*+q_quant": 0.4888, "kv_norm.*+kv_rope_qdq": 0.5099},
                                measured_cycles={k: v["cycles"] for k, v in V.items()},
                                floor_cycles={k: v["floor_cycles"] for k, v in V.items()}),
               default="opt-in: applied only in the recovery baseline; the SU (ot_hdc_v41x_vec) and its lowering are "
                       "unchanged", note=a.note or "")
    out = base / "levers/su_norm.json"
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(verdict=rec["verdict"], exact=rec["exact"], closes=closes, routed=phys), indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("prep", "run", "record", "screen", "divc", "lever"))
    ap.add_argument("--out")
    ap.add_argument("--cases")
    ap.add_argument("--variant", choices=tuple(VARIANTS))
    ap.add_argument("--fp", choices=("dpi", "rtl"), default="dpi")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--rxs", type=int, default=0, help="run: RoPE extra register stage (RTL RXS)")
    ap.add_argument("--sxc", type=int, default=0, help="run: scale multipliers on the operand-cut LM+1 unit (RTL SXC)")
    ap.add_argument("--la", type=int, default=4, help="run: add latency of the unit (RTL LA: 4 = f12_l4, 5 = l5x)")
    ap.add_argument("--top", default="ot_dsrom_su_norm")
    ap.add_argument("--sources", default=None, help="screen: comma list (default: the unit's sources)")
    ap.add_argument("--param", action="append")
    ap.add_argument("--work")
    ap.add_argument("--verdict", default="ADOPT")
    ap.add_argument("--note", default=None)
    ap.add_argument("--record", default=str(ROOT / "results/rtl/dsrom_recovery_20261004/su_norm/measure.json"))
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run, record=cmd_record, screen=cmd_screen, divc=cmd_divc, lever=cmd_lever)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
