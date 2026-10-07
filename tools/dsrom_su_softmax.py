#!/usr/bin/env python3
"""DS-ROM recovery lever su_softmax: the attention softmax of one die's 16 heads as ONE fused 1.2 GHz pipeline
(rtl/hdc/v41x/ot_dsrom_su_softmax.sv), measured at full shape (H 16, T 640 and T 128) on the golden 1M operands of
the representative layers (L0 sliding T 128; L3 / L20 / L24 T 640: the su_cases.pkl chains *.attn.softmax_T*) and
on random stress rows, bit-exact against tools/hdc_golden_v41 (the chain's own checks for the golden cases).

    python3 tools/dsrom_su_softmax.py prep  --cases su_cases.pkl --work W [--lph 16] [--stress 6]
    python3 tools/dsrom_su_softmax.py build --work W [--lph 16]       # Verilator (compute host)
    python3 tools/dsrom_su_softmax.py run   --work W [--lph 16]       # every prepared case -> W/run_LPH.json
    python3 tools/dsrom_su_softmax.py record --work W --lph 16 [--lph-alt 64] [--screen S.json] [--route R.json]

Node times (1.2 GHz cycles; cycle 0 = the first score vector at the unit's input, all scores available as in the
SU chain's measurement; the graph's dependencies are kept):
  attn.max        cycle the row maxima reach the reduction root (DIN + stream + scale + lane max + tree + RWU)
  attn.exp        root max -> last e out (RWD + re-read + sub + exp + DOUT): the tile's P.V input
  attn.den        last e out -> row sums at the root (chunk chain + trees + RWU, minus the DOUT already counted)
  attn.sink       row sums at the root -> den at the lanes (add + RWD); exp(sink - max) ran beside the row sum
  attn.normalize  first PV vector at the unit's input -> last o out (DIN + stream + divide + BF16 + RoPE + DOUT)
attn.pv (the attention tile, unchanged) sits between exp and normalize as before.
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
H, TAIL, ROW = 16, 64, 512
FAST = 1.2e9
DIN, DOUT, RWU, RWD = 33, 23, 9, 9
RTL = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_cg.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
       "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv",
       "rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv", "rtl/hdc/v41x/ot_dsrom_su_softmax_add6.sv",
       "rtl/hdc/v41x/ot_dsrom_su_softmax_m9.sv", "rtl/hdc/v41x/ot_dsrom_su_softmax_add.sv", "rtl/hdc/v41x/ot_dsrom_su_softmax_exp6.sv",
       "rtl/hdc/v41x/ot_dsrom_su_softmax.sv"]
TB = "rtl/test/tb_dsrom_su_softmax.sv"
# simulation: the keep-prefix integer adders as their behavioural `+` (same function, combinational; the N 1,024
# SU bench's dpi_beh convention), the FP units as RTL
SIM_RTL = [("rtl/test/sim_hdc_prefix_beh.sv" if p == "rtl/hdc/ot_hdc_prefix.sv" else p) for p in RTL]
OUT = ROOT / "results/rtl/dsrom_recovery_20261004/su_softmax"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def u32(x):
    return np.asarray(x, dtype=F).reshape(-1).view(np.uint32)


def reference(s_raw, scale, sink, pv, cos, sin):
    """tools/dsrom_1m_su.chain_attend's golden (hdc_golden_v41.attend's softmax + normalise + inverse RoPE)."""
    import hdc_golden_v41 as V
    s = V.mul(s_raw, F(scale))
    mb = np.max(s, axis=1)
    e = V.exp(V.add(s, V.neg(mb)[:, None]))
    es = V.reduce_rows(e)
    den = V.add(es, V.exp(V.add(sink, V.neg(mb))))
    o0 = V.to_bf16(V.div(pv, den[:, None]))
    o = V.rope_tail(o0, (cos, sin), inverse=True)
    return dict(s=s, max=mb, e=e, es=es, den=den, o=o)


def golden_cases(cases_pkl):
    d = pickle.loads(Path(cases_pkl).read_bytes())
    out = []
    for c in d["cases"]:
        if c["meta"]["fn"] != "attend":
            continue
        T = c["meta"]["T"]
        init = dict(c["init"])
        ops = c["ops"]
        s_raw = init[ops[0]["abase"]].reshape(H, T)
        sink = init[ops[2]["abase"]]
        pv = init[ops[3]["abase"]].reshape(H, ROW)
        scale = np.asarray(ops[0]["imm1"], np.uint32).view(F)
        cos = np.asarray(c["cr_lo"][:TAIL // 2]).astype(np.uint32).view(F)
        sin = np.asarray(c["cr_hi"][:TAIL // 2]).astype(np.uint32).view(F)
        chk = {lab: np.asarray(w, np.uint32) for lab, _a, w, _k in c["checks"]}
        ref = reference(s_raw, scale, sink, pv, cos, sin)
        want = dict(s="scaled scores", max="row max", e="exp(s - max) (P before BF16, the tile's P.V input)",
                    es="row sum", den="denominator (row sum + exp(sink - max))", o="o (inverse RoPE): wo_a's input")
        agree = {k: bool(np.array_equal(u32(ref[k]), chk[v])) for k, v in want.items()}
        assert all(agree.values()), (c["name"], agree)
        out.append(dict(name=c["name"], layer=c["meta"]["layer"], T=T, s_raw=s_raw, scale=scale, sink=sink, pv=pv,
                        cos=cos, sin=sin, ref=ref, source="golden", reference_equals_chain_checks=agree))
    return out


def stress_cases(n, seed=20261004):
    rng = np.random.default_rng(seed)
    out = []
    for k in range(n):
        T = (640, 128)[k % 2]
        kind = k % 3
        if kind == 0:
            s_raw = rng.normal(0, 30, (H, T)).astype(F)
        elif kind == 1:      # wide range: exp underflows to +0 for most of a row, exact ties of the max
            s_raw = (rng.normal(0, 1, (H, T)) * rng.choice([1, 100, 1e4], (H, T))).astype(F)
            s_raw[:, 5] = s_raw.max(axis=1)
        else:                # BF16-valued scores (the tile's q.k of BF16 operands accumulates FP32; any FP32 here)
            s_raw = (rng.standard_cauchy((H, T)) * 3).astype(F)
            s_raw = np.clip(s_raw, -1e5, 1e5).astype(F)
        scale = F(rng.choice([0.0441941738, 0.125, 1.0]))
        sink = rng.normal(0, 3, H).astype(F)
        pv = (rng.normal(0, 1, (H, ROW)) * rng.choice([1e-3, 1, 50], (H, ROW))).astype(F)
        cos = rng.uniform(-1, 1, TAIL // 2).astype(F)
        sin = rng.uniform(-1, 1, TAIL // 2).astype(F)
        ref = reference(s_raw, scale, sink, pv, cos, sin)
        out.append(dict(name=f"stress{k}_T{T}", layer=None, T=T, s_raw=s_raw, scale=scale, sink=sink, pv=pv, cos=cos,
                        sin=sin, ref=ref, source=f"random seed {seed} case {k}"))
    return out


def hexrow(vals):
    """One memory line: element 0 in the low 32 bits."""
    return "".join(f"{int(v):08x}" for v in reversed(list(vals)))


def lanes_vec(m, v, lph):
    """vector v of every head: lane h*lph + j = m[h, v*lph + j]."""
    return np.concatenate([m[h, v * lph:(v + 1) * lph] for h in range(H)])


def write_case(d, c, lph):
    d.mkdir(parents=True, exist_ok=True)
    T = c["T"]
    nv = T // lph
    lt = int(np.ceil(np.log2(nv))) if nv > 1 else 0
    sr = c["s_raw"].view(np.uint32)
    (d / "s.mem").write_text("".join(hexrow(lanes_vec(sr, v, lph)) + "\n" for v in range(nv)))
    pv = c["pv"].view(np.uint32)
    (d / "pv.mem").write_text("".join(hexrow(lanes_vec(pv, u, lph)) + "\n" for u in range(ROW // lph)))
    r = c["ref"]
    e = np.asarray(r["e"], F).view(np.uint32)
    (d / "e_exp.mem").write_text("".join(hexrow(lanes_vec(e, v, lph)) + "\n" for v in range(nv)))
    ob = (np.asarray(r["o"], F).view(np.uint32) >> 16).astype(np.uint32)
    (d / "o_exp.mem").write_text("".join("".join(f"{int(x):04x}" for x in reversed(list(lanes_vec(ob, u, lph))))
                                         + "\n" for u in range(ROW // lph)))
    par = [nv, lt, int(u32(c["scale"])[0])]
    (d / "par.mem").write_text("".join(f"{x:08x}\n" for x in par))
    (d / "vec.mem").write_text("".join(hexrow(u32(x)) + "\n" for x in (c["sink"], r["max"], r["es"], r["den"])))
    (d / "rope.mem").write_text(hexrow(u32(c["cos"])) + "\n" + hexrow(u32(c["sin"])) + "\n")


def cmd_prep(a):
    work = Path(a.work)
    cs = golden_cases(a.cases) + stress_cases(a.stress)
    meta = []
    for c in cs:
        write_case(work / f"lph{a.lph}" / c["name"], c, a.lph)
        meta.append(dict(name=c["name"], layer=c["layer"], T=c["T"], source=c["source"],
                         reference_equals_chain_checks=c.get("reference_equals_chain_checks")))
    (work / f"lph{a.lph}" / "cases.json").write_text(json.dumps(dict(cases=meta, cases_pkl_sha256=sha(a.cases)),
                                                               indent=1) + "\n")
    print("prepared", len(cs), [c["name"] for c in cs])
    return 0


def verilator():
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    return str(vl) if vl.exists() else "verilator"


def nvmax(lph):
    return 640 // lph


def cmd_build(a):
    obj = Path(a.work) / f"obj_lph{a.lph}{a.tag}"
    nvm = nvmax(a.lph)
    ltm = max(1, int(np.ceil(np.log2(nvm))))
    cmd = [verilator(), "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module", "tb_dsrom_su_softmax", *os.environ.get("VL_DEFS", "").split(),
           f"-GLPH={a.lph}", f"-GNVMAX={nvm}", f"-GLTMAX={ltm}", f"-GLM={a.lm}", f"-GLA={a.la}", f"-GELM={a.elm}", f"-GELA={a.ela}", f"-GADD6={a.add6}", f"-GEXP6={a.exp6}", f"-GEXPNS={a.expns}", f"-GDENK={a.denk}", f"-GMARGIN={a.margin}", f"-GSAFE={a.safe}", "-Mdir", str(obj), "-j", str(a.jobs),
           "--unroll-count", "4", "-fno-dfg", *[str(ROOT / p) for p in SIM_RTL], str(ROOT / TB), "-CFLAGS", "-O1"]
    subprocess.run(cmd, check=True)
    return 0


def cmd_run(a):
    work = Path(a.work)
    exe = work / f"obj_lph{a.lph}{a.tag}" / "Vtb_dsrom_su_softmax"
    meta = json.loads((work / f"lph{a.lph}" / "cases.json").read_text())
    rows = []
    for m in meta["cases"]:
        d = work / f"lph{a.lph}" / m["name"]
        r = subprocess.run([str(exe)], cwd=d, capture_output=True, text=True)
        g = re.search(r"SMX (.*)", r.stdout)
        if not g:
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit(f"no SMX line for {m['name']}")
        kv = dict(x.split("=") for x in g.group(1).split())
        kv = {k: int(v) for k, v in kv.items()}
        row = dict(m, **kv)
        row["exact"] = all(kv[k] == 0 for k in ("err_max", "err_es", "err_den", "err_e", "err_o")) and \
            kv["n_e"] == H * m["T"] and kv["n_o"] == H * ROW
        row["nodes_cycles"] = {
            "attn.max": kv["t_mx"], "attn.exp": kv["t_elast"] - kv["t_mx"], "attn.den": kv["t_es"] - kv["t_elast"],
            "attn.sink": kv["t_den"] - kv["t_es"], "attn.normalize": kv["t_olast"] - kv["t_pv0"]}
        rows.append(row)
        print(m["name"], row["exact"], row["nodes_cycles"], flush=True)
    res = dict(lph=a.lph, lm=a.lm, la=a.la, elm=a.elm, ela=a.ela, add6=a.add6, exp6=a.exp6, expns=a.expns, denk=a.denk, margin=a.margin, safe=a.safe, tag=a.tag, rows=rows, all_exact=all(r["exact"] for r in rows), generated_utc=now(),
               source_commit=git_head(), rtl_sha256={p: sha(ROOT / p) for p in RTL + SIM_RTL + [TB]})
    (work / f"run_lph{a.lph}{a.tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    print("RUN", "pass" if res["all_exact"] else "FAIL")
    return 0 if res["all_exact"] else 1


NODES = ("attn.max", "attn.exp", "attn.den", "attn.sink", "attn.normalize")
T128_LAYERS = ("L0", "L1")          # sliding-window layers (T 128); every other layer T 640 (composition patches)


def cmd_record(a):
    """Commit the measured runs (W/run_lph*.json copied to the record dir) and write the lever record."""
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {}
    for f in a.runs.split(","):
        r = json.loads(Path(f).read_text())
        if r.get("tag"):                    # tagged rounds (a6x6, x7) differ in ADD6/EXP6/EXPNS/DENK, not LM/LA
            key = f"lph{r['lph']}_{r['tag']}"
        else:
            key = f"lph{r['lph']}_e{r['elm']}{r['ela']}" + (f"_u{r['lm']}{r['la']}" if (r.get("lm", 5), r.get("la", 4)) != (5, 4) else "")
        runs[key] = r
        if Path(f).resolve() != (OUT / f"run_{key}.json").resolve():
            (OUT / f"run_{key}.json").write_text(json.dumps(r, indent=1) + "\n")
    main = runs[a.main]
    assert main["all_exact"]
    def per_T(r, T):
        rows = [x for x in r["rows"] if x["T"] == T]
        cyc = rows[0]["nodes_cycles"]
        assert all(x["nodes_cycles"] == cyc for x in rows), "timing must not depend on the data"
        return cyc
    t640, t128 = per_T(main, 640), per_T(main, 128)
    phys = json.loads(Path(a.phys).read_text()) if a.phys else {}
    src = (f"ot_dsrom_su_softmax H 16 LPH {main['lph']} (exp LM {main['elm']} / LA {main['ela']}, ot_dsrom_su_fdiv_f12), "
           f"fused 1.2 GHz, DIN 33 / DOUT 23 / RWU 9 / RWD 9 wire stages; exact on L0/L3/L20/L24 golden 1M + stress "
           f"(su_softmax/run_{a.main}.json)")
    nodes = {}
    for n in NODES:
        nodes["*." + n] = dict(us=round(t640[n] / FAST * 1e6, 5), cycles=t640[n], source=f"{src}; T 640",
                               cls="measured", kind="fused_fast")
    for L in T128_LAYERS:
        for n in NODES:
            nodes[f"{L}.{n}"] = dict(us=round(t128[n] / FAST * 1e6, 5), cycles=t128[n], source=f"{src}; T 128",
                                     cls="measured", kind="fused_fast")
    rec = dict(schema="opentallas.dsrom-recovery.lever.v1", lever="su_softmax", verdict=a.verdict,
               exact=bool(main["all_exact"]), ss_ff=phys.get("summary"), nodes=nodes,
               measurement=dict(main=a.main, runs={k: dict(all_exact=v["all_exact"],
                                                           T640=per_T(v, 640), T128=per_T(v, 128))
                                                    for k, v in runs.items()},
                                cases=[dict(name=x["name"], source=x["source"], exact=x["exact"]) for x in main["rows"]],
                                clock_hz=FAST, wire=dict(DIN=DIN, DOUT=DOUT, RWU=RWU, RWD=RWD)),
               default="opt-in: applied only in the recovery baseline; the stream unit's softmax lowering is unchanged",
               note=a.note)
    lv = ROOT / "results/rtl/dsrom_recovery_20261004/levers/su_softmax.json"
    lv.write_text(json.dumps(rec, indent=1) + "\n")
    print("RECORD", lv)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("prep", "build", "run", "record"))
    ap.add_argument("--runs", default="")
    ap.add_argument("--main", default="")
    ap.add_argument("--phys", default="")
    ap.add_argument("--verdict", default="ADOPT")
    ap.add_argument("--note", default="")
    ap.add_argument("--cases")
    ap.add_argument("--work", required=True)
    ap.add_argument("--lph", type=int, default=16)
    ap.add_argument("--stress", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--lm", type=int, default=5)
    ap.add_argument("--la", type=int, default=4)
    ap.add_argument("--add6", type=int, default=0)
    ap.add_argument("--exp6", type=int, default=0)
    ap.add_argument("--expns", type=int, default=0)
    ap.add_argument("--denk", type=int, default=0)
    ap.add_argument("--margin", type=int, default=0)
    ap.add_argument("--safe", type=int, default=0)
    ap.add_argument("--elm", type=int, default=5)
    ap.add_argument("--ela", type=int, default=4)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    return dict(prep=cmd_prep, build=cmd_build, run=cmd_run, record=cmd_record)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
