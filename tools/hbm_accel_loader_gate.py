#!/usr/bin/env python3
"""Exactness gate of the HBM accelerator's host -> HBM loader (rtl/hbm_accel/loader/ot_hbm_accel_loader.sv).

Takes the two partition images of one die of the DeepSeek-V4.1 HBM system run (the $readmemh files that bench
loads at time 0, e.g. <case>/die0_p0.hex and die0_p1.hex, NS = 2, MEM_WORDS 2^21), picks the densest 8 MiB
die-global window (the weight region) and a second, disjoint 1 MiB window, lays both out in a host-memory image,
and runs rtl/test/hbm_accel/tb_hbm_accel_loader.sv under Verilator: the loader must copy both windows through
AXI -> CDC -> ot_gpu_memsys -> HBM model so that every model word equals the system image inside the windows and
stays zero outside, with payload and HBM read-back CRC-32 equal to tools/mem_compiler/ecc.py signature().
Run on a compute host:  python3 tools/hbm_accel_loader_gate.py --image-prefix <case>/die0 --work W --output R
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
import ecc  # noqa: E402

MEM_WORDS = 1 << 21
NS = 2
TB = "rtl/test/hbm_accel/tb_hbm_accel_loader.sv"
RTL = ["rtl/hbm_accel/loader/ot_hbm_accel_loader.sv", "rtl/gpu_sys/ot_gpu_cdc_fifo.sv", "rtl/link/ot_link_afifo.sv",
       "rtl/gpu_sys/ot_gpu_memsys.sv", "rtl/gpu_sys/ot_gpu_xbar.sv", "rtl/gpu_sys/ot_gpu_l2_slice.sv",
       "rtl/gpu_sys/ot_gpu_hbm_partition.sv", "rtl/hdc/kv/ot_hdc_hbm_model.sv"]
XFER = re.compile(r"XFER (\S+) status=(\d+) crc_got=([0-9a-f]+) vcrc_got=([0-9a-f]+) crc_exp=([0-9a-f]+) "
                  r"sectors=(\d+) cycles=(\d+) bytes=(\d+) verify=(\d+)")
COMPARE = re.compile(r"COMPARE words=(\d+) loaded=(\d+) nonzero_loaded=(\d+) mismatches=(\d+) memsys_fault=(\d)")


def read_hex(p: Path) -> list[int]:
    return [int(x, 16) for x in p.read_text().split()]


def die_word(parts, addr: int) -> int:
    """Die-global byte address (32-byte aligned) -> the sector word (mem_image.placement, NS = 2)."""
    s = (addr >> 7) & 1
    local = ((addr >> 8) << 7) | (addr & 0x7F)
    return parts[s][(local >> 5) % MEM_WORDS]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image-prefix", required=True, help="<dir>/die0 -> die0_p0.hex, die0_p1.hex")
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--win-mib", type=int, default=8)
    ap.add_argument("--win2-mib", type=int, default=1)
    ap.add_argument("--hclk-ns", type=float, default=1.0)
    ap.add_argument("--hlat", type=int, default=400, help="host read latency, host cycles")
    ap.add_argument("--verilator", default=str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    exp = [Path(f"{a.image_prefix}_p{p}.hex") for p in range(NS)]
    parts = [read_hex(p) for p in exp]
    assert all(len(x) == MEM_WORDS for x in parts)
    die_bytes = NS * MEM_WORDS * 32
    # densest window (by nonzero sectors), 1 MiB granularity
    mib = 1 << 20
    nz_per_mib = []
    for m in range(die_bytes // mib):
        nz_per_mib.append(sum(1 for x in range(m * mib, (m + 1) * mib, 32) if die_word(parts, x)))
    W1 = a.win_mib
    best = max(range(len(nz_per_mib) - W1 + 1), key=lambda m: sum(nz_per_mib[m:m + W1]))
    cand = [m for m in range(len(nz_per_mib) - a.win2_mib + 1)
            if (m + a.win2_mib <= best or m >= best + W1)]
    best2 = max(cand, key=lambda m: sum(nz_per_mib[m:m + a.win2_mib]))
    wins = [(best * mib, W1 * mib, 1, "weights_densest"), (best2 * mib, a.win2_mib * mib, 0, "second_region")]
    host, transfers = [], []
    for daddr, nbytes, ver, name in wins:
        words = [die_word(parts, daddr + 32 * i) for i in range(nbytes // 32)]
        transfers.append({"name": name, "host_sector": len(host), "die_addr": daddr, "bytes": nbytes,
                          "crc": ecc.signature(words, 256), "verify": ver,
                          "nonzero_sectors": sum(1 for w in words if w)})
        host.extend(words)
    crc4k = ecc.signature(host[:128], 256)
    himg = a.work / "host.hex"
    himg.write_text("".join(f"{w:064x}\n" for w in host))
    hwords = 1 << max(10, (len(host) - 1).bit_length())

    build = a.work / "obj"
    cmd = [a.verilator, "--binary", "--timing", "-j", "16", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-PINMISSING",
           "-Wno-MULTIDRIVEN", "--top-module", "tb_hbm_accel_loader", f"-GMEM_WORDS={MEM_WORDS}",
           f"-GHWORDS={hwords}", f"-GHCLK={a.hclk_ns}", "-Mdir", str(build), "-o", "tb", TB, *RTL]
    tb0 = time.time()
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (a.work / "build.log").write_text(b.stdout + b.stderr)
    if b.returncode:
        print(b.stderr[-3000:])
        raise SystemExit("build failed")
    build_s = time.time() - tb0
    args = [f"+HOSTIMG={himg}", f"+EXP0={exp[0]}", f"+EXP1={exp[1]}", f"+NT={len(transfers)}", f"+HLAT={a.hlat}",
            f"+CRC4K={crc4k:08x}"]
    args += [f"+T{i}={t['host_sector']}:{t['die_addr']}:{t['bytes']}:{t['crc']:08x}:{t['verify']}"
             for i, t in enumerate(transfers)]
    tr0 = time.time()
    r = subprocess.run([str(build / "tb"), *args], cwd=a.work, capture_output=True, text=True)
    out = r.stdout + r.stderr
    (a.work / "run.log").write_text(out)
    run_s = time.time() - tr0
    xfers = []
    for m in XFER.finditer(out):
        name, st, cg, vg, ce, ns, cy, by, ver = m.groups()
        cy, by = int(cy), int(by)
        xfers.append({"name": name, "status": int(st), "crc_got": cg, "vcrc_got": vg, "crc_exp": ce,
                      "sectors": int(ns), "host_cycles": cy, "bytes": by, "verify": int(ver),
                      "GBps": round(by / (cy * a.hclk_ns), 3) if cy else None})
    cm = COMPARE.search(out)
    compare = dict(zip(("words", "loaded", "nonzero_loaded", "mismatches", "memsys_fault"),
                       map(int, cm.groups()))) if cm else None
    ok = "PASS transfers" in out and r.returncode == 0
    rec = {
        "schema": "opentallas.hbm_accel.loader_gate.v1",
        "date": time.strftime("%Y-%m-%d"),
        "dut": "rtl/hbm_accel/loader/ot_hbm_accel_loader.sv (ENABLE=1, BURST 16, MAXOUT 8, OUTW 96, VOUT 16)",
        "memory": "ot_gpu_memsys NC 1, NS 2, NPC 2, MEM_WORDS 2^21 per partition (128 MiB die), HBM model "
                  "rtl/hdc/kv/ot_hdc_hbm_model.sv, no load-time image",
        "image": {"partitions": [str(p) for p in exp],
                  "sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in exp],
                  "source": "DeepSeek-V4.1 HBM system run (results/rtl/hbm_system_rtl_20261003/STATUS.md) die image"},
        "host": {"clock_ns": a.hclk_ns, "read_latency_cycles": a.hlat, "beat_bytes": 32},
        "transfers": transfers, "crc4k": f"{crc4k:08x}",
        "results": xfers, "compare": compare,
        "verdict": "PASS" if ok else "FAIL",
        "simulator": a.verilator, "build_seconds": round(build_s, 1), "run_seconds": round(run_s, 1),
        "sources": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in [TB, *RTL, "tools/hbm_accel_loader_gate.py"]},
        "seconds": round(time.time() - t0, 1),
    }
    for t in transfers:
        t["crc"] = f"{t['crc']:08x}"
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"verdict": rec["verdict"], "compare": compare, "results": xfers}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
