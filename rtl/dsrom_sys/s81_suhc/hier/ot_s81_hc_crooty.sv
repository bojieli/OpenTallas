`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_crooty (s81-suhc-hier-1011, 2026-10-11): the N half of a split outer column root (structural variant of
// ot_s81_hc_croot, dsfd_sp_hc CSPLIT=1): 575.992 x 200, beside the centre pin tile.  It owns the slab pins over its
// third of the face -- chain C's y slice and four VM write slots -- and the y slice FIFO.  Below it, ot_s81_hc_crootr
// (the chain root) asks for each POST beat's slice (p_req) and gets it back registered (p_y) three cycles later; the
// write slots come down from it (p_w) into pin flops.  Every crossing registered both sides.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crooty #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, C = 0, YD = 16
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [YS-1:0]        y_s,
    output reg  [3:0]           wq_v,
    output reg  [4*14-1:0]      wq_row,
    output reg  [4*16-1:0]      wq_mask,
    output reg  [4*512-1:0]     wq_d,
    input  wire                 yacc,
    input  wire                 p_req,
    input  wire [4*WSL-1:0]     p_w,
    output reg  [YS-1:0]        p_y,
    output reg                  p_flt
);
    // tile-local reset relay (2 flops at the pin): the srs port drives exactly one flop; every reset of the tile
    // is the relay output (no pin-to-register reset path, no reset-removal hold flood off an input port)
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL) % NS;
            owner = 3;
            if (sz <= NS) begin
                if (L0 > 0 && s0 >= B0 && s0 + sz <= B0 + L0) owner = 0;
                else if (L1 > 0 && s0 >= B1 && s0 + sz <= B1 + L1) owner = 1;
                else if (L2 > 0 && s0 >= B2 && s0 + sz <= B2 + L2) owner = 2;
            end
        end
    endfunction
    function automatic integer expd(input integer n, input integer c);
        expd = (owner(n) == c) && (c != 3) && (n == 1 || owner(n / 2) != c);
    endfunction
    function automatic integer exidx(input integer n, input integer c);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m, c); exidx = t; end
    endfunction
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL, c);
    endfunction
    function automatic integer imoff(input integer c);
        integer t, cc;
        begin t = 0; for (cc = 0; cc < c; cc = cc + 1) t = t + necnt(cc); imoff = t; end
    endfunction    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_PI = S_RT + 24 * S_RT, P_D = P_PI + 8, RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2;
    localparam integer YS = LC * GS * 32;
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
    // y slice FIFO in SRAM (v2, 2026-10-12: the YD x YS flop array was 45k of the tile's 57.9k flops on one clock
    // root): ot_fifo_sram_fwft over ceil(YS / 256) ot_sram_1r1w_128x256 macros with its 2-entry register head, so a
    // record pushed in cycle k is the head in k + 1 -- the timing of the flop array it replaces (yw / yr kept for
    // the occupancy fault only).
    wire [YS-1:0] yh;
    wire          yhv, yovf;
    ot_fifo_sram_fwft #(.W(YS), .DEPTH(YD), .MACRO(2)) u_yf (.clk(sk), .rst_n(rs_n), .push(ya), .wdata(yp2),
        .pop(pr), .hv(yhv), .head(yh), .ovf(yovf));
    always @(posedge sk) p_y <= yh;                               // the head, registered (valid the cycle after pr)
    // writes: capture, pin flops
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
