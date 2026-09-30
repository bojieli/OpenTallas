#!/usr/bin/env python3
"""W15b: COLL_TOPK_MERGE select unit (rtl/chip/ot_coll_topk_merge.sv) against the golden, end to end in RTL.

    python3 tools/w15_topk_merge.py run [--n-ranks 4] [--nmax 2048] [--p 64] [--dig 4] --work DIR [--out JSON]

Builds cases (the two L20 uses: n = k = 512 with BF16-valued scores, n = k = 2048 with block maxima and one +inf pin;
ties, -0 / +0, -inf, k = 1 and k = N*n), runs the Verilator bench, checks every output id against
    sorted(global_ids[topk_lowest_index(global_scores, k)])        (tools/hdc_golden_v41.topk_lowest_index)
and records the cycles go -> done for each case.  Semantics: the COLL_TOPK_MERGE contract of W17's L20 ISA record
(branch claude/w17-isa-l20): global id = rank * stride + local id, ids ascending in each rank's list.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as GV  # noqa: E402

SRC = ["rtl/test/tb_w15_topk_merge.sv", "rtl/chip/ot_coll_topk_merge.sv"]
VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
VFLAGS = ["--binary", "--timing", "-Wno-fatal", "-Wno-WIDTH", "-Wno-lint", "-Wno-style", "-Wno-MULTIDRIVEN"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bf16(x):
    b = np.asarray(x, np.float32).view(np.uint32)
    r = ((b.astype(np.uint64) + 0x7FFF + ((b >> 16) & 1)) >> 16 << 16).astype(np.uint32)
    return r.view(np.float32)


def cases(N, nmax, rng):
    out = []
    # L20 use 1: index top-k, n = k = 512, BF16-valued scores (heavy ties), stride SC1 = 262,144
    if nmax >= 512:
        s = bf16(rng.normal(0, 1, (N, 512)).astype(np.float32) * 4)
        out.append(("l20_index_topk", 512, 512, 262144, s))
    # L20 use 2: candidate blocks, n = k = 2048 (block maxima, one +inf pin), stride 32,768
    if nmax >= 2048:
        s = bf16(rng.normal(0, 1, (N, 2048)).astype(np.float32) * 8)
        s[1, 7] = np.inf
        out.append(("l20_candidate_blocks", 2048, 2048, 32768, s))
    # stress: small k over ties, signed zeros and -inf; argmax (k = 1) with a tie; k = N*n
    n = min(nmax, 256)
    s = rng.choice(np.array([0.0, -0.0, 1.0, -1.0, 2.5, -np.inf, np.inf, 1e-40], np.float32), size=(N, n))
    out.append(("ties_zeros_inf_k37", n, 37, 1000, s.copy()))
    out.append(("ties_zeros_inf_kall", n, N * n, 1000, s.copy()))
    s2 = rng.normal(0, 1, (N, n)).astype(np.float32)
    s2[2, 5] = s2[0, 9] = np.float32(9.0)
    out.append(("argmax_tie_k1", n, 1, 4096, s2))
    s3 = np.zeros((N, n), np.float32)
    s3[:, ::2] = -0.0
    out.append(("all_zero_signed_k100", n, 100, 777, s3))
    s4 = rng.uniform(-1, 1, (N, n)).astype(np.float32)
    out.append(("uniform_k_half", n, N * n // 2, 1 << 20, s4))
    s5 = np.full((N, n), -np.inf, np.float32)
    s5[3, 1] = -1e30
    out.append(("mostly_neg_inf_k17", n, 17, 300, s5))
    return out


def golden(s, stride, k):
    N, n = s.shape
    ids = (np.arange(N)[:, None] * stride + np.arange(n)[None, :]).reshape(-1).astype(np.int64)
    sel = GV.topk_lowest_index(s.reshape(-1), k)
    return sorted(int(ids[i]) for i in sel)


def run(a):
    N, nmax = a.n_ranks, a.nmax
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260930)
    cs = cases(N, nmax, rng)
    CAP = N * nmax
    sc = np.zeros((len(cs), CAP // 16, 16), np.uint32)
    idw = np.zeros((len(cs), CAP // 16, 16), np.uint32)
    lines = []
    for c, (name, n, k, stride, s) in enumerate(cs):
        flat = s.reshape(-1).view(np.uint32)
        sc[c, : N * n // 16] = flat.reshape(-1, 16)
        idw[c, : N * n // 16] = np.tile(np.arange(n, dtype=np.uint32), N).reshape(-1, 16)
        lines.append(f"{n:08x}{k:08x}{stride:08x}")

    def wr(path, arr):
        with open(path, "w") as f:
            for w in arr.reshape(-1, 16):
                f.write("".join(f"{int(x):08x}" for x in w[::-1]) + "\n")
    (work / "cases.hex").write_text("\n".join(lines) + "\n")
    wr(work / "score.hex", sc)
    wr(work / "id.hex", idw)
    bd = work / "build"
    cmd = [str(VERILATOR), *VFLAGS, "-j", "8", "--top-module", "tb_w15_topk_merge", "-Mdir", str(bd),
           f"-GN={N}", f"-GNMAX={nmax}", f"-GP={a.p}", f"-GDIG={a.dig}", f"-GNCASE={len(cs)}", *SRC]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-4000:])
    r = subprocess.run([str(bd / "Vtb_w15_topk_merge"), f"+VEC={work}"], capture_output=True, text=True,
                       timeout=7200)
    log = r.stdout
    (work / "log.txt").write_text(log + r.stderr)
    got = [int(x, 16) for x in (work / "out.hex").read_text().split()]
    rows, pos = [], 0
    tl = [l for l in log.splitlines() if l.startswith("TOPK ")]
    for c, (name, n, k, stride, s) in enumerate(cs):
        f = dict(kv.split("=") for kv in tl[c].split()[1:])
        words = int(f["words"])
        out = got[pos: pos + 16 * words]
        pos += 16 * words
        want = golden(s, stride, k)
        ok = out[:k] == want and all(x == 0 for x in out[k:]) and words == math.ceil(k / 16) and f["fault"] == "0"
        rows.append(dict(case=name, ranks=N, n=n, k=k, stride=stride, cycles=int(f["cycles"]), words=words,
                         exact=ok))
    rec = dict(schema="w15_topk_merge_v1",
               claim_boundary="Cycle-accurate RTL simulation (Verilator 5.050) of the select unit alone, loaded "
                              "with the gathered candidates; cycles are go -> done at the unit's clock (the "
                              "gather is the all-gather's, measured by tools/w15_collectives.py).",
               parameters=dict(N=N, NMAX=nmax, P=a.p, DIG=a.dig),
               cycle_model="(32/DIG) x (N*n/P + ~9) + N*n/P + ~9 (HIST passes, PICK, FILTER)",
               golden="tools/hdc_golden_v41.topk_lowest_index over rank-major global scores, then sorted ids",
               cases=rows, all_exact=all(r["exact"] for r in rows),
               source_sha256={p: sha(ROOT / p) for p in [*SRC, "tools/w15_topk_merge.py", "tools/hdc_golden_v41.py"]},
               git=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
               dirty=[l for l in subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                                                text=True).stdout.splitlines() if l.strip()])
    print(json.dumps(rows, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--n-ranks", type=int, default=4)
    r.add_argument("--nmax", type=int, default=2048)
    r.add_argument("--p", type=int, default=64)
    r.add_argument("--dig", type=int, default=4)
    r.add_argument("--work", required=True)
    r.add_argument("--out")
    a = ap.parse_args(argv)
    run(a)


if __name__ == "__main__":
    main()
