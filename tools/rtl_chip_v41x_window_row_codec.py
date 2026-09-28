#!/usr/bin/env python3
"""Source-pinned exact packed-window-row codec and 1M ring-address gate."""

import hashlib
import inspect
import json
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from runtime.prefill.v41_aux_kv_rows import pack_window_row
from runtime.prefill.v41_hbm_placement import MAX_CONTEXT, WINDOW_SLOTS
from runtime.reference.formats import (NumericReferenceError, decode_e4m3fn,
                                       decode_e8m0, encode_binary32_rne)
from tools import hdc_golden_v41 as G

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/chip/ot_chip_v41x_window_row_codec.sv"
TB = ROOT / "rtl/test/tb_chip_v41x_window_row_codec.sv"
SOURCES = [RTL, TB, Path(__file__), ROOT / "runtime/prefill/v41_aux_kv_rows.py",
           ROOT / "runtime/prefill/v41_hbm_placement.py",
           ROOT / "runtime/reference/formats.py"]
OUT = ROOT / "results/rtl/chip_v41x_window_row_codec.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function_sha(function):
    return hashlib.sha256(inspect.getsource(function).encode()).hexdigest()


def expected(row, pos, base, region, sector, element):
    off = (pos % WINDOW_SLOTS) * 17 + sector
    addr = (base + off) & ((1 << 30) - 1)
    fault = (pos >= MAX_CONTEXT or sector >= 17 or region < WINDOW_SLOTS * 17
             or base + off >= 1 << 30 or base + region >= 1 << 30
             or base + off >= base + region)
    data = int.from_bytes(row[32*sector:32*sector+32].ljust(32, b"\0"), "little") if not fault else 0
    strobe = (0xFFFFFFFF if sector < 16 else 0xFFFF) if not fault else 0
    code = decode_e4m3fn(row[element])
    scale = decode_e8m0(row[512 + element // 32])
    try:
        if code.value is None or scale.value is None:
            raise NumericReferenceError("nonfinite code or scale")
        bits = encode_binary32_rne(code.value * scale.value)
        efault = 0
    except NumericReferenceError:
        bits, efault = 0, 1
    return addr, data, strobe, int(fault), bits, efault


def main():
    rng = random.Random(0x528f8)
    valid_codes = [v for v in range(256) if (v & 0x7f) != 0x7f]
    vectors = []
    code_of = {float(decode_e4m3fn(c).value): c
               for c in range(256) if (c & 0x7f) != 0x7f}
    code_of[0.0] = 0
    # Include real deployed golden quantization output, not only arbitrary
    # byte patterns.  Each block's scale comes from its 32 pre-quantized inputs.
    for shape in (0.03, 2.5, 300.0):
        x = np.asarray([rng.uniform(-shape, shape) for _ in range(512)], dtype=G.F)
        q, exponents = G.quant_fp8(x)
        deployed = pack_window_row([code_of[float(v)] for v in q],
                                   [int(e) + 127 for e in exponents])
        expected_bf16 = G.qdq_fp8(x)
        decoded_bf16 = G.to_bf16(np.asarray(
            [float(decode_e4m3fn(deployed[i]).value *
                   decode_e8m0(deployed[512+i//32]).value) for i in range(512)], dtype=G.F))
        assert np.array_equal(G.bits(expected_bf16), G.bits(decoded_bf16))
        vectors.extend((deployed, 127, 1000, 2176, i//32, i) for i in range(512))
    # Fixed boundaries: each sector, each scale boundary, ring wrap, maximum
    # position, out-of-range position, region overflow, and last partial sector.
    codes = [valid_codes[(i * 43) % len(valid_codes)] for i in range(512)]
    scales = [0, 1, 64, 120, 126, 127, 128, 129, 150, 200, 240, 254, 127, 127, 127, 127]
    row = pack_window_row(codes, scales)
    for pos in (0, 127, 128, MAX_CONTEXT-1, MAX_CONTEXT):
        for sec in range(18):
            vectors.append((row, pos, 1000, 2176, sec, (sec*31) % 512))
    for i in range(800):
        c = [rng.choice(valid_codes) for _ in range(512)]
        s = [rng.randrange(255) for _ in range(16)]
        row = pack_window_row(c, s)
        vectors.append((row, rng.randrange(MAX_CONTEXT), 65536, 2176,
                        rng.randrange(17), rng.randrange(512)))
    bad_code = bytearray(row); bad_code[511] = 0xff
    bad_scale = bytearray(row); bad_scale[512+15] = 0xff
    vectors.extend(((bytes(bad_code), 0, 1000, 2176, 15, 511),
                    (bytes(bad_scale), 0, 1000, 2176, 16, 511)))
    vectors.extend((row, MAX_CONTEXT-1, base, region, 16, 511)
                   for base, region in (((1 << 30)-1, 2176), ((1 << 30)-2176, 2176),
                                        (1000, 2175), (1000, 2176)))
    # Append two writes to the same ring slot.  Apply the RTL-emitted sector
    # data and strobes to a logical HBM store, then check each readback.  The
    # die scheduler's request ordering remains a separate integration gate.
    a = pack_window_row([0x38] * 512, [127] * 16)
    b = pack_window_row([0x3c] * 512, [128] * 16)
    replay_start = len(vectors)
    for payload in (a, b):
        vectors.extend((payload, 128, 1000, 2176, sec, 0) for sec in range(17))
    with tempfile.TemporaryDirectory(prefix="v41_window_codec_") as td:
        t = Path(td)
        src, dst, binary = t / "vectors.txt", t / "actual.txt", t / "sim.vvp"
        with src.open("w") as f:
            for row, pos, base, region, sector, element in vectors:
                f.write(f"{int.from_bytes(row, 'little'):01056x} {pos} {base} {region} {sector} {element}\n")
        subprocess.run(["iverilog", "-g2012", "-s", "tb_chip_v41x_window_row_codec",
                        "-o", str(binary), str(RTL), str(TB)], check=True, cwd=ROOT)
        subprocess.run(["vvp", str(binary), f"+IN={src}", f"+OUT={dst}"], check=True, cwd=ROOT)
        lines = dst.read_text().splitlines()
        assert len(lines) == len(vectors)
        for i, (line, vector) in enumerate(zip(lines, vectors)):
            got = tuple(int(value, 2 if j in (3, 5) else 16)
                        for j, value in enumerate(line.split()))
            want = expected(*vector)
            assert got == want, (i, got, want)
        sector_store = {}
        for row_number, payload in enumerate((a, b)):
            for sec in range(17):
                address, data, mask, fault, _, _ = (
                    int(value, 2 if j in (3, 5) else 16)
                    for j, value in enumerate(lines[replay_start+row_number*17+sec].split()))
                assert fault == 0
                prior = sector_store.get(address, bytearray(32))
                raw = data.to_bytes(32, "little")
                for lane in range(32):
                    if mask >> lane & 1:
                        prior[lane] = raw[lane]
                sector_store[address] = prior
            got = b"".join(sector_store[1000+sec] for sec in range(17))[:528]
            assert got == payload
    record = {
        "status": "pass", "scope": "standalone window-row codec; no integrated prefetch or FP32 quantizer",
        "profile": "opentallas.deepseek_v41.window_fp8_e4m3_s32_e8m0.row.v1",
        "vectors": len(vectors), "mismatches": 0,
        "payload_bytes": 528, "sector_bytes": 32, "sectors_per_row": 17,
        "hbm_pitch_bytes": 544, "window_slots": WINDOW_SLOTS,
        "max_context": MAX_CONTEXT, "read_after_write_rows": 2,
        "deployed_golden_rows": 3,
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES},
        "golden_functions": {fn.__name__: function_sha(fn) for fn in
                             (G._ceil_log2, G._round_grid, G.quant_fp8,
                              G.qdq_fp8, G.to_bf16)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
