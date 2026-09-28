#!/usr/bin/env python3
"""Exact integrated block-dot gate for full-shape chunk8 and reduced legacy modes."""
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
import rtl_hdc_v41_blockdot_campaign as C  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_chunk8_blockdot_integration.json"
STACK = ROOT / "rtl/hdc/v41/ot_hdc_chunk8_stack.sv"
RTL = [ROOT / "rtl/hdc/v41/ot_hdc_blockdot.sv", STACK]
SOURCES = RTL + C.LIB + [C.TB_BD, C.HARNESS, Path(__file__),
                         ROOT / "tools/rtl_hdc_v41_blockdot_campaign.py",
                         ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py"]
RESULT = re.compile(r"V41BD rows=(\d+) checked=(\d+) errors=(\d+) faults_expected_and_raised=(\d+) "
                    r"blocks=(\d+) bubbles=(\d+) cycles=(\d+)")


def _cap() -> None:
    lim = 16 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (lim, lim))


def long_vectors(directory: Path) -> dict:
    """Four full 192-block rows; one differs between sequential and chunk8."""
    G = C.G
    G.set_arith("chunk8")
    rng = np.random.default_rng(192)
    nb, nr = 192, 4
    x = G.to_bf16(rng.normal(size=32 * nb).astype(np.float32))
    q = G.E2M1[rng.integers(0, 16, size=(nr, 32 * nb))]
    exponents = rng.integers(-4, 3, size=(nr, nb), dtype=np.int64)
    weights = G.Q8(q, exponents)
    xq, xe = G.quant_fp8(x)
    xcodes = C.e4m3_codes(xq)
    terms = [np.ldexp((weights.q[:, b*32:(b+1)*32] @ xq[b*32:(b+1)*32]).astype(np.float32),
                      weights.e[:, b] + xe[b]).astype(np.float32) for b in range(nb)]
    chunk = G.csum(np.stack(terms, axis=-1))
    sequential = np.zeros(nr, dtype=np.float32)
    for term in terms:
        sequential = G.add(sequential, term)
    order_sensitive = int(np.count_nonzero(chunk.view(np.uint32) != sequential.view(np.uint32)))
    assert order_sensitive >= 1
    with (directory / "bd_blk.mem").open("w") as blk, (directory / "bd_job.mem").open("w") as job, \
         (directory / "bd_exp.mem").open("w") as exp:
        for row in range(nr):
            job.write(f"{row*nb:08x}{nb:04x}0000\n")
            exp.write(f"{int(G.bits(chunk[row])):08x}"
                      f"{int(G.bits(G.to_bf16(chunk[row])) >> 16):04x}\n")
            wc = C.e2m1_codes(weights.q[row])
            for b in range(nb):
                meta = (1 << 20) | ((int(xe[b]) & 0x3ff) << 10) | (int(weights.e[row,b]) & 0x3ff)
                blk.write(f"{meta:08x}{C.hexw(xcodes[b*32:(b+1)*32],8):064x}"
                          f"{C.hexw(wc[b*32:(b+1)*32],8):064x}\n")
    return {"rows": nr, "blocks": nr * nb, "blocks_per_row": nb,
            "order_sensitive_rows": order_sensitive}


def _check(log: str, rows: int, blocks: int) -> dict:
    match = RESULT.search(log)
    if not match or "PASS" not in log:
        raise RuntimeError("block-dot RTL gate did not report PASS: " + log[-800:])
    got = list(map(int, match.groups()))
    if got[0] != rows or got[1] != rows or got[2] != 0 or got[4] != blocks:
        raise RuntimeError(f"unexpected block-dot count: {got}")
    return {"rows": got[0], "checked": got[1], "mismatches": got[2],
            "faults_expected_and_raised": got[3], "blocks": got[4], "cycles": got[6]}


def run(output: Path = OUT) -> dict:
    with tempfile.TemporaryDirectory(prefix="v41_chunk8_bd_") as temp:
        base = Path(temp)
        long = base / "long"
        legacy = base / "legacy"
        for d in (long, legacy):
            d.mkdir()
        long_meta = long_vectors(long)
        C.G.set_arith("legacy")
        legacy_meta = C.build_vectors(legacy, seed=41028, n_random=32, real=False)
        verilator = os.environ.get("OT_VERILATOR", "verilator")
        command = [verilator, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH",
                   "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-TIMESCALEMOD", "--top-module",
                   "tb_hdc_v41_blockdot", "--prefix", "Vtb", "-GCHUNK8=1", "-GMAXB=1024",
                   "-GMAXJ=1024", "-Mdir", str(base / "obj"), *map(str, RTL + C.LIB),
                   str(C.TB_BD), str(C.HARNESS), "-CFLAGS", "-O1", "-j", "2"]
        build = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                               timeout=300, preexec_fn=_cap)
        if build.returncode:
            raise RuntimeError("Verilator build failed: " + build.stderr[-1200:])
        exact = subprocess.run([str(base / "obj/Vtb"), "+NBLK=768", "+NJOB=4", "+BUBBLE=0",
                                "+SEED=13"], cwd=long, capture_output=True, text=True, timeout=30)
        if exact.returncode:
            raise RuntimeError("chunk8 simulation failed: " + exact.stderr[-800:])
        chunk_result = _check(exact.stdout, 4, 768)
        compile_legacy = subprocess.run(["iverilog", "-g2012", "-o", str(base / "legacy.vvp"),
                                         "-s", "tb_hdc_v41_blockdot_icarus", *map(str, RTL + C.LIB),
                                         str(C.TB_BD)], cwd=ROOT, capture_output=True, text=True, timeout=60)
        if compile_legacy.returncode:
            raise RuntimeError("Icarus legacy compile failed: " + compile_legacy.stderr[-800:])
        old = subprocess.run(["vvp", "-n", str(base / "legacy.vvp"),
                              f"+NBLK={legacy_meta['blockdot_blocks']}",
                              f"+NJOB={legacy_meta['blockdot_rows']}", "+BUBBLE=0", "+SEED=13"],
                             cwd=legacy, capture_output=True, text=True, timeout=30)
        if old.returncode:
            raise RuntimeError("legacy simulation failed: " + old.stderr[-800:])
        old_result = _check(old.stdout, legacy_meta["blockdot_rows"], legacy_meta["blockdot_blocks"])
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(SOURCES))}
    record = {"schema": "opentallas.rtl.v41_chunk8_blockdot_integration.v1", "status": "pass",
              "chunk8": chunk_result | long_meta, "legacy_default": old_result,
              "claim_scope": "One ot_hdc_blockdot lane, complete 192-block rows, bit-exact against "
                             "golden chunk8; reduced sequential default regression. No full-shape layer or P&R.",
              "source_sha256": pins}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    rec = run()
    print(json.dumps({"status": rec["status"], "chunk8": rec["chunk8"],
                      "legacy_default": rec["legacy_default"]}))
