#!/usr/bin/env python3
"""Compile source-produced expert IDs into the existing 24-SM native ABI.

The caller supplies the layer, die and input-job identity. No router, weights,
activation payload, arithmetic, ownership ledger or hardware is constructed.
seq.hex is ONE eight-word operation shared by the active SMs, not a serial
24-operation program. descriptors.json selects each SM's slice in the flat
1088-bit weight stream produced by the shared workgroup layout provider.
"""
import argparse
import hashlib
import json
from numbers import Integral
from pathlib import Path
import struct

try:
    from .dshbm_expert_workgroup import steer
except ImportError:  # Direct script invocation: tools/ is on sys.path.
    from dshbm_expert_workgroup import steer


SEQ_FIELDS = ("rows", "c", "groups", "fmt", "lines", "gs", "load", "xaddrs")
SEQ_WORDS = (12, 8, 3, 2, 288, 1, 1, 24)


def read_expert_ids(path):
    """Read exactly six little-endian u32 IDs; never sort or repair them."""
    data = Path(path).read_bytes()
    if len(data) != 24:
        raise ValueError("expert_ids.u32 must contain exactly six little-endian u32 IDs")
    return struct.unpack("<6I", data)


def compile_descriptors(expert_ids, *, layer, die, input_job):
    """Return a data-only native table; all expert/SM steering is delegated."""
    ids = tuple(expert_ids)
    if (len(ids) != 6 or any(isinstance(x, bool) or not isinstance(x, Integral)
                            or not 0 <= x < 384 for x in ids)
            or tuple(sorted(set(ids))) != ids):
        raise ValueError("six distinct released IDs in ascending source order, range 0..383, required")
    if isinstance(layer, bool) or not isinstance(layer, Integral) or layer < 0:
        raise ValueError("caller-supplied layer must be a nonnegative integer")
    if not isinstance(input_job, str) or not input_job.strip():
        raise ValueError("caller-supplied input-job identity must be a nonempty string")
    selected = steer(ids, die)
    if tuple(d.sm for d in selected) != tuple(range(24)):
        raise ValueError("shared steering must select exactly SM0..23 in emitted caller order")
    records = []
    for d in selected:
        if d.row_stop - d.row_start != 12 or not 0 <= d.row_start < d.row_stop <= 2304:
            raise ValueError("shared steering returned an invalid released checkpoint row range")
        base = d.sm * 288
        if not 0 <= base < (1 << 32) or not 0 < 288 < (1 << 24):
            raise ValueError("native d_base32/d_lines24 width overflow")
        records.append({
            "sm": d.sm, "slot": d.slot, "expert": d.expert,
            "matrix": d.matrix, "row_start": d.row_start, "row_stop": d.row_stop,
            "tensor": f"layers.{int(layer)}.{d.tensor}",
            "d_base": base, "d_lines": 288,
            "op_rows": 12, "op_c": 8, "op_g": 3, "op_fmt": 2, "op_gs": 1,
            "load": 1, "xaddrs": 24,
        })
    return {
        "schema": "dshbm_expert_workgroup_descriptor_r1",
        "layer": int(layer), "die": int(die), "input_job": input_job,
        "expert_ids": [int(x) for x in ids],
        "descriptors": records, "inactive_sms": list(range(24, 32)),
        "seq_fields": list(SEQ_FIELDS), "seq_words": list(SEQ_WORDS),
        "seq_scope": "one operation per active SM; not 24 operations on one SM",
        "weight_stream": {"line_bits": 1088, "lines": 6912,
                          "ordering": "descriptor order, contiguous 288-line SM slices",
                          "d_base_unit": "1088-bit line", "d_base_bits": 32,
                          "d_lines_bits": 24},
        "scope": "descriptor metadata only; payload delivery, execution, timing and physical admission unqualified",
    }


def write_descriptors(record, out):
    """Write the native table and shared single-op bench sequence template."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "descriptors.json").write_text(json.dumps(record, indent=2) + "\n")
    (out / "seq.hex").write_text("".join(f"{word:08x}\n" for word in SEQ_WORDS))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expert-ids", type=Path, required=True,
                        help="actual six source-produced little-endian u32 IDs")
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--die", type=int, required=True)
    parser.add_argument("--input-job", required=True, help="opaque caller identity, preserved verbatim")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        record = compile_descriptors(read_expert_ids(args.expert_ids), layer=args.layer,
                                     die=args.die, input_job=args.input_job)
        record["expert_ids_source"] = {
            "path": str(args.expert_ids.resolve()),
            "sha256": hashlib.sha256(args.expert_ids.read_bytes()).hexdigest(),
            "encoding": "little-endian u32", "bytes": 24,
        }
        write_descriptors(record, args.out)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
