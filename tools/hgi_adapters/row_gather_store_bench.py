#!/usr/bin/env python3
"""Full-shape FP32 STORE vectors for G96/c2 software ROW_GATHER and a 64-row selected chunk.

The emitted compiler descriptor supplies --vm-base (145344 in the G24 snapshot). Each source word has a distinct
finite FP32 bit pattern; the independent reference scatters the words by row/slot into the two contiguous HBM runs.
No numerical conversion occurs on FP32 STORE. Expected words include the full destination, so drops/duplicates and
incorrect stride or slot selection fail. The bench prints cycles and checks that every write is acknowledged at retire.
"""
import argparse
import json
from pathlib import Path

import dma_bench as B


def generate(out, vm_base):
    out.mkdir(parents=True, exist_ok=True)
    records, cases, initial_vm, expected_hbm, manifest = [], [], [], [], []
    for name, rows, slots in (("slot_gather_c2", 96, 2), ("selected_chunk", 64, 1)):
        initial = {vm_base + i: 0x3F800000 + i for i in range(rows * 512 * slots)}
        expected, moves = {}, []
        for slot in range(slots):
            src = B.md(space=1, fmt=0, base=vm_base + slot * 512, n=512, m=rows, stride=slots * 512)
            dest = ((1 << 35) + (1 << 33) if slots == 2 else 1 << 35) + slot * rows * 2048
            dst = B.md(space=0, fmt=0, base=dest, n=512, m=rows, stride=2048)
            moves.append(B.rec(1, src, dst))
            for row in range(rows):
                for word in range(512):
                    expected[dest // 4 + row * 512 + word] = initial[vm_base + row * slots * 512 + slot * 512 + word]
        cases.append([len(records), slots, len(initial_vm), len(initial), 0, 0, 0, 0, len(expected_hbm), len(expected)])
        records += [B.pack(move) for move in moves]
        initial_vm += sorted(initial.items())
        expected_hbm += sorted(expected.items())
        manifest.append(dict(case=name, rows=rows, words_per_row=512, records=slots,
                             bytes_per_record=rows * 2048, total_bytes=rows * 2048 * slots,
                             vm_base=vm_base, source_stride_words=slots * 512))
    (out / "mo_rec.mem").write_text("".join(f"{x:0176x}\n" for x in records))
    (out / "mo_case.mem").write_text("".join("".join(f"{x:08x}" for x in c) + "\n" for c in cases))
    (out / "mo_vmi.mem").write_text("".join(f"{a:08x}{v:08x}\n" for a, v in initial_vm))
    (out / "mo_hbe.mem").write_text("".join(f"{a:010x}{v:08x}\n" for a, v in expected_hbm))
    for name in ("mo_hbi.mem", "mo_vme.mem"):
        (out / name).write_text("0\n")
    (out / "mo_sizes.svh").write_text(f"localparam integer NREC={len(records)},NCASE=2,VMI={len(initial_vm)},"
                                     f"HBE={len(expected_hbm)},HBI=1,VME=1;\n")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--vm-base", type=int, required=True)
    args = parser.parse_args()
    generate(args.out, args.vm_base)
