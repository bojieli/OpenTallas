`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection Sinkhorn of the V4.1 decode core: the SIMPLE bit-exact
// reference implementation, on one pipelined binary32 adder and one pipelined
// correctly rounded divider (ot_hdc_fdiv).
//
// Port-compatible with rtl/hdc/v41/ot_hdc_sinkhorn.sv (the latency-optimised
// unit, one normalisation per clock, built separately); the decode core
// instantiates whichever `SINKHORN_FAST` selects.
//
// FUNCTION (tools/hdc_golden_v41.py Model.hc_mixes after the exponential):
//     step 0 (rows):    comb = e / seqsum_row(e) + eps
//     step 1 (columns): comb = comb / (seqsum_col(comb) + eps)
//     then (ITERS - 1) x { rows, columns }: comb = comb / (seqsum(comb) + eps)
// every sum sequential in index order, ((a + b) + c) + d.  One step issues the
// four lines' three additions in lock-step (4 per phase), the eps additions,
// then 16 divisions one per cycle; each phase waits for its results.  About
// 80 cycles a step, 40 steps: the unit runs beside the sublayer, whose result
// is the only consumer.
// ---------------------------------------------------------------------------
module ot_hdc_sinkhorn_seq #(
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [511:0] in_e,
    output reg          out_valid,
    output wire [511:0] y,
    output reg          fault,
    output wire         busy
);
    localparam integer STEPS = 2 * ITERS;
    localparam [2:0] P_IDLE = 0, P_S1 = 1, P_S2 = 2, P_S3 = 3, P_EPS = 4, P_DIV = 5, P_E2 = 6, P_DONE = 7;
    reg [2:0]  ph;
    reg [7:0]  step;
    reg [4:0]  n_iss, n_got;
    reg [31:0] m [0:15];
    reg [31:0] s [0:3];
    reg        flt;
    assign in_ready = (ph == P_IDLE);
    assign busy = (ph != P_IDLE);
    genvar gk;
    generate
        for (gk = 0; gk < 16; gk = gk + 1) begin : g_y
            assign y[32*gk +: 32] = m[gk];
        end
    endgenerate
    wire colstep = step[0];                           // even steps: rows; odd: columns
    // element k of line r at position c: rows r*4 + c, columns c*4 + r
    function automatic [3:0] el(input col, input [1:0] r, input [1:0] c);
        el = col ? {c, r} : {r, c};
    endfunction
    wire [4:0] nphase = (ph == P_DIV || ph == P_E2) ? 5'd16 : 5'd4;
    // adder
    reg        a_v;
    reg [31:0] a_x, a_y;
    reg [3:0]  a_dst;
    reg        a_tos;                                 // result to s[] (else m[])
    wire [31:0] a_out;
    wire a_f;
    ot_hdc_fadd u_add (clk, rst_n, a_v, a_x, a_y, a_out, a_f);
    wire [3:0] a_dst5;
    wire       a_tos5;
    wire [5:0] av;
    ot_hdc_vline #(.D(5)) u_av (.clk(clk), .rst_n(rst_n), .v(a_v), .vd(av));
    ot_hdc_delay #(.W(5), .D(5)) u_ad (.clk(clk), .rst_n(rst_n), .d({a_dst, a_tos}), .q({a_dst5, a_tos5}));
    // divider
    reg        d_v;
    reg [31:0] d_x, d_y;
    reg [3:0]  d_dst;
    wire [31:0] d_out;
    wire d_vo, d_f;
    ot_hdc_fdiv u_div (.clk(clk), .rst_n(rst_n), .v(d_v), .a(d_x), .b(d_y), .y(d_out), .vo(d_vo), .fault(d_f));
    wire [3:0] d_dst31;
    ot_hdc_delay #(.W(4), .D(31)) u_dd (.clk(clk), .rst_n(rst_n), .d(d_dst), .q(d_dst31));

    wire [1:0] ir = n_iss[1:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= P_IDLE; out_valid <= 1'b0; a_v <= 1'b0; d_v <= 1'b0; fault <= 1'b0; flt <= 1'b0;
        end else begin
            out_valid <= 1'b0; a_v <= 1'b0; d_v <= 1'b0;
            if (av[5] && a_f) flt <= 1'b1;
            if (d_vo && d_f) flt <= 1'b1;
            case (ph)
                P_IDLE: if (in_valid) begin
                    ph <= P_S1; step <= 0; n_iss <= 0; n_got <= 0; flt <= 1'b0;
                end
                P_S1, P_S2, P_S3, P_EPS, P_E2: begin
                    if (n_iss != nphase) begin
                        a_v <= 1'b1; n_iss <= n_iss + 1'b1;
                        case (ph)
                            P_S1: begin a_x <= m[el(colstep, ir, 2'd0)]; a_y <= m[el(colstep, ir, 2'd1)];
                                        a_dst <= {2'd0, ir}; a_tos <= 1'b1; end
                            P_S2: begin a_x <= s[ir]; a_y <= m[el(colstep, ir, 2'd2)]; a_dst <= {2'd0, ir}; a_tos <= 1'b1; end
                            P_S3: begin a_x <= s[ir]; a_y <= m[el(colstep, ir, 2'd3)]; a_dst <= {2'd0, ir}; a_tos <= 1'b1; end
                            P_EPS: begin a_x <= s[ir]; a_y <= EPS; a_dst <= {2'd0, ir}; a_tos <= 1'b1; end
                            default: begin a_x <= m[n_iss[3:0]]; a_y <= EPS; a_dst <= n_iss[3:0]; a_tos <= 1'b0; end
                        endcase
                    end
                    if (n_got == nphase) begin
                        n_iss <= 0; n_got <= 0;
                        case (ph)
                            P_S1: ph <= P_S2;
                            P_S2: ph <= P_S3;
                            P_S3: ph <= (step == 0) ? P_DIV : P_EPS;
                            P_EPS: ph <= P_DIV;
                            default: begin ph <= P_S1; step <= step + 1'b1; end      // P_E2 (step 0 only)
                        endcase
                    end
                end
                P_DIV: begin
                    if (n_iss != 5'd16) begin
                        d_v <= 1'b1; n_iss <= n_iss + 1'b1;
                        d_x <= m[n_iss[3:0]]; d_dst <= n_iss[3:0];
                        //: the line of element k: rows k/4, columns k%4
                        d_y <= s[colstep ? n_iss[1:0] : n_iss[3:2]];
                    end
                    if (n_got == 5'd16) begin
                        n_iss <= 0; n_got <= 0;
                        if (step == 0) ph <= P_E2;
                        else if (step + 1 == STEPS) ph <= P_DONE;
                        else begin ph <= P_S1; step <= step + 1'b1; end
                    end
                end
                P_DONE: begin out_valid <= 1'b1; fault <= flt; ph <= P_IDLE; end
                default: ph <= P_IDLE;
            endcase
            if (av[5] || d_vo) n_got <= (ph == P_IDLE) ? 5'd0 : n_got + 1'b1;
        end
    end
    integer k;
    always @(posedge clk) begin
        if (ph == P_IDLE && in_valid)
            for (k = 0; k < 16; k = k + 1) m[k] <= in_e[32*k +: 32];
        if (av[5]) begin
            if (a_tos5) s[a_dst5[1:0]] <= a_out; else m[a_dst5] <= a_out;
        end
        if (d_vo) m[d_dst31] <= d_out;
    end
endmodule
