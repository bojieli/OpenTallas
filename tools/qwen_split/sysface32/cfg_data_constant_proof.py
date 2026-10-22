#!/usr/bin/env python3
"""Source-literal proof for the SYSFACE32 cfg_data constant bits (native inventory constant_outputs_not_FF).

cfg_data is written only by ot_qwen_d2d_cal_seq (reset '0, IMG words TX_IMG/RX_IMG[32*x+:32], RXB0/TXB0 = SEG2 (ADM=1)
or SEG1, TX_SEG2/RX_SEG2, TX_SEG1/RX_SEG1), all compile-time localparams of d2d_cal_image_mu.svh.  A cfg_data bit is a
source-literal constant 0 iff it is 0 in every one of those words, for every image set the face can elaborate (C and K).
"""
import json, re, sys
from pathlib import Path
svh = Path(sys.argv[1]).read_text()
lp = {}
for m in re.finditer(r"localparam \[[^\]]+\] (\w+) = \d+'h([0-9a-fA-F]+)", svh):
    lp[m[1]] = int(m[2], 16)
words = {}
for s in "CK":
    for d in ("TX", "RX"):
        img = lp[f"D2D_CAL_{s}_{d}_IMG"]
        for x in range(32):
            words[f"{s}_{d}_IMG[{x}]"] = (img >> (32 * x)) & 0xffffffff
        for g in ("SEG1", "SEG2"):
            words[f"{s}_{d}_{g}"] = lp[f"D2D_CAL_{s}_{d}_{g}"]
ormask = 0
for v in words.values():
    ormask |= v
zero = [b for b in range(32) if not (ormask >> b) & 1]
claimed = [int(b) for b in sys.argv[2].split(",")]
ok = set(claimed) <= set(zero)
out = {"schema": "opentallas.sysface32.cfg_data_constant_proof.v1", "svh": sys.argv[1], "words": len(words),
       "or_mask_hex": f"{ormask:08x}", "source_zero_bits": zero, "native_constant_bits": claimed, "PASS": ok,
       "scope": "every cfg_data source word (reset 0, C/K TX/RX IMG x32, SEG1, SEG2) has these bits 0; the native TIELO outputs are source-literal constants, no functional tie"}
print(json.dumps(out, indent=1)); sys.exit(0 if ok else 1)
