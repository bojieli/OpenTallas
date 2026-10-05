#!/usr/bin/env python3
"""Source-pinned 192-block QE integration gate; full width, one row group."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41_blockdot_campaign as B  # noqa: E402

RTL = [ROOT / f"rtl/hdc/v41/{name}.sv" for name in
       ("ot_hdc_v41_qe", "ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_blockdot", "ot_hdc_chunk8_stack")]
TB = ROOT / "rtl/test/tb_hdc_v41_fullshape_qe.sv"
SOURCES = RTL + B.LIB + [TB, Path(__file__), ROOT / "tools/hdc_golden_v41.py",
                         ROOT / "tools/hdc_golden.py", ROOT / "tools/rtl_hdc_v41_blockdot_campaign.py"]
OUT = ROOT / "results/rtl/hdc_v41_fullshape_qe_gate.json"
PATTERN = re.compile(r"V41QE rows=(\d+) errors=(\d+) cycles=(\d+) unrounded=(\d+) fp4=(\d+) fault=(\d+)")


def _cap():
    limit = 24 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def vectors(path: Path, fp4: bool):
    G.set_arith("chunk8")
    rng = np.random.default_rng(4104192)
    nb, rows = 192, 8
    x = G.to_bf16(rng.normal(size=32 * nb).astype(np.float32))
    table = G.E2M1 if fp4 else G.E4M3[np.array([i for i in range(256) if i & 0x7f != 0x7f])]
    codes = table[rng.integers(0, len(table), size=(rows, 32 * nb))]
    exps = rng.integers(-4, 3, size=(rows, nb), dtype=np.int64)
    w = G.Q8(codes, exps)
    qx, xe = G.quant_fp8(x)
    terms = [np.ldexp((w.q[:, b*32:(b+1)*32] @ qx[b*32:(b+1)*32]).astype(np.float32),
                      w.e[:, b] + xe[b]).astype(np.float32) for b in range(nb)]
    acc = G.csum(np.stack(terms, axis=-1))
    assert np.array_equal(G.bits(G.to_bf16(acc)), G.bits(G.linear_q(w, x)))
    order = []
    for block in range(nb):
        for row in range(rows):
            wc = (B.e2m1_codes if fp4 else B.e4m3_codes)(codes[row, block*32:(block+1)*32])
            word = B.hexw(wc, 8) | ((int(exps[row, block]) & 0xffff) << 256)
            order.append(word)
    with (path / "x.mem").open("w") as f:
        for block in range(nb):
            f.write(f"{B.hexw(G.bits(x[block*32:(block+1)*32]), 32):0256x}\n")
    (path / "q.mem").write_text("".join(f"{word:068x}\n" for word in order))
    (path / "acc.mem").write_text("".join(f"{int(a):08x}\n" for a in G.bits(acc)))
    (path / "bf16.mem").write_text("".join(f"{int(a):08x}\n" for a in G.bits(G.to_bf16(acc))))
    return {"rows": rows, "blocks_per_row": nb, "weight_words": len(order), "fp4": fp4,
            "activation_blocks": nb,
            "source_vector_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in sorted(path.glob("*.mem"))}}


def run(output: Path = OUT):
    with tempfile.TemporaryDirectory(prefix="v41_fullshape_qe_") as tmp:
        directory = Path(tmp)
        metas = {}
        for fp4 in (False, True):
            sub = directory / ("fp4" if fp4 else "fp8")
            sub.mkdir()
            metas[sub.name] = vectors(sub, fp4)
        verilator = os.environ.get("OT_VERILATOR", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
        cmd = [verilator, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH",
               "-Wno-UNUSED", "-Wno-TIMESCALEMOD", "--top-module", "tb_hdc_v41_fullshape_qe",
               "-Mdir", str(directory / "obj"), *map(str, RTL + B.LIB + [TB]), "-j", "2"]
        build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300, preexec_fn=_cap)
        if build.returncode:
            raise RuntimeError("QE build failed: " + build.stderr[-1800:])
        results = []
        for fp4 in (False, True):
            for mode in (0, 1):
                p = subprocess.run([str(directory / "obj/Vtb_hdc_v41_fullshape_qe"),
                                    f"+UNROUNDED={mode}", f"+FP4={int(fp4)}"],
                                   cwd=directory / ("fp4" if fp4 else "fp8"),
                                   capture_output=True, text=True, timeout=60)
                if p.returncode or "PASS" not in p.stdout:
                    raise RuntimeError("QE simulation failed: " + p.stdout[-1000:] + p.stderr[-1000:])
                match = PATTERN.search(p.stdout)
                if not match:
                    raise RuntimeError("QE result absent: " + p.stdout[-1000:])
                rows, errors, cycles, got_mode, got_fp4, fault = map(int, match.groups())
                if (rows, errors, got_mode, got_fp4, fault) != (8, 0, mode, int(fp4), 0):
                    raise RuntimeError("QE result invalid: " + match.group(0))
                results.append({"fp4": fp4, "unrounded": bool(mode), "rows": rows,
                                "mismatches": errors, "cycles": cycles, "fault": fault})
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(SOURCES))}
    record = {"schema": "opentallas.rtl.v41_fullshape_qe_gate.v1", "status": "pass",
              "scope": "192-block, 8-row standalone QE LINQ including activation quantization, FP8/FP4 ROM stream, "
                       "CHUNK8, and VM writes; no full layer or physical timing",
              "vectors": metas, "runs": results, "source_sha256": pins}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
