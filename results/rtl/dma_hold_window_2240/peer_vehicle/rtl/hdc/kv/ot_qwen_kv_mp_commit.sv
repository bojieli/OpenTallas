`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B ROM DSpark on the 4-stack KV path: the hardened MULTI-POSITION COMMIT / ROLLBACK /
// VISIBILITY element of ot_qwen_rt_kv_stream4_mp_service (that module is the behavioural model of the
// whole service; this is its synthesizable token-side control, expression for expression):
//   * step state: block start P, block size np (1 .. VPMAX), committed_len / committed_v;
//   * per token lane (SW = 64 a cycle): E4M3 encode of the FP32 value and the visibility check --
//     K lane (tile t, lane l) and V row p must lie in the block P .. P+np-1 (else bad: fault 3),
//     the K tile select (P/16 or P/16+1) and the V block row j = p - P;
//   * the open-tile fill mask tail_lm (lanes < P mod 16 come from HBM, the rest from the block);
//   * commit: commit_n in 1 .. np (fault 12), every token K/V acknowledged (ack debt = 0, fault 13),
//     committed_len = P + commit_n; the next start must be at committed_len (fault 14): the rejected
//     rows P + commit_n .. P + np - 1 are rolled back by construction (the next fill reads rows
//     < committed_len and masks open-tile lanes >= committed_len mod 16);
//   * start: np > VPMAX (fault 12), P + np > 8192 (fault 1, the stream map's window).
// Lane path: the lane inputs and the step state they are checked against (P, P + np) are registered
// at the element boundary (stage 1), the decode is registered in stage 2: lane outputs are two edges
// after the lane, checked against the state of the cycle the lane was presented (the service's
// semantics, one cycle later).  Faults are sticky.
// ---------------------------------------------------------------------------
module ot_qwen_kv_mp_commit #(
    parameter integer SW = 64, AW = 24, NW = 18, VPMAX = 4
) (
    input  wire              clk, rst_n,
    input  wire              start,          // layer start (block step)
    input  wire [NW-1:0]     pos,
    input  wire [3:0]        npos,
    input  wire [SW-1:0]     kv_we,
    input  wire [SW*AW-1:0]  kv_waddr,
    input  wire [SW*32-1:0]  kv_wdata,
    input  wire              commit_v,
    input  wire [3:0]        commit_n,
    input  wire              ack_debt,       // token K/V written and not yet acknowledged by HBM (or in flight)
    output reg  [SW-1:0]     lane_v, lane_bad, lane_isk, lane_sel,
    output reg  [SW*2-1:0]   lane_j,
    output reg  [SW*8-1:0]   lane_code,
    output reg  [127:0]      tail_lm,
    output reg  [NW-1:0]     P, committed_len,
    output reg  [3:0]        NPr,
    output reg               committed_v,
    output reg  [15:0]       fault_code
);
    localparam integer KVB = 131072;
    function automatic [8:0] f32_e4m3(input [31:0] b);   // {bad, code}: the service's encoder
        reg [7:0] e; reg [22:0] m;
        begin
            e = b[30:23]; m = b[22:0];
            if (e == 0 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd0};
            else if (e >= 8'd121 && e <= 8'd135 && m[19:0] == 0) f32_e4m3 = {1'b0, b[31], e[3:0] - 4'd8, m[22:20]};
            else if (e == 8'd120 && m[20:0] == 0) f32_e4m3 = {1'b0, b[31], 4'd0, 1'b1, m[22:21]};
            else if (e == 8'd119 && m[21:0] == 0) f32_e4m3 = {1'b0, b[31], 5'd0, 1'b1, m[22]};
            else if (e == 8'd118 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd1};
            else f32_e4m3 = {1'b1, 8'd0};
        end
    endfunction
    // stage 1: lanes and the step state of their cycle
    reg [SW-1:0] we1; reg [SW*AW-1:0] wa1; reg [SW*32-1:0] wd1; reg [12:0] P1; reg [13:0] PE1;
    always @(posedge clk) begin
        wa1 <= kv_waddr; wd1 <= kv_wdata; P1 <= P[12:0]; PE1 <= 14'(P + {{(NW-4){1'b0}}, NPr});
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) we1 <= 0; else we1 <= kv_we;
    wire [8:0] T = P1[12:4];
    integer li;
    always @(posedge clk) begin
        for (li = 0; li < SW; li = li + 1) begin
            reg [AW-1:0] e; reg [AW-5:0] a; reg [8:0] fc; reg [16:0] w; reg [12:0] pp; reg [8:0] t;
            e = wa1[li*AW +: AW]; a = e[AW-1:4];
            fc = f32_e4m3(wd1[li*32 +: 32]);
            lane_code[li*8 +: 8] <= fc[7:0];
            lane_isk[li] <= a < KVB;
            if (a < KVB) begin
                t = a[15:7];
                lane_bad[li] <= we1[li] && (fc[8] || a[19:17] != 0 || {t, e[3:0]} < P1 || {1'b0, t, e[3:0]} >= PE1);
                lane_sel[li] <= (VPMAX > 1) && (t != T);
                lane_j[li*2 +: 2] <= 2'd0;
            end else begin
                w = a - KVB; pp = w[15:3];
                lane_bad[li] <= we1[li] && (fc[8] || a >= KVB + 131072 || pp < P1 || {1'b0, pp} >= PE1);
                lane_sel[li] <= 1'b0;
                lane_j[li*2 +: 2] <= (VPMAX > 1) ? 2'(pp - P1) : 2'd0;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lane_v <= 0; P <= 0; NPr <= 4'd1; committed_len <= 0; committed_v <= 1'b0; fault_code <= 0; tail_lm <= 0;
        end else begin
            lane_v <= we1;
            if (start) begin
                P <= pos; NPr <= (npos == 0) ? 4'd1 : npos;
                tail_lm <= (128'd1 << (8 * pos[3:0])) - 128'd1;
                if (npos > VPMAX) fault_code[12] <= 1'b1;
                if ({1'b0, pos} + ((npos == 0) ? 1 : npos) > 8192) fault_code[1] <= 1'b1;
                if (committed_v) begin
                    committed_v <= 1'b0;
                    if (pos != committed_len) fault_code[14] <= 1'b1;
                end
            end
            if (commit_v) begin
                if (commit_n == 0 || commit_n > NPr) fault_code[12] <= 1'b1;
                if (ack_debt) fault_code[13] <= 1'b1;
                committed_len <= P + {{(NW-4){1'b0}}, commit_n};
                committed_v <= 1'b1;
            end
        end
    end
endmodule
