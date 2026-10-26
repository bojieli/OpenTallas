`timescale 1ns/1ps
`default_nettype none
module ot_hbm_sm_attn_tile_g #(
    parameter integer SUB = 4, parameter integer RPT = 2, parameter integer LBS = 2, parameter integer LSB = 16,
    parameter integer NC = 8, parameter integer IL = 8, parameter integer TAGW = 16, parameter integer XD = 128,
    parameter integer NBEAT = 13, parameter integer TCK = 1, parameter integer NMG = 32, parameter integer A1B = 9,
    parameter integer A2B = 7, parameter integer PT4 = 1, parameter integer HOLD = `ifdef OT_SMH_CG_MUT_HOLD0 0 `else 64 `endif,
    parameter integer MUT_LATE = `ifdef OT_SMH_CG_MUT_LATE 32 `else 0 `endif,
    // [cg-smt] 2026-10-10 OT_SMH_CG_ENREG: the tile ICG's ENA from one register beside the gate (ot_cg_tile ENREG, 0 cycles).
    // Root cause (tile_wg cg a6d34a72e smtc cal): ENA from cnt / wq at leaf insertion 670 ps -> ICG CK at 217 ps over
    // 160 ps of wire (507 ps slew): TT setup -198 / -352 ps.
    parameter integer ENREG = `ifdef OT_SMH_CG_ENREG 1 `else 0 `endif
) (
    input wire clk,rst_n,cgi,output wire cgo,
    input wire [2:0] attn_column,input wire [1:0] attn_rowbase,
    input  wire [RPT*A1B-1:0] xs_a1, input wire [RPT*5-1:0] xs_g1, input wire [RPT*A2B-1:0] xs_a2, input wire [RPT*5-1:0] xs_g2,
    input  wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rin,
    input  wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bin,
    output wire [RPT*(6+TAGW+LBS*266+LSB*16+1+$clog2(XD))-1:0] rout,
    output wire [1+$clog2(XD)+NBEAT+2048-1:0]                  bout,
    input  wire [(SUB-RPT)*(2+32+TAGW)-1:0]                    gin,
    output wire [SUB*(2+32+TAGW)-1:0]                          gout
);
    wire gclk;
    // el1013-smh-r14 OT_SMH_PINREG: receiver-owned hold on the wake pin.  cgi lands in the two raw-clock registers beside
    // the clk pin (wq, en_r; clock arrival ~4 ps) through one input buffer: FF hold -37.5 ps against the class-0 boundary
    // reference (input min = the raw registers' own arrival), and the spine keeps those port-net cells fixed and
    // dont_touch, so hold repair stalled (r11 / r13 OT_HOLD_STALL I2R = 2).  Two kept HB4xp67 (ot_hdly, ~38 ps each at
    // FF) in front of both registers; identity in simulation.  TT setup: the wake has the full receiver share.
    wire cgi_h;
    ot_hdly #(.W(1), .N(
`ifdef OT_SMH_PINREG
        2
`else
        0
`endif
        )) u_hdly_cgi (.a(cgi), .y(cgi_h));
    // el1013-smh-r11 OT_SMH_RSTPIN: no reset on the raw clock (RSTEN 0, RAWRST 0); the wake holds the gate open in reset
    // (cg_en is high in reset: ot_hgi_sm_leaf resets it to 1 and each tile forwards it one raw register a hop), and the
    // reset itself enters the gated tile through its pin flop (ot_hbm_accel_smh_rst_tree).
    // RESET CONTRACT of the gated tile: rst_n low for >= 32 clk edges with cgi high (hops + pin flop + tree + child relays);
    // the tile's state leaves reset 9 edges after the port (tree 5/6 + child relay 3), inside the HOLD = 64 open window.
    ot_cg_tile #(.HOLD(HOLD), .MUT_LATE(MUT_LATE), .ENREG(ENREG)
`ifdef OT_SMH_RSTPIN
                 , .RSTEN(0), .RAWRST(0)
`endif
                 ) u_cgt (.clk(clk), .rst_n(rst_n), .cgi(cgi_h), .cgo(cgo), .gclk(gclk));
    // Static slice positions settle while reset holds the tile gate open.
    // Five regional stations avoid a raw north-face wire crossing the cluster.
    localparam integer STRAPW = A1B + 5 + A2B + 5;
    wire [RPT*A1B-1:0] sx_a1;
    wire [RPT*5-1:0] sx_g1, sx_g2;
    wire [RPT*A2B-1:0] sx_a2;
    genvar sr;
    generate for (sr = 0; sr < RPT; sr = sr + 1) begin : g_strap
        wire [STRAPW-1:0] d = {xs_g2[sr*5 +: 5], xs_a2[sr*A2B +: A2B],
                                  xs_g1[sr*5 +: 5], xs_a1[sr*A1B +: A1B]};
        wire [STRAPW-1:0] q;
        ot_hbm_accel_smh_strap_region #(.W(STRAPW),
            .MUT(`ifdef OT_SMH_MUT_STRAP_REGION (sr == 1) `else 0 `endif)) u_sr (.clk(gclk), .d(d), .q(q));
        assign {sx_g2[sr*5 +: 5], sx_a2[sr*A2B +: A2B],
                sx_g1[sr*5 +: 5], sx_a1[sr*A1B +: A1B]} = q;
    end endgenerate
    ot_hbm_sm_attn_tile #(.SUB(SUB), .RPT(RPT), .LBS(LBS), .LSB(LSB), .NC(NC), .IL(IL), .TAGW(TAGW), .XD(XD),
                            .NBEAT(NBEAT), .TCK(TCK), .NMG(NMG), .A1B(A1B), .A2B(A2B), .PT4(PT4)) u (
        .clk(gclk), .rst_n(rst_n), .attn_column(attn_column), .attn_rowbase(attn_rowbase), .xs_a1(sx_a1), .xs_g1(sx_g1), .xs_a2(sx_a2), .xs_g2(sx_g2), .rin(rin), .bin(bin),
        .rout(rout), .bout(bout), .gin(gin), .gout(gout));
endmodule
module ot_hbm_sm_attn_be_g #(
    parameter integer CONTROL_DELAY=8,
    parameter integer SUB = 4, parameter integer RPT = 2, parameter integer IL = 8, parameter integer RMAX = 4096,
    parameter integer LEV = 4, parameter integer TAGW = 16, parameter integer NH = 4, parameter integer HOLD = `ifdef OT_SMH_CG_MUT_HOLD0 0 `else 64 `endif,
    parameter integer MUT_LATE = `ifdef OT_SMH_CG_MUT_LATE 32 `else 0 `endif
) (
    input wire clk,rst_n,cgi,output wire cgo,
    input wire [2:0] attn_column,input wire [28:0] command,
    input  wire [SUB*(2+32+TAGW)-1:0]          gin,
    input  wire [(NH-1)*(2+32+$clog2(RMAX))-1:0] qin,
    output wire [NH*(2+32+$clog2(RMAX))-1:0]     qout
);
    wire gclk;
    ot_cg_tile #(.HOLD(HOLD), .MUT_LATE(MUT_LATE)) u_cgt (.clk(clk), .rst_n(rst_n), .cgi(cgi), .cgo(cgo), .gclk(gclk));
    ot_hbm_sm_attn_be #(.CONTROL_DELAY(CONTROL_DELAY),.SUB(SUB), .RPT(RPT), .IL(IL), .RMAX(RMAX), .LEV(LEV), .TAGW(TAGW), .NH(NH)) u (
        .clk(gclk), .rst_n(rst_n), .attn_column(attn_column), .command(command), .gin(gin), .qin(qin), .qout(qout));
endmodule
`default_nettype wire
