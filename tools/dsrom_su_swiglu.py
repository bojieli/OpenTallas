#!/usr/bin/env python3
"""DS-ROM recovery, SU-chain lever su_swiglu: the fused 1.2 GHz pipeline ffn.swiglu -> ffn.route_w -> ffn.quant2
(ot_dsrom_su_swiglu) and the multi-instance quantiser bank for attn.z_quant / attn.idx.q (ot_dsrom_su_qbank), on
the 1M token's golden operands (position 1,048,575, die 0 of TP4; representative layers L0 / L3 / L20 / L24),
bit-exact against the golden, timed in RTL at full shape.

Operands: the SU case set of tools/dsrom_1m_su.py (su_cases.pkl: *.ffn.swiglu, *.ffn.shared_swiglu, *.attn.idx.q
with their golden checks) and the quantiser block files of its `quant` step (quant_work/<L>_<node>/aq_{in,exp}.mem:
the golden blocks and aq_expect of tools/rtl_hdc_v41_blockdot_campaign.py).  prep cross-checks them against each
other and against the golden functions (tools/hdc_golden_v41.py), and adds random stress cases with golden expects.

    python3 tools/dsrom_su_swiglu.py prep --cases su_cases.pkl --quant-work quant_work --out DIR
    python3 tools/dsrom_su_swiglu.py run  --out DIR --fp rtl|dpi_beh --w 64|1024 [--nb 32]     (Verilator)
    python3 tools/dsrom_su_swiglu.py record --out DIR ...                                         (lever record)
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
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
F = np.float32
LAYERS = ("L0", "L3", "L20", "L24")
FAST = 1.2e9
NIN, NOUT = 33, 23            # hub traverse at 1.2 GHz: 22 / 15 slow stages x 748/504 (SS wire reach)
RTL = ["rtl/hdc/v41x/ot_dsrom_su_swiglu.sv", "rtl/hdc/v41x/ot_dsrom_su_f12.sv"]
ADD6 = "rtl/hdc/v41x/ot_dsrom_su_add6.sv"
LIB = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
       "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv",
       "rtl/hdc/v41/ot_hdc_actquant.sv"]
DPI = {"rtl/hdc/ot_hdc_fastfp.sv": ["rtl/test/sim_hdc_v41x_fastfp_dpi.sv", "rtl/test/sim_hdc_v41x_fastfp_wrap.sv",
                                    "rtl/test/sim_hdc_v41x_fastfp_dpi.cpp"],
       "rtl/hdc/ot_hdc_fp32_add_lat.sv": ["rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv",
                                          "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp", "rtl/test/sim_hdc_fp32_lat_tops.sv"],
       "rtl/hdc/ot_hdc_fp32_mul_lat.sv": [],
       "rtl/hdc/ot_hdc_fp32_f12.sv": ["rtl/test/sim_hdc_fp32_f12_dpi_tops.sv"],
       "rtl/hdc/ot_hdc_prefix.sv": ["rtl/test/sim_hdc_prefix_beh.sv"],
       ADD6: ["rtl/test/sim_dsrom_su_add6_dpi.sv"]}
TB = {"swiglu": "rtl/test/tb_dsrom_su_swiglu.sv", "qbank": "rtl/test/tb_dsrom_su_qbank.sv"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bits(x):
    return np.asarray(x, dtype=F).view(np.uint32)


def wmem(p, words):
    Path(p).write_text("".join(f"{int(w) & 0xFFFFFFFF:08x}\n" for w in words))


def read_aq(d):
    """quant_work dir -> (fp4 flag, blocks [n, 32] uint32, exp lines as ints)."""
    ins = [ln.strip() for ln in (Path(d) / "aq_in.mem").read_text().split()]
    exs = [ln.strip() for ln in (Path(d) / "aq_exp.mem").read_text().split()]
    fp4 = {int(s[0], 16) for s in ins}
    assert len(fp4) == 1
    blocks = []
    for s in ins:
        v = int(s[1:], 16)
        blocks.append([(v >> (32 * i)) & 0xFFFFFFFF for i in range(32)])
    return fp4.pop(), np.asarray(blocks, np.uint32), exs


def aq_lines(a, fp4):
    import rtl_hdc_v41_blockdot_campaign as BC
    out = []
    for b in np.asarray(a, F).reshape(-1, 32):
        f_, e, codes, y = BC.aq_expect(b, fp4)
        out.append(f"{f_:01x}{e & 0xFFF:03x}{BC.hexw(codes, 8):064x}{BC.hexw(y, 16):0128x}")
    return out


# ======================================================================================================================
def golden_swiglu(g, u, w, lim):
    import hdc_golden_v41 as V
    u_ = np.clip(np.asarray(u, F), -lim, lim).astype(F)
    g_ = np.minimum(np.asarray(g, F), lim).astype(F)
    a = V.mul(V.silu(g_), u_)
    if w is not None:
        a = V.mul(np.asarray(w, F), a)
    return V.to_bf16(a)


def golden_rope(x, cos, sin):
    import hdc_golden_v41 as V
    return V.rope_tail(np.asarray(x, F).reshape(-1, 128), (np.asarray(cos, F), np.asarray(sin, F))).reshape(-1)


def cmd_prep(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d = pickle.loads(Path(a.cases).read_bytes())
    cs = {c["name"]: c for c in d["cases"]}
    qw = Path(a.quant_work)
    cases = []
    rng = np.random.default_rng(20261004)

    def put_swiglu(name, g, u, w, lim, want_a, exp_lines, src):
        cd = out / name
        cd.mkdir(exist_ok=True)
        n = len(g)
        wmem(cd / "g.mem", bits(g)); wmem(cd / "u.mem", bits(u))
        if w is not None:
            wmem(cd / "w.mem", bits(w))
        wmem(cd / "a.mem", bits(want_a))
        (cd / "exp.mem").write_text("\n".join(exp_lines) + "\n")
        cases.append(dict(name=name, kind="swiglu", routed=w is not None, n=n, blocks=len(exp_lines),
                          lim=f"{int(bits(lim)):08x}", source=src))

    for L in LAYERS:
        for routed in (True, False):
            c = cs[f"{L}.ffn.{'swiglu' if routed else 'shared_swiglu'}"]
            op = c["ops"][0]
            init = dict(c["init"])
            g, u = np.asarray(init[op["abase"]], F), np.asarray(init[op["cbase"]], F)
            lim = np.uint32(op["imm3"]).view(F)
            w = None
            if routed:
                wv = np.asarray(init[op["bbase"]], F)
                w = np.repeat(wv, op["nin"]).astype(F)
            want = c["checks"][0][2].view(F)
            gold = golden_swiglu(g, u, w, lim)
            assert np.array_equal(bits(gold), bits(want)), (L, routed, "golden function vs su_cases check")
            node = "ffn.quant2" if routed else "ffn.shared_quant"
            fp4, blocks, exs = read_aq(qw / f"{L}_{node}")
            assert fp4 == 0 and np.array_equal(blocks.reshape(-1), bits(want)), (L, node, "quant input != activation")
            assert aq_lines(want, 0) == exs, (L, node, "aq_expect vs quant.json expects")
            put_swiglu(f"{L}.{'swiglu' if routed else 'shared_swiglu'}", g, u, w, lim, want, exs,
                       f"su_cases {c['name']} (check: golden BF16 activation) + quant_work/{L}_{node}")
    # random stress (routed): the real limit, g / u over the activation's range and the exp clamp, exact edges
    lim = np.uint32(cs["L20.ffn.swiglu"]["ops"][0]["imm3"]).view(F)
    n = 4096
    sc = rng.choice([1e-3, 0.1, 1.0, 4.0, 12.0, 120.0], size=n).astype(F)
    g = (rng.standard_normal(n) * sc).astype(F)
    u = (rng.standard_normal(n) * sc).astype(F)
    g[:16] = [0.0, -0.0, lim, -lim, np.nextafter(lim, F(0)), np.nextafter(lim, F(100)), 87.0, -87.0, 88.5, -88.5,
              -100.0, 1e-30, -1e-30, 1e-40, -1e-40, 15.0]
    u[16:32] = [0.0, -0.0, lim, -lim, np.nextafter(lim, F(0)), np.nextafter(lim, F(100)), -np.nextafter(lim, F(100)),
                1e-40, -1e-40, 3.0e38, -3.0e38, 1.0, -1.0, 0.5, 2.0, 1e-30]
    w = np.repeat(rng.uniform(0.0, 3.0, n // 32).astype(F), 32)
    want = golden_swiglu(g, u, w, lim)
    put_swiglu("random.swiglu", g, u, w, lim, want, aq_lines(want, 0), "random stress (seed 20261004), golden "
               "hdc_golden_v41 silu/mul/to_bf16 + aq_expect")
    # ---- quantiser bank: z_quant (FP8), idx.q (RoPE + FP4)
    for L in LAYERS:
        fp4, blocks, exs = read_aq(qw / f"{L}_attn.z_quant")
        cd = out / f"{L}.z_quant"
        cd.mkdir(exist_ok=True)
        wmem(cd / "x.mem", blocks.reshape(-1))
        (cd / "exp.mem").write_text("\n".join(exs) + "\n")
        assert aq_lines(blocks.reshape(-1).view(F), fp4) == exs
        cases.append(dict(name=f"{L}.z_quant", kind="qbank", rope=False, fp4=fp4, blocks=len(exs),
                          source=f"quant_work/{L}_attn.z_quant (golden z = bf16(wo_a) die slice)"))
    for L in ("L20", "L24"):
        c = cs[f"{L}.attn.idx.q"]
        x = np.asarray(dict(c["init"])[c["ops"][0]["abase"] - 64], F)
        cos = np.asarray(c["cr_lo"][:32]).astype(np.uint32).view(F)       # CROM holds binary32 bit patterns
        sin = np.asarray(c["cr_hi"][:32]).astype(np.uint32).view(F)
        r = golden_rope(x, cos, sin)
        assert np.array_equal(bits(r.reshape(-1, 128)[:, 64:]).reshape(-1), c["checks"][0][2]), (L, "rope")
        fp4, blocks, exs = read_aq(qw / f"{L}_attn.idx.q")
        assert fp4 == 1 and np.array_equal(blocks.reshape(-1), bits(r)), (L, "idx.q quant input != rope rows")
        assert aq_lines(r, 1) == exs
        cd = out / f"{L}.idx_q"
        cd.mkdir(exist_ok=True)
        wmem(cd / "x.mem", bits(x)); wmem(cd / "r.mem", bits(r)); wmem(cd / "cs.mem", np.concatenate([bits(cos), bits(sin)]))
        (cd / "exp.mem").write_text("\n".join(exs) + "\n")
        cases.append(dict(name=f"{L}.idx_q", kind="qbank", rope=True, fp4=1, blocks=len(exs),
                          source=f"su_cases {c['name']} (x, CROM cos/sin, check) + quant_work/{L}_attn.idx.q"))
    for fp4 in (0, 1):                       # random quantiser stress: wide range, subnormals, ties, zeros
        nb = 256
        e = rng.integers(-140, 60, size=(nb, 1))
        xb = (rng.standard_normal((nb, 32)) * np.exp2(e)).astype(F)
        xb[0] = 0.0
        xb[1, :] = -0.0
        xb[2, ::2] = 448.0 * np.exp2(-3)
        x = xb.reshape(-1)
        cd = out / f"random.q{'fp4' if fp4 else 'fp8'}"
        cd.mkdir(exist_ok=True)
        wmem(cd / "x.mem", bits(x))
        exs = aq_lines(x, fp4)
        (cd / "exp.mem").write_text("\n".join(exs) + "\n")
        cases.append(dict(name=cd.name, kind="qbank", rope=False, fp4=fp4, blocks=nb, source="random stress"))
    x = (rng.standard_normal(32 * 128) * rng.choice([1e-3, 1.0, 50.0], size=32 * 128)).astype(F)
    x = bits(np.asarray(x, F)) & np.uint32(0xFFFF0000)
    x = x.view(F)
    cos = rng.uniform(-1, 1, 32).astype(F)
    sin = rng.uniform(-1, 1, 32).astype(F)
    r = golden_rope(x, cos, sin)
    cd = out / "random.idx_q"
    cd.mkdir(exist_ok=True)
    wmem(cd / "x.mem", bits(x)); wmem(cd / "r.mem", bits(r)); wmem(cd / "cs.mem", np.concatenate([bits(cos), bits(sin)]))
    exs = aq_lines(r, 1)
    (cd / "exp.mem").write_text("\n".join(exs) + "\n")
    cases.append(dict(name="random.idx_q", kind="qbank", rope=True, fp4=1, blocks=len(exs), source="random stress"))
    man = dict(cases=cases, su_cases_sha256=sha(a.cases), generated_utc=now())
    (out / "cases.json").write_text(json.dumps(man, indent=1) + "\n")
    print("PREP", len(cases), [c["name"] for c in cases])
    return 0


# ======================================================================================================================
def verilator():
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    return str(vl) if vl.exists() else "verilator"


def sources(fp):
    out = []
    for p in LIB + [ADD6]:
        out += DPI[p] if (fp == "dpi_beh" and p in DPI) else [p]
    return [str(ROOT / p) for p in RTL + out]


def build(kind, params, fp, work):
    tag = kind + "_" + "_".join(f"{k}{v}" for k, v in params.items()) + "_" + fp
    obj = work / f"obj_{tag}"
    exe = obj / f"Vtb_dsrom_su_{kind}"
    if not exe.exists():
        cmd = [verilator(), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-lint", "--top-module",
               f"tb_dsrom_su_{kind}", "-Mdir", str(obj), "-j", os.environ.get("OT_VJ", "16"),
               "--unroll-count", "4096", *[f"-G{k}={v}" for k, v in params.items()],
               *sources(fp), str(ROOT / TB[kind])]
        if os.environ.get("OT_VFLAGS"):
            cmd[1:1] = os.environ["OT_VFLAGS"].split()
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            (work / f"build_{tag}.log").write_text(r.stdout + r.stderr)
            raise SystemExit(f"build failed {tag}: {work}/build_{tag}.log")
        (work / f"build_{tag}.s").write_text(f"{time.time() - t0:.0f}\n")
    return exe, tag


def cmd_run(a):
    out = Path(a.out)
    work = Path(a.work or out / "work")
    work.mkdir(parents=True, exist_ok=True)
    man = json.loads((out / "cases.json").read_text())
    rows = []
    sel = set(a.only.split(",")) if a.only else None
    for c in man["cases"]:
        if sel and c["name"] not in sel:
            continue
        cd = out / c["name"]
        if c["kind"] == "swiglu":
            params = dict(W=a.w, ROUTED=int(c["routed"]), NIN=NIN, NOUT=NOUT, LM=a.lm, LA=a.la, QLAT=a.qlat)
            if a.ireg:                                       # lanes' pin registers (default off: tags unchanged)
                params["IREG"] = 1
            exe, tag = build("swiglu", params, a.fp, work)
            n = -(-c["n"] // a.w) * a.w
            gm = (cd / "g.mem").read_text().split()
            if n > len(gm):                                  # pad to whole vectors with +0 lanes
                for f in ("g.mem", "u.mem") + (("w.mem",) if c["routed"] else ()):
                    (cd / f"pad{a.w}_{f}").write_text((cd / f).read_text() + "00000000\n" * (n - len(gm)))
            run_dir = work / f"run_{c['name']}_{tag}"
            run_dir.mkdir(exist_ok=True)
            for f in ("g.mem", "u.mem", "w.mem", "a.mem", "exp.mem"):
                src = cd / (f"pad{a.w}_{f}" if (cd / f"pad{a.w}_{f}").exists() else f)
                if src.exists():
                    (run_dir / f).write_text(src.read_text())
            args = [f"+N={n}", f"+NA={c['n']}", f"+NBLK={c['blocks']}", f"+LIM={c['lim']}"]
            r = subprocess.run([str(exe), *args], cwd=run_dir, capture_output=True, text=True)
            m = re.search(r"SWG W=(\d+) n=(\d+) vectors=(\d+) a_errors=(\d+) blocks_checked=(\d+) q_errors=(\d+) "
                          r"first_in=(-?\d+) a_first=(-?\d+) a_last=(-?\d+) last_out=(-?\d+)", r.stdout)
            assert m, r.stdout[-2000:] + r.stderr[-2000:]
            W, nn, nv, ea, nchk, eq, fi, af, al, lo = map(int, m.groups())
            rows.append(dict(case=c["name"], kind="swiglu", routed=c["routed"], W=W, elements=c["n"], vectors=nv,
                             a_errors=ea, blocks_checked=nchk, q_errors=eq, first_in=fi, act_first=af, act_last=al,
                             last_out=lo, cycles=lo - fi + 1, us=round((lo - fi + 1) / FAST * 1e6, 5),
                             exact=bool("PASS" in r.stdout), fp=a.fp, build=tag))
        else:
            params = dict(NB=a.nb, ROPE=int(c["rope"]), NIN=NIN, NOUT=NOUT, LM=a.lm, LA=a.la, QLAT=a.qlat)
            exe, tag = build("qbank", params, a.fp, work)
            run_dir = work / f"run_{c['name']}_{tag}"
            run_dir.mkdir(exist_ok=True)
            for f in ("x.mem", "exp.mem", "cs.mem", "r.mem"):
                if (cd / f).exists():
                    (run_dir / f).write_text((cd / f).read_text())
            r = subprocess.run([str(exe), f"+NBLK={c['blocks']}", f"+FP4={c['fp4']}"], cwd=run_dir, capture_output=True,
                               text=True)
            m = re.search(r"QBK NB=(\d+) ROPE=(\d+) nblk=(\d+) beats=(\d+) rope_errors=(\d+) blocks_checked=(\d+) "
                          r"q_errors=(\d+) first_in=(-?\d+) last_out=(-?\d+)", r.stdout)
            assert m, r.stdout[-2000:] + r.stderr[-2000:]
            NB, rp, nblk, nbeat, er, nchk, eq, fi, lo = map(int, m.groups())
            rows.append(dict(case=c["name"], kind="qbank", rope=bool(rp), NB=NB, blocks=nblk, beats=nbeat,
                             rope_errors=er, blocks_checked=nchk, q_errors=eq, first_in=fi, last_out=lo,
                             cycles=lo - fi + 1, us=round((lo - fi + 1) / FAST * 1e6, 5),
                             exact=bool("PASS" in r.stdout), fp=a.fp, build=tag))
        print(json.dumps(rows[-1]), flush=True)
    tagf = f"run_{a.fp}_W{a.w}_NB{a.nb}_m{a.lm}a{a.la}q{a.qlat}{'_ireg' if a.ireg else ''}{'_' + a.only.replace(',', '+') if a.only else ''}.json"
    res = dict(schema="opentallas.dsrom-recovery.su-swiglu.run.v1", generated_utc=now(), fp=a.fp, W=a.w, NB=a.nb, LM=a.lm, LA=a.la, QLAT=a.qlat,
               NIN=NIN, NOUT=NOUT, clock_hz=FAST, rows=rows, status="pass" if rows and all(r["exact"] for r in rows)
               else "fail", source_sha256={p: sha(ROOT / p) for p in RTL + LIB + [ADD6] + list(TB.values())
                                           + ["tools/dsrom_su_swiglu.py"]},
               simulator=subprocess.run([verilator(), "--version"], capture_output=True, text=True).stdout.strip())
    (out / tagf).write_text(json.dumps(res, indent=1) + "\n")
    print("RUN", res["status"], tagf)
    return 0 if res["status"] == "pass" else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("prep", "run"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--cases")
    ap.add_argument("--quant-work")
    ap.add_argument("--work")
    ap.add_argument("--fp", choices=("rtl", "dpi_beh"), default="rtl")
    ap.add_argument("--w", type=int, default=64)
    ap.add_argument("--nb", type=int, default=32)
    ap.add_argument("--only", default=None)
    ap.add_argument("--lm", type=int, default=5, help="FP multiply latency (5: mul_f12_l5, 6: _l6)")
    ap.add_argument("--la", type=int, default=4, help="FP add latency (4: add_f12_l4, 5: _l5x)")
    ap.add_argument("--qlat", type=int, default=5, help="quantiser scale multiply latency")
    ap.add_argument("--ireg", action="store_true", help="swiglu lanes with pin registers (IREG = 1, S81-RERUN)")
    ap.add_argument("--nin", type=int, default=None, help="hub stages in (default 33: the ROM's 22 slow stages)")
    ap.add_argument("--nout", type=int, default=None, help="hub stages out (default 23: the ROM's 15 slow stages)")
    a = ap.parse_args()
    global NIN, NOUT
    NIN = a.nin if a.nin is not None else NIN
    NOUT = a.nout if a.nout is not None else NOUT
    return dict(prep=cmd_prep, run=cmd_run)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
