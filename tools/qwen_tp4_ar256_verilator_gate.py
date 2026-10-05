#!/usr/bin/env python3
"""One-stream 256-word all-reduce vs the legacy 2 x 128 split, under Verilator.

Real TP-4 sequencers (ot_qwen_tp_seq_w12, ENABLE_AR256=1), the real collective
(ot_rom_oneshot_allreduce: rank-order binary32 fold, credits, LAT-cycle links),
stub core handshake (rtl/test/tb_qwen_tp4_ar256_vl.sv).  Every case is checked
word by word in RTL against tools/hdc_golden.fold, and the split and one-stream
write logs must be identical.  Vector sets: uniform, and adversarial (subnormals,
signed zeros, near-overflow finite sums, catastrophic cancellation, rank-order
sensitive triples).  Fault behaviour: a sum past the finite range must fault in
both modes, and a corrupted `last` must fault the sequencers.  A DEPTH sweep
measures the credit sizing (Little's law: DEPTH >= min(vector words, 2 LAT + k)).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import hdc_golden as G

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["rtl/rom/ot_qwen_tp_seq_w12.sv", "rtl/rom/ot_rom_oneshot_allreduce.sv",
           "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/test/tb_qwen_tp4_ar256_vl.sv",
           "tools/hdc_golden.py", "tools/qwen_tp4_ar256_verilator_gate.py"]
VERILATOR = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vectors(kind, rng):
    f32 = np.float32
    if kind == "uniform":
        return rng.uniform(-4, 4, (4, 256, 16)).astype(f32)
    if kind == "overflow":
        p = rng.uniform(-1, 1, (4, 256, 16)).astype(f32)
        p[:, 77, 5] = np.array([3.0e38, 3.0e38, 1.0, 1.0], dtype=f32)   # p0 + p1 rounds past FLT_MAX
        return p
    # adversarial: magnitudes spanning subnormal to near FLT_MAX, per lane
    e = rng.integers(-149, 128, (4, 256, 16))
    m = rng.uniform(1, 2, (4, 256, 16))
    p = (np.sign(rng.uniform(-1, 1, (4, 256, 16))) * m * np.exp2(e.astype(np.float64)))
    p = np.clip(p, -3.0e38, 3.0e38).astype(f32)
    tiny = np.float32(1.401298464324817e-45)                    # smallest subnormal
    big = np.float32(3.3e38)
    w = 0
    # rank-order sensitive: ((2^24 + 1) - 2^24) + 1 = 1 + 1 = 2 vs balanced tree 1
    p[:, w, 0] = [2**24, 1, -(2**24), 1]
    p[:, w, 1] = [0.0, -0.0, 0.0, -0.0]
    p[:, w, 2] = [-0.0, -0.0, -0.0, -0.0]                        # canonical +0 result
    p[:, w, 3] = [tiny, tiny, -tiny, tiny]                         # subnormal arithmetic
    p[:, w, 4] = [big, -big, big, -big]                            # near-overflow, exact cancellation
    p[:, w, 5] = [big, big * np.float32(-0.5), big * np.float32(-0.5), tiny]
    p[:, w, 6] = [1.1754942e-38, -1.1754942e-38 / 2, 1e-45, -1e-45]  # normal/subnormal boundary
    p[:, w, 7] = [1.0, 1e-8, 1e-8, 1e-8]                          # sub-ulp addends, round to even
    p[:, 1:9, 8:16] = rng.choice(np.array([0.0, -0.0, tiny, -tiny, 1e-40, -1e-40], dtype=f32), (4, 8, 8))
    # near-overflow finite sums on whole words
    p[:, 9, :] = np.array([[big, -big * np.float32(0.9), big * np.float32(0.9), -big]] * 16, dtype=f32).T
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--lat", type=int, default=339)
    ap.add_argument("--depths", default="128,256,512,1024")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    if args.result.exists():
        raise SystemExit("Refusing to overwrite an existing verdict")
    args.work.mkdir(parents=True, exist_ok=False)
    pins = {p: sha(ROOT / p) for p in SOURCES}
    depths = [int(x) for x in args.depths.split(",")]
    result = {"schema": "opentallas.qwen-tp4-ar256-verilator-gate.v1", "status": "fail", "source_sha256": pins,
              "simulator": subprocess.check_output([VERILATOR, "--version"], text=True).strip(),
              "design_point": {"tp": 4, "lanes": 16, "elements": 4096, "lat": args.lat, "depths": depths},
              "builds": {}, "cases": {},
              "claim_boundary": "Real sequencers, VM word ports, rank-order binary32 collective and links under "
                                "Verilator; stub core handshake.  No layer/token claim; no SS/FF sign-off."}
    bins = {}
    try:
        for depth in depths:
            mdir = args.work / f"obj_d{depth}"
            t0 = time.monotonic()
            p = subprocess.run([VERILATOR, "--binary", "--timing", "-O3", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                                "-Wno-TIMESCALEMOD", "-Wno-PINMISSING", "-Wno-INITIALDLY", "-Wno-BLKSEQ",
                                "--top-module", "tb_qwen_tp4_ar256_vl", f"-GDEPTH={depth}", f"-GLAT={args.lat}",
                                "--Mdir", str(mdir), "-j", "8", *(str(ROOT / s) for s in SOURCES[:4])],
                               capture_output=True, text=True)
            (args.work / f"build_d{depth}.log").write_text(p.stdout + p.stderr)
            result["builds"][depth] = {"returncode": p.returncode, "seconds": round(time.monotonic() - t0, 1)}
            if p.returncode:
                raise RuntimeError(f"verilator build DEPTH={depth} failed: {p.stderr[-2000:]}")
            bins[depth] = mdir / "Vtb_qwen_tp4_ar256_vl"

        def run(name, depth, vec, split, inject=0, expect_fault=0):
            p = subprocess.run([str(bins[depth]), f"+VEC={vec}", f"+SPLIT={split}", f"+INJECT_LAST={inject}",
                                f"+EXPECT_FAULT={expect_fault}"], capture_output=True, text=True, timeout=3600)
            log = args.work / f"{name}.log"
            log.write_text(p.stdout + p.stderr)
            m = re.search(r"QWEN_AR256VL PASS .*cycles=(\d+) .*mismatches=(\d+) seq_fault=([01]+) coll_fault=([01]+) "
                          r"codes=([0-9a-f]+) first_err_word=(-?\d+) stalls=(\d+)", p.stdout)
            if p.returncode or not m:
                raise RuntimeError(f"{name}: no PASS verdict\n{p.stdout[-1500:]}{p.stderr[-1500:]}")
            writes = [l for l in p.stdout.splitlines() if l.startswith("W ")]
            case = {"depth": depth, "split": split, "cycles": int(m[1]), "mismatches": int(m[2]), "seq_fault": m[3],
                    "coll_fault": m[4], "fault_codes": m[5], "first_err_word": int(m[6]), "link_stalls": int(m[7]),
                    "writes_sha256": hashlib.sha256("\n".join(writes).encode()).hexdigest(), "log_sha256": sha(log)}
            result["cases"][name] = case
            return case

        def emit(path, array):
            path.write_text("".join("".join(f"{int(v):08x}" for v in row[::-1]) + "\n" for row in array))

        sets = [("uniform", s) for s in range(args.seeds)] + [("adversarial", s) for s in range(args.seeds)]
        top = max(depths)
        for kind, seed in sets + [("overflow", 0)]:
            vec = args.work / f"v_{kind}{seed}"
            vec.mkdir()
            parts = vectors(kind, np.random.default_rng(20261003 + seed))
            with np.errstate(over="ignore"):
                summ = G.fold(parts)
            for d in range(4):
                emit(vec / f"part_die{d}.hex", G.bits(parts[d]))
            emit(vec / "sum.hex", G.bits(summ))
            tag = f"{kind}{seed}"
            if kind == "overflow":
                assert not np.isfinite(summ).all()
                a = run(f"{tag}_split128", top, vec, 1, expect_fault=1)
                b = run(f"{tag}_one256", top, vec, 0, expect_fault=1)
                if a["first_err_word"] != b["first_err_word"] or a["fault_codes"] != b["fault_codes"]:
                    raise RuntimeError("fault behaviour differs between split and one-stream")
                continue
            assert np.isfinite(summ).all()
            if kind == "adversarial":
                flat = G.bits(parts).ravel()
                result.setdefault("adversarial_coverage", {})[tag] = {
                    "subnormal_partials": int((((flat & 0x7F800000) == 0) & ((flat & 0x7FFFFFFF) != 0)).sum()),
                    "negative_zero_partials": int((flat == 0x80000000).sum()),
                    "partials_above_1e38": int((np.abs(parts) > 1e38).sum()),
                    "subnormal_sums": int((((G.bits(summ) & 0x7F800000) == 0) & ((G.bits(summ) & 0x7FFFFFFF) != 0)).sum())}
            a = run(f"{tag}_split128", top, vec, 1)
            b = run(f"{tag}_one256", top, vec, 0)
            if a["writes_sha256"] != b["writes_sha256"]:
                raise RuntimeError(f"{tag}: one-stream output differs from split")
            if kind == "uniform" and seed == 0:
                run(f"{tag}_one256_bad_last", top, vec, 0, inject=1)
                for depth in depths:
                    if depth != top:
                        c = run(f"{tag}_one256_depth{depth}", depth, vec, 0)
                        if c["writes_sha256"] != b["writes_sha256"]:
                            raise RuntimeError(f"DEPTH {depth} output differs")
        one = result["cases"]["uniform0_one256"]["cycles"]
        spl = result["cases"]["uniform0_split128"]["cycles"]
        result["cycles"] = {"split128": spl, "one256": one, "saved_per_allreduce": spl - one,
                            "one256_by_depth": {d: result["cases"][f"uniform0_one256_depth{d}" if d != top
                                                                   else "uniform0_one256"]["cycles"] for d in depths}}
        result["source_stable"] = pins == {p: sha(ROOT / p) for p in SOURCES}
        if not result["source_stable"] or spl - one <= 0:
            raise RuntimeError("source instability or no cycle gain")
        result["status"] = "pass"
    except Exception as exc:  # the verdict is recorded either way
        result["error"] = str(exc)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    with args.result.open("x") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "cycles": result.get("cycles"), "error": result.get("error")},
                     indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
