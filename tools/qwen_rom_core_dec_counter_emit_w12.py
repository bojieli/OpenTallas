#!/usr/bin/env python3
"""Default-off exact byte-sliced cycle counter with registered carry forecasts."""
import argparse
from pathlib import Path
import qwen_rom_core_dec_chaseq_emit_w12 as C


def apply(text):
    old='    parameter integer DEC_LA_CHASE_Q = 0\n) ('
    new='    parameter integer DEC_LA_CHASE_Q = 0,\n    parameter integer DEC_LA_COUNT_LA = 0\n) ('
    if text.count(old)!=1:
        raise ValueError('counter parameter anchor not unique')
    text=text.replace(old,new)
    old="    ot_hdc_inc_k #(.W(32)) u_la_cycles (.a(cycles), .inc(1'b1), .y(la_cycles1), .co());"
    new='''    // Invariant: each carry bit describes all-ones in the current low
    // 8/16/24 bits. Forecast the invariant for the next busy increment.
    reg [2:0] la_cycle_carry;
    genvar cyc_byte;
    generate if (DEC_LA != 0 && DEC_LA_COUNT_LA != 0) begin : g_cycles_la
        always @(posedge clk or negedge rst_n)
            if (!rst_n) la_cycle_carry <= 3'b000;
            else if (st == S_IDLE && start) la_cycle_carry <= 3'b000;
            else if (st != S_IDLE) begin
                la_cycle_carry[0] <= (&cycles[7:1]) && !cycles[0];
                la_cycle_carry[1] <= (&cycles[15:1]) && !cycles[0];
                la_cycle_carry[2] <= (&cycles[23:1]) && !cycles[0];
            end
        for (cyc_byte=0; cyc_byte<4; cyc_byte=cyc_byte+1) begin : g_byte
            if (cyc_byte == 0) begin : g_low
                ot_hdc_inc_k #(.W(8)) u_inc (.a(cycles[7:0]), .inc(1'b1), .y(la_cycles1[7:0]), .co());
            end else begin : g_high
                ot_hdc_inc_k #(.W(8)) u_inc (.a(cycles[8*cyc_byte +: 8]),
                    .inc(la_cycle_carry[cyc_byte-1]), .y(la_cycles1[8*cyc_byte +: 8]), .co());
            end
        end
    end else begin : g_cycles_original
        ot_hdc_inc_k #(.W(32)) u_la_cycles (.a(cycles), .inc(1'b1), .y(la_cycles1), .co());
    end endgenerate'''
    if text.count(old)!=1:
        raise ValueError('counter increment anchor not unique')
    return text.replace(old,new)


def emit(text):
    return apply(C.emit(text))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(emit(C.B.E.V.E.CORE.read_text()))
