`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81 SU q RMSNorm -> FP8, split into small hardened masters (el1011-s81su-qn, 2026-10-12; PHYSICAL SPEC QN v3).
// Replaces the two QN lane tiles of ot_s81_su_tile (TK 0: 450,764 flops on one root each) by
//   TAP    ot_s81_su_qnt_reference x 2   (data halves: half h carries bits [256 h, 256 h + 256) of every spine row; the control is
//                               identical in both): pin flops, row numbering, a registered rotation of the operand rows
//                               into positions (operand row index mod RPB), each with its vector index; job fields.
//   NORM   ot_s81_su_qne x NE  (NE = N / 8; 8 lanes = one golden chunk each, position-independent, hardened once):
//                               x and the 4 gain sets in one SRAM bank, ONE multiplier a lane (time-shared: the squares
//                               while the operands stream in, then x * r / w * p in blocks of LM vectors), the chunk's
//                               sequential sum -> a registered partial; y = bf16(w * (x * r)) registered out.
//   REDUCE ot_s81_su_qnr x 1   : the NE chunk sums -> the golden's pairwise tree (aligned: engine n = chunk n), the
//                               vector levels, ss / D, + eps, rsqrt -> rstd, broadcast over equal-depth relays.
//   QUANT  ot_s81_su_qnq x NQ  (NQ = N / 32): the QB v3 engine pattern (ot_dsrom_actquant_f12, XSRAM wait line, one
//                               32-element block from 4 norm engines), pair exchange, one write slot each: an even
//                               engine the codes row {q_b+1, q_b}, an odd engine the masked exps word {e_b, e_b-1}.
// Values: every step is the golden's (ot_dsrom_su_norm / ot_s81_su_norm_lg): lane-local multiplies, the chunk chain
// (8 lanes summed sequentially), the chunk tree pairwise in order, the vector levels, the same divc / eps / rsqrt; only
// latency changes.  VM rows as before: vector v of the job writes rows obase + v (N / 64 + 1) + [0, N / 64) (codes) and
// + N / 64 (exps, one masked word a block pair).  No pass assembly anywhere: every engine takes its own position when
// it arrives; the reduce matches the NE partials of a vector by the vector's parity (2 entries an engine), and the scale
// phase starts at the rstd, which reaches every engine in the same cycle, so the y of a block leave in one cycle.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_qnt_reference #(
    parameter integer N = 256, S_RD = 16, NFI = 33, MUT = 0
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire                   dn_st_i,
    input  wire [3:0]             dn_kind_i,
    input  wire [1:0]             dn_gsel_i,
    input  wire [7:0]             dn_jid_i,
    input  wire [S_RD-1:0]        dn_v_i,
    input  wire [S_RD*256-1:0]    dn_d_i,         // this half of every slot
    input  wire [NFI-1:0]         i_f,            // the norm engines' / reduce's sticky faults (relayed)
    output reg  [N/16-1:0]        e_v,            // position j: operand row j of a vector (this half)
    output reg  [N/16*256-1:0]    e_d,
    output reg  [N/16*8-1:0]      e_t,            // its vector index
    output reg                    e_gq,           // the job is a gain load (K_GQ)
    output reg  [1:0]             e_gr, e_gw,     // gain set read (QN) / written (GQ)
    output reg                    e_go,           // a QN job's parameter row is in (a pulse)
    output reg  [13:0]            e_ob,           // the QN job's obase (half 0)
    output reg  [31:0]            e_eps,          // the QN job's eps (half 0)
    output reg                    o_fu, o_fo, o_alive, o_den, o_rdy,
    output reg  [7:0]             o_rjid
);
    localparam integer L = N / 16, LL = $clog2(L);
    localparam [3:0] K_QN = 0, K_GQ = 6;
`ifndef SYNTHESIS
    initial if ((1 << LL) != L || L < 2 || S_RD > L) $fatal(1, "ot_s81_su_qnt_reference: N / 16 a power of two >= max(2, S_RD)");
`endif
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg dq_st; reg [3:0] dq_kind; reg [1:0] dq_gsel; reg [7:0] dq_jid; reg [S_RD-1:0] dq_v; reg [S_RD*256-1:0] dq_d;
    reg [NFI-1:0] fq;
    always @(posedge clk) begin dq_kind <= dn_kind_i; dq_gsel <= dn_gsel_i; dq_jid <= dn_jid_i; dq_d <= dn_d_i; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin dq_st <= 1'b0; dq_v <= 0; fq <= 0; end
                                           else begin dq_st <= dn_st_i; dq_v <= dn_v_i; fq <= i_f; end
    // job context and row numbering (the first row of a QN / GQ job is its parameter row, the rest operand rows).
    // rcnt (rows before this cycle's group) = st_r ? 0 : ra + pc_r, from REGISTERED terms only: pc_r = the previous
    // group's slot count (popcount of the dq_v pin flops, its own stage), st_r its start, ra = the previous rcnt.
    // Induction: rcnt(t+1) = st(t) ? 0 : rcnt(t) + pc(t), the former recurrence; reset 0 = the former reset.  So the
    // popcount is never in series with the add (was dq_v -> rc_j 725 ps / 19 lv) and no input pin feeds logic.
    localparam integer PCW = $clog2(S_RD + 1);
    reg mine, gq; reg [1:0] gsel; reg [7:0] jid; reg [15:0] ra; reg [PCW-1:0] pc_r; reg st_r;
    reg [PCW-1:0] pc;
    always @(*) begin : pcnt
        integer i;
        pc = 0;
        for (i = 0; i < S_RD; i = i + 1) pc = pc + dq_v[i];
    end
    wire [15:0] rcnt = st_r ? 16'd0 : ra + pc_r;
    // the rotation offset off = (rcnt - 1) mod L, REGISTERED, one copy a position (265-bit 2:1 mux a level each) in a
    // kept module (SYNTH_KEEP_MODULES): synthesis cannot merge the copies into one 12k-load net (opt_merge folded the
    // former plain rc_j copies).  Next off = (st ? 0 : rcnt + pc) - 1 on LL bits only (popcount mod L + a 4-bit add);
    // the mux selects stay register outputs (an add in front of them cost the e_d outputs 340 ps after placement).
    localparam integer KW = LL;
    wire [LL-1:0] off_n = (dq_st ? {LL{1'b0}} : rcnt[LL-1:0] + pc[LL-1:0]) - 1'b1;
    wire [KW*L-1:0] kq;
    genvar gj;
    generate for (gj = 0; gj < L; gj = gj + 1) begin : g_off
        ot_s81_su_qn_keep_ff_reference #(.W(KW)) u_k (.clk(clk), .rst_n(rst_n), .d(off_n),
                                            .q(kq[KW * gj +: KW]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin mine <= 1'b0; gq <= 1'b0; gsel <= 2'd0; jid <= 8'd0; ra <= 16'd0; pc_r <= 0; st_r <= 1'b0; end
        else begin
            if (dq_st) begin mine <= (dq_kind == K_QN || dq_kind == K_GQ); gq <= (dq_kind == K_GQ); gsel <= dq_gsel;
                             jid <= dq_jid; end
            ra <= rcnt; pc_r <= pc; st_r <= dq_st;
        end
    end
    wire prm = mine && dq_v[0] && rcnt == 16'd0;
    // per slot: operand-row valid, vector index; rotate left by off = (rcnt - 1) mod L into positions
    localparam integer RB = 256 + 8 + 1;
    reg [L*RB-1:0] rv [0:LL];
    always @(*) begin : rot
        integer s, k;
        reg [15:0] ix;
        rv[0] = 0;
        for (s = 0; s < S_RD; s = s + 1) begin
            ix = rcnt + s - 16'd1;
            rv[0][RB * s +: RB] = {mine && dq_v[s] && (rcnt != 16'd0 || s != 0), ix[LL +: 8], dq_d[256 * s +: 256]};
        end
        for (k = 0; k < LL; k = k + 1)
            for (s = 0; s < L; s = s + 1) begin : pos
                reg [LL-1:0] off;
                off = kq[KW * s +: KW];
                rv[k + 1][RB * s +: RB] = off[k] ? rv[k][RB * ((s - (1 << k) + L) % L) +: RB] : rv[k][RB * s +: RB];
            end
    end
    always @(posedge clk) begin : oreg
        integer j;
        for (j = 0; j < L; j = j + 1) begin
            e_d[256 * j +: 256] <= rv[LL][RB * j +: 256];
            e_t[8 * j +: 8] <= rv[LL][RB * j + 256 +: 8];
        end
        if (prm && !gq) begin e_ob <= dq_d[13:0]; e_eps <= dq_d[96 +: 32]; end
        e_gq <= gq; e_gr <= (MUT == 4) ? 2'd0 : gsel; e_gw <= gsel;
    end
    always @(posedge clk or negedge rst_n) begin : vreg
        integer j;
        if (!rst_n) begin e_v <= 0; e_go <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rdy <= 0; o_rjid <= 0; end
        else begin
            for (j = 0; j < L; j = j + 1) e_v[j] <= rv[LL][RB * j + 264];
            e_go <= prm && !gq; o_rdy <= prm && !gq; o_rjid <= jid;
            o_fu <= o_fu | (|fq); o_fo <= 1'b0; o_alive <= 1'b1; o_den <= 1'b1;
        end
    end
endmodule

// a register that synthesis must keep (SYNTH_KEEP_MODULES + keep): per-position copies of a broadcast control value.
// Reset value all ones = the off of rcnt 0 (bit-identical to the former rc_j <= 0 copies).
module ot_s81_su_qn_keep_ff_reference #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d,
                                                           output wire [W-1:0] q);
    (* keep = "true" *) reg [W-1:0] q_k;
    always @(posedge clk or negedge rst_n) if (!rst_n) q_k <= {W{1'b1}}; else q_k <= d;
    assign q = q_k;
endmodule

