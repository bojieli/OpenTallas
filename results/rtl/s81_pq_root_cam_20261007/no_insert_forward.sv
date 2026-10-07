// Candidate staged native sibling CAM. Model: committed fullshape design.json
// ret_root_r128. New module is opt-in by instantiation; original is unchanged.
// D/QD remain full128. No timing or mutable-state protection claim is made.
module ot_s81_pq_ret_root_cam #(
    parameter integer D = 128,
    parameter integer QD = 128
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    output reg         r_v,
    output reg  [15:0] r_row,
    output reg  [2:0]  r_pos,
    output reg  [31:0] r_fp32,
    output reg  [15:0] r_bf16,
    output reg         r_e,
    output reg         fault
);
    import ot_v41_ret_pkg::*;
    localparam integer QW = $clog2(QD);
    // input queue
    reg [31:0] qt [0:QD-1];
    reg [31:0] qd [0:QD-1];
    reg        qe [0:QD-1];
    reg [QW-1:0] qr, qw;
    reg [QW:0] qc;
    // buffer
    reg        bv [0:D-1];
    reg [31:0] bt [0:D-1];
    reg [31:0] bd [0:D-1];
    reg        be [0:D-1];
    // adder
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    reg add;
    reg [31:0] add_a, add_b;
    wire [32:0] st;
    // Stage A uses a registered queue head. Adder results retain priority.
    reg [31:0] head_t, head_d;
    reg head_e;
    wire use_q = !sv && qc != 0;
    wire [31:0] at = sv ? st[32:1] : norm(head_t);
    wire [31:0] ad = sv ? sum : head_d;
    wire ae = sv ? (st[0] | err != 2'd0) : head_e;
    wire av = sv || qc != 0;
    reg cv;
    reg [31:0] ct, cd;
    reg ce;
    reg [D-1:0] match_vec, frees;
    integer k, hit, fr;
    always @* begin
        hit = -1; fr = -1;
        for (integer n = D-1; n >= 0; n = n-1) begin
            if (match_vec[n]) hit = n;
            if (frees[n]) fr = n;
        end
    end
    wire remove_b = cv && !complete(ct) && hit >= 0;
    wire insert_b = cv && !complete(ct) && hit < 0 && fr >= 0;
    // A observes the buffer state AFTER B's same-edge update. This forwards
    // both insertion tags and newly freed entries without changing pairing.
    reg [D-1:0] next_match_vec, next_frees;
    reg effective_valid;
    reg [31:0] effective_tag;
    always @* begin
        next_match_vec = 0; next_frees = 0;
        effective_valid = 0; effective_tag = 0;
        for (integer n = 0; n < D; n = n+1) begin
            effective_valid = bv[n]; effective_tag = bt[n];
            if (remove_b && hit == n) effective_valid = 0;
            if (1'b0 && insert_b && fr == n) begin
                effective_valid = 1; effective_tag = ct;
            end
            next_match_vec[n] = effective_valid && sibling(effective_tag, at);
            next_frees[n] = !effective_valid;
        end
    end
    wire [31:0] pt = (hit >= 0) ? parent(bt[hit], ct) : 32'd0;
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(add_a), .b(add_b),
                                .y(sum), .err(err), .valid_out(sv));
    reg [32:0] tag_in;
    ot_hdc_delay #(.W(33), .D(5)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_in), .q(st));
    wire [32:0] rb = {1'b0, cd} + 33'h7FFF + {32'd0, cd[16]};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qw <= 0; qc <= 0; cv <= 0; match_vec <= 0; frees <= 0; r_v <= 1'b0; fault <= 1'b0; add <= 1'b0;
            for (k = 0; k < D; k = k + 1) bv[k] <= 1'b0;
        end else begin
            r_v <= 1'b0;
            add <= 1'b0;
            cv <= av;
            match_vec <= next_match_vec; frees <= next_frees;
            if (i_v) qw <= qw + 1'b1;
            if (use_q) qr <= qr + 1'b1;
            qc <= qc + (i_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (i_v && qc == QD && !use_q) fault <= 1'b1;
            if (cv) begin
                if (complete(ct)) begin
                    r_v <= 1'b1;
                end else if (hit >= 0) begin
                    add <= 1'b1;
                    bv[hit] <= 1'b0;
                end else if (fr >= 0) begin
                    bv[fr] <= 1'b1;
                end else fault <= 1'b1;
            end
        end
    end
    wire [QW-1:0] next_qr = qr + 1'b1;
    always @(posedge clk) begin
        ct <= at; cd <= ad; ce <= ae;
        // Empty/singleton push bypass avoids reading an old RAM value when
        // the producer writes the new queue head on this same edge.
        if (use_q) begin
            if (qc == 1 && i_v) begin head_t <= i_t; head_d <= i_d; head_e <= i_e; end
            else if (qc > 1) begin head_t <= qt[next_qr]; head_d <= qd[next_qr]; head_e <= qe[next_qr]; end
        end else if (qc == 0 && i_v) begin head_t <= i_t; head_d <= i_d; head_e <= i_e; end
        if (i_v) begin qt[qw] <= i_t; qd[qw] <= i_d; qe[qw] <= i_e; end
        r_row <= ct[28:13]; r_pos <= ct[31:29]; r_fp32 <= cd; r_bf16 <= rb[31:16]; r_e <= ce;
        if (cv && !complete(ct) && hit >= 0) begin
            // left operand: lower lo
            if (bt[hit][12:8] < ct[12:8]) begin add_a <= bd[hit]; add_b <= cd; end
            else begin add_a <= cd; add_b <= bd[hit]; end
        end
        tag_in <= {pt, (hit >= 0) ? (be[hit] | ce) : 1'b0};
        if (cv && !complete(ct) && hit < 0 && fr >= 0) begin bt[fr] <= ct; bd[fr] <= cd; be[fr] <= ce; end
    end
endmodule
