#!/usr/bin/env python3
"""Default-off bounded remainder state over the preserved DEC_LA emitter."""
import argparse
from pathlib import Path
import qwen_rom_core_dec_emit_w12 as E


def apply(text):
    edits = [
        ('    parameter integer DEC_LA = 0\n) (',
         '    parameter integer DEC_LA = 0,\n    parameter integer DEC_LA_BOUND = 0\n) ('),
        ('    reg [LA_SW-1:0] la_lo [0:LA_NO*16-1];',
         """    // E2 remainder < ODD, packed above H low bits: at most ODD*2**H-1.
    // Preserve original SW truncation for other parameters. E1/E2/E3 unchanged.
    localparam integer LA_LO_W = (DEC_LA_BOUND != 0 && LA_ODD > 0 && LA_H > 0)
        ? ((LA_H + $clog2(LA_ODD) < LA_SW) ? LA_H + $clog2(LA_ODD) : LA_SW) : LA_SW;
    reg [LA_LO_W-1:0] la_lo [0:LA_NO*16-1];"""),
    ]
    for old,new in edits:
        if text.count(old)!=1:
            raise ValueError(f'bounded-state anchor not unique: {old!r}')
        text=text.replace(old,new)
    return text


def emit(text):
    return apply(E.emit(text))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(emit(E.V.E.CORE.read_text()))
