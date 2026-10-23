`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_dsdv_afifo_n32 (S81-SHLK12 s10e, 2026-10-20): native-32 form of ot_link_afifo for dsdv_sh_lk's completion FIFO
// (u_cx: W 64, AW 4, wclk = rclk = ck).  Same ports, same Gray pointers / credits / overflow law, same values on the
// same edges at every port.  Differences are structural only:
//   * WRITE-BEHIND: wdata is staged every edge and the entry is written ONE wclk edge after the push through
//     registered per-16-bit-slice entry enables (the push / wbin decode no longer steers W x 2^AW flops).  The read side
//     first sees the entry through the 2-stage Gray synchroniser, at least two rclk edges after the push, so with
//     rclk == wclk (the only use) the entry is always written before it can be read (simulation guard below).
//   * the read word comes through NRC kept one-hot read-pointer copies (D = one-hot of the NEXT read address);
//   * rempty_c: NE kept copies of rempty as registers (D = the next empty), for the consumer's replicated pop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_dsdv_afifo_n32 #(
    parameter integer W    = 64,
    parameter integer AW   = 4,
    parameter integer SYNC = 2,
    parameter integer NE   = 2
) (
    input  wire          wclk,
    input  wire          wrst_n,
    input  wire          wr,
    input  wire [W-1:0]  wdata,
    output wire          wfull,
    output reg  [AW:0]   wfreed,
    output reg           ovf,
    input  wire          rclk,
    input  wire          rrst_n,
    input  wire          rd,
    output wire          rempty,
    output wire [NE-1:0] rempty_c,
    output wire [W-1:0]  rdata,
    output wire [AW:0]   rcount
);
    localparam integer D = 1 << AW;
`ifndef SYNTHESIS
    initial if (W % 32 != 0) $fatal(1, "ot_dsdv_afifo_n32: W must be a multiple of 32");
`endif
    localparam integer WS = (W + 15) / 16;               // write slices
    localparam integer NRC = (W + 31) / 32;              // read copies (32 bits each)
    reg [W-1:0] mem [0:D-1];
    function automatic [AW:0] g2b(input [AW:0] g);
        integer k;
        begin
            g2b[AW] = g[AW];
            for (k = AW - 1; k >= 0; k = k - 1) g2b[k] = g2b[k+1] ^ g[k];
        end
    endfunction
    reg  [AW:0] wbin, wgray, rbin_seen;
    reg  [AW:0] rgray_s [0:SYNC-1];
    wire [AW:0] rgray_w = rgray_s[SYNC-1];
    wire [AW:0] wbin_n = wbin + 1'b1;
    wire [AW:0] wgray_n = wbin_n ^ (wbin_n >> 1);
    assign wfull = (wgray == {~rgray_w[AW:AW-1], rgray_w[AW-2:0]});
    wire        push = wr && !wfull;
    wire [AW:0] rbin_w = g2b(rgray_w);
    integer i, j;
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wbin <= 0; wgray <= 0; ovf <= 1'b0; rbin_seen <= 0; wfreed <= 0;
            for (i = 0; i < SYNC; i = i + 1) rgray_s[i] <= 0;
        end else begin
            rgray_s[0] <= rgray;
            for (i = 1; i < SYNC; i = i + 1) rgray_s[i] <= rgray_s[i-1];
            wfreed <= rbin_w - rbin_seen;
            rbin_seen <= rbin_w;
            if (wr && wfull) ovf <= 1'b1;
            if (push) begin wbin <= wbin_n; wgray <= wgray_n; end
        end
    end
    // write-behind
    reg [W-1:0] wd_q;
    (* keep *) reg [D*WS-1:0] we_c;                      // [e*WS + s]
    always @(posedge wclk) wd_q <= wdata;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) we_c <= '0;
        else for (i = 0; i < D; i = i + 1) for (j = 0; j < WS; j = j + 1) we_c[i*WS + j] <= push && (wbin[AW-1:0] == i);
    always @(posedge wclk)
        for (i = 0; i < D; i = i + 1) for (j = 0; j < WS; j = j + 1)
            if (we_c[i*WS + j]) mem[i][16*j +: 16] <= wd_q[16*j +: 16];
    // read side
    reg  [AW:0] rbin, rgray;
    reg  [AW:0] wgray_s [0:SYNC-1];
    wire [AW:0] wgray_r = wgray_s[SYNC-1];
    assign rempty = (rgray == wgray_r);
    wire        pop = rd && !rempty;
    wire [AW:0] rbin_nx = rbin + (pop ? 1'b1 : 1'b0);
    wire [AW:0] rgray_nx = rbin_nx ^ (rbin_nx >> 1);
    (* keep *) reg [NRC*D-1:0] roh_c;
    (* keep *) reg [NE-1:0]    remp_c;
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rbin <= 0; rgray <= 0; roh_c <= {NRC{{(D-1){1'b0}}, 1'b1}}; remp_c <= {NE{1'b1}};
            for (i = 0; i < SYNC; i = i + 1) wgray_s[i] <= 0;
        end else begin
            wgray_s[0] <= wgray;
            for (i = 1; i < SYNC; i = i + 1) wgray_s[i] <= wgray_s[i-1];
            rbin <= rbin_nx; rgray <= rgray_nx;
            roh_c <= {NRC{{{(D-1){1'b0}}, 1'b1} << rbin_nx[AW-1:0]}};
            remp_c <= {NE{rgray_nx == wgray_s[SYNC-2]}};
        end
    end
    assign rempty_c = remp_c;
    for (genvar g = 0; g < NRC; g = g + 1) begin : g_rd
        localparam integer LO = 32 * g, NB = 32;
        wire [D-1:0] oh = roh_c[g*D +: D];
        reg  [NB-1:0] v;
        integer k;
        always @* begin v = {NB{1'b0}}; for (k = 0; k < D; k = k + 1) v = v | ({NB{oh[k]}} & mem[k][LO +: NB]); end
        assign rdata[LO +: NB] = v;
    end
    assign rcount = g2b(wgray_r) - rbin;
`ifndef SYNTHESIS
    // the entry a read can see must already be written (true for rclk == wclk: >= 2 rclk edges after the push)
    reg [D-1:0] pend;
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) pend <= '0;
        else pend <= ({D{1'b0}} | (push ? ({{(D-1){1'b0}}, 1'b1} << wbin[AW-1:0]) : {D{1'b0}}));
    always @(posedge rclk) if (rrst_n && !rempty && pend[rbin[AW-1:0]]) $fatal(1, "ot_dsdv_afifo_n32: read of an entry not yet written");
    always @(posedge rclk) if (rrst_n && (remp_c != {NE{rempty}})) $fatal(1, "ot_dsdv_afifo_n32: empty copy diverged");
`endif
endmodule
