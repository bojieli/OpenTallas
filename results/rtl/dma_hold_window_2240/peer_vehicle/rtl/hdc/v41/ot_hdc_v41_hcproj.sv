`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection projection engine (HE) of the DeepSeek-V4.1 decode core.
//
// The mixes of a hyper-connection are an FP32-weight matrix-vector product
// (tools/hdc_golden_v41.py Model.hc_mixes: matvec(fn, flat, HC_SPLIT), fn
// [24, 640] binary32): K in S = HC_SPLIT contiguous chunks, each sequential
// from +0, the chunk sums a pairwise tree ((c0+c1)+(c2+c3))+...  Every other
// matrix of the model is BF16 or block-quantised, so the shared BF16 matrix
// engine keeps its exact BF16 multipliers and these projections get this small
// engine of their own, which runs BESIDE the matrix engine: a sublayer's
// attention or MoE work proceeds while its mixes accumulate.
//
// S x NL lanes x IL interleaved outputs, the matrix engine's lane structure:
// each lane is the qualified binary32 multiplier (ot_hdc_fmul) feeding the
// qualified adder (ot_hdc_fadd), whose sum circulates back exactly IL cycles
// later, so every chunk sum accumulates its products strictly in order while
// the lane retires one multiply-accumulate per cycle.  Element order: k (0 ..
// i_k-1, the chunk length), then slot j; lane (c, l) of slot j is row j*NL + l,
// chunk c; its weight is lane c*NL + l of word wbase + k*IL + j; its x is the
// vector-memory element xbase + c*i_k + k (one read port per chunk).  After
// the last k, slot j's chunk sums pass a pipelined tree of log2(S) adder
// levels and its NL results are written as one masked word at obase + j*NL.
// Latency: i_k * IL cycles, plus 5 per tree level, for up to NL*IL outputs.
//
// LANE MULTIPLIER (MP, multi-token prediction): MP copies of the lanes and the
// tree; copy p serves position slot p of an op with i_m > p (x at + p*i_xps,
// results at + p*i_ops, its own x ports and write port), all copies taking the
// same weight word.  MP = 1 is the one-position engine, port for port.
// ---------------------------------------------------------------------------
module ot_hdc_v41_hcproj #(
    parameter integer NL = 3,
    parameter integer IL = 8,
    parameter integer S  = 8,           // K chunks (a power of two)
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer MP = 1            // lane multiplier: positions per weight read
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_k,               // chunk length
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_obase,
    input  wire [2:0]        i_m,               // positions served (0 = 1)
    input  wire [AW-1:0]     i_xps,             // x element stride per position
    input  wire [AW-1:0]     i_ops,             // result element stride per position
    output reg               hr_re,
    output reg  [AW-1:0]     hr_addr,
    input  wire [S*NL*32-1:0] hr_q,
    output reg  [MP*S-1:0]   x_re,
    output reg  [MP*S*AW-1:0] x_addr,
    input  wire [MP*S*32-1:0] x_q,
    output reg  [MP-1:0]     o_we,
    output reg  [MP*AW-1:0]  o_addr,
    output reg  [MP*32-1:0]  o_mask,
    output reg  [MP*1024-1:0] o_data,
    output reg               fault
);
    localparam integer PW = $clog2(IL);
    localparam integer LV = $clog2(S);
    localparam integer LW = S * NL * 32;          // one tree level
    reg              active;
    reg [NW-1:0]     k, k_r, nout;
    reg [PW-1:0]     j;
    reg [AW-1:0]     cur, xk, obase, xps, ops;
    reg [2:0]        m_r;
    assign ready = !active;
    integer cpi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; hr_re <= 1'b0; x_re <= 0;
        end else begin
            hr_re <= active;
            for (cpi = 0; cpi < MP; cpi = cpi + 1) x_re[cpi*S +: S] <= {S{active && cpi < m_r}};
            if (!active) begin
                if (go) begin
                    active <= 1'b1; k <= 0; j <= 0; k_r <= i_k; nout <= i_nout;
                    cur <= i_wbase; xk <= i_xbase; obase <= i_obase;
                    m_r <= (i_m == 3'd0) ? 3'd1 : i_m; xps <= i_xps; ops <= i_ops;
                end
            end else begin
                cur <= cur + 1'b1;
                j <= j + 1'b1;
                if (j == IL - 1) begin
                    j <= 0; xk <= xk + 1'b1; k <= k + 1'b1;
                    if (k + 1 == k_r) active <= 1'b0;
                end
            end
        end
    end
    // issue tags (registered with the addresses)
    reg          e_v, e_first, e_last;
    reg [PW-1:0] e_j;
    integer c;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0; else e_v <= active;
    end
    always @(posedge clk) begin
        hr_addr <= cur;
        for (cpi = 0; cpi < MP; cpi = cpi + 1)
            for (c = 0; c < S; c = c + 1) x_addr[(cpi*S + c)*AW +: AW] <= xk + c * k_r + cpi * xps;
        e_first <= (k == 0); e_last <= (k + 1 == k_r); e_j <= j;
    end
    // s1: memories answer; s2: operands captured
    reg          s1_v, s2_v, s1_first, s2_first, s1_last, s2_last;
    reg [PW-1:0] s1_j, s2_j;
    reg [S*NL*32-1:0] s2_w;
    reg [MP*S*32-1:0] s2_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s2_v <= 1'b0; end
        else begin s1_v <= e_v; s2_v <= s1_v; end
    end
    always @(posedge clk) begin
        s1_first <= e_first; s1_last <= e_last; s1_j <= e_j;
        s2_first <= s1_first; s2_last <= s1_last; s2_j <= s1_j;
        s2_w <= hr_q; s2_x <= x_q;
    end
    // tags across the multiplier (5) and the adder (5)
    wire [5:0] vm;
    ot_hdc_vline #(.D(5)) u_vm (.clk(clk), .rst_n(rst_n), .v(s2_v), .vd(vm));
    wire m_first, m_last;
    wire [PW-1:0] m_j;
    ot_hdc_delay #(.W(2 + PW), .D(5)) u_tm (.clk(clk), .rst_n(rst_n), .d({s2_first, s2_last, s2_j}),
                                           .q({m_first, m_last, m_j}));
    wire [5:0] va;
    ot_hdc_vline #(.D(5)) u_va (.clk(clk), .rst_n(rst_n), .v(vm[5]), .vd(va));
    wire a_last;
    wire [PW-1:0] a_j;
    ot_hdc_delay #(.W(1 + PW), .D(5)) u_ta (.clk(clk), .rst_n(rst_n), .d({m_last, m_j}), .q({a_last, a_j}));
    // the tree: 5 cycles per level; the slot tag rides beside it
    wire [5*LV:0] tv;
    ot_hdc_vline #(.D(5*LV)) u_tv (.clk(clk), .rst_n(rst_n), .v(va[5] && a_last), .vd(tv));
    wire [PW-1:0] t_j;
    ot_hdc_delay #(.W(PW), .D(5*LV)) u_tj (.clk(clk), .rst_n(rst_n), .d(a_j), .q(t_j));
    wire [MP-1:0] cp_fault;
    genvar cp;
    generate for (cp = 0; cp < MP; cp = cp + 1) begin : g_cp
    // tree levels: level L holds S >> L chunk sums per lane l (index c*NL + l)
    wire [(LV+1)*LW-1:0] lvl;
    wire [S*NL-1:0] lf;
    genvar l, g, L;
        for (g = 0; g < S; g = g + 1) begin : g_chunk
            for (l = 0; l < NL; l = l + 1) begin : g_lane
                wire [31:0] prod, fb, sum;
                wire f0, f1;
                ot_hdc_fmul u_mul (clk, rst_n, s2_v, s2_w[32*(g*NL + l) +: 32], s2_x[32*(cp*S + g) +: 32], prod, f0);
                //: the sum of slot j re-enters exactly IL cycles after it left the adder's input
                ot_hdc_fadd u_add (clk, rst_n, vm[5], m_first ? 32'd0 : fb, prod, sum, f1);
                ot_hdc_delay #(.W(32), .D(IL - 5)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum), .q(fb));
                assign lvl[32*(g*NL + l) +: 32] = sum;
                assign lf[g*NL + l] = f0 | f1;
            end
        end
    wire [(LV+1)*S*NL-1:0] tf;
    assign tf[S*NL-1:0] = {(S*NL){1'b0}};
        for (L = 1; L <= LV; L = L + 1) begin : g_lvl
            for (g = 0; g < (S >> L); g = g + 1) begin : g_pair
                for (l = 0; l < NL; l = l + 1) begin : g_lane
                    ot_hdc_fadd u_t (clk, rst_n, tv[5*(L-1)],
                                     lvl[(L-1)*LW + 32*((2*g)*NL + l) +: 32],
                                     lvl[(L-1)*LW + 32*((2*g+1)*NL + l) +: 32],
                                     lvl[L*LW + 32*(g*NL + l) +: 32], tf[L*S*NL + g*NL + l]);
                end
            end
            //: the unused upper part of a level
            assign lvl[L*LW + (S >> L)*NL*32 +: (S - (S >> L))*NL*32] = {((S - (S >> L))*NL*32){1'b0}};
            assign tf[L*S*NL + (S >> L)*NL +: (S - (S >> L))*NL] = {((S - (S >> L))*NL){1'b0}};
        end
    wire [NL*32-1:0] res = lvl[LV*LW +: NL*32];
    integer q;
    wire [1023:0] res_pad = {{(1024 - NL*32){1'b0}}, res};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we[cp] <= 1'b0; else o_we[cp] <= tv[5*LV] && cp < m_r;
    end
    always @(posedge clk) begin
        o_addr[cp*AW +: AW] <= obase + t_j * NL + cp * ops;
        for (q = 0; q < 32; q = q + 1) begin
            o_mask[cp*32 + q] <= (q < NL) && ({{(32-PW){1'b0}}, t_j} * NL + q < nout);
            o_data[cp*1024 + 32*q +: 32] <= res_pad[32*q +: 32];
        end
    end
    assign cp_fault[cp] = (|lf) || (|tf);
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; end
        else begin
            idle <= !active && !go && !e_v && !s1_v && !s2_v && !(|vm) && !(|va) && !(|tv) && !(|o_we);
            fault <= |cp_fault;
        end
    end
endmodule
