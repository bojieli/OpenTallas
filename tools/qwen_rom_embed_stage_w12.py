#!/usr/bin/env python3
"""Emit the embedding stage E of the REAL_MEM Qwen ROM runtime (default-off).

The retained runtime preloads the token's X row into the vector memory.  With REAL_MEM the X
row comes from the INT8 embedding ROM (rtl/hdc/ot_qwen_rt_embed_rom.sv) through the core's
INT8_EMBED stream path: one stream-unit instruction, the same one hdc_program.build_program
emits for an embedding stage (a_src = SRC_ALT, a_d = DYN_EMBED, 4,096 elements to VM X) without
the sum of squares (layer 0's program opens with its own), then END.  One END descriptor, no
collective: every die embeds the full row.  No matrix, scale or constant image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import hdc_isa as I
import hdc_program as P
import hdc_qwen_fullshape_isa_w12 as QI
import hdc_qwen_fullshape_program_w12 as FP


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    vm, _ = FP.vm_map()
    prog = [dict(unit=I.UNIT_SU, su_nout=1, su_nin=4096, a_src=I.SRC_ALT, a_base=0, a_d=I.DYN_EMBED, a_si=1,
                 dst=I.DST_VM, d_base=vm['X'], d_si=1),
            dict(unit=I.UNIT_END, barrier=1)]
    words = [QI.encode_instruction(f) for f in prog]
    desc = [QI.encode_descriptor(P.COLL_END, 0, 0, 0, 0)]
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'program.hex').write_text(''.join(f'{w:0256x}\n' for w in words))
    (a.out / 'segments.hex').write_text(''.join(f'{d:016x}\n' for d in desc))
    for name in ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex'):
        (a.out / name).write_text('')
    rec = {'schema': 'opentallas.qwen-rom-embed-stage.v1', 'x_vm_element': vm['X'],
           'instructions': [{k: v for k, v in QI.decode_instruction(w).items() if v} for w in words],
           'sha256': {n: hashlib.sha256((a.out / n).read_bytes()).hexdigest() for n in ('program.hex', 'segments.hex')}}
    (a.out / 'embed_stage.json').write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
    print(json.dumps(rec['instructions']))


if __name__ == '__main__':
    main()
