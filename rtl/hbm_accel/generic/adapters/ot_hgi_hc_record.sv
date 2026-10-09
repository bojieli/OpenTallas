`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 HC record adapter (hgi-adapters, 2026-10-09).  Unit 10 (HC.HC_MIX, the DS hyper-connection mix) onto the HC
// unit's job port: the HCP projection engine's command (ot_hdc_v41x_hcp cmd_*: npos, nout, nchunk, scale, nf, eps,
// wbase, xbase) + its HBM weight window (ot_hdc_v41x_hcp_hbm_window start / hbm_base / nwords) + the mix output.
// Decode + handshake only.
//   Record (hgi_sim ds_native: HC.HC_MIX A = h (VM, the HC x D residual), B = the layer's HC weight set (HBM), O = mix
//   (VM, 24 words = pre 4 | post 4 | comb 16)).  Job: npos 1, nout 24, K = effective n of A, nchunk = K / 8 (K must be a
//   multiple of 8), scale 1 (the RMS scale r, golden hc_mixes), nf = binary32(K) (exact: K < 2^24), eps = cfg_hc_eps
//   (the model constant from the descriptor's static block), xbase = A base, w_hbm = B.base >> 5 (sector),
//   nwords = 24 K / 8 (weight words of 8 FP32 a bank row), obase = O base.
// Retire = the HC unit's done (mix written to O); fault -> rec_fault + halt.  Refusals: unit != 10, op != 0, A / B / O
// absent, A or O not VM, B not HBM, K = 0 or K % 8 != 0, O.n != 24, B.base not 32-byte aligned.
// Latency: accept E0, decode E1, job_v E2.  LEGACY = 1 adds the static legacy pass-through.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_hc_record #(
    parameter integer MUT_NF = 0,         // mutant: nf = K / 8 (the chunk count) instead of K
    parameter integer LEGACY = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hgi_en,
    input  wire [31:0]   cfg_hc_eps,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_a, rec_b, rec_o,
    input  wire [20:0]   rec_n_a, rec_n_o,
    output reg           rec_done,
    output reg           rec_fault,
    output wire          halted,
    input  wire          lg_v,
    output wire          lg_rdy,
    input  wire [228:0]  lg_job,
    // HC unit job: {obase 18, nwords 24, w_hbm 35, xbase 18, wbase 16, eps 32, nf 32, scale 1, nchunk 18, nout 5, npos 1}
    // = 200 b, padded to 229 with zeros
    output wire          job_v,
    input  wire          job_rdy,
    output wire [228:0]  job,
    input  wire          job_done,
    input  wire          job_fault
);
    wire hen = LEGACY ? hgi_en : 1'b1;
    reg raw_v, busy, iss, halt_q, in_done, in_fault;
    reg [127:0] hdr_q; reg [255:0] a_q, b_q, o_q; reg [20:0] na_q, no_q; reg [31:0] eps_q;
    reg [228:0] job_q;
    always @(posedge clk) begin in_done <= job_done; in_fault <= job_fault; eps_q <= cfg_hc_eps; end
    assign halted = halt_q;
    assign rec_rdy = hen && !raw_v && !busy && !halt_q;
    assign job_v = hen ? iss : lg_v;
    assign job = hen ? job_q : lg_job;
    assign lg_rdy = !hen && job_rdy;
    wire [6:0] opq = hdr_q[99:93];
    wire bad = (hdr_q[127:124] != 4'd10) || (hdr_q[123:118] != 6'd0) || !opq[0] || !opq[1] || !opq[4] ||
               (a_q[1:0] != 2'd1) || (o_q[1:0] != 2'd1) || (b_q[1:0] != 2'd0) || (na_q == 21'd0) || (|na_q[2:0]) ||
               (|na_q[20:18]) || (no_q != 21'd24) || (|b_q[12:8]);
    // binary32 of K (exact, K < 2^24): exponent 127 + msb, mantissa = K << (23 - msb)
    reg [4:0] msb; integer i;
    always @* begin msb = 5'd0; for (i = 0; i < 21; i = i + 1) if (na_q[i]) msb = i[4:0]; end
    wire [20:0] kf = MUT_NF ? {3'd0, na_q[20:3]} : na_q;
    reg [4:0] msbf;
    always @* begin msbf = 5'd0; for (i = 0; i < 21; i = i + 1) if (kf[i]) msbf = i[4:0]; end
    wire [43:0] mant = {23'd0, kf} << (5'd23 - msbf);
    wire [31:0] nf = {1'b0, 8'd127 + {3'd0, msbf}, mant[22:0]};
    wire [17:0] nchunk = na_q[20:3];
    wire [23:0] nwords = {nchunk, 4'd0} + {nchunk, 3'd0};            // 24 x K / 8
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin raw_v <= 1'b0; busy <= 1'b0; iss <= 1'b0; halt_q <= 1'b0; rec_done <= 1'b0; rec_fault <= 1'b0;
                          hdr_q <= 0; a_q <= 0; b_q <= 0; o_q <= 0; na_q <= 0; no_q <= 0; job_q <= 0; end
        else begin
            rec_done <= 1'b0; rec_fault <= 1'b0;
            if (rec_v && rec_rdy) begin raw_v <= 1'b1; hdr_q <= rec_hdr; a_q <= rec_a; b_q <= rec_b; o_q <= rec_o;
                                        na_q <= rec_n_a; no_q <= rec_n_o; end
            if (raw_v) begin
                raw_v <= 1'b0;
                if (bad) begin rec_fault <= 1'b1; halt_q <= 1'b1; end
                else begin
                    busy <= 1'b1; iss <= 1'b1;
                    job_q <= {29'd0, o_q[25:8], nwords, b_q[47:13] /* w_hbm: B.base >> 5 */, a_q[25:8], 16'd0, eps_q, nf,
                              1'b1, nchunk, 5'd24, 1'b1};
                end
            end
            if (iss && job_rdy && hen) iss <= 1'b0;
            if (busy && !iss) begin
                if (in_fault) begin rec_fault <= 1'b1; halt_q <= 1'b1; busy <= 1'b0; end
                else if (in_done) begin rec_done <= 1'b1; busy <= 1'b0; end
            end
        end
    end
endmodule
`default_nettype wire
