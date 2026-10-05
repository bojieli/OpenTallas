#!/usr/bin/env python3
"""One captured SIM_ONLY PV job: integer source transcription versus chunk8 golden.

Consumes accepted bytes only. Does not replay ATT, infer original-run inputs,
read checkpoint payloads, or claim hardware timing. All output records are fresh.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def topbit(x, width):
    t = np.zeros(x.shape, dtype=np.int64)
    for i in range(width):
        t = np.where((x >> i) != 0, i, t)
    return t


def jam(x, n):
    n = np.asarray(n, dtype=np.uint64)
    small = np.minimum(n, 63)
    return np.where(n >= 64, (x != 0).astype(np.uint64),
                    (x >> small) | ((x & ((np.uint64(1) << small) - np.uint64(1))) != 0))


def iadd(a, b):
    """Frozen endpoint binary32 add, with per-value fault propagation separate."""
    a, b = a.astype(np.uint64), b.astype(np.uint64)
    ea, eb = (a >> 23) & 255, (b >> 23) & 255
    bad = (ea == 255) | (eb == 255)
    ma = (a & 0x7fffff) | np.where(ea != 0, 0x800000, 0).astype(np.uint64)
    mb = (b & 0x7fffff) | np.where(eb != 0, 0x800000, 0).astype(np.uint64)
    ea, eb = np.maximum(ea, 1), np.maximum(eb, 1)
    sa, sb = a >> 31, b >> 31
    swap = (ea < eb) | ((ea == eb) & (ma < mb))
    ea, eb = np.where(swap, eb, ea), np.where(swap, ea, eb)
    ma, mb = np.where(swap, mb, ma), np.where(swap, ma, mb)
    sa, sb = np.where(swap, sb, sa), np.where(swap, sa, sb)
    ma, mb = ma << 3, jam(mb << 3, ea - eb)
    m = np.where(sa == sb, ma + mb, ma - mb)
    carry = (m & (1 << 27)) != 0
    m, ea = np.where(carry, jam(m, 1), m), ea + carry.astype(np.uint64)
    # Source loop performs exact cancellation normalization, at most 26 shifts.
    for _ in range(27):
        shift = (m < (1 << 26)) & (ea > 1) & (m != 0)
        if not np.any(shift):
            break
        m = np.where(shift, m << 1, m)
        ea -= shift.astype(np.uint64)
    sig, low = m >> 3, m & 7
    sig += ((low > 4) | ((low == 4) & ((sig & 1) != 0))).astype(np.uint64)
    carry = sig >= 0x1000000
    sig, ea = np.where(carry, sig >> 1, sig), ea + carry.astype(np.uint64)
    bad |= ea >= 255
    exponent = np.where((ea == 1) & (sig < 0x800000), 0, ea)
    result = (sa << 31) | (exponent << 23) | (sig & 0x7fffff)
    result = np.where(sig == 0, 0, result)
    result = np.where((b & 0x7fffffff) == 0, a, result)
    result = np.where((a & 0x7fffffff) == 0,
                      np.where((b & 0x7fffffff) != 0, b, 0), result)
    return np.where(bad, 0, result).astype(np.uint32), bad


def iproduct(a, b):
    a, b = a.astype(np.uint64), b.astype(np.uint64)
    ea, eb = (a >> 7) & 255, (b >> 7) & 255
    bad = (ea == 255) | (eb == 255)
    ma = (a & 127) | np.where(ea != 0, 128, 0).astype(np.uint64)
    mb = (b & 127) | np.where(eb != 0, 128, 0).astype(np.uint64)
    p = ma * mb
    sign = ((a ^ b) >> 15) & 1
    es = np.maximum(ea, 1).astype(np.int64) + np.maximum(eb, 1).astype(np.int64)
    top = topbit(p, 16)
    exponent = es - 141 + top
    bad |= exponent >= 255
    normal = (sign << 31) | (np.maximum(exponent, 0).astype(np.uint64) << 23) | ((p << (23 - top).astype(np.uint64)) & 0x7fffff)
    shift = es - 119
    n = np.clip(-shift, 1, 63).astype(np.uint64)
    sub = p >> n
    tail = p & ((np.uint64(1) << n) - np.uint64(1))
    half = np.uint64(1) << (n - np.uint64(1))
    sub += ((tail > half) | ((tail == half) & ((sub & 1) != 0))).astype(np.uint64)
    sub = np.where(-shift >= 32, 0, sub)
    sub = np.where(shift >= 0, p << np.clip(shift, 0, 63).astype(np.uint64), sub)
    sub = np.where(sub != 0, (sign << 31) | sub, 0)
    return np.where(bad | (p == 0), 0, np.where(exponent >= 1, normal, sub)).astype(np.uint32), bad


def decode(kv):
    # Four tightly packed 4240-bit rows per accepted 16960-bit bus; no 4256 stride.
    raw = kv.view(np.uint8).reshape(640, 530)
    rowbits = np.unpackbits(raw, axis=1, bitorder="little")

    def field(offset, width):
        return np.sum(rowbits[:, offset:offset + width].astype(np.uint64) << np.arange(width, dtype=np.uint64), axis=1)

    integer = np.zeros((640, 512), dtype=np.uint16)
    golden = np.zeros((640, 512), dtype=np.float32)
    bad = np.zeros((640, 512), dtype=bool)
    formats = []
    for group in range(16):
        base = group * 265
        fmt = field(base + 264, 1) != 0
        formats.append(int(np.count_nonzero(fmt)))
        for lane in range(32):
            c8, s8 = field(base + lane * 8, 8), field(base + 256, 8)
            c4, s4 = field(base + lane * 4, 4), field(base + 128 + (lane // 16) * 8, 8)
            e8, e4, se4 = (c8 >> 3) & 15, (c4 >> 1) & 3, (s4 >> 3) & 15
            sign = np.where(fmt, (c4 >> 3) ^ (s4 >> 7), c8 >> 7)
            prod8 = np.where(e8 != 0, 8, 0).astype(np.uint64) | (c8 & 7)
            prod4 = (np.where(e4 != 0, 2, 0).astype(np.uint64) | (c4 & 1)) * (np.where(se4 != 0, 8, 0).astype(np.uint64) | (s4 & 7))
            prod = np.where(fmt, prod4, prod8)
            exp = np.where(fmt, np.maximum(e4, 1).astype(np.int64) + np.maximum(se4, 1).astype(np.int64) - 12,
                           np.maximum(e8, 1).astype(np.int64) + s8.astype(np.int64) - 137)
            nan = np.where(fmt, (se4 == 15) & ((s4 & 7) == 7), ((e8 == 15) & ((c8 & 7) == 7)) | (s8 == 255))
            top = topbit(prod, 6)
            exponent = exp + top + 127
            fault = nan | ((prod != 0) & ((exponent < 1) | (exponent > 254)))
            val = (sign << 15) | (np.maximum(exponent, 0).astype(np.uint64) << 7) | ((prod << (7 - top).astype(np.uint64)) & 127)
            val = np.where(prod == 0, sign << 15, val)
            integer[:, group * 32 + lane] = np.where(fault, 0, val).astype(np.uint16)
            bad[:, group * 32 + lane] = fault
            # Independent format-table math, not the endpoint exponent assembly.
            fp8 = np.ldexp(np.where(e8 == 0, (c8 & 7) / 8.0, 1.0 + (c8 & 7) / 8.0),
                           np.where(e8 == 0, -6, e8.astype(np.int64) - 7))
            fp8 *= np.where((c8 >> 7) != 0, -1.0, 1.0)
            fp8 *= np.exp2(s8.astype(np.int64) - 127)
            fp4 = np.array([0., .5, 1., 1.5, 2., 3., 4., 6.])[c4 & 7] * np.where((c4 >> 3) != 0, -1., 1.)
            scale = np.ldexp(np.where(se4 == 0, (s4 & 7) / 8.0, 1. + (s4 & 7) / 8.0),
                             np.where(se4 == 0, -6, se4.astype(np.int64) - 7)) * np.where((s4 >> 7) != 0, -1., 1.)
            golden[:, group * 32 + lane] = np.where(fmt, fp4 * scale, fp8).astype(np.float32)
    return integer, golden, bad, formats


def compare(a, b):
    mismatch = np.flatnonzero(a.reshape(-1) != b.reshape(-1))
    first = None
    if mismatch.size:
        i = int(mismatch[0])
        first = {"index": i, "head": i // 512, "dimension": i % 512,
                 "a": f"{int(a.reshape(-1)[i]):08x}", "b": f"{int(b.reshape(-1)[i]):08x}"}
    return {"compared": int(a.size), "mismatches": int(mismatch.size), "first": first}


def run(root, out, closed=False):
    started = time.monotonic()
    out.mkdir(exist_ok=False)
    cap = root / "captured"
    required = {"accepted_p.u32": 20480, "accepted_kv.u32": 339200,
                "old_pv_bus.u32": 32768, "adapter_PV.u32": 32768}
    names = ({"accepted_p.u32": "PV_accepted_p.u32", "accepted_kv.u32": "PV_accepted_kv.u32",
              "old_pv_bus.u32": "PV_old_pv.u32", "adapter_PV.u32": "PV.u32"} if closed else {})
    arrays = {}
    for name, size in required.items():
        p = cap / names.get(name, name)
        if p.stat().st_size != size:
            raise ValueError(f"exact capture extent {name}")
        arrays[name] = np.fromfile(p, dtype="<u4")
    terminal = json.loads((root / "terminal.json").read_text())
    if terminal["exit"] != 0:
        raise ValueError("capture terminal not PASS")
    p = arrays["accepted_p.u32"].view("<u2").reshape(640, 16).T.copy()
    ki, kg, faults, formats = decode(arrays["accepted_kv.u32"])
    decode_check = compare(ki.astype(np.uint32) << 16, kg.view(np.uint32))
    if np.any(faults) or np.any(((p >> 7) & 255) == 255):
        raise ValueError("captured fault/nonfinite operands: require explicit exceptional golden")
    integer = np.zeros((16, 512), dtype=np.uint32)
    golden = np.zeros_like(integer)
    stage_checks = {"product_mismatches": 0, "chunk8_mismatches": 0, "tree_mismatches": 0, "integer_faults": 0}
    for h in range(16):
        products, bad = iproduct(p[h][None, :], ki.T)
        fp = p[h].astype(np.uint32) << 16
        golden_products = (kg.T * fp.view(np.float32)[None, :]).astype(np.float32)
        # Golden arithmetic canonicalizes zero at each multiplication/addition.
        golden_products[golden_products == 0] = np.float32(0)
        stage_checks["product_mismatches"] += int(np.count_nonzero(products != golden_products.view(np.uint32)))
        stage_checks["integer_faults"] += int(np.count_nonzero(bad))
        products = products.reshape(512, 80, 8)
        golden_products = golden_products.reshape(512, 80, 8)
        chunks = np.zeros((512, 80), dtype=np.uint32)
        gc = np.zeros((512, 80), dtype=np.float32)
        for j in range(8):
            chunks, bad = iadd(chunks, products[:, :, j])
            stage_checks["integer_faults"] += int(np.count_nonzero(bad))
            gc = (gc + golden_products[:, :, j]).astype(np.float32)
            gc[gc == 0] = np.float32(0)
        stage_checks["chunk8_mismatches"] += int(np.count_nonzero(chunks != gc.view(np.uint32)))
        chunks = np.pad(chunks, ((0, 0), (0, 48)))
        gc = np.pad(gc, ((0, 0), (0, 48)))
        while chunks.shape[1] > 1:
            chunks, bad = iadd(chunks[:, 0::2], chunks[:, 1::2])
            stage_checks["integer_faults"] += int(np.count_nonzero(bad))
            gc = (gc[:, 0::2] + gc[:, 1::2]).astype(np.float32)
            gc[gc == 0] = np.float32(0)
            stage_checks["tree_mismatches"] += int(np.count_nonzero(chunks != gc.view(np.uint32)))
        integer[h] = chunks[:, 0]
        golden[h] = gc[:, 0].view(np.uint32)
    old = arrays["old_pv_bus.u32"].reshape(8, 64, 16).transpose(2, 1, 0).reshape(16, 512)
    adapter = arrays["adapter_PV.u32"].reshape(16, 512)
    checks = {"integer_vs_golden": compare(integer, golden), "integer_vs_old_pv": compare(integer, old),
              "golden_vs_old_pv": compare(golden, old), "old_pv_vs_adapter": compare(old, adapter),
              "golden_vs_adapter": compare(golden, adapter), "dequant_integer_vs_format_tables": decode_check}
    integer.astype("<u4").tofile(out / "integer_PV.u32")
    golden.astype("<u4").tofile(out / "golden_PV.u32")
    pins = {}
    for rel in ["terminal.json", "frozen_inputs.json" if closed else "inputs/frozen_inputs.json", "captured/events.tsv"] + ["captured/" + names.get(n, n) for n in required] + ["source/capture.cpp", "source/s81_sim_only_attention_endpoint.hpp", "source/s81_minimum_attention_cut.hpp", "source/adapter_config.hpp"]:
        actual_rel = ("headers/tools/runtime/dsrom/" + Path(rel).name
                      if closed and rel in ("source/s81_sim_only_attention_endpoint.hpp", "source/s81_minimum_attention_cut.hpp") else rel)
        pins[actual_rel] = sha(root / actual_rel)
    record = {"schema": "dsrom-i63-same-accepted-bytes-r1", "scope": ("Connected controlled-source rank0 QK -> native SU I61/I62 -> PV; SIM_ONLY endpoint/native adapter/VM ACK; no full token or hardware timing" if closed else "ONE controlled-source rank0 I63 PV; SIM_ONLY endpoint/native adapter; no original-run input attribution or hardware timing"),
              "source_commit": terminal["source_commit"], "capture_root": str(root), "python": platform.python_version(), "numpy": np.__version__,
              "tool_sha256": sha(Path(__file__)), "capture_pins": pins, "geometry": {"heads": 16, "dimensions": 512, "rows": 640, "row_bits": 4240, "products": 5242880, "chunk_size": 8, "chunks": 80, "padded_chunks": 128},
              "fp4_rows_by_group": formats, "checks": checks, "stage_checks": stage_checks,
              "original_full_run_qualification": False, "hardware_timing_qualification": False,
              "elapsed_seconds": time.monotonic() - started,
              "verdict": "PASS" if all(v["mismatches"] == 0 for v in checks.values()) and not any(stage_checks.values()) else "FAIL"}
    (out / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--closed-chain", action="store_true", help="Consume the existing connected QK/SU/PV capture filenames")
    args = ap.parse_args()
    raise SystemExit(run(args.capture_root, args.out, args.closed_chain))
