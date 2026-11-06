`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_dout (S81-KP4 2026-10-17): output hard tile of the S81 KP4 decoder cluster ot_s81_kp4_dec: the
// correction-mask SRAM delay (32 x 546, written every cycle with cw, read DC = 9 cycles later), the corrected word
// d_q ^ (apply ? mask : 0) straight from the two read ports (d_q = ot_s81_kp4_ddly's macro read port through the seam),
// and the fixed-offset beat select {word k-1, word k}[523 + 32k -: 512] into q_d.  fs (from ot_s81_kp4_dchn) starts
// the beat phase; apply / o_unc / o_ne / fs and cw cross the same seam, so DC does not depend on the seam latency.
// Regional synchronous reset, no datapath reset.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_dout (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [543:0]  d_q,
    input  wire [543:0]  cw,
    input  wire [7:0]    apply,
    input  wire          o_unc,
    input  wire [4:0]    o_ne,
    input  wire          fs,
    output reg           q_v,
    output reg  [511:0]  q_d,
    output reg           q_first,
    output reg           q_unc,
    output reg  [4:0]    q_nerr,
    output reg  [7:0]    q_seq
);
    localparam integer NRO = 16;         // beat select copies (32 bits each)
    localparam integer DC = 9;           // corr SRAM delay
    wire [0:0] rs_n;
    ot_s81_kp4_rst #(.NL(1)) u_rst (.clk(clk), .rst_n(rst_n), .rs_n(rs_n));
    integer i;
    genvar gk, gb;
    // ================= correction-mask SRAM delay (write and read every cycle; fixed distance DC)
    reg  [4:0] ptr;                      // free-running cycle pointer
    always @(posedge clk) if (!rs_n[0]) ptr <= 5'd0; else ptr <= ptr + 5'd1;
    wire [4:0] rd_c = ptr - DC[4:0];
    wire [545:0] c_rd;
    ot_sram_1r1w_32x546_m1 u_cmem (.clk(clk), .r_ce_in(1'b1), .r_addr_in(rd_c), .rd_out(c_rd),
        .w_ce_in(1'b1), .w_addr_in(ptr), .wd_in({2'b00, cw}), .w_mask_in({546{1'b1}}));
    (* keep *) reg [9:0] os [0:NRO-1];   // one-hot beat index: os[*][k] at T' + 57 + k
    always @(posedge clk)
        if (!rs_n[0]) for (i = 0; i < NRO; i = i + 1) os[i] <= 10'd0;
        else for (i = 0; i < NRO; i = i + 1) os[i] <= {os[i][8:0], fs};
    reg  [543:0] cwo, cwp;
    generate for (gb = 0; gb < 544; gb = gb + 1) begin : g_cor
        always @(posedge clk) cwo[gb] <= d_q[gb] ^ (apply[gb / 68] & c_rd[gb]);
    end endgenerate
    always @(posedge clk) cwp <= cwo;
    wire [1087:0] w2 = {cwp, cwo};
    wire [511:0]  bsrc [0:9];
    generate for (gk = 0; gk < 10; gk = gk + 1) begin : g_bsrc
        assign bsrc[gk] = w2[523 + 32 * gk -: 512];
    end endgenerate
    generate for (gb = 0; gb < 512; gb = gb + 1) begin : g_bm_o
        wire [9:0] s;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_s
            assign s[gk] = bsrc[gk][gb];
        end
        always @(posedge clk) q_d[gb] <= |(s & os[gb / 32]);
    end endgenerate
    always @(posedge clk)
        if (!rs_n[0]) begin q_v <= 1'b0; q_first <= 1'b0; q_unc <= 1'b0; q_nerr <= 0; q_seq <= 0; end
        else begin
            q_v <= |os[0];
            q_first <= os[0][0];
            if (os[0][0]) begin q_unc <= o_unc; q_nerr <= o_ne; q_seq <= cwo[531:524]; end
        end
endmodule
