#!/usr/bin/env python3
"""Compile native LG selectors solely from the whole-SU command image.

cal.mem bits [31:0] read, [63:32] write, bank=q*8+p. pgslice
VM read pins pass straight to LG; drain payload register drives LG at E+4.
No expected answer or DUT signal is an input to this compiler.
"""
import argparse
import json
from pathlib import Path


def compile_calendar(lines):
    cal = [0] * len(lines)
    nr = nw = 0
    for e, line in enumerate(lines):
        for q in range(4):
            quarter = line >> (q * 2422)
            vmr = (quarter >> (74 + 54 + 312)) & ((1 << 240) - 1)
            vmw = (quarter >> (74 + 54)) & ((1 << 312) - 1)
            for p in range(8):
                if (vmr >> (p * 30 + 29)) & 1:
                    cal[e] |= 1 << (q * 8 + p)
                    nr += 1
                if (vmw >> (p * 39 + 38)) & 1:
                    if e + 4 >= len(lines):
                        raise ValueError(f"write at edge{e} escapes programme")
                    cal[e + 4] |= 1 << (32 + q * 8 + p)
                    nw += 1
    return cal, dict(edges=len(lines), read_slots=nr, write_slots=nw,
                     layout="[63:32]write32 [31:0]read32; bit q*8+p",
                     read_command_to_lg_edges=0, write_command_to_lg_edges=4,
                     source="prog.mem commands only; independent of expected results")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("programme", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    lines = [int(x, 16) for x in args.programme.read_text().split()]
    cal, meta = compile_calendar(lines)
    args.output.write_text("".join(f"{x:016x}\n" for x in cal))
    args.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
