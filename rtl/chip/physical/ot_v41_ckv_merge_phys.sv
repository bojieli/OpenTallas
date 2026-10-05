`timescale 1ns/1ps
// Physical characterisation wrapper of ot_chip_v41x_ckv_stream_merge (not a
// functional block).  The merger's wide ports (4 x 4,224-bit window rows,
// 4 x 2,304-bit CKV rows, the 4 x 16 x 265-bit engine beat) sit inside the
// attention neighbourhood on the die and never cross a block boundary; here
// they are registered on both sides so the timed paths are the merger's own
// register-to-register logic:
//   * the wide inputs are loaded from a 256-bit port by a shift chain
//     (win and ckv row registers, loaded one 256-bit word per cycle);
//   * the kv beat is captured in a register and folded by a two-stage
//     registered XOR tree to one 265-bit word.
// Control inputs are registered; valid/ready handshakes cross unchanged.
module ot_v41_ckv_merge_phys (
    input  wire clk,
    input  wire rst_n,
    input  wire ld_w, ld_c,
    input  wire [255:0] ld_data,
    input  wire job_v,
    output wire job_ready,
    input  wire [7:0] window_count,
    input  wire [9:0] n_sel,
    input  wire w_v,
    output wire w_ready,
    input  wire [3:0] w_m,
    input  wire [2:0] c_n,
    output wire [2:0] c_take,
    input  wire [9:0] c_rank,
    input  wire kv_ready,
    output reg  kv_v_q,
    output reg  [3:0] kv_m_q,
    output reg  [264:0] kv_fold,
    output wire done, fault
);
    localparam integer WB = 4 * 4224, CB = 4 * 2304, KB = 4 * 16 * 265;
    reg [WB-1:0] w_rows;
    reg [CB-1:0] c_rows;
    always @(posedge clk) begin
        if (ld_w) w_rows <= {ld_data, w_rows[WB-1:256]};
        if (ld_c) c_rows <= {ld_data, c_rows[CB-1:256]};
    end
    reg job_v_q, w_v_q, kv_ready_q;
    reg [7:0] wc_q; reg [9:0] ns_q, cr_q; reg [3:0] wm_q; reg [2:0] cn_q;
    always @(posedge clk) begin
        job_v_q <= job_v; w_v_q <= w_v; kv_ready_q <= kv_ready;
        wc_q <= window_count; ns_q <= n_sel; cr_q <= c_rank; wm_q <= w_m; cn_q <= c_n;
    end
    wire kv_v; wire [3:0] kv_m; wire [KB-1:0] kv_w; wire [1:0] fc;
    ot_chip_v41x_ckv_stream_merge u_m (
        .clk(clk), .rst_n(rst_n), .job_v(job_v_q), .job_ready(job_ready),
        .window_count(wc_q), .n_sel(ns_q),
        .w_v(w_v_q), .w_ready(w_ready), .w_m(wm_q), .w_rows(w_rows),
        .c_n(cn_q), .c_take(c_take), .c_rank(cr_q), .c_rows(c_rows),
        .kv_v(kv_v), .kv_ready(kv_ready_q), .kv_m(kv_m), .kv_w(kv_w),
        .done(done), .fault(fault), .fault_code(fc));
    reg [KB-1:0] kv_q;
    reg [8*265-1:0] f1;
    integer g, h;
    always @(posedge clk) begin
        kv_v_q <= kv_v; kv_m_q <= kv_m; kv_q <= kv_w;
        for (g = 0; g < 8; g = g + 1) begin
            f1[g*265 +: 265] = 265'd0;
            for (h = 0; h < 8; h = h + 1) f1[g*265 +: 265] = f1[g*265 +: 265] ^ kv_q[(g*8 + h)*265 +: 265];
        end
    end
    reg [8*265-1:0] f1_q;
    always @(posedge clk) begin
        f1_q <= f1;
        kv_fold = 265'd0;
        for (g = 0; g < 8; g = g + 1) kv_fold = kv_fold ^ f1_q[g*265 +: 265];
    end
endmodule
