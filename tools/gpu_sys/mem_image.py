#!/usr/bin/env python3
"""HBM partition load images for rtl/gpu_sys/ot_gpu_memsys.sv.

Placement rule (die-global byte address X, NS slices, MEM_WORDS 32-byte words per partition):
    slice      s     = (X >> 7) & (NS - 1)                       # 128-byte interleave
    local      L     = ((X >> (7 + log2 NS)) << 7) | (X & 0x7f)  # slice-select bits removed
    sector     S     = L >> 5                                    # partition-local 32-byte sector
    model word W     = S % MEM_WORDS                             # u_model.mem[W] (S must be < MEM_WORDS)
    byte lane  b     = X & 31                                    # bits [8b +: 8] of the 256-bit word
Memory array (hierarchical): <memsys>.g_on.g_s[s].u_part.g_on.u_model.mem   (reg [255:0] mem [0:MEM_WORDS-1])

Loading: write_images() writes "<out_dir>/<prefix>_p<s>.hex" (or "<prefix>_d<die>_p<s>.hex" with die=), one per
partition, zero-filled, one 64-hex-digit word per line (byte lane 31 first, i.e. the Verilog literal of the 256-bit
word).  The partition zeroes its array at time 0 and then runs $readmemh("<prefix>_p<s>.hex", u_model.mem) (memsys
DIE_IDX = -1) or $readmemh("<prefix>_d<DIE_IDX>_p<s>.hex", ...) (DIE_IDX >= 0), where <prefix> is the plusarg
+gpu_sys_mem_prefix=<out_dir>/<prefix> if given, else the memsys parameter IMAGE_PREFIX (empty: nothing loaded).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

VERILOG_SNIPPET = """\
// system top: either pass the prefix as a parameter ...
ot_gpu_memsys #(.ENABLE(1), .NC(4), .NS(2), .NPC(2), .MEM_WORDS(16384), .IMAGE_PREFIX("build/mem/die0")) u_mem (...);
// ... or at run time (overrides the parameter in every partition of every memsys instance):
//   ./Vtop +gpu_sys_mem_prefix=build/mem/die0      -> loads build/mem/die0_p0.hex, build/mem/die0_p1.hex
// multi-die top: give die d's memsys .DIE_IDX(d), write images with write_images(..., prefix="mem", die=d), run
//   ./Vtop +gpu_sys_mem_prefix=build/mem/mem       -> die d loads build/mem/mem_d<d>_p0.hex, ..._p1.hex
// inside ot_gpu_hbm_partition (already implemented):
//   initial begin for (w = 0; w < MEM_WORDS; w++) u_model.mem[w] = 0;
//                 if (prefix != "") $readmemh($sformatf("%s_p%0d.hex", prefix, PART_IDX), u_model.mem); end
//   (with DIE_IDX >= 0 the name is "%s_d%0d_p%0d.hex", prefix, DIE_IDX, PART_IDX)
"""


def _lns(ns: int) -> int:
    if ns < 1 or ns & (ns - 1):
        raise ValueError(f"NS must be a power of two, got {ns}")
    return ns.bit_length() - 1


def placement(addr: int, ns: int, mem_words: int) -> tuple[int, int, int, int]:
    """Die-global byte address -> (slice, partition-local sector, model word, byte lane)."""
    lns = _lns(ns)
    s = (addr >> 7) & (ns - 1)
    local = ((addr >> (7 + lns)) << 7) | (addr & 0x7F)
    sector = local >> 5
    return s, sector, sector % mem_words, addr & 31


def die_address(slice_idx: int, sector: int, lane: int, ns: int) -> int:
    """Inverse of placement(): (slice, partition-local sector, lane) -> die-global byte address."""
    lns = _lns(ns)
    local = (sector << 5) | lane
    return ((local >> 7) << (7 + lns)) | (slice_idx << 7) | (local & 0x7F)


def build_arrays(mem_map: dict, ns: int, mem_words: int) -> np.ndarray:
    """Return uint8[ns, mem_words, 32] partition contents (zero-filled)."""
    lns = _lns(ns)
    img = np.zeros((ns, mem_words, 32), dtype=np.uint8)
    for base, data in mem_map.items():
        buf = np.frombuffer(bytes(data), dtype=np.uint8) if not isinstance(data, np.ndarray) \
            else np.ascontiguousarray(data, dtype=np.uint8).reshape(-1)
        if base < 0 or base + len(buf) > 1 << 32:
            raise ValueError(f"segment at {base:#x} outside the 32-bit byte address space")
        x = np.arange(base, base + len(buf), dtype=np.int64)
        s = (x >> 7) & (ns - 1)
        local = ((x >> (7 + lns)) << 7) | (x & 0x7F)
        sector = local >> 5
        if len(sector) and int(sector.max()) >= mem_words:
            raise ValueError(f"segment at {base:#x} reaches partition sector {int(sector.max())} >= MEM_WORDS "
                             f"{mem_words} (the model would alias it)")
        img[s, sector, x & 31] = buf
    return img


def _write_hex(path: Path, words: np.ndarray) -> None:
    # words: uint8[n, 32], lane 0 = least significant byte -> print lane 31 first
    hexrows = words[:, ::-1].tobytes().hex()
    n = words.shape[0]
    path.write_text("\n".join(hexrows[i * 64:(i + 1) * 64] for i in range(n)) + "\n")


def write_images(mem_map: dict, ns: int, mem_words: int, out_dir, prefix: str = "mem",
                 die: int | None = None) -> list[str]:
    """Write one zero-filled $readmemh image per partition; returns the file names (index = slice).

    die=None -> "<prefix>_p<s>.hex" (memsys DIE_IDX = -1); die=d -> "<prefix>_d<d>_p<s>.hex" (memsys DIE_IDX = d),
    so every die of a multi-die top loads its own images under one +gpu_sys_mem_prefix=<out_dir>/<prefix>.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    img = build_arrays(mem_map, ns, mem_words)
    files = []
    for s in range(ns):
        p = out / (f"{prefix}_p{s}.hex" if die is None else f"{prefix}_d{die}_p{s}.hex")
        _write_hex(p, img[s])
        files.append(str(p))
    return files


def write_die_sectors(mem_map: dict, n_sectors: int, path) -> str:
    """Die-global sector view [0, n_sectors) (sector = X >> 5) as a $readmemh file (bench golden)."""
    flat = np.zeros(n_sectors * 32, dtype=np.uint8)
    for base, data in mem_map.items():
        buf = np.frombuffer(bytes(data), dtype=np.uint8) if not isinstance(data, np.ndarray) \
            else np.ascontiguousarray(data, dtype=np.uint8).reshape(-1)
        lo, hi = max(base, 0), min(base + len(buf), n_sectors * 32)
        if hi > lo:
            flat[lo:hi] = buf[lo - base:hi - base]
    _write_hex(Path(path), flat.reshape(n_sectors, 32))
    return str(path)


def self_check() -> list[str]:
    errs = []
    for ns in (1, 2, 4, 8):
        for x in (0, 31, 32, 127, 128, 129, 4096 + 77, 0x12345, 0xFFFFFE0):
            s, sec, _, lane = placement(x, ns, 1 << 30)
            if die_address(s, sec, lane, ns) != x:
                errs.append(f"placement inverse ns={ns} x={x:#x}")
    rng = np.random.default_rng(0)
    data = rng.integers(0, 256, 3000, dtype=np.uint8)
    img = build_arrays({1000: data}, 2, 4096)
    for i in (0, 1, 500, 2999):
        s, _, w, lane = placement(1000 + i, 2, 4096)
        if img[s, w, lane] != data[i]:
            errs.append(f"build_arrays byte {i}")
    return errs


if __name__ == "__main__":
    e = self_check()
    print("FAIL " + "; ".join(e) if e else "PASS mem_image self-check")
    raise SystemExit(1 if e else 0)
