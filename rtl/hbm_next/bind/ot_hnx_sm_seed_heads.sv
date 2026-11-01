`timescale 1ns/1ps
`default_nettype none
// Exact boundary forms: seed absent from interface; original chain identity is internal.
module ot_hbm_sm_attn_tile_seed #(
    parameter integer SUB = 4,
    parameter integer RPT = 2,
    parameter integer LBS = 2,
    parameter integer LSB = 16,
    parameter integer NC  = 8,
    parameter integer IL  = 8,
    parameter integer TAGW = 16,
    parameter integer XD  = 128,
    parameter integer NBEAT = 13,
    parameter integer TCK = 1,
    parameter integer NMG = 32,             // mask bits per one-hot replica
    parameter integer A1B = 9,              // strap bits of the block-dot field offset (its low 11 - A1B bits are 0)
    parameter integer A2B = 7,              // strap bits of the BF16 field offset
    parameter integer PT4 = 1               // hbm-blocks 2026-10-07 (m3h): a FOURTH pass-through register on the x-write beat
                                            //   and on every row bundle (m3f tile_w: u_bldm -> u_bld2 -44.13 / u_bld -> u_bldm
                                            //   -42.11 / u_rpm -> u_rp2 -27.24, 4-5 levels of wire): +1 per tile hop on both
) (
    input  wire                     clk,
    input wire rst_n,
    input wire [2:0] attn_column,input wire [1:0] attn_rowbase,
    input  wire [RPT*A1B-1:0]       xs_a1,
    input  wire [RPT*5-1:0]         xs_g1,
    input  wire [RPT*A2B-1:0]       xs_a2,
    input  wire [RPT*5-1:0]         xs_g2,
    input  wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rin,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bin,
    output wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rout,
    output wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bout,
    output wire [SUB*(2+32+TAGW)-1:0]                          gout
);
    ot_hbm_sm_attn_tile #(
        .SUB(SUB),
        .RPT(RPT),
        .LBS(LBS),
        .LSB(LSB),
        .NC(NC),
        .IL(IL),
        .TAGW(TAGW),
        .XD(XD),
        .NBEAT(NBEAT),
        .TCK(TCK),
        .NMG(NMG),
        .A1B(A1B),
        .A2B(A2B),
        .PT4(PT4)
    ) u_seed (
        .clk(clk),
        .rst_n(rst_n),
        .attn_column(attn_column),
        .attn_rowbase(attn_rowbase),
        .xs_a1(xs_a1),
        .xs_g1(xs_g1),
        .xs_a2(xs_a2),
        .xs_g2(xs_g2),
        .rin(rin),
        .bin(bin),
        .rout(rout),
        .bout(bout),
        .gin('0),
        .gout(gout)
    );
endmodule
module ot_hbm_sm_attn_be_seed #(
    parameter integer CONTROL_DELAY=8,
    parameter integer SUB  = 4,
    parameter integer RPT  = 2,
    parameter integer IL   = 8,
    parameter integer RMAX = 4096,
    parameter integer LEV  = 4,
    parameter integer TAGW = 16,
    parameter integer NH   = 4,
    parameter integer STK  = 1              // 1: ot_hbm_accel_stack (pending lookup registered, +1 cycle); 0: ot_gpu_stack
) (
    input  wire                              clk,
    input wire rst_n,
    input wire [2:0] attn_column,
    input wire [28:0] command,
    input  wire [SUB*(2+32+TAGW)-1:0]        gin,
    output wire [NH*(2+32+$clog2(RMAX))-1:0]     qout
);
    ot_hbm_sm_attn_be #(
        .CONTROL_DELAY(CONTROL_DELAY),
        .SUB(SUB),
        .RPT(RPT),
        .IL(IL),
        .RMAX(RMAX),
        .LEV(LEV),
        .TAGW(TAGW),
        .NH(NH),
        .STK(STK)
    ) u_seed (
        .clk(clk),
        .rst_n(rst_n),
        .attn_column(attn_column),
        .command(command),
        .gin(gin),
        .qin('0),
        .qout(qout)
    );
endmodule
`default_nettype wire
