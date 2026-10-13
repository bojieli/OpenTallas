`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_crooty (s81-suhc-hier-1011, 2026-10-11): the N half of a split outer column root (structural variant of
// ot_s81_hc_croot, dsfd_sp_hc CSPLIT=1): 575.992 x 200, beside the centre pin tile.  It owns the slab pins over its
// third of the face -- chain C's y slice and four VM write slots -- and the y slice FIFO.  Below it, ot_s81_hc_crootr
// (the chain root) asks for each POST beat's slice (p_req) and gets it back registered (p_y) three cycles later; the
// write slots come down from it (p_w) into pin flops.  Every crossing registered both sides.
// v3 (2026-10-12, [hc-crooty]): split into two hard tiles, each with its own clock root and reset relay -- v2's one
// root over ~18.4k flops + 11 SRAM macros (575.992 x 300.24) never converged hold.  ot_s81_hc_crooty_y (far side, above
// crootr's forward column): y_s -> yp -> yp2 -> SRAM FIFO -> p_y, p_req, yacc, p_flt (~14.1k flops + 11 macros);
// ot_s81_hc_crooty_w (comb side, above crootr's T_wr): p_w -> w_c -> wq_* (~4.3k flops).  The two paths share nothing
// but sk/srs, so the cut is cycle-neutral; this wrapper is wires only and keeps the v2 port list.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crooty #(
    parameter integer FIFO_SLICE = 256,
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, C = 0, YD = 16
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [YS-1:0]        y_s,
    output wire [3:0]           wq_v,
    output wire [4*14-1:0]      wq_row,
    output wire [4*16-1:0]      wq_mask,
    output wire [4*512-1:0]     wq_d,
    input  wire                 yacc,
    input  wire                 p_req,
    input  wire [4*WSL-1:0]     p_w,
    output wire [YS-1:0]        p_y,
    output wire                 p_flt
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2;
    localparam integer YS = LC * GS * 32;
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    ot_s81_hc_crooty_y #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .C(C), .YD(YD), .FIFO_SLICE(FIFO_SLICE)) u_y (.sk(sk), .srs(srs),
        .y_s(y_s), .yacc(yacc), .p_req(p_req), .p_y(p_y), .p_flt(p_flt));
    ot_s81_hc_crooty_w #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .C(C), .YD(YD)) u_w (.sk(sk), .srs(srs),
        .p_w(p_w), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_crooty_y: the y slice path (hard tile, far side).  N: y_s; S: p_req in, p_y / p_flt out; inner face: yacc.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crooty_y #(
    parameter integer FIFO_SLICE = 0,
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, C = 0, YD = 16
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [YS-1:0]        y_s,
    input  wire                 yacc,
    input  wire                 p_req,
    output reg  [YS-1:0]        p_y,
    output reg                  p_flt
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2;
    localparam integer YS = LC * GS * 32;
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    // tile-local reset relay (2 flops at the pin): the srs port drives exactly one flop; every reset of the tile
    // is the relay output (no pin-to-register reset path, no reset-removal hold flood off an input port)
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    localparam integer YB = $clog2(YD);
    reg  [YS-1:0] yp, yp2;
    reg           ya, pr;
    reg  [YB:0]   yn;
    reg  [YB-1:0] yw, yr;
    always @(posedge sk) begin yp <= y_s; yp2 <= yp; end
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin ya <= 1'b0; pr <= 1'b0; yn <= 0; yw <= 0; yr <= 0; p_flt <= 1'b0; end
        else begin
            ya <= yacc; pr <= p_req;
            if (ya) yw <= yw + 1'b1;
            if (pr) yr <= yr + 1'b1;
            yn <= yn + ya - pr;
            if ((ya && !pr && yn == YD) || (pr && yn == 0)) p_flt <= 1'b1;
        end
    // y slice FIFO in SRAM: ot_fifo_sram_fwft over ceil(YS / 256) ot_sram_1r1w_128x256 macros with its 2-entry register
    // head, so a record pushed in cycle k is the head in k + 1 (yw / yr kept for the occupancy fault only).  ESL 256: the
    // head in one slice per macro, each with its own head/occupancy copy (v2/v3a: one select net drove 5.6k loads).
    wire [YS-1:0] yh;
    wire          yhv, yovf;
    generate if(FIFO_SLICE>0) begin:g_slice
        localparam integer NF=(YS+FIFO_SLICE-1)/FIFO_SLICE;
        wire [NF-1:0] hv,ov;
        for(genvar f=0;f<NF;f=f+1) begin:g_f
            localparam integer LO=f*FIFO_SLICE,FW=(YS-LO<FIFO_SLICE)?YS-LO:FIFO_SLICE;
            ot_fifo_sram_fwft #(.W(FW),.DEPTH(YD),.MACRO(2),.ESL(256)) u_yf (
                .clk(sk),.rst_n(rs_n),.push(ya),.wdata(yp2[LO+:FW]),.pop(pr),
                .hv(hv[f]),.head(yh[LO+:FW]),.ovf(ov[f]));
        end
        assign yhv=&hv;assign yovf=|ov;
    end else begin:g_legacy
        ot_fifo_sram_fwft #(.W(YS), .DEPTH(YD), .MACRO(2), .ESL(256)) u_yf (.clk(sk), .rst_n(rs_n), .push(ya), .wdata(yp2),
            .pop(pr), .hv(yhv), .head(yh), .ovf(yovf));
    end endgenerate
    always @(posedge sk) p_y <= yh;                               // the head, registered (valid the cycle after pr)
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_crooty_w: the VM write slots (hard tile, comb side).  S: p_w in; N: wq_* out.  Capture + pin flops.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crooty_w #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, C = 0, YD = 16
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [4*WSL-1:0]     p_w,
    output reg  [3:0]           wq_v,
    output reg  [4*14-1:0]      wq_row,
    output reg  [4*16-1:0]      wq_mask,
    output reg  [4*512-1:0]     wq_d
);
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    // tile-local reset relay (2 flops at the pin): the srs port drives exactly one flop; every reset of the tile
    // is the relay output (no pin-to-register reset path, no reset-removal hold flood off an input port)
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg [4*WSL-1:0] w_c;
    always @(posedge sk) w_c <= p_w;
    integer s;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin wq_v <= 0; end
        else for (s = 0; s < 4; s = s + 1) wq_v[s] <= w_c[WSL * s];
    always @(posedge sk)
        for (s = 0; s < 4; s = s + 1) begin
            wq_row[14 * s +: 14] <= w_c[WSL * s + 1 +: 14];
            wq_mask[16 * s +: 16] <= w_c[WSL * s + 15 +: 16];
            wq_d[512 * s +: 512] <= w_c[WSL * s + 31 +: 512];
        end
endmodule


// Standalone v3 W leaf; top assembly adoption remains separately gated.
module ot_s81_hc_crooty_w #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, C = 0, YD = 16
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [4*WSL-1:0]     p_w,
    output reg  [3:0]           wq_v,
    output reg  [4*14-1:0]      wq_row,
    output reg  [4*16-1:0]      wq_mask,
    output reg  [4*512-1:0]     wq_d
);
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    // tile-local reset relay (2 flops at the pin): the srs port drives exactly one flop; every reset of the tile
    // is the relay output (no pin-to-register reset path, no reset-removal hold flood off an input port)
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg [4*WSL-1:0] w_c;
    always @(posedge sk) w_c <= p_w;
    integer s;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin wq_v <= 0; end
        else for (s = 0; s < 4; s = s + 1) wq_v[s] <= w_c[WSL * s];
    always @(posedge sk)
        for (s = 0; s < 4; s = s + 1) begin
            wq_row[14 * s +: 14] <= w_c[WSL * s + 1 +: 14];
            wq_mask[16 * s +: 16] <= w_c[WSL * s + 15 +: 16];
            wq_d[512 * s +: 512] <= w_c[WSL * s + 31 +: 512];
        end
endmodule
