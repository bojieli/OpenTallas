#!/usr/bin/env python3
"""Family weight specs for ``rom_gen.py weights`` (ROM-WEIGHTS-1119): which released tensor slice each ROM holds.

    python3 tools/mem_compiler/rom_weight_specs.py s81hd --row-map physical/die_plan/s81_head/bind/row_map.json \\
        --rank 0 --out spec_r0.json [--slots 0-3]

s81hd = the S81 head die (ot_s81hd_bundle: 4 x ot_s81hd_elemA_cv + 1 x ot_s81hd_elemB_cv, each 2 x ot_rom_4096x274_m8
read ping-pong).  DeepSeek-V4.1-Flash ``head.weight`` [129280, 5120] BF16, bytes unchanged:
  * elemA q (q = 0..3): rows ROW0 + 32 q .. + 32 (valid rows only), K 0..4095: 8,192 words of 16 BF16, row-major;
  * elemB: the bundle's 128 rows in the B join order 32 q + k (k-major over q), K 4096..5119; invalid rows are zero;
  * every element's image is SKEWED (rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv): physical word p, lane j = logical word
    (p - SK (j mod 8)) mod 8192 with SK = 1 + popcount(CUT 9'h1ff) + SPLIT9 1 = 11; word p sits in ROM p % 2 at p // 2
    (instances <INSTANCE>_0 / _1, INSTANCE = bundle "a<q>" / "b" as ot_s81hd_bundle names them).
Row ownership (ROW0, valid rows per bundle slot, dark slots) comes from the head row map (bind/row_map.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HEAD_KEY = "head.weight"
HEAD_SHAPE = (129280, 5120)
S81HD_SK = 11
S81HD_MACRO = "ot_rom_4096x274_m8"


def s81hd_b_order(valid: int) -> list[int | None]:
    """elemB row order: position 4 k + q holds bundle row 32 q + k (None where the row is past the valid rows)."""
    return [r if r < valid else None for r in (32 * q + k for k in range(32) for q in range(4))]


def s81hd_rom_entries(prefix: str, row0: int | None, valid: int) -> list[dict]:
    roms = []
    for q in range(4):
        n = max(0, min(32, valid - 32 * q))
        segs = [{"tensor": HEAD_KEY, "row0": row0 + 32 * q, "rows": n, "col0": 0, "cols": 4096}] if n else []
        roms.append({"instances": [f"{prefix}a{q}_0", f"{prefix}a{q}_1"], "skew": S81HD_SK, "skew_mod": 8, "segments": segs})
    segs = ([{"tensor": HEAD_KEY, "row0": row0, "rows": valid, "col0": 4096, "cols": 1024,
              "row_order": s81hd_b_order(valid)}] if valid else [])
    roms.append({"instances": [f"{prefix}b_0", f"{prefix}b_1"], "skew": S81HD_SK, "skew_mod": 8, "segments": segs})
    return roms


def s81hd_spec(row_map: Path, rank: int, slots: range | None = None, checkpoint: dict | None = None) -> dict:
    rm = json.loads(Path(row_map).read_text())
    if rm.get("schema") != "opentallas.s81.head-row-map.v1" or rm["vocabulary"] != HEAD_SHAPE[0]:
        raise ValueError("unexpected head row map")
    rk = next(r for r in rm["ranks"] if r["rank"] == rank)
    roms = []
    for s in rk["slots"]:
        if slots is not None and s["slot"] not in slots:
            continue
        valid = int(s["weight_rows"] or 0)
        if valid > rm["rows_per_bundle"]:
            raise ValueError(f"slot {s['slot']}: {valid} rows > bundle")
        roms += s81hd_rom_entries(f"hd_r{rank}_{s['part']}_", s["weight_row0"], valid)
    return {"schema": "opentallas.rom-weights-spec.v1", "family": "s81hd", "macro": S81HD_MACRO, "lane_bits": 16,
            "payload_bits": 256, "checkpoint": checkpoint or {}, "rank": rank,
            "row_map_sha256": hashlib.sha256(Path(row_map).read_bytes()).hexdigest(), "roms": roms}


def _slots(text: str | None) -> range | None:
    if not text:
        return None
    a, _, b = text.partition("-")
    return range(int(a), int(b or a) + 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="family", required=True)
    h = sub.add_parser("s81hd")
    h.add_argument("--row-map", type=Path, required=True)
    h.add_argument("--rank", type=int, required=True)
    h.add_argument("--slots", help="slot range a-b (default: every slot of the rank)")
    h.add_argument("--revision", default="dba1be0a40aa45a94ad051997016db3960a90277")
    h.add_argument("--index-sha256", default="74b0686a3d2891980d5e303251b075a3bccae2c2ff650747db2620a649b98fa8")
    h.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    spec = s81hd_spec(a.row_map, a.rank, _slots(a.slots),
                      {"repo": "deepseek-ai/DeepSeek-V4.1-Flash", "revision": a.revision, "index_sha256": a.index_sha256})
    a.out.write_text(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"roms": sum(len(r["instances"]) for r in spec["roms"]), "out": str(a.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
