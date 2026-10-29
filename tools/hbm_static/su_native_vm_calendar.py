#!/usr/bin/env python3
"""Compile native LG selectors solely from the whole-SU command image.

cal.mem bits [31:0] read, [63:32] write, bank=q*8+p. pgslice
VM read pins pass straight to LG; drain payload register drives LG at E+4.
No expected answer or DUT signal is an input to this compiler.
"""
import argparse
import json
from pathlib import Path


def compile_calendar(lines, quarters=4, qids=None, quarter_bits=2422):
    if quarters not in (2, 4) or quarter_bits not in (2422, 2470):
        raise ValueError('unsupported real producer geometry')
    qids = tuple(range(quarters)) if qids is None else tuple(qids)
    if len(qids) != quarters or len(set(qids)) != quarters or any(q not in range(4) for q in qids):
        raise ValueError('one distinct physical QID per producer')
    if quarters == 2 and qids != (2, 3):
        raise ValueError('actual two-quarter source is NW2/NE3')
    cal = [0] * len(lines)
    nr = nw = 0
    for e, line in enumerate(lines):
        if line < 0 or line >= 1 << (quarters * quarter_bits):
            raise ValueError('programme word exceeds selected producer columns')
        for q, qid in enumerate(qids):
            quarter = line >> (q * quarter_bits)
            vmr = (quarter >> (74 + 54 + 312)) & ((1 << 240) - 1)
            vmw = (quarter >> (74 + 54)) & ((1 << 312) - 1)
            for p in range(8):
                if (vmr >> (p * 30 + 29)) & 1:
                    cal[e] |= 1 << (qid * 8 + p)
                    nr += 1
                if (vmw >> (p * 39 + 38)) & 1:
                    if e + 4 >= len(lines):
                        raise ValueError(f"write at edge{e} escapes programme")
                    cal[e + 4] |= 1 << (32 + qid * 8 + p)
                    nw += 1
    return cal, dict(edges=len(lines), read_slots=nr, write_slots=nw,
                     layout="[63:32]write32 [31:0]read32; bit q*8+p",
                     read_command_to_lg_edges=0, write_command_to_lg_edges=4,
                     source="prog.mem commands only; independent of expected results")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("programme", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument('--quarters', type=int, choices=[2,4], default=4)
    ap.add_argument('--qids', type=int, nargs='+')
    ap.add_argument('--quarter-bits', type=int, choices=[2422,2470], default=2422)
    args = ap.parse_args()
    lines = [int(x, 16) for x in args.programme.read_text().split()]
    cal, meta = compile_calendar(lines,args.quarters,args.qids,args.quarter_bits)
    if args.quarters == 2:
        meta.update(quarters=2,qids=[2,3],quarter_bits=args.quarter_bits,
                    qualification='SU local selectors only; complete native bank clients/arrival slots remain required')
    args.output.write_text("".join(f"{x:016x}\n" for x in cal))
    args.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
