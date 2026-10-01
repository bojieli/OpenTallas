#!/usr/bin/env python3
"""ROM-field images of one full-shape V4.1 layer die (W17) from the die's weight-op list.

    python3 tools/v41_die_field.py --snapshot <HF snapshot> --weights DIR/weights.json --out DIR \
        [--np 8192 --active 6899 --regions 128 --nbf 1024 --depth 8192 --phw 6]

weights.json: the rank's weight ops in program order, [{pc, kind: "qe"|"me", key, tensor, fmt, rows: [r0, r1],
cols: [c0, c1], out: "bf16"|"fp32"}] (tools/v41_die_l0_images.py).  Every op is one field PHASE (its own x; the
program issues one matrix per op).  The field is the die's: NP pair slots (the return tree), `active` elements
(the W1/W10 floorplan's pairs), R return regions (one root and VM write port each), NBF BF16-capable pairs.
Writes, into --out: e<p>.words.hex / e<p>.cfg.hex per active pair, field.txt, spine_phase.hex, spine_stream.hex,
spine_keys.hex (the adapter's phase-key CAM: {valid, ME op, key}), and field_phases.json (per phase: matrix,
split, stream beats, the bank map's t_read and t_phase, segments per pair).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w17_runtime_v41_die_images as I  # noqa: E402
from rtl_v41_rom_array import Ckpt, Mat  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mat(ck: Ckpt, name: str, fmt: str, rows: int, K: int, r0: int, k0: int) -> Mat:
    """A rank slice.  A BF16 phase over an FP8-stored tensor (wo_a: the golden computes it as mv on its dequantised
    values, W10's bank map places it on the BF16 lanes) carries the exact BF16 of code * 2^scale."""
    dt = ck.raw(name + ".weight")[0]
    if fmt == "bf16" and dt == "F8_E4M3":
        q = Mat(ck, name, "fp8", rows, K, r0=r0, k0=k0)
        v = np.ldexp(q.w.q, np.repeat(q.w.e, 32, axis=1)).astype(np.float32)
        b = v.view(np.uint32)
        assert np.all((b & 0xFFFF) == 0), "FP8 x UE8M0 value not exact in BF16"
        m = Mat.__new__(Mat)
        m.name, m.fmt, m.rows, m.K, m.r0, m.k0, m.phase = name, "bf16", rows, K, r0, k0, "wo_a"
        m.u16 = (b >> 16).astype(np.uint16)
        m.wf = v
        return m
    return Mat(ck, name, fmt, rows, K, r0=r0, k0=k0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--np", type=int, default=8192)
    ap.add_argument("--active", type=int, default=6899)
    ap.add_argument("--regions", type=int, default=128)
    ap.add_argument("--nbf", type=int, default=1024)
    ap.add_argument("--depth", type=int, default=8192)
    ap.add_argument("--phw", type=int, default=6)
    a = ap.parse_args()
    t0 = time.time()
    ops = json.loads(a.weights.read_text())
    ck = Ckpt(a.snapshot)
    fld = I.Field(a.np, a.regions, a.nbf, depth=a.depth, active=a.active)
    keys = []
    for op in ops:
        (r0, r1), (c0, c1) = op["rows"], op["cols"]
        name = op["tensor"][:-len(".weight")] if op["tensor"].endswith(".weight") else op["tensor"]
        m = mat(ck, name, op["fmt"], r1 - r0, c1 - c0, r0, c0)
        fp32 = op["out"] == "fp32"
        ph = I.add_phase(fld, [m], (fp32, fp32), 0)
        ph.update(pc=op["pc"], kind=op["kind"], key=op["key"])
        keys.append((1 << 31) | ((1 if op["kind"] == "me" else 0) << 30) | (int(op["key"]) & ((1 << 30) - 1)))
        print(f"phase {ph['index']} pc {op['pc']} {op['tensor']} {op['fmt']} rows {r1 - r0} K {c1 - c0} beats "
              f"{ph['nbeat']} t_read {ph['t_read']} t_phase {ph['t_phase_model']} segs/pair {ph['segments_per_pair_max']}",
              flush=True)
    assert len(fld.phases) <= (1 << a.phw), "more phases than the configuration ROM holds"
    assert len(set(keys)) == len(keys), "two phases share a key"
    I.write_field(fld, a.out, a.phw, flat_viamaps=False)
    (a.out / "spine_keys.hex").write_text("".join(f"{k:08x}\n" for k in keys + [0] * ((1 << a.phw) - len(keys))))
    rec = dict(schema="opentallas.rtl.w17_die_field_images.v1", weights=str(a.weights), weights_sha256=sha(a.weights),
               params=dict(np=a.np, active=a.active, regions=a.regions, nbf=a.nbf, depth=a.depth, phw=a.phw),
               rom_fill_max_words=int(fld.fill.max()), stream_words=len(fld.stream), phases=fld.phases,
               checkpoint_header_sha256=ck.pins,
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / "tools/w17_runtime_v41_die_images.py",
                                                                         ROOT / "tools/v41_rom_ksplit_bankmap.py",
                                                                         ROOT / "tools/rtl_v41_rom_array.py")},
               wall_s=round(time.time() - t0, 1))
    (a.out / "field_phases.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"done {len(fld.phases)} phases, fill max {int(fld.fill.max())} words, stream {len(fld.stream)} words, "
          f"{time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
