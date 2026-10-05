#!/usr/bin/env python3
"""Real reduced L0.router operand/weight/expected-result fixture for the ME HBM gate."""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

os.environ["HDC_V41_ARITH"] = "chunk8"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdc_program_v41 as P
import hdc_isa as I
import hdc_golden_v41 as V
import hdc_golden as G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mbank", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    m = V.Model()
    prompt, _ = V.prompt_and_expected()
    lay = P.Layout(m)
    prog = P.Builder(lay, qchunk=P.QCHUNK).build()
    pc = next(i for i, f in enumerate(prog) if f.get("_tag") == "L0.router")
    f = prog[pc]
    assert (pc, f["me_wbase"], f["me_nout"], f["me_tiles"], f["me_k"], f["me_split"]) == (55, 10100, 12, 1, 40, 2)
    token, pos = prompt[-1], len(prompt)-1
    st = P.golden_prefill(m, prompt[:-1])
    mach = P.Machine(lay, lay.kv_image(st), lay.vm_image(st, pos))
    mach.tokens = list(prompt[:-1])
    mach.run(prog, token, pos, stop=pc)
    xb = f["me_xbase"]
    x = G.bits(mach.vm[xb:xb+160])
    mach.run(prog, token, pos, stop=pc+1, entry=pc)
    ob = f["me_obase"] * I.W_LANES
    y = G.bits(mach.vm[ob:ob+12])
    (args.out / "x.hex").write_text("".join(f"{int(v):08x}\n" for v in x))
    (args.out / "y.hex").write_text("".join(f"{int(v):08x}\n" for v in y))
    lo, hi = 10100*64, (10100+36)*64
    words = np.zeros(hi-lo, dtype=np.uint32)
    addr = 0
    for line in args.mbank.read_text().splitlines():
        if line.startswith("@"):
            addr = int(line[1:], 16)
        else:
            if lo <= addr < hi:
                words[addr-lo] = int(line, 16)
            addr += 1
    (args.out / "mbank_slice.hex").write_text("".join(f"{int(v):08x}\n" for v in words))
    meta = {"pc": pc, "tag": "L0.router", "token": token, "pos": pos, "wbase": 10100,
            "bank_words": 36, "x_elements": 160, "expected_rows": 12,
            "mbank_source": str(args.mbank), "claim": "reduced real L0.router operation only"}
    (args.out / "fixture.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
