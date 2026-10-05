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
          "rtl/hdc/v41/ot_hdc_actquant.sv"]
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


def build(out: Path, variant, fp, n):
    p = dict(VARIANTS[variant], N=n or VARIANTS[variant]["N"])
    tag = f"{variant}_{fp}_N{p['N']}"
    obj = out / f"build_{tag}"
    exe = obj / "Vtb_dsrom_su_norm"
    if not exe.exists():
        srcs = [ROOT / s for s in COMMON + FP_SRC[fp]] + [RTL, TB]
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
    exe, p, tag = build(out, a.variant, a.fp, a.n)
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
               source_sha256={str(Path(s)): sha(ROOT / s) for s in COMMON + FP_SRC[a.fp] +
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


def floor_terms(v):
    """The fused chain's floor in 1.2 GHz cycles: the golden op DAG's longest path on dedicated f12 units at the
    variant's lane count (the stream and vector-level terms are the width trade), plus the wire charged once and the
    vector-memory read (accept) cycle."""
    p = VARIANTS[v]
    LM, LA = 5, 4
    nv = -(-p["D"] // p["N"])
    lt = (p["N"] // 8).bit_length() - 1
    t = dict(vm_read=1, hub_in=HUB_IN)
    if p["HC"]:
        t["mix_4mul_3add_rnd"] = LM + 3 * LA + 1
    t.update(square=LM, chunk_chain_7add=7 * LA, tree_in_vector=lt * LA,
             stream_and_vector_levels=vector_levels(nv, LA), result_wire=RW, divide_by_D=19, add_eps=LA,
             rsqrt=1 + 3 * (3 * LM + LA), broadcast_wire=BW, scale_stream=nv - 1, scale_mul_mul_rnd=2 * LM + 1)
    if p["RD"]:
        t["rope_mul_add_rnd"] = LM + LA + 1
    if p["QUANT"]:
        t["actquant"] = 13
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
        ft = floor_terms(v)
        meas[v] = dict(params=full["params"], exact=ok, cases_full_shape=len(full["rows"]), golden_cases=len(gold),
                       golden_layers=sorted({r["layer"] for r in gold}), cases_rtl_N64=len(rtl["rows"]),
                       checked_elements_full=sum(r["checked_y"] for r in full["rows"]),
                       checked_quant_blocks_full=sum(r["checked_q"] for r in full["rows"]),
                       cycles=dict(c, q_after_y=c["q_last"] - c["y_last"]),
                       us={k: round(x / FAST * 1e6, 5) for k, x in dict(c, q_after_y=c["q_last"] - c["y_last"]).items()},
                       floor_cycles=sum(ft.values()), floor_terms=ft,
                       residual_over_floor=c["q_last"] - sum(ft.values()) if p["QUANT"] else None)
    res = dict(schema="opentallas.dsrom-recovery.su-norm.measure.v1", generated_utc=now(),
               clock_hz=FAST, wire=dict(HUB_IN=HUB_IN, HUB_OUT=HUB_OUT, RW=RW, BW=BW,
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("prep", "run", "record"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--cases")
    ap.add_argument("--variant", choices=tuple(VARIANTS))
    ap.add_argument("--fp", choices=("dpi", "rtl"), default="dpi")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--record", default=str(ROOT / "results/rtl/dsrom_recovery_20261004/su_norm/measure.json"))
    ap.add_argument("--hub-in", type=int, default=None, help="hub stages in (default 33: the ROM's 22 slow stages)")
    ap.add_argument("--hub-out", type=int, default=None, help="hub stages out (default 23: the ROM's 15 slow stages)")
    a = ap.parse_args()
    global HUB_IN, HUB_OUT
    HUB_IN = a.hub_in if a.hub_in is not None else HUB_IN
    HUB_OUT = a.hub_out if a.hub_out is not None else HUB_OUT
    return dict(prep=cmd_prep, run=cmd_run, record=cmd_record)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
