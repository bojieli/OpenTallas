#!/usr/bin/env python3
"""Performance + exactness campaign for the V4.1x candidate-block select (layer 20):
rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv -- block max over 8, newest block pinned to +inf, top-k
blocks (k = 2,048 shipped), at the indexer's 64 scores/cycle (4 quarters x 16 score lanes,
8 block lanes), in place of the 64 x 64 candidate array.

The golden is tools/hdc_golden_v41.py `Model.candidate_blocks` itself (called with the
shipped block size and k); every segment's kept block list must be bit-exact.  Families:
shipped per-die sizes (200K: 50,000 scores / 6,250 blocks; 1M: 262,144 / 32,768) with
normal / uniform / recency / real reduced-vehicle scores (resampled and the real L20
streams tiled), filter worst cases (ascending -> overflow replay, all equal, masked),
coverage (random n not a multiple of 8, random k, random 8-aligned quarter cuts, bubbles,
output back-pressure), and the real reduced vehicle's own L20 candidate selections
(block 8, k = 64) on a reduced instance.  Spec (docs/ARCH_SPEC_V41.md section 6 item 6):
64 scores/cycle ingest and done within ~20 us (4 layer times) at 1M per die.

Writes results/rtl/hdc_v41x_sel_cand_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41x_sel_campaign as S  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_sel_cand_campaign.json"
RTL = S.RTL + [ROOT / "rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv"]
TB = ROOT / "rtl/test/tb_hdc_v41x_sel_cand.sv"
HARNESS = ROOT / "rtl/test/hdc_v41x_sel_cand_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/rtl_hdc_v41x_sel_campaign.py", Path(__file__)]
SUMMARY = re.compile(S.SUMMARY.pattern.replace("V41XSEL ", "V41XSELC "))
CLOCK_HZ = 1.034e9
BUDGET_S = 20e-6
NINF = S.NINF


def golden_blocks(bits, cand_b, k):
    """Kept block indices (ascending) from the golden's own candidate_blocks."""
    s = S.vals_of(bits)
    fake = types.SimpleNamespace(cand_b=cand_b, cand_k=k)
    keep = G.Model.candidate_blocks(fake, s, len(s))[::cand_b]
    return [int(i) for i in np.nonzero(keep)[0]]


def segment(rng, bits, k, SL, Q=4, cut="even", cand_b=8, K=None):
    """(per-quarter beats, k, per-quarter expected blocks, meta); the unit clamps k to K."""
    bits = np.asarray(bits, np.int64)
    n = len(bits)
    kept = golden_blocks(bits, cand_b, k if K is None else min(k, K))
    nb = -(-n // cand_b)
    if cut == "even":
        c = [((nb * j) // Q) * cand_b for j in range(Q + 1)]
    else:
        c = [0] + sorted(int(x) * cand_b for x in rng.integers(0, nb, Q - 1)) + [nb * cand_b]
    c[-1] = n
    c = [min(x, n) for x in c]
    # quarter Q-1 must hold the newest position: pull the last cut below n
    if c[Q - 1] >= n:
        c[Q - 1] = ((n - 1) // cand_b) * cand_b
        for j in range(Q - 1):
            c[j] = min(c[j], c[Q - 1])
    beats, exps = [], []
    for q in range(Q):
        lo, hi = c[q], c[q + 1]
        bq = []
        for b0 in range(lo, hi, SL):
            lanes = [(int(bits[i]), i) if i < hi else None for i in range(b0, b0 + SL)]
            bq.append(lanes)
        if not bq:
            bq.append([None] * SL)
        beats.append(bq)
        exps.append([b for b in kept if lo <= b * cand_b < hi])
    return beats, k, exps, {"n": n, "blocks": nb}


def write_vectors(segs, Q, SL, d: Path, tag):
    pfx = d / tag
    h = hashlib.sha256()
    for q in range(Q):
        li, le = [], []
        for beats, k, exps, _ in segs:
            bq = beats[q]
            for bi, lanes in enumerate(bq):
                lv = sum(1 << j for j, e in enumerate(lanes) if e is not None)
                fields = " ".join(f"{e[0]:x} {e[1]:x}" if e else "0 0" for e in lanes)
                li.append(f"{int(bi == len(bq) - 1)} {k} {lv:x} {fields}\n")
            le.append(f"S {len(exps[q])} {len(bq)}\n")
            le += [f"{b:x}\n" for b in exps[q]]
        Path(f"{pfx}.in{q}").write_text("".join(li))
        Path(f"{pfx}.exp{q}").write_text("".join(le))
        h.update(Path(f"{pfx}.in{q}").read_bytes() + Path(f"{pfx}.exp{q}").read_bytes())
    return pfx, {"vectors_sha256": h.hexdigest(), "segments": len(segs)}


def build(obj: Path, Q, SL, IW, K, AW, maxb=8192):
    obj.mkdir(parents=True, exist_ok=True)
    subprocess.run([S.VERILATOR, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module", "tb_hdc_v41x_sel_cand",
                    f"-GQ={Q}", f"-GSL={SL}", f"-GIW={IW}", f"-GK={K}", f"-GAW={AW}", f"-GMAXB={maxb}",
                    "-Mdir", str(obj), *[str(p) for p in RTL], str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"],
                   check=True, capture_output=True)
    return obj / "Vtb_hdc_v41x_sel_cand"


def simulate(binary, pfx, bub=0, ordy=0, seed=1):
    r = subprocess.run([str(binary), f"+PFX={pfx}", f"+BUBBLE={bub}", f"+ORDY={ordy}", f"+SEED={seed}"],
                       capture_output=True, text=True)
    out = r.stdout.replace("V41XSELC ", "V41XSEL ")
    return S.parse(out)


def run_config(name, Q, SL, IW, K, AW, segs, labels, d, runs=((0, 0, 1),)):
    pfx, st = write_vectors(segs, Q, SL, d, name)
    b = build(d / f"obj_{name}", Q, SL, IW, K, AW)
    out = []
    for bub, ordy, seed in runs:
        r = simulate(b, pfx, bub, ordy, seed)
        for ps, lab, sg in zip(r.get("per_segment", []), labels, segs):
            ps["family"] = lab
            ps["n"] = sg[3]["n"]
            ps["blocks"] = sg[3]["blocks"]
            ps["total_cycles"] = ps["last"] - ps["first"] + 1 + ps["tail"]
            ps["total_us"] = round(ps["total_cycles"] / CLOCK_HZ * 1e6, 3)
        out.append({"bubble_pct": bub, "out_ready_low_pct": ordy, "seed": seed, **r})
    return {"name": name, "Q": Q, "SL": SL, "IW": IW, "K": K, "AW": AW, **st, "runs": out,
            "pass": all(r["pass"] for r in out)}


def run(quick=False, real_positions=160, workers=6):
    d = Path(tempfile.mkdtemp(prefix="v41xselc_", dir=S.SCRATCH))
    real = S.real_sets(real_positions, S.SCRATCH / f"v41xsel_real_{real_positions}.pkl")
    pool = np.concatenate([b for (_, _, b) in real["sets"]])
    streams = [b for (L, p, b) in real["sets"] if L == real["cand_src"] and len(b) >= 16]
    rng = np.random.default_rng(20260927)
    K, SL, IW, AW = 2048, 16, 20, 10
    reps = 1 if quick else 2
    jobs = []
    fams = ["normal", "uniform", "recency", "real_resampled", "real_tiled"]
    for n, tag in ((50000, "shipped_200k"), (262144, "shipped_1m")):
        segs, labs = [], []
        for f in fams:
            for _ in range(reps):
                segs.append(segment(rng, S.family(rng, f, n, K, pool, streams), K, SL))
                labs.append(f)
        jobs.append((tag, 4, SL, IW, K, AW, segs, labs, ((0, 0, 1),)))
    segs, labs = [], []
    for f, n in (("ascending", 50000), ("descending", 50000), ("all_equal", 50000), ("masked", 50000),
                 ("masked_few", 50000), ("ascending", 262144)):
        segs.append(segment(rng, S.family(rng, f, n, K, pool, streams), K, SL))
        labs.append(f)
    jobs.append(("worst_cases", 4, SL, IW, K, AW, segs, labs, ((0, 0, 1),)))
    # coverage: reduced K and small memories, random n / k / cuts, bubbles + back-pressure
    segs, labs = [], []
    Kc = 64
    for _ in range(60 if quick else 500):
        n = int(rng.integers(1, 6000))
        k = Kc if rng.random() < 0.6 else int(rng.integers(0, 128))
        f = ["normal", "ties", "raw", "masked", "masked_few", "ascending", "recency", "real_resampled"][int(rng.integers(0, 8))]
        segs.append(segment(rng, S.family(rng, f, n, max(k, 1), pool, streams), k, SL, 4,
                            "random" if rng.random() < 0.6 else "even", K=Kc))
        labs.append(f)
    jobs.append(("coverage_k64_aw6", 4, SL, 16, Kc, 6, segs, labs, ((0, 0, 1), (15, 40, 3))))
    # the real reduced vehicle's L20 candidate selections (block 8, k = cand_k)
    segs, labs = [], []
    for (L, p, b) in real["sets"]:
        if L == real["cand_src"]:
            segs.append(segment(rng, b, real["candidate_topk_blocks"], SL, 4, "even"))
            labs.append(f"real_L{L}_p{p}")
    jobs.append(("real_reduced_k64", 4, SL, 16, real["candidate_topk_blocks"], 6, segs, labs, ((0, 0, 1), (15, 40, 3))))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        configs = [f.result() for f in [ex.submit(run_config, *j) for j in jobs]]
    rows = []
    for c in configs:
        if c["name"] in ("shipped_200k", "shipped_1m", "worst_cases"):
            for ps in c["runs"][0].get("per_segment", []):
                rows.append({kk: ps[kk] for kk in ("family", "n", "blocks", "k", "tail", "stall", "ovf", "total_cycles",
                                                   "total_us", "first", "last", "nhead", "n2", "n3")})
    typical = [r for r in rows if r["family"] in fams]
    one_m = [r for r in typical if r["n"] == 262144]
    rate = min((r["n"] / (r["last"] - r["first"] + 1) for r in typical), default=None)
    ok = all(c["pass"] for c in configs)
    spec = {
        "exact_golden_equality": {"measured": ok, "met": ok},
        "ingest_scores_per_cycle": {"spec": 64, "measured_min": round(rate, 3) if rate else None,
                                    "stall_cycles": sum(r["stall"] for r in typical),
                                    "met": rate is not None and rate >= 63.9 and sum(r["stall"] for r in typical) == 0},
        "done_within_20us_at_1m": {"spec_us": 20.0, "measured_max_us": max((r["total_us"] for r in one_m), default=None),
                                   "measured_max_cycles": max((r["total_cycles"] for r in one_m), default=None),
                                   "clock_hz": CLOCK_HZ,
                                   "met": bool(one_m) and max(r["total_us"] for r in one_m) <= 20.0},
        "worst_case_1m_ascending_us": max((r["total_us"] for r in rows if r["family"] == "ascending" and r["n"] == 262144),
                                          default=None),
    }
    return {
        "schema": "opentallas-rtl-campaign-v1",
        "block": "sel (layer-20 candidate-block select)",
        "rtl": {str(p.relative_to(ROOT)): S.sha(p) for p in RTL},
        "bench": {str(p.relative_to(ROOT)): S.sha(p) for p in (TB, HARNESS)},
        "tools": {str(p.relative_to(ROOT)): S.sha(p) for p in TOOLS},
        "simulator": subprocess.run([S.VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
        "real_vehicle": {"positions": real["positions"], "cand_src": real["cand_src"],
                         "candidate_topk_blocks": real["candidate_topk_blocks"],
                         "candidate_block_size": real["candidate_block_size"]},
        "status": "pass" if ok and spec["done_within_20us_at_1m"]["met"] and spec["ingest_scores_per_cycle"]["met"] else "fail",
        "spec": spec, "shipped": rows, "configs": configs, "quick": quick,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--real-positions", type=int, default=160)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--output", type=Path, default=OUT)
    a = ap.parse_args()
    res = run(a.quick, a.real_positions, a.workers)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(res, indent=1, default=int) + "\n")
    print(json.dumps(res["spec"], indent=1, default=int))
    print("status", res["status"])
    return 0 if res["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
