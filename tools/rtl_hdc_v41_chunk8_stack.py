#!/usr/bin/env python3
"""Source-pinned standalone R-ARITH block-term tree gate.

The vectors include actual reduced-checkpoint QE block terms and longer
concatenations of those terms to exercise the full-shape reduction order.
The expected result comes from hdc_golden_v41.csum, not an RTL-shaped model.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41_blockdot_campaign as SOURCE  # noqa: E402

RTL = ROOT / "rtl/hdc/v41/ot_hdc_chunk8_stack.sv"
TB = ROOT / "rtl/test/tb_hdc_chunk8_stack.sv"
SOURCES = [RTL, TB, ROOT / "rtl/hdc/ot_hdc_delay.sv",
           ROOT / "rtl/hdc/ot_hdc_fpu.sv", ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv",
           ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py",
           ROOT / "tools/rtl_hdc_v41_blockdot_campaign.py",
           Path(__file__)]


def bits(x):
    return int(G.bits(np.float32(x)))


def block_terms(w, x, row):
    xq, xe = G.quant_fp8(x)
    nb = w.q.shape[1] // 32
    return np.asarray([
        np.ldexp(np.float32(np.dot(w.q[row, 32*b:32*(b+1)], xq[32*b:32*(b+1)])),
                 int(w.e[row, b] + xe[b]))
        for b in range(nb)
    ], dtype=np.float32)


def sequential(xs):
    acc = np.float32(0)
    for x in xs:
        acc = G.add(acc, x)
    return acc


def real_reduction_vectors(limit=8):
    """Capture genuine order-sensitive R-ARITH operands during a reduced decode."""
    saved = G.csum
    found = []
    calls = 0

    def watch(t, axis=-1, c=G.CHUNK):
        nonlocal calls
        calls += 1
        a = np.moveaxis(np.asarray(t, dtype=np.float32), axis, -1)
        if len(found) < limit and 8 < a.shape[-1] <= 192:
            for r, row in enumerate(a.reshape(-1, a.shape[-1])[:64]):
                if np.all(np.isfinite(row)) and bits(saved(row)) != bits(sequential(row)):
                    found.append((f"real_reduced_csum_call{calls}_row{r}", row.copy()))
                    if len(found) == limit:
                        break
        return saved(t, axis, c)

    G.csum = watch
    try:
        model = G.Model()
        prompt, _ = G.prompt_and_expected()
        state = model.new_state()
        model.decode_token(prompt[0], 0, state)
    finally:
        G.csum = saved
    assert found, "no real reduced vector distinguishes chunk8 and sequential order"
    return found


def vectors():
    G.set_arith("chunk8")
    cap = SOURCE.capture_real(1)
    real = [(i, w, x) for i, (w, x) in enumerate(cap["lin"]) if w.q.shape[1] == 768]
    assert len(real) >= 1, "reduced checkpoint no longer provides 24-block QE rows"
    call, w, x = real[0]
    rows = [block_terms(w, x, r) for r in range(min(64, w.q.shape[0]))]
    out = [("directed_order", np.asarray([2**24, 1, -(2**24), 1, 0, 0, 0, 0] * 2,
                                            dtype=np.float32))]
    pattern = np.asarray([2**24, 1, -(2**24), 1, -3, 3, 2**-20, -(2**-20)], dtype=np.float32)
    out += [(f"directed_len{n}", np.resize(pattern, n).astype(np.float32))
            for n in (1, 7, 8, 9, 10, 17, 23, 31, 64, 192)]
    out += [(f"real_call{call}_row{r}", a) for r, a in enumerate(rows[:24])]
    # A reduced row has 24 blocks, and its small quantised terms often add
    # exactly.  Concatenating eight independent real rows makes a 192-block
    # stress stream without inventing operand values; this is not a model row.
    rng = np.random.default_rng(0x41C8)
    for t in range(32):
        choice = rng.choice(len(rows), 8, replace=False)
        out.append((f"real_composite_{t}", np.concatenate([rows[int(r)] for r in choice])))
    out += real_reduction_vectors()
    for name, a in out:
        assert len(a) <= 192 and np.all(np.isfinite(a)), name
    diffs = [name for name, a in out if bits(G.csum(a)) != bits(sequential(a))]
    assert "directed_order" in diffs, "control failed to distinguish orders"
    assert any(x.startswith("real_reduced_csum") for x in diffs), "real reduced vector did not distinguish orders"
    return out, diffs, call


def run(output: Path):
    items, diffs, call = vectors()
    with tempfile.TemporaryDirectory(prefix="v41_chunk8_") as td:
        d = Path(td)
        terms, jobs, expected = [], [], []
        for _, a in items:
            jobs.append((len(terms), len(a)))
            terms.extend(bits(x) for x in a)
            root = np.float32(G.csum(a))
            expected.append((bits(root), bits(G.to_bf16(root)) >> 16))
        (d / "terms.mem").write_text("".join(f"{x:08x}\n" for x in terms))
        (d / "jobs.mem").write_text("".join(f"{s:08x}{n:04x}0000\n" for s, n in jobs))
        (d / "expect.mem").write_text("".join(f"{a:08x}{b:04x}\n" for a, b in expected))
        exe = d / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_chunk8_stack", "-o", str(exe),
                        *map(str, SOURCES[:5])], check=True, capture_output=True, text=True)
        proc = subprocess.run(["vvp", str(exe), f"+NTERM={len(terms)}", f"+NJOB={len(items)}"],
                              cwd=d, capture_output=True, text=True, timeout=180)
        if proc.returncode or "PASS" not in proc.stdout:
            raise RuntimeError(proc.stdout + proc.stderr)
    record = {
        "status": "PASS", "scope": "standalone block-term reducer; no QE/core/full-token integration or P&R",
        "arith": "chunk8", "rows": len(items), "terms": len(terms),
        "real_checkpoint_qe_call": call,
        "real_reduced_order_sensitive": sum(x.startswith("real_reduced_csum") for x in diffs),
        "real_composites_order_sensitive": sum(x.startswith("real_composite") for x in diffs),
        "order_sensitive_names": diffs,
        "stdout": proc.stdout.strip(),
        "checkpoint_sha256": hashlib.sha256(G.CHECKPOINT.read_bytes()).hexdigest(),
        "checkpoint_path": str(G.CHECKPOINT.relative_to(G.BUILD)),
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in SOURCES},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/rtl/hdc_v41_chunk8_stack.json"
    print(json.dumps(run(path), indent=2))
