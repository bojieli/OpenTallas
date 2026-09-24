#!/usr/bin/env python3
"""RTL campaign for the V4.1 decode core's Engram hash and router softplus pipes.

Runs, from the repository root:

1. the correctly rounded binary32 pipes under Verilator:
   * rtl/hdc/v41/ot_hdc_fdiv.sv against the host's IEEE division, and
   * rtl/hdc/v41/ot_hdc_fsqrt.sv against the host's IEEE square root and,
     cycle for cycle (one cycle later), against the qualified
     rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv,
   on edge-biased operands (subnormals, zeros, ties, nonfinite) with bubbles;
2. rtl/hdc/v41/ot_hdc_engram_hash.sv on token streams -- the oracle workload's
   prompt and generated ids, a tokenised text, and random streams (including
   ids outside the compressed vocabulary and every 12-bit extreme) -- every
   hash column's row address against tools/hdc_golden_v41.EngramTables.hashes;
3. rtl/hdc/v41/ot_hdc_softplus.sv on random arguments (every binade, both
   signs, subnormals, zeros, the exp clamp edges, nonfinite) and on the REAL
   router inputs of the reduced V4.1 model (the golden's gate matvec at every
   layer of the oracle's 24 positions), softplus and sqrt(softplus) against
   tools/hdc_golden_v41.softplus / .sqrt;
4. a Verilator lint of both tops.

Steps 2-3 run under both Icarus and Verilator with random input bubbles, bit
for bit.  The Engram constant tables are generated from the golden
(`--emit-tables` rewrites rtl/hdc/v41/ot_hdc_engram_tables_pkg.sv).  Writes
results/rtl/hdc_v41_engram_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("OPENTALLAS_BUILD", str(ROOT / "build"))
import hdc_golden_v41 as G  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_engram_campaign.json"
V41 = ROOT / "rtl/hdc/v41"
TABLES = V41 / "ot_hdc_engram_tables_pkg.sv"
HASH = V41 / "ot_hdc_engram_hash.sv"
SOFTPLUS = V41 / "ot_hdc_softplus.sv"
FDIV = V41 / "ot_hdc_fdiv.sv"
FSQRT = V41 / "ot_hdc_fsqrt.sv"
QSQRT = ROOT / "rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv"
HDC = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_sfu")]
PIPES = [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
SP_SOURCES = [SOFTPLUS, FDIV, FSQRT, *HDC, *PIPES]
TB_HASH = ROOT / "rtl/test/tb_hdc_engram_hash.sv"
TB_SP = ROOT / "rtl/test/tb_hdc_softplus.sv"
TB_SQEQ = ROOT / "rtl/test/tb_hdc_fsqrt_equiv.sv"
TB_HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
ARITH_HARNESS = ROOT / "rtl/test/hdc_v41_arith_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_golden_v41.py", Path(__file__)]
ARITH_VECTORS = 20_000_000
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-PINCONNECTEMPTY",
              "-Wno-IMPORTSTAR")
VL_FLAGS = ("--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ")
# a tokenised text stream (natural-language n-grams) for the hash
TEXT = ("The hardwired decode core streams one token position per cycle through the Engram hash: "
        "the last four compressed token ids are multiplied by per-layer constants, combined by XOR, "
        "and reduced modulo a prime per head.  Each residue, plus the head's offset, is the row of the "
        "embedding table that the lookup reads.  The router scores every expert with the square root "
        "of softplus, adds a bias, and keeps the top six.  1, 2, 3; x = y + z; (a) [b] {c} -- done!")
RE_ARITH = re.compile(r"ARITH checked=(\d+) mismatches=(\d+) faults=(\d+) subnormal_results=(\d+)")
RE_SQEQ = re.compile(r"SQRTEQ checked=(\d+) refused=(\d+) mismatches=(\d+)")
RE_HASH = re.compile(r"ENGRAM vectors=(\d+) checked=(\d+) errors=(\d+) cycles=(\d+)")
RE_SP = re.compile(r"SOFTPLUS vectors=(\d+) checked=(\d+) errors=(\d+) faults=(\d+) cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- Engram constant tables ------------------------------------------------------------
def engram_tables():
    c = json.loads(G.CONFIG.read_text())
    return G.EngramTables(c, c["vocab_size"])


def _packed(entries, width):
    """A packed Verilog constant with entries[i] at [width*i +: width]."""
    v = 0
    for i, e in enumerate(entries):
        assert 0 <= int(e) < (1 << width), (e, width)
        v |= int(e) << (width * i)
    total = width * len(entries)
    return f"{total}'h{v:0{(total + 3) // 4}x}"


def emit_tables() -> str:
    t = engram_tables()
    layers, n, heads = len(t.layer_ids), t.n, t.primes.shape[2]
    cols = (n - 1) * heads
    primes = t.primes.reshape(layers, cols)
    rows = t.offsets + primes
    res_w = int(primes.max()).bit_length()
    row_w = int(rows.max() - 1).bit_length()
    id_w = 12
    assert len(t.token_map) <= (1 << id_w) and t.pad < (1 << id_w)
    nib = [int(t.multipliers[li, s]) * d for li in range(layers) for s in range(n) for d in range(16)]
    res, lines = [], []
    for li in range(layers):
        for col in range(cols):
            q = int(primes[li, col])
            res.extend((d << (4 * j)) % q for j in range(16) for d in range(16))
    per_col = 16 * 16
    res_chunks = [_packed(res[i:i + per_col], res_w) for i in range(0, len(res), per_col)]
    lines += [
        "`timescale 1ns/1ps",
        "// GENERATED by tools/rtl_hdc_v41_engram_campaign.py --emit-tables from",
        "// tools/hdc_golden_v41.EngramTables (the release's EngramLayout / NgramHashState).",
        "// Do not edit.  tests/test_hdc_v41_engram_rtl.py checks it is current.",
        "package ot_hdc_engram_tables_pkg;",
        f"    localparam integer ENG_LAYERS = {layers};      // Engram layers {list(t.layer_ids)}",
        f"    localparam integer ENG_N      = {n};      // max n-gram order",
        f"    localparam integer ENG_HEADS  = {heads};",
        f"    localparam integer ENG_COLS   = {cols};     // (N-1) * HEADS hash columns per layer",
        f"    localparam integer ENG_ID_W   = {id_w};     // compressed token id width",
        f"    localparam integer ENG_RES_W  = {res_w};     // residue width (largest prime {int(primes.max())})",
        f"    localparam integer ENG_ROW_W  = {row_w};     // row address width (largest table {int(rows.max())} rows)",
        f"    localparam [{id_w - 1}:0] ENG_PAD = {id_w}'d{t.pad};   // compressed id of the pad token",
        "    // ENG_NIB[p*16 + d] = d * multiplier[layer][s], p = layer*N + s",
        f"    localparam [{64 * len(nib) - 1}:0] ENG_NIB = {_packed(nib, 64)};",
        "    // ENG_PRIME[c], ENG_OFFSET[c]: column c = layer*COLS + (s-1)*HEADS + head",
        f"    localparam [{res_w * layers * cols - 1}:0] ENG_PRIME = {_packed(primes.reshape(-1), res_w)};",
        f"    localparam [{row_w * layers * cols - 1}:0] ENG_OFFSET = {_packed(t.offsets.reshape(-1), row_w)};",
        "    // ENG_RES[(c*16 + j)*16 + d] = (d << 4j) mod prime[c]; one line per column, column 0 last",
        f"    localparam [{res_w * len(res) - 1}:0] ENG_RES = {{",
    ]
    lines += [f"        {chunk}{',' if i else ''}" for i, chunk in reversed(list(enumerate(res_chunks)))]
    lines += ["    };", "endpackage", ""]
    return "\n".join(lines)


# -- vectors ------------------------------------------------------------------------------
def engram_streams(t, rng):
    """Sequences of compressed ids: (name, [cid, ...])."""
    prompt, gen = G.prompt_and_expected()
    real = [int(t.token_map[i]) for i in prompt + gen]
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(G.TOKENIZER))
    text_ids = [i for i in tok.encode(TEXT).ids if i < len(t.token_map)]
    text = [int(t.token_map[i]) for i in text_ids]
    cv = int(t.token_map.max()) + 1
    streams = [("oracle_workload", real), ("tokenised_text", text),
               ("single_positions", [0]), ("pad_ids", [t.pad] * 6),
               ("extremes", [0, 4095, cv - 1, cv, 4095, 4095, 0, 0, 2048, 4095, 1, t.pad])]
    for k in range(600):
        length = int(rng.integers(1, 60))
        if k % 3 == 0:
            ids = rng.integers(0, 4096, length)             # the whole 12-bit id space
        elif k % 3 == 1:
            ids = rng.integers(0, cv, length)               # the model's compressed vocabulary
        else:
            ids = rng.choice([0, 1, t.pad, cv - 1, cv, 4094, 4095], length)
        streams.append((f"random_{k}", [int(i) for i in ids]))
    return streams


def engram_vectors(path: Path, t, rng):
    """One line per position: first cid row[0] .. row[L*C-1] (hex)."""
    ident = type(t).__new__(type(t))
    ident.__dict__.update(t.__dict__)
    ident.token_map = np.arange(4096, dtype=np.int64)       # the golden's hash, on compressed ids
    ident.pad = t.pad
    lines, counts = [], {}
    streams = engram_streams(t, rng)
    for name, ids in streams:
        for p in range(len(ids)):
            hist = ids[:p + 1]
            rows = []
            for li in range(len(t.layer_ids)):
                rows.extend(int(r) for r in ident.hashes(hist, li))
            lines.append(f"{int(p == 0):x} {ids[p]:03x} " + " ".join(f"{r:05x}" for r in rows) + "\n")
        key = name if not name.startswith("random_") else "random"
        counts[key] = counts.get(key, 0) + len(ids)
    path.write_text("".join(lines))
    return len(lines), counts


def router_inputs():
    """Every router softplus argument of the golden decoding the oracle's 24 positions."""
    rec = []
    orig = G.softplus

    def spy(x):
        rec.append(np.asarray(x, dtype=G.F).copy())
        return orig(x)

    G.softplus = spy
    try:
        model = G.Model()
        prompt, gen = G.prompt_and_expected()
        state = model.new_state()
        for p, tok in enumerate(prompt + gen):
            model.decode_token(tok, p, state)
    finally:
        G.softplus = orig
    return np.concatenate(rec).astype(G.F)


def softplus_args(rng):
    F = np.float32
    mags = np.exp2(rng.uniform(-149, 128, 8000)).astype(F)
    sub = G.from_bits(rng.integers(1, 1 << 23, 1000).astype(np.uint32))
    edge = np.array([0.0, -0.0, 87.0, -87.0, 88.0, -88.0, 87.5, -87.5, 100.0, -100.0, 1e-45, -1e-45,
                     1.1754944e-38, -1.1754944e-38, 3.4028235e38, -3.4028235e38, 1.0, -1.0, 0.6931472,
                     -0.6931472, 2.0, -2.0, 16.0, -16.0, 20.0, -20.0], dtype=F)
    nonfinite = G.from_bits(np.array([0x7F800000, 0xFF800000, 0x7FC00000, 0xFFC00000, 0x7F800001,
                                      0xFF812345], dtype=np.uint32))
    bits = G.from_bits(rng.integers(0, 1 << 32, 4000, dtype=np.uint64).astype(np.uint32))
    return np.concatenate([
        rng.uniform(-100, 100, 8000).astype(F), rng.uniform(-3, 3, 8000).astype(F),
        rng.uniform(-30, 30, 4000).astype(F), mags, -mags, sub, -sub, edge, nonfinite, bits,
    ]).astype(F)


def softplus_vectors(path: Path, xs):
    """One line per argument: x softplus sqrt(softplus) fault (hex); a nonfinite
    golden result is a fault and the RTL returns +0."""
    with np.errstate(all="ignore"):
        sp = np.asarray(G.softplus(xs), dtype=np.float32)
        r = np.asarray(G.sqrt(sp), dtype=np.float32)
    fault = ~np.isfinite(sp)
    sp_b, r_b = G.bits(sp).copy(), G.bits(r).copy()
    sp_b[fault] = 0
    r_b[fault] = 0
    path.write_text("".join(f"{int(a):08x} {int(b):08x} {int(c):08x} {int(f):x}\n"
                            for a, b, c, f in zip(G.bits(xs), sp_b, r_b, fault)))
    return len(xs), int(fault.sum())


# -- simulation ---------------------------------------------------------------------------
def verilator_bench(obj: Path, top: str, sources, harness: Path, defines=()):
    cflags = " ".join(("-O1", *defines))
    subprocess.run(["verilator", *VL_FLAGS, "--top-module", top, "-Mdir", str(obj), *map(str, sources),
                    str(harness), "-CFLAGS", cflags], check=True, capture_output=True)
    return obj / f"V{top}"


def icarus_bench(out: Path, top: str, sources):
    subprocess.run(["iverilog", "-g2012", "-DHDC_SELF_CLOCK", "-s", f"{top}_clk", "-o", str(out),
                    *map(str, sources)], check=True, capture_output=True)
    return out


def run() -> dict:
    rng = np.random.default_rng(41)
    rec = {}
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        # 1. correctly rounded divide and square root
        exe = verilator_bench(s / "odiv", "ot_hdc_fdiv", [FDIV, *HDC, *PIPES], ARITH_HARNESS, ("-DDUT_DIV",))
        out = subprocess.run([str(exe), f"+N={ARITH_VECTORS}"], check=True, capture_output=True, text=True).stdout
        m = RE_ARITH.search(out)
        rec["fdiv"] = {"reference": "host IEEE binary32 division, RNE, canonical +0",
                       "operands": ARITH_VECTORS, "checked": int(m.group(1)), "mismatches": int(m.group(2)),
                       "refusals_expected_and_raised": int(m.group(3)), "subnormal_results": int(m.group(4)),
                       "pass": "PASS" in out}
        exe = verilator_bench(s / "osq", "ot_hdc_fsqrt", [FSQRT, *HDC, *PIPES], ARITH_HARNESS, ("-DDUT_SQRT",))
        out = subprocess.run([str(exe), f"+N={ARITH_VECTORS}"], check=True, capture_output=True, text=True).stdout
        m = RE_ARITH.search(out)
        exe = verilator_bench(s / "osqeq", "tb_hdc_fsqrt_equiv", [FSQRT, QSQRT, *HDC, *PIPES, TB_SQEQ], TB_HARNESS,
                              ("-DVTOP=Vtb_hdc_fsqrt_equiv",))
        eq = subprocess.run([str(exe), f"+N={ARITH_VECTORS}"], check=True, capture_output=True, text=True).stdout
        e = RE_SQEQ.search(eq)
        rec["fsqrt"] = {"reference": "host IEEE binary32 square root, RNE, canonical +0",
                        "operands": ARITH_VECTORS, "checked": int(m.group(1)), "mismatches": int(m.group(2)),
                        "refusals_expected_and_raised": int(m.group(3)),
                        "qualified_equivalence": {"module": str(QSQRT.relative_to(ROOT)),
                                                  "latency_offset_cycles": 1, "checked": int(e.group(1)),
                                                  "refused": int(e.group(2)), "mismatches": int(e.group(3)),
                                                  "pass": "PASS" in eq},
                        "pass": "PASS" in out and "PASS" in eq}
        # 2. Engram hash
        t = engram_tables()
        hv = s / "hash.txt"
        n_hash, counts = engram_vectors(hv, t, rng)
        hash_src = [TABLES, HASH, TB_HASH]
        runs = {}
        exe = verilator_bench(s / "ohash", "tb_hdc_engram_hash", hash_src, TB_HARNESS,
                              ("-DVTOP=Vtb_hdc_engram_hash",))
        runs["verilator"] = subprocess.run([str(exe), f"+VEC={hv}"], check=True, capture_output=True,
                                           text=True).stdout
        vvp = icarus_bench(s / "hash.vvp", "tb_hdc_engram_hash", hash_src)
        runs["icarus"] = subprocess.run(["vvp", "-n", str(vvp), f"+VEC={hv}"], check=True, capture_output=True,
                                        text=True).stdout
        rec["engram_hash"] = {"positions": n_hash, "positions_by_stream": counts,
                              "columns_per_position": len(t.layer_ids) * (t.n - 1) * t.primes.shape[2],
                              "reference": "tools/hdc_golden_v41.EngramTables.hashes (Python integers)"}
        for sim, text in runs.items():
            m = RE_HASH.search(text)
            rec["engram_hash"][sim] = {"checked": int(m.group(2)), "errors": int(m.group(3)),
                                       "cycles": int(m.group(4)),
                                       "pass": "PASS" in text and int(m.group(2)) == n_hash}
        rec["engram_hash"]["pass"] = all(rec["engram_hash"][k]["pass"] for k in runs)
        # 3. softplus / router score
        router = router_inputs()
        xs = np.concatenate([router, softplus_args(rng)]).astype(np.float32)
        sv = s / "sp.txt"
        n_sp, n_fault = softplus_vectors(sv, xs)
        runs = {}
        exe = verilator_bench(s / "osp", "tb_hdc_softplus", [*SP_SOURCES, TB_SP], TB_HARNESS,
                              ("-DVTOP=Vtb_hdc_softplus",))
        runs["verilator"] = subprocess.run([str(exe), f"+VEC={sv}"], check=True, capture_output=True,
                                           text=True).stdout
        vvp = icarus_bench(s / "sp.vvp", "tb_hdc_softplus", [*SP_SOURCES, TB_SP])
        runs["icarus"] = subprocess.run(["vvp", "-n", str(vvp), f"+VEC={sv}"], check=True, capture_output=True,
                                        text=True).stdout
        rec["softplus"] = {"arguments": n_sp, "router_arguments": int(router.size),
                           "router_argument_sha256": hashlib.sha256(router.tobytes()).hexdigest(),
                           "router_argument_range": [float(router.min()), float(router.max())],
                           "nonfinite_golden_results": n_fault,
                           "reference": "tools/hdc_golden_v41.softplus and .sqrt; a nonfinite golden "
                                        "result must be a fault with +0 outputs"}
        for sim, text in runs.items():
            m = RE_SP.search(text)
            rec["softplus"][sim] = {"checked": int(m.group(2)), "errors": int(m.group(3)),
                                    "faults": int(m.group(4)), "cycles": int(m.group(5)),
                                    "pass": "PASS" in text and int(m.group(2)) == n_sp}
        rec["softplus"]["pass"] = all(rec["softplus"][k]["pass"] for k in runs)
    # 4. lint
    lint = {}
    for top, src in (("ot_hdc_engram_hash", [TABLES, HASH]), ("ot_hdc_softplus", SP_SOURCES)):
        p = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", top, *map(str, src)],
                           capture_output=True, text=True)
        lint[top] = {"returncode": p.returncode, "messages": p.stderr.strip().splitlines()[:20]}
    ok = all(rec[k]["pass"] for k in ("fdiv", "fsqrt", "engram_hash", "softplus")) and \
        all(v["returncode"] == 0 for v in lint.values())
    inputs = [TABLES, HASH, SOFTPLUS, FDIV, FSQRT, QSQRT, *HDC, *PIPES, TB_HASH, TB_SP, TB_SQEQ, TB_HARNESS,
              ARITH_HARNESS, *TOOLS]
    return {
        "schema": "opentallas.hdc-v41-engram-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "functional RTL simulation (Verilator 4.038 and Icarus 11, cycle-accurate at the "
                          "module boundary) of the Engram hash and softplus/router-score pipes against the "
                          "V4.1 HDC golden; clock rate and area are in the ASAP7 physical records under "
                          "results/physical_abi3/asap7/hdc/v41/.",
        "pipelines": {"ot_hdc_engram_hash": {"latency_cycles": 12, "initiation_interval": 1},
                      "ot_hdc_softplus": {"latency_cycles": 259, "initiation_interval": 1},
                      "ot_hdc_fdiv": {"latency_cycles": 31, "initiation_interval": 1},
                      "ot_hdc_fsqrt": {"latency_cycles": 31, "initiation_interval": 1}},
        **rec,
        "verilator_lint": {"flags": list(LINT_FLAGS), **lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--emit-tables", action="store_true",
                        help=f"rewrite {TABLES.relative_to(ROOT)} from the golden and exit")
    args = parser.parse_args()
    if args.emit_tables:
        TABLES.write_text(emit_tables())
        print("wrote", TABLES.relative_to(ROOT))
        return 0
    result = run()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"], "hash positions", result["engram_hash"]["positions"],
          "softplus arguments", result["softplus"]["arguments"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
