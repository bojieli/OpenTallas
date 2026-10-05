#!/usr/bin/env python3
"""Pack ONE deployment into the memory images the integrated vehicle loads.

tools/build_abi3_deployment_rtl_vectors.py packs every shipped target into one
set of concatenated images, so it cannot emit a single deployment's images
without rebuilding the committed set. This packs one, which is what a reduced
regression configuration needs.

The layout is not invented here; it is the same arithmetic that builder performs,
and the ``--verify-against`` mode proves that by packing a target whose images
are already committed and comparing row for row. A packer that agrees with the
committed images on a known deployment is the only reason to trust it on a new
one.

    program      program.bin[256:] in 32-byte little-endian rows (8 lanes of 32 bits)
    header       program.bin[:256] in 4-byte little-endian words
    descriptors  each table record's first 192 bytes, zero-padded, little-endian
                 (48 lanes of 32 bits)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.deployment import Deployment  # noqa: E402

DESCRIPTOR_PREFIX_BYTES = 192


def pack(directory: Path) -> dict[str, object]:
    deployment = Deployment.read(directory)
    image = (directory / "program.bin").read_bytes()
    header_blob = image[:256]
    body = image[256:]

    program_words = [
        int.from_bytes(body[o : o + 32], "little") for o in range(0, len(body), 32)
    ]
    header_words = [
        int.from_bytes(header_blob[i : i + 4], "little")
        for i in range(0, len(header_blob), 4)
    ]
    table = deployment.table
    desc_words = []
    for index in range(len(table)):
        record = table._records[index]  # noqa: SLF001
        prefix = record[:DESCRIPTOR_PREFIX_BYTES]
        prefix = prefix + bytes(DESCRIPTOR_PREFIX_BYTES - len(prefix))
        desc_words.append(int.from_bytes(prefix, "little"))

    return {
        "program_words": program_words,
        "header_words": header_words,
        "desc_words": desc_words,
        "instruction_count": int.from_bytes(header_blob[16:20], "little"),
        "entrypoint_count": int.from_bytes(header_blob[20:24], "little"),
        "declared_work": int.from_bytes(header_blob[184:192], "little"),
        "descriptor_count": len(desc_words),
        "deployment_sha256": deployment.deployment_digest.hex(),
    }


def hex_rows(values: list[int], width_bits: int) -> list[str]:
    digits = width_bits // 4
    return [f"{v:0{digits}x}" for v in values]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deployment", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--verify-against", type=Path,
                    help=("a directory of committed images; the packed rows must "
                          "match its leading rows exactly"))
    args = ap.parse_args()

    packed = pack(args.deployment)
    prog = hex_rows(packed["program_words"], 256)
    desc = hex_rows(packed["desc_words"], DESCRIPTOR_PREFIX_BYTES * 8)
    hdr = hex_rows(packed["header_words"], 32)

    print(f"  {args.deployment}")
    print(f"    deployment sha256   {packed['deployment_sha256']}")
    print(f"    program rows        {len(prog)}")
    print(f"    descriptor rows     {len(desc)}")
    print(f"    instruction_count   {packed['instruction_count']}")
    print(f"    entrypoint_count    {packed['entrypoint_count']}")
    print(f"    declared_work       {packed['declared_work']}")

    if args.verify_against:
        ok = True
        for name, rows in (("a3_program.hex", prog), ("a3_descriptor.hex", desc),
                           ("a3_header.hex", hdr)):
            committed = (args.verify_against / name).read_text().split()
            lead = committed[: len(rows)]
            if lead != rows:
                ok = False
                first = next((i for i, (a, b) in enumerate(zip(lead, rows)) if a != b),
                             None)
                print(f"    MISMATCH {name}: first differing row {first}")
            else:
                print(f"    {name:<20} leading {len(rows)} rows MATCH the committed image")
        if not ok:
            return 1
        print("    packer agrees with the committed images on this deployment")

    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "a3_program.hex").write_text("".join(r + "\n" for r in prog))
        (args.out_dir / "a3_descriptor.hex").write_text("".join(r + "\n" for r in desc))
        (args.out_dir / "a3_header.hex").write_text("".join(r + "\n" for r in hdr))
        (args.out_dir / "layout.json").write_text(json.dumps(
            {k: v for k, v in packed.items()
             if k not in ("program_words", "header_words", "desc_words")},
            indent=2, sort_keys=True) + "\n")
        print(f"    wrote images to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
