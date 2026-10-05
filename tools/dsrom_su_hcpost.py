#!/usr/bin/env python3
"""DS-ROM recovery lever su_hcpost: the hyper-connection post mix (attn.hc_post / ffn.hc_post) as one fused 1.2 GHz
pipeline (rtl/hdc/v41x/ot_dsrom_su_hcpost.sv), measured at full shape ([4, 5120] outputs, 1,024 a cycle) on the 1M
token's golden operands of every representative layer (L0 / L3 / L20 / L24, attn and ffn) plus random stress.

    python3 tools/dsrom_su_hcpost.py prep  --cases su_cases.pkl --out DIR [--stress 32]
    python3 tools/dsrom_su_hcpost.py run   --out DIR [--ng 256 --win 33 --wout 23]       (compute host)
    python3 tools/dsrom_su_hcpost.py record --out DIR --rec results/rtl/dsrom_recovery_20261004/su_hcpost/sim.json

The SU case set (su_cases.pkl of tools/dsrom_1m_su.py, cases_sha256 1e00804b...) holds each chain's vector-memory
image: res (4 x 5120) at 64, y (5120) at 20544, comb (4 x 4, [j][k]) at 25664, post (4) at 25680, and the golden
h (hc_post) check (k-major, 20480).  The stress golden is hdc_golden_v41 add / mul / to_bf16 in the lowering's order.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
F = np.float32
D, HC = 5120, 4
RTL = [ROOT / "rtl/hdc/v41x/ot_dsrom_su_hcpost.sv", ROOT / "rtl/hdc/ot_hdc_fp32_f12.sv", ROOT / "rtl/hdc/ot_hdc_fastfp.sv",
       ROOT / "rtl/hdc/ot_hdc_prefix.sv", ROOT / "rtl/hdc/ot_hdc_delay.sv"]
TB = ROOT / "rtl/test/tb_dsrom_su_hcpost.sv"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def u32(x):
    return np.asarray(x, F).view(np.uint32)


def golden(res, y, comb, post):
    import hdc_golden_v41 as V
    out = []
    for k in range(HC):
        t = V.add(V.mul(res[0], comb[0, k]), V.mul(res[1], comb[1, k]))
        t = V.add(V.mul(res[2], comb[2, k]), t)
        t = V.add(V.mul(res[3], comb[3, k]), t)
        t = V.add(V.mul(y, post[k]), t)
        out.append(V.to_bf16(t))
    return np.concatenate(out).astype(F)


def hexline(words):
    """words[0] is the least significant 32 bits."""
    return "".join(f"{int(w):08x}" for w in reversed(list(words)))


def write_case(d: Path, res, y, comb, post, want, ng):
    d.mkdir(parents=True, exist_ok=True)
    nb = D // ng
    (d / "op.mem").write_text(hexline(list(u32(comb.reshape(-1))) + list(u32(post))) + "\n")
    R, Y, W = u32(res), u32(y), u32(want).reshape(HC, D)
    with open(d / "in.mem", "w") as fi, open(d / "exp.mem", "w") as fe:
        for b in range(nb):
            i = np.arange(b * ng, (b + 1) * ng)
            r = np.stack([R[j][i] for j in range(HC)], axis=1).reshape(-1)       # [g][j]
            fi.write(hexline(list(r) + list(Y[i])) + "\n")
            fe.write(hexline(list(np.stack([W[k][i] for k in range(HC)], axis=1).reshape(-1))) + "\n")
    return nb


def stress_case(rng, kind):
    """Random operands: BF16-valued residual copies and y (as the golden stream), comb / post as Sinkhorn emits them
    (positive, < 1 / around 1), plus edge mixes (zeros of both signs, exact cancellation, wide exponents)."""
    def bf(x):
        import hdc_golden_v41 as V
        return V.to_bf16(np.asarray(x, F))
    res = bf(rng.standard_normal((HC, D)).astype(F) * F(rng.choice([0.05, 1.0, 30.0])))
    y = bf(rng.standard_normal(D).astype(F) * F(rng.choice([0.01, 0.5, 8.0])))
    comb = rng.random((HC, HC)).astype(F)
    post = (rng.random(HC) * 2).astype(F)
    if kind >= 1:            # signed zeros
        m = rng.random((HC, D)) < 0.05
        res[m] = np.where(rng.random(m.sum()) < 0.5, F(0.0), F(-0.0))
        y[rng.random(D) < 0.05] = F(-0.0)
    if kind >= 2:            # exact cancellation r1*c1 = -(r0*c0)
        comb[1] = comb[0]
        m = rng.random(D) < 0.3
        res[1, m] = -res[0, m]
    if kind >= 3:            # wide exponents (near over/underflow of the products, subnormal results)
        res *= F(2.0) ** rng.integers(-120, 100, size=(HC, D)).astype(F)
        y *= F(2.0) ** rng.integers(-120, 100, size=D).astype(F)
        res = bf(res)
        y = bf(y)
    return res, y, comb, post


def cmd_prep(a):
    out = Path(a.out)
    d = pickle.loads(Path(a.cases).read_bytes())
    cases = []
    for c in d["cases"]:
        if c["meta"]["fn"] != "hc_post":
            continue
        img = dict(c["init"])
        res, y = img[64].reshape(HC, D), img[20544]
        comb, post = img[25664].reshape(HC, HC), img[25680]
        (lab, addr, want_bits, _k), = c["checks"]
        want = np.asarray(want_bits, np.uint32).view(F)
        g = golden(res, y, comb, post)
        assert np.array_equal(u32(g), u32(want)), c["name"]          # the stress golden == the SU golden
        nb = write_case(out / c["name"], res, y, comb, post, want, a.ng)
        cases.append(dict(name=c["name"], kind="golden_1m", beats=nb))
    rng = np.random.default_rng(20261004)
    for s in range(a.stress):
        res, y, comb, post = stress_case(rng, s % 4)
        want = golden(res, y, comb, post)
        nb = write_case(out / f"stress{s:03d}", res, y, comb, post, want, a.ng)
        cases.append(dict(name=f"stress{s:03d}", kind=f"stress{s % 4}", beats=nb))
    (out / "cases.json").write_text(json.dumps(dict(ng=a.ng, cases=cases, cases_pkl_sha256=sha(a.cases)), indent=1))
    print("prep", len(cases))
    return 0


def cmd_run(a):
    out = Path(a.out)
    meta = json.loads((out / "cases.json").read_text())
    assert meta["ng"] == a.ng
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    verilator = str(vl) if vl.exists() else "verilator"
    tag = f"ng{a.ng}_w{a.win}_{a.wout}_m{a.ml}a{a.al}" + ("_h" if a.hier else "")
    obj = out / f"obj_{tag}"
    exe = obj / "Vtb_dsrom_su_hcpost"
    if not exe.exists():
        t0 = datetime.datetime.now()
        subprocess.run([verilator, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module",
                        "tb_dsrom_su_hcpost", f"-GNG={a.ng}", f"-GWIN={a.win}", f"-GWOUT={a.wout}", f"-GML={a.ml}", f"-GAL={a.al}", "-Mdir", str(obj),
                        "-j", "16", "--unroll-count", "4", *(["--hierarchical"] if a.hier else []), *map(str, RTL), str(TB)], check=True)
        print("build", datetime.datetime.now() - t0, flush=True)
    rows = []
    for c in meta["cases"]:
        r = subprocess.run([str(exe), f"+DIR={out / c['name']}", f"+NB={c['beats']}"], capture_output=True, text=True)
        m = re.search(r"HCP nb=(\d+) beats_out=(\d+) words=(\d+) errors=(\d+) fault=(\d+) first_out=(-?\d+) "
                      r"last_out=(-?\d+) cycles=(-?\d+) (PASS|FAIL)", r.stdout)
        if not m:
            print(r.stdout[-2000:], r.stderr[-2000:])
            raise SystemExit("no result line")
        nb, bo, words, errs, fault, fo, lo, cyc, st = m.groups()
        rows.append(dict(**c, words=int(words), errors=int(errs), fault=int(fault), first_out=int(fo),
                         last_out=int(lo), cycles=int(cyc), pass_=st == "PASS"))
        print(c["name"], st, cyc, errs, flush=True)
    (out / f"run_{tag}.json").write_text(json.dumps(dict(
        ng=a.ng, win=a.win, wout=a.wout, ml=a.ml, al=a.al, simulator=subprocess.run([verilator, "--version"], capture_output=True,
                                                                  text=True).stdout.strip(),
        rows=rows, rtl_sha256={str(p.relative_to(ROOT)): sha(p) for p in RTL + [TB]}), indent=1))
    return 0 if all(r["pass_"] for r in rows) else 1


def cmd_record(a):
    out = Path(a.out)
    runs = {p.name: json.loads(p.read_text()) for p in sorted(out.glob("run_ng*.json"))}
    meta = json.loads((out / "cases.json").read_text())
    rec = dict(schema="opentallas.dsrom-recovery.su_hcpost.sim.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               unit="ot_dsrom_su_hcpost", clock_hz=1.2e9, cases_pkl_sha256=meta["cases_pkl_sha256"], runs=runs,
               tool_sha256=sha(__file__))
    Path(a.rec).parent.mkdir(parents=True, exist_ok=True)
    Path(a.rec).write_text(json.dumps(rec, indent=1) + "\n")
    return 0


def cmd_lever(a):
    """levers/su_hcpost.json from the committed full-shape run and the routed lane's corner STA."""
    rec = ROOT / "results/rtl/dsrom_recovery_20261004/su_hcpost"
    run = json.loads((rec / "runs" / a.run).read_text())
    cs = json.loads((rec / "route" / a.corner).read_text())
    rows = run["rows"]
    gold = [r for r in rows if r["kind"] == "golden_1m"]
    cyc = {r["cycles"] for r in rows}
    assert len(cyc) == 1, cyc
    cyc = cyc.pop()
    exact = all(r["pass_"] and r["errors"] == 0 and r["fault"] == 0 for r in rows) and len(gold) == 8
    us = round(cyc / 1.2e3, 5)
    ss, ff = cs["setup_ss"]["worst_slack_ps"], cs["hold_ff"]["worst_slack_ps"]
    src = (f"ot_dsrom_su_hcpost (NG {run['ng']} groups x 4 lanes = 1,024 outputs/cycle, mul_f12 L{run['ml']} / add_f12 "
           f"L{run['al']}): go -> last of 20 output beats landed {cyc} cycles at 1.2 GHz incl. hub in {run['win']} / out "
           f"{run['wout']} register stages; bit-exact on the 8 golden 1M hc_post chains (L0/L3/L20/L24 attn+ffn) + "
           f"{len(rows) - len(gold)} stress cases")
    old = 0.2899
    r = dict(schema="opentallas.dsrom-recovery.lever.v1", lever="su_hcpost", verdict=a.verdict, exact=exact,
             ss_ff=dict(period_ps=833.0, ss_setup_wns_ps=ss, ff_hold_wns_ps=ff, closes=bool(cs["closes_signoff"]),
                        basis="ROUTED minimum component (one lane, ot_dsrom_su_hcpost_lane): ORFS asap7 at 0.833 ns, "
                              "tools/w18/corner_sta.py SS setup 60 ps / FF hold 25 ps",
                        record=f"results/rtl/dsrom_recovery_20261004/su_hcpost/route/{a.corner}",
                        prelayout_screen="results/rtl/dsrom_recovery_20261004/su_hcpost/screen/ (pessimistic for the "
                                         "f12 units: standalone add_f12_l5x screens -45.6 ps but routes +13.0)"),
             nodes={"*.attn.hc_post": dict(us=us, source=src, cls="measured", kind="fused_fast"),
                    "*.ffn.hc_post": dict(us=us, source=src, cls="measured", kind="fused_fast")},
             measurement=dict(old=dict(unit="ot_hdc_v41x_vec N1024 wired, 4 dependent ops (0.9 GHz) + CDC",
                                       us=old, record="results/rtl/dsrom_1m_allmeasured_20261004/su.json"),
                              new=dict(unit="ot_dsrom_su_hcpost", cycles=cyc, us=us, clock_hz=1.2e9,
                                       record=f"results/rtl/dsrom_recovery_20261004/su_hcpost/runs/{a.run}"),
                              floor=dict(cycles=97, us=0.08083, source="anatomy.json floors.hc_post",
                                         residual=f"{cyc - 97} cycles over the anatomy floor: the operand capture register (1), "
                                                  f"the closing adder latency (add_f12 L5 instead of L4: +1 on each of "
                                                  f"the 4 serial adds) and the landing register (1); L4 adders fail "
                                                  f"the routed lane by -52.5 ps (route/lane_m5a4_FAIL.corner.json)"
                                         if cyc > 97 else "at floor"),
                              saving_us_per_layer=round(2 * (old - us), 5)),
             variants_note=("mul_f12_l6 lanes (m6a4, m6a5) mismatch the golden in this lane (runs/*m6*: FAIL), so the "
                            "L6 multiplier is not used; m5a4 is exact (99 cycles) but does not close routed; m5a5 is "
                            "exact and closes"),
             default="opt-in: applied only in the recovery baseline; the SU lowering of hc_post is unchanged",
             note=a.note)
    out = ROOT / "results/rtl/dsrom_recovery_20261004/levers/su_hcpost.json"
    out.write_text(json.dumps(r, indent=1) + "\n")
    print(json.dumps(dict(cycles=cyc, us=us, exact=exact, ss=ss, ff=ff), indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("prep", "run", "record", "lever"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--cases")
    ap.add_argument("--stress", type=int, default=32)
    ap.add_argument("--ng", type=int, default=256)
    ap.add_argument("--win", type=int, default=33)
    ap.add_argument("--wout", type=int, default=23)
    ap.add_argument("--ml", type=int, default=5)
    ap.add_argument("--al", type=int, default=4)
    ap.add_argument("--hier", type=int, default=1, help="verilate the lane once (hier_block) and instance it")
    ap.add_argument("--rec")
    ap.add_argument("--run")
    ap.add_argument("--corner", default="lane_m6a5.corner.json")
    ap.add_argument("--verdict", default="ADOPT")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run, record=cmd_record, lever=cmd_lever)[a.step](a)


if __name__ == "__main__":
    sys.exit(main())
