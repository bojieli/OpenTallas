#!/usr/bin/env python3
"""ds-1010/pqc (2026-10-10): differential lockstep bench of the S81 PQ core VM read, v13b fixed one-edge read vs the
v14 XRV valid-return read (physical/s81_pq_xrv/pinned/rtl/v41die/ot_v41_spine_pqc_w17w10.sv).

The 1M field vehicle's input (the 1M-context golden VM dump) no longer exists on any host, so this bench uses
SYNTHETIC programs on the same field vehicle shape as tools/dsrom_field_spine.py (NP 32 pair slots, R 1, NBF 5,
FAST/PP W10 elements, PHW 3, VAW 17): seeded random FP8 / FP4 / BF16 weight matrices and x, placed by the W17/W10
image writer (tools/v41_die_images_w17w10.add_phase, its own legal LPT placement), with the golden rows of
tools/hdc_golden_v41 (chunk8).  Cases cover every op class the spine decodes: Q family (FP8 / FP4 weights, FP8
quantised x) and BF family (BF16 x buffer), FP32 and BF16 outputs, K from one VRD block to KMAX, multi-position ops
(np > 0, the MTP positions), and nodes of back-to-back ops across both x buffers and the four tags.

Vehicle: rtl/test/dsrom_sys/ot_v41_fieldtop_pqc_xrv.sv (the field vehicle with a request-driven stationed VM model:
each read returns the row block AT ITS OWN ADDRESS, D edges after the request, in order, with the return valid).
REFERENCE = v13b mode (XRV 0) at D 1 (the co-located read it was designed for).  Every other run must produce the
SAME ordered row-write transactions per op (address, data) as the reference and every golden row exactly once.

    python3 tools/s81/pqc_xrv_bench.py build --work W [--jobs 16]       (6 Verilator builds: L/X/XC x PQ 0/1)
    python3 tools/s81/pqc_xrv_bench.py run   --work W --record OUT.json [--jobs 32]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import v41_die_images_w17w10 as I  # noqa: E402

_LPT = I._place
import dsrom_1m_field as F1  # noqa: E402  (monkeypatches I._place with the S81 hook; restored below)
import dsrom_recovery_field as F  # noqa: E402
import hdc_golden_v41 as G  # noqa: E402
from rtl_v41_rom_array import Mat  # noqa: E402

I._place = _LPT

PIN = ROOT / "physical/s81_pq_xrv/pinned"
SPINE = PIN / "rtl/v41die/ot_v41_spine_pqc_w17w10.sv"
TOP = "ot_v41_fieldtop_pqc_xrv"
VEH = ROOT / "rtl/test/dsrom_sys/ot_v41_fieldtop_pqc_xrv.sv"
TB = ROOT / "rtl/test/dsrom_sys/tb_pqc_xrv_field.cpp"
NP, NR, NBF, PHW, VAW = 32, 1, 5, 3, 17
XSTRIDE, OBASE, OSTRIDE = 8192, 98304, 2048
QD = 4
D_REAL = 2 + (QD + 6) + 2          # hub relay stations each way + ot_s81ph_vm_mem L = QD + 6
XCAP_OK = 16                       # >= D_REAL + 1 (registered outstanding count)
XCAP_BAD = D_REAL                  # one below the round trip in count terms
BUILDS = {  # name: (XRV, XCAP)
    "L": (0, 16), "X": (1, XCAP_OK), "XC": (1, XCAP_BAD)}


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sources():
    """Main's field vehicle RTL with the pinned v13b set (spine v14, aq12m, its arithmetic) taking precedence."""
    pinned = sorted(p for p in PIN.rglob("*.sv") if "physical" not in p.relative_to(PIN).parts)
    names = {p.name for p in pinned}
    die = [ROOT / f"rtl/v41die/{n}.sv" for n in ("ot_v41_retn_w17w10", "ot_v41_pair_pq_ld", "ot_v41_pair_pq_w17w10",
                                                 "ot_v41_field_pq_w17w10")] + [ROOT / "rtl/v41rom/ot_v41_kreg.sv"]
    rest = [p for p in dict.fromkeys(F.RTL + die + F1.ROMS) if p.name not in names]
    return pinned + rest + [VEH]


def cmd_build(a):
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([F1.VERILATOR, "-V"], text=True)).group(1)
    srcs = sources()
    out = {}
    for pq in (0, 1):
        for name, (xrv, xcap) in BUILDS.items():
            tag = f"{name}_pq{pq}"
            bdir = (a.work / "build" / tag).resolve()
            bdir.mkdir(parents=True, exist_ok=True)
            out[tag] = (bdir, pq, xrv, xcap)

    def one(item):
        tag, (bdir, pq, xrv, xcap) = item
        params = ["-GFAST=1", "-GPP=1", "-GBP=0", f"-GNP={NP}", f"-GR={NR}", f"-GNBF={NBF}", f"-GPHW={PHW}",
                  f"-GVAW={VAW}", f"-GPQ={pq}", f"-GXRV={xrv}", f"-GXCAP={xcap}"]
        mdir = bdir / "obj"
        steps = []
        for nm, cmd in (
                ("verilate", [F1.VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style",
                              "-Wno-TIMESCALEMOD", "--top-module", TOP, "--prefix", "Vpq", "--Mdir", str(mdir),
                              *params, *map(str, srcs)]),
                ("make", ["make", "-C", str(mdir), "-f", "Vpq.mk", f"-j{a.jobs}", "Vpq__ALL.a", "OPT_FAST=-O2",
                          "OPT_SLOW=-O1"]),
                ("link", ["g++", "-std=c++20", "-O2", f"-DNR={NR}", f"-DVAW={VAW}", f"-I{vroot}/include",
                          f"-I{vroot}/include/vltstd", f"-I{mdir}", str(TB), str(mdir / "Vpq__ALL.a"),
                          f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                          "-pthread", "-o", str(bdir / "tb")])):
            t0 = time.time()
            p = subprocess.run(cmd, capture_output=True, text=True)
            (bdir / f"{nm}.log").write_text(p.stdout + p.stderr)
            steps.append(dict(name=nm, seconds=round(time.time() - t0, 1), returncode=p.returncode))
            if p.returncode:
                return tag, steps, (p.stdout + p.stderr)[-2000:]
        (bdir / "build.json").write_text(json.dumps(dict(tag=tag, params=params, steps=steps, tb_sha256=sha(bdir / "tb"),
                                                         source_sha256={str(s.relative_to(ROOT)): sha(s) for s in srcs + [TB]}),
                                                    indent=1) + "\n")
        return tag, steps, None

    bad = 0
    with cf.ThreadPoolExecutor(len(out)) as ex:
        for tag, steps, err in ex.map(one, out.items()):
            print(tag, steps, "OK" if err is None else "FAIL\n" + err, flush=True)
            bad += err is not None
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ synthetic images
def syn_mat(rng, fmt, rows, K, name):
    m = Mat.__new__(Mat)
    m.name, m.fmt, m.rows, m.K, m.r0, m.k0, m.phase = name, fmt, rows, K, 0, 0, "wq_b"
    if fmt == "bf16":
        sign = rng.integers(0, 2, (rows, K)).astype(np.uint16) << 15
        ex = rng.integers(118, 128, (rows, K)).astype(np.uint16) << 7
        m.u16 = (sign | ex | rng.integers(0, 128, (rows, K)).astype(np.uint16)).astype(np.uint16)
        m.wf = G.from_bits(m.u16.astype(np.uint32) << 16)
        return m
    m.exp = rng.integers(118, 128, (rows, K // 32)).astype(np.uint8)
    if fmt == "fp8":
        c = rng.integers(0, 256, (rows, K)).astype(np.uint8)
        c[(c & 0x7F) == 0x7F] ^= 1                       # no NaN codes
        m.codes = c
        q = G.E4M3[c]
    else:
        m.nib = rng.integers(0, 16, (rows, K)).astype(np.uint8)
        q = G.E2M1[m.nib]
    m.w = G.Q8(q.astype(np.float64), m.exp.astype(np.int64) - 127)
    return m


# a case: list of ops; an op: (fmt, out_fp32, [(rows, K)...], npos)
CASES = {
    "q8_bf16out_k2048": [("fp8", False, [(48, 2048)], 1)],
    "q4_fp32out_k1536": [("fp4", True, [(40, 1536)], 1)],
    "bf_fp32out_k1024": [("bf16", True, [(8, 1024)], 1)],
    "bf_bf16out_k512": [("bf16", False, [(16, 512)], 1)],
    "q8_k6144_kmax": [("fp8", False, [(32, 6144)], 1)],
    "q8_two_mats_k3072": [("fp8", True, [(24, 3072), (16, 3072)], 1)],
    "mtp_q8_np3": [("fp8", False, [(32, 1024)], 3)],
    "mtp_bf_np2": [("bf16", True, [(8, 1024)], 2)],
    "node4_mixed": [("fp8", False, [(32, 4096)], 1), ("bf16", True, [(8, 1024)], 1),
                    ("fp4", False, [(24, 2048)], 1), ("fp8", True, [(32, 6144)], 1)],
    "node6_tagwrap": [("fp8", False, [(16, 1024)], 1), ("fp8", True, [(16, 512)], 1), ("bf16", False, [(8, 512)], 1),
                      ("fp4", True, [(16, 1024)], 1), ("fp8", False, [(24, 2048)], 1), ("bf16", True, [(8, 1024)], 1)],
    "node3_mtp_mixed": [("fp8", False, [(16, 2048)], 2), ("bf16", False, [(8, 1024)], 2), ("fp4", True, [(16, 1024)], 2)],
}


def make_case(name, img: Path):
    G.set_arith("chunk8")
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(name.encode()).digest()[:4], "little"))
    fld = I.Field(NP, NR, NBF, pp=True, fast=True)
    vm = np.zeros(1 << VAW, dtype=np.uint32)
    expect, opl, ranges = {}, [], []
    xb = 0
    for k, (fmt, fp32, shapes, npos) in enumerate(CASES[name]):
        mats = [syn_mat(rng, fmt, r, K, f"{name}.{k}.{i}") for i, (r, K) in enumerate(shapes)]
        meta = I.add_phase(fld, mats, (fp32, fp32), 0)
        K = shapes[0][1]
        ob = OBASE + k * OSTRIDE
        assert npos * meta["nrows"] <= OSTRIDE
        for pos in range(npos):
            x = F1.rand_x(f"{name}.{k}.{pos}", K, fmt == "bf16")
            vm[xb + pos * XSTRIDE:xb + pos * XSTRIDE + K] = x
            gold = I.golden_phase(mats, G.from_bits(x).astype(G.F))
            for i in range(meta["nrows"]):
                f32, b16 = gold[i]
                expect[ob + pos * meta["nrows"] + i] = f32 if fp32 else (b16 << 16)
        opl.append(f"{k} {npos - 1} {xb} {XSTRIDE} {ob} {meta['nrows']}")
        ranges.append((ob, ob + npos * meta["nrows"]))
        xb += npos * XSTRIDE
        assert xb <= OBASE
    assert len(CASES[name]) <= (1 << PHW)
    I.write_field(fld, img, PHW)
    (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
    (img.parent / "ops.txt").write_text("\n".join(opl) + "\n")
    return expect, ranges


# ------------------------------------------------------------------------------------------------ runs
# (label, build, plusargs, expected verdict)
def variants():
    v = [("ref_v13b_D1", "L", dict(D=1), "pass"),
         ("xrv_real_D14", "X", dict(D=D_REAL), "pass"),
         ("xrv_D1", "X", dict(D=1), "pass"),
         ("xrv_real_minus1", "X", dict(D=D_REAL - 1), "pass"),
         ("xrv_real_plus1", "X", dict(D=D_REAL + 1), "pass"),
         ("xrv_jitter8_s1", "X", dict(D=D_REAL, J=8, S=1), "pass"),
         ("xrv_jitter8_s2", "X", dict(D=D_REAL, J=8, S=2), "pass"),
         ("mut_valid_early", "X", dict(D=D_REAL, K=1), "fail"),
         ("mut_valid_late", "X", dict(D=D_REAL, K=2), "fail"),
         ("mut_cap_below_rtt", "XC", dict(D=D_REAL), "fail"),
         ("mut_legacy_at_real", "L", dict(D=D_REAL), "fail")]
    # fe-push/pqc: --require-pass LABEL[,..] flips a mutant to an expected PASS (the closure loop's negative-control
    # stage: it must then FAIL, i.e. the mutant is still caught)
    return [(l_, b, pa, "pass" if l_ in REQUIRE_PASS else e) for l_, b, pa, e in v]


REQUIRE_PASS: set = set()


def run_one(args):
    work, case, label, build, pq, pa = args
    rd = Path(work) / "runs" / case
    exe = Path(work) / "build" / f"{build}_pq{pq}" / "tb"
    plus = [f"+OT_XD={pa.get('D', 1)}", f"+OT_XJIT={pa.get('J', 0)}", f"+OT_XSKEW={pa.get('K', 0)}",
            f"+OT_XSEED={pa.get('S', 1)}"]
    p = subprocess.run([str(exe), str(rd / "img"), str(rd / "ops.txt"), *plus], capture_output=True, text=True,
                       timeout=3600)
    lines = p.stdout.splitlines()
    w = [(int(t[1]), int(t[2]), int(t[3], 16)) for t in (ln.split() for ln in lines) if t and t[0] == "W"]
    node = next((ln for ln in lines if ln.startswith("NODE ")), "")
    nd = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", node)}
    return dict(case=case, label=label, build=build, pq=pq, plus=plus, rc=p.returncode,
                tail=(lines[-1] if lines else p.stderr[-300:]), writes=w, node=nd)


def judge(r, ref, expect, ranges, real_fixed):
    """Exact = tb PASS, every golden row written once with its golden word, and per op the same ordered (addr, data)
    transactions as the v13b reference.  Rate gate (fixed real latency runs only): no cap stall."""
    seq = [(a, d) for _, a, d in r["writes"]]
    got = {}
    for a, d in seq:
        got.setdefault(a, []).append(d)
    wrong = [a for a, v in expect.items() if got.get(a) != [v]]
    extra = [a for a in got if a not in expect]
    per_op = [[x for x in seq if lo <= x[0] < hi] for lo, hi in ranges]
    ref_op = [[x for x in [(a, d) for _, a, d in ref["writes"]] if lo <= x[0] < hi] for lo, hi in ranges]
    order_ok = per_op == ref_op
    exact = r["rc"] == 0 and r["tail"].startswith("PASS") and not wrong and not extra and order_ok
    stall = r["node"].get("xstall", 0)
    rate_ok = (not real_fixed) or stall == 0
    return dict(exact=exact, rate_ok=rate_ok, verdict="pass" if exact and rate_ok else "fail",
                rows=len(expect), mismatched=len(wrong), extra=len(extra), order_equal_ref=order_ok,
                tb_tail=r["tail"], xstall=stall, xomax=r["node"].get("xomax"),
                go_to_last_w=(r["node"]["last_w"] - r["node"]["go"]) if r["node"].get("last_w", -1) >= 0 else None,
                go_to_idle=(r["node"]["idle"] - r["node"]["go"]) if "idle" in r["node"] else None)


def cmd_run(a):
    work = a.work.resolve()
    exp = {}
    for c in CASES:
        img = work / "runs" / c / "img"
        img.mkdir(parents=True, exist_ok=True)
        exp[c] = make_case(c, img)
    print("images", len(exp), flush=True)
    tasks = [(str(work), c, lab, b, pq, pa) for c in CASES for pq in (0, 1) for lab, b, pa, _ in variants()]
    res = {}
    with cf.ProcessPoolExecutor(a.jobs) as ex:
        for r in ex.map(run_one, tasks):
            res[(r["case"], r["pq"], r["label"])] = r
    want = {lab: e for lab, _, _, e in variants()}
    out_runs, bad = [], []
    for (c, pq, lab), r in sorted(res.items()):
        ref = res[(c, pq, "ref_v13b_D1")]
        pa = next(p for l_, _, p, _ in variants() if l_ == lab)
        real_fixed = pa.get("D") == D_REAL and not pa.get("J")
        j = judge(r, ref, *exp[c], real_fixed)
        out_runs.append(dict(case=c, pq=pq, label=lab, build=r["build"], plusargs=r["plus"], **j))
    # per (variant, pq): a pass variant must pass on EVERY case; a mutant must fail on at least one case (and we
    # report on how many)
    summary = []
    for lab, b, pa, e in variants():
        for pq in (0, 1):
            rs = [x for x in out_runs if x["label"] == lab and x["pq"] == pq]
            npass = sum(x["verdict"] == "pass" for x in rs)
            ok = (npass == len(rs)) if e == "pass" else (npass < len(rs))
            summary.append(dict(variant=lab, pq=pq, expect=e, cases=len(rs), passed=npass,
                                failed=len(rs) - npass, as_expected=ok,
                                fail_modes=sorted({("inexact" if not x["exact"] else "rate") for x in rs
                                                   if x["verdict"] == "fail"})))
            if not ok:
                bad.append((lab, pq))
    # latency price: XRV at the real round trip vs the v13b reference at D 1 (its design point)
    price = []
    for c in CASES:
        for pq in (0, 1):
            r0 = next(x for x in out_runs if x["case"] == c and x["pq"] == pq and x["label"] == "ref_v13b_D1")
            r1 = next(x for x in out_runs if x["case"] == c and x["pq"] == pq and x["label"] == "xrv_real_D14")
            r2 = next(x for x in out_runs if x["case"] == c and x["pq"] == pq and x["label"] == "xrv_D1")
            price.append(dict(case=c, pq=pq, ops=len(CASES[c]),
                              ref_go_to_last_w=r0["go_to_last_w"], xrv_real_go_to_last_w=r1["go_to_last_w"],
                              delta_cycles=(r1["go_to_last_w"] - r0["go_to_last_w"])
                              if None not in (r0["go_to_last_w"], r1["go_to_last_w"]) else None,
                              xrv_D1_minus_ref=(r2["go_to_last_w"] - r0["go_to_last_w"])
                              if None not in (r0["go_to_last_w"], r2["go_to_last_w"]) else None))
    srcs = sources()
    rec = dict(
        schema="opentallas.ds1010.pqc_xrv_bench.v1",
        verdict="PASS" if not bad else "FAIL", unexpected=bad,
        claim_boundary=("Verilator 2-state differential bench of the S81 PQ core (spine v13b / v14 XRV) on the field "
                        "vehicle shape with SYNTHETIC seeded programs (not the 1M golden token: its VM dump is gone); "
                        "each run checked against the chunk8 golden and against the v13b reference's ordered row "
                        "writes per op. The VM model is request-driven and stationed (D edges, in order, valid)."),
        round_trip=dict(QD=QD, D_real=D_REAL, path="2 hub relay stations + ot_s81ph_vm_mem L = QD + 6 + 2 stations",
                        xcap_ok=XCAP_OK, xcap_mutant=XCAP_BAD),
        mutants=dict(mut_valid_early="return valid one edge before its data", mut_valid_late="return valid one edge "
                     "after its data", mut_cap_below_rtt=f"XCAP {XCAP_BAD} < round trip + 1 (rate gate: cap stalls "
                     "at the fixed real latency)", mut_legacy_at_real="v13b fixed one-edge read behind the real path"),
        summary=summary, price=price, runs=out_runs,
        source_sha256={str(s.relative_to(ROOT)): sha(s) for s in srcs + [TB, Path(__file__)]},
        git_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(rec, indent=1) + "\n")
    for s in summary:
        print(f"{s['variant']:20s} pq{s['pq']} expect {s['expect']:4s} passed {s['passed']}/{s['cases']} "
              f"{'OK' if s['as_expected'] else 'UNEXPECTED'} {s['fail_modes']}")
    for p in price:
        print("price", p)
    print("VERDICT", rec["verdict"])
    return 0 if not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("build", "run", "images"))
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--record", type=Path)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--require-pass", default="", help="comma list of mutant labels to expect PASS (negative control)")
    a = ap.parse_args()
    REQUIRE_PASS.update(x for x in a.require_pass.split(",") if x)
    if a.cmd == "build":
        return cmd_build(a)
    if a.cmd == "images":
        for c in CASES:
            img = a.work / "runs" / c / "img"
            img.mkdir(parents=True, exist_ok=True)
            e, r = make_case(c, img)
            print(c, len(e), r)
        return 0
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
