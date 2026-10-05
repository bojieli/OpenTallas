#!/usr/bin/env python3
"""Default-off chase-count NEXT register over the bounded-state ROM decode."""
import argparse
from pathlib import Path
import qwen_rom_core_dec_bound_emit_w12 as B


def apply(text):
    old='    parameter integer DEC_LA_BOUND = 0\n) ('
    new='    parameter integer DEC_LA_BOUND = 0,\n    parameter integer DEC_LA_CHASE_Q = 0\n) ('
    if text.count(old)!=1:
        raise ValueError('chase parameter anchor not unique')
    text=text.replace(old,new)
    old='    assign d_chase_n = (DEC_LA != 0) ? fqd_d_chase_n[la_nx] : d_chase_n_q;'
    new='''    // Capture the head count with the other NEXT controls. A simultaneous
    // issue consumes the previous count; nonblocking capture supplies the next.
    reg [15:0] la_chase_q;
    always @(posedge clk) if (DEC_LA != 0 && DEC_LA_CHASE_Q != 0 && load)
        la_chase_q <= fqd_d_chase_n[la_rd];
    assign d_chase_n = (DEC_LA != 0)
        ? ((DEC_LA_CHASE_Q != 0) ? la_chase_q : fqd_d_chase_n[la_nx]) : d_chase_n_q;'''
    if text.count(old)!=1:
        raise ValueError('chase field anchor not unique')
    return text.replace(old,new)


def emit(text):
    return apply(B.emit(text))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(emit(B.E.V.E.CORE.read_text()))
