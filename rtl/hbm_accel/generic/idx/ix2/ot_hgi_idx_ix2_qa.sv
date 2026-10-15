`timescale 1ns/1ps
`default_nettype none
// ix2 QUERY tile (hbm-redesign-idx 2026-10-13).  Head weights: the <= 5 B sectors land from their lanes into a
// 5-sector buffer (relative sector r comes from lane (b0 + r) mod 8, a frame constant), then one registered shift by
// B.base mod 8 gives the 32 weights; a non-zero low half inside the 32 words -> bad.  Query: every lane pushes its A
// sectors in order into its own 2 slots here (QC = 2 lane credits; a_cr returns one).  Block j = A sectors 4j .. 4j+3
// = the four lanes (a0 + 4j + i) mod 8, which alternate between two fixed lane sets (the two lane quads when a0 is a
// multiple of 4); when the four lanes of block j all hold a sector and a selector credit is free the block is loaded
// into qb: slot head 2:1, lane-set 2:1 (block parity), static rotate by a0 mod 4.  One block a cycle sustained.
// The last block is held until kin_sent (keep_en).  The lane payload lands directly in one of the lane's two slot
// registers (write enable = the lane's a_v pin and the slot pointer); B sectors likewise in the weight buffer.
module ot_hgi_idx_ix2_qa #(
    parameter integer MUT = 0       // 1: head weight of the next head
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire          run,
    input  wire          keep_en_i,
    input  wire [17:0]   a_base_i, b_base_i,
    input  wire [2047:0] ab_d,
    input  wire [7:0]    b_v,
    input  wire [7:0]    a_v,
    output reg  [7:0]    a_cr,
    input  wire          kin_sent,
    input  wire          qbr,
    output reg  [1047:0] qb,
    output reg           qa_done,
    output reg           qa_bad
);
    integer l, r, i;
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    reg st_q, run_q, keep_en, ks_q, qbr_q; reg [2:0] a_lo; reg [5:0] b_lo;
    always @(posedge clk or negedge rn)
        if (!rn) begin st_q <= 1'b0; run_q <= 1'b0; ks_q <= 1'b0; qbr_q <= 1'b0; end
        else begin st_q <= start; run_q <= run; ks_q <= kin_sent; qbr_q <= qbr; end
    always @(posedge clk) begin keep_en <= keep_en_i; a_lo <= a_base_i[5:3]; b_lo <= b_base_i[5:0]; end
    // B (head weights, once a frame): pin flops of the 8 lane buses before the head-weight select (10-13: B went
    // through that select straight from the pins: 663 input -> register endpoints of up to 9 levels).  A is NOT
    // delayed: an A sector lands in its slot register straight from the pin (write enable = the lane's a_v and the
    // slot pointer), the slot is the pin register.  (A pin flop in front of the slots was tried: it lengthens the
    // lane's 2-credit loop by an edge, the lanes rewind, front 217 -> 305 cycles.)
    reg [2047:0] in_d; reg [7:0] bv_q;
    always @(posedge clk or negedge rn) if (!rn) bv_q <= 8'd0; else bv_q <= b_v;
    always @(posedge clk) in_d <= ab_d;
    // the block's quarter -> lane map: one kept copy of the frame constant a quarter (a_lo[0] drove 7,283 loads)
    (* keep = 1 *) reg [1:0] ppq [0:3];
    always @(posedge clk) if (st_q) for (i = 0; i < 4; i = i + 1) ppq[i] <= a_lo[1:0] + 2'(i);
    // ---------------------------------------------------------------- head weights
    reg [127:0] bh [0:4]; reg [7:0] bz [0:4]; reg [4:0] bgot; reg wts_ok; reg [15:0] wts [0:31];
    reg [2:0] bl; reg [5:0] bw; reg [7:0] nz; reg bad_w;
    wire [4:0] bneed = (b_lo[2:0] == 3'd0) ? 5'b01111 : 5'b11111;
    always @* begin
        bad_w = 1'b0;
        for (i = 0; i < 32; i = i + 1) begin bw = {3'd0, b_lo[2:0]} + 6'(i); if (bz[bw[5:3]][bw[2:0]]) bad_w = 1'b1; end
    end
    always @(posedge clk) begin
        for (r = 0; r < 5; r = r + 1) begin
            bl = b_lo[5:3] + 3'(r);
            for (i = 0; i < 8; i = i + 1) nz[i] = in_d[{29'd0, bl}*256 + i*32 +: 16] != 16'd0;
            if (bv_q[bl]) begin
                for (i = 0; i < 8; i = i + 1) bh[r][i*16 +: 16] <= in_d[{29'd0, bl}*256 + i*32 + 16 +: 16];
                bz[r] <= nz;
            end
        end
        if (bgot == bneed && !wts_ok)
            for (i = 0; i < 32; i = i + 1) begin bw = {3'd0, b_lo[2:0]} + 6'(i); wts[i] <= bh[bw[5:3]][bw[2:0]*16 +: 16]; end
    end
    // ---------------------------------------------------------------- lane slots and blocks
    reg [255:0] sl [0:15]; reg [7:0] swp, srp; reg [1:0] scnt [0:7];        // lane l slot e at 2 l + e
    reg [7:0] jn; reg [2:0] qcred; reg [7:0] m0, have; reg [3:0] q0; reg [1:0] pp; reg [2:0] ln;
    wire [7:0] msk = jn[0] ? ~m0 : m0;
    always @* for (l = 0; l < 8; l = l + 1) have[l] = scnt[l] != 2'd0;
    wire send = run_q && wts_ok && !qa_bad && jn != 8'd128 && qcred != 3'd0 && (have & msk) == msk &&
                (jn != 8'd127 || !keep_en || ks_q);
    always @(posedge clk) begin
        for (l = 0; l < 8; l = l + 1) if (a_v[l]) sl[2*l + {31'd0, swp[l]}] <= ab_d[l*256 +: 256];
        if (send) begin
            for (i = 0; i < 4; i = i + 1) begin
                pp = ppq[i]; ln = {q0[pp] ^ jn[0], pp};
                qb[8 + i*256 +: 256] <= sl[{ln, srp[ln]}];
            end
            qb[1047 -: 16] <= wts[(MUT == 1) ? jn[6:2] + 5'd1 : jn[6:2]];
            qb[7:1] <= {jn[1:0], jn[6:2]};
        end
    end
    always @(posedge clk or negedge rn)
        if (!rn) begin
            bgot <= 5'd0; wts_ok <= 1'b0; jn <= 8'd0; qcred <= 3'd4; m0 <= 8'd0; a_cr <= 8'd0; q0 <= 4'd0; swp <= 8'd0; srp <= 8'd0;
            qb[0] <= 1'b0; qa_done <= 1'b0; qa_bad <= 1'b0;
            for (l = 0; l < 8; l = l + 1) scnt[l] <= 2'd0;
        end else begin
            a_cr <= send ? msk : 8'd0;
            qb[0] <= send;
            qa_done <= jn == 8'd128;
            if (send) jn <= jn + 8'd1;
            qcred <= qcred + 3'(qbr_q) - 3'(send);
            for (l = 0; l < 8; l = l + 1) begin
                scnt[l] <= scnt[l] + 2'(a_v[l]) - 2'(send && msk[l]);
                if (a_v[l]) swp[l] <= !swp[l];
                if (send && msk[l]) srp[l] <= !srp[l];
            end
            for (r = 0; r < 5; r = r + 1) if (bv_q[3'(b_lo[5:3] + 3'(r))]) bgot[r] <= 1'b1;
            if (bgot == bneed && run_q) begin wts_ok <= 1'b1; if (bad_w) qa_bad <= 1'b1; end
            if (st_q) begin
                bgot <= 5'd0; wts_ok <= 1'b0; jn <= 8'd0; qcred <= 3'd4; a_cr <= 8'd0; swp <= 8'd0; srp <= 8'd0;
                qa_done <= 1'b0; qa_bad <= 1'b0;
                for (l = 0; l < 8; l = l + 1) begin
                    scnt[l] <= 2'd0;
                    m0[l] <= 3'(3'(l) - a_lo) < 3'd4;                      // lane l is in the set of the even blocks
                end
                for (i = 0; i < 4; i = i + 1) q0[i] <= a_lo[2] ^ (2'(i) < a_lo[1:0]);   // quad of position i, even blocks
            end
        end
endmodule
`default_nettype wire
