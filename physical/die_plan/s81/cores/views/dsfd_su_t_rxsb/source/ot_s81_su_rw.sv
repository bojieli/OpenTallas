`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_su_rw (s81-functional-token r3 2026-10-14, die item F11): SU job kind RW (11) = L*.ffn.weights, the routing
// weights of the k chosen experts (tools/hdc_golden_v41.Model.moe, every rounding the golden's):
//     tot = seqsum(scores[ids[0]], .., scores[ids[k-1]])   (sequential binary32 adds, RNE, canonical +0)
//     den = tot + 1e-20                                     (binary32 add)
//     w_j = (scores[ids[j]] / den) * route_scale            (correctly rounded divide, then multiply)
// written INTO the routed SwiGLU job's descriptor row (a word-masked write of its words off .. off+k-1, the SW job's
// per-vector routing weights), so the SW job that follows reads the weights this job computed.
// Operand rows, one a cycle in this order (i_v / i_x): row 0 = the ids row (word j = expert id j, ascending; the
// compiler places the selector's ids row directly before the router all-gather's score rows), rows 1.. = the unbiased
// score rows (16 binary32 a row; score i at row 1 + i/16, word i%16); i_last marks the last score row.
// One adder (ot_dsrom_qadd), one divider (ot_dsrom_su_fdiv_f12, the SO tile's), one multiplier (ot_hdc_qmul_lat):
// latency ~ k (LA + 1) + LA + 34 + k + LM.  Result: o_v one cycle, o_d the weights at words off .. off+k-1, o_m their
// word mask.
// fault: an id outside the score rows seen, a unit fault (sticky until reset).
// MUT 4 (negative control): the route_scale multiply is skipped (w_j = scores / den).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_rw #(
    parameter integer LM = 5, LA = 4, MUT = 0, KMAX = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,           // one cycle: a new job (the configuration is sampled with the first operand row)
    input  wire [3:0]    k_i,             // experts (1 .. KMAX)
    input  wire [31:0]   scale_i,         // route_scale (binary32)
    input  wire [3:0]    off_i,           // first target word
    input  wire          i_v,
    input  wire [511:0]  i_x,
    input  wire          i_last,
    output reg           o_v,
    output reg  [511:0]  o_d,
    output reg  [15:0]   o_m,
    output reg           fault
);
    localparam integer LMR = LM + 1, LAR = (LA >= 5) ? LA : LA + 1;
    localparam [31:0] EPS20 = 32'h1E3CE508;            // binary32(1e-20)
    reg  [3:0]   k, off;
    reg  [31:0]  scale;
    reg  [15:0]  cnt;                                  // operand rows seen
    reg  [8:0]   id [0:KMAX-1];
    reg  [31:0]  sc [0:KMAX-1];
    reg  [KMAX-1:0] got;
    reg  [2:0]   st;                                   // 0 idle, 1 rows, 2 sum, 3 den, 4 div/mul, 5 out
    reg  [3:0]   j, nw;
    reg  [31:0]  acc;
    reg  [31:0]  w [0:KMAX-1];
    integer i, ww;

    // ---------------------------------------------------------------- units
    reg          a_v; reg [31:0] a_a, a_b; wire [31:0] a_y; wire a_f;
    ot_dsrom_qadd #(.LAT(LAR)) u_add (clk, rst_n, a_v, a_a, a_b, a_y, a_f);
    wire [LAR:0] a_vl;
    ot_hdc_vline #(.D(LAR)) u_av (.clk(clk), .rst_n(rst_n), .v(a_v), .vd(a_vl));
    reg          d_v; reg [31:0] d_a; reg [31:0] den; wire [31:0] d_y; wire d_vo, d_f;
    ot_dsrom_su_fdiv_f12 #(.NR(0)) u_div (.clk(clk), .rst_n(rst_n), .v(d_v), .a(d_a), .b(den), .y(d_y), .vo(d_vo), .fault(d_f));
    wire         m_v = d_vo;
    wire [31:0]  m_y; wire m_f;
    ot_hdc_qmul_lat #(LMR) u_mul (clk, rst_n, m_v, d_y, scale, m_y, m_f);
    wire [LMR:0] m_vl;
    ot_hdc_vline #(.D(LMR)) u_mv (.clk(clk), .rst_n(rst_n), .v(m_v), .vd(m_vl));
    reg  [31:0]  q_hold [0:KMAX-1];                    // MUT 4: the quotients themselves
    reg  [3:0]   nqh;

    reg          pend;                                 // the dependent add in flight
    wire [KMAX-1:0] need = (KMAX'(1) << k) - KMAX'(1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= 0; cnt <= 0; got <= 0; fault <= 0; o_v <= 0; a_v <= 0; d_v <= 0; j <= 0; nw <= 0; nqh <= 0; pend <= 0;
        end else begin
            o_v <= 0; a_v <= 0; d_v <= 0;
            if (a_f || d_f || m_f) fault <= 1;
            if (start) begin
                st <= 1; cnt <= 0; got <= 0; nw <= 0; nqh <= 0; pend <= 0;
            end else case (st)
                1: if (i_v) begin                               // operand rows
                       cnt <= cnt + 1;
                       if (cnt == 0) begin
                           for (i = 0; i < KMAX; i = i + 1) id[i] <= i_x[32 * i +: 9];
                           k <= k_i; off <= off_i; scale <= scale_i;
                           if (k_i == 0 || k_i > KMAX || {1'b0, off_i} + {1'b0, k_i} > 5'd16) fault <= 1;
                       end
                       else for (i = 0; i < KMAX; i = i + 1)
                           if (i < k && {7'd0, id[i][8:4]} == cnt - 16'd1) begin sc[i] <= i_x[32 * id[i][3:0] +: 32]; got[i] <= 1'b1; end
                       if (i_last && cnt >= 1) begin st <= 2; j <= 1; end
                   end
                2: begin                                        // tot: acc = sc[0], then acc + sc[j], j = 1 .. k-1
                       if ((got & need) != need) fault <= 1;
                       if (k == 1) begin acc <= sc[0]; st <= 3; end
                       else if (!pend) begin a_v <= 1; a_a <= (j == 1) ? sc[0] : acc; a_b <= sc[j]; pend <= 1; end
                       else if (a_vl[LAR]) begin
                           acc <= a_y; pend <= 0;
                           if (j == k - 1) st <= 3; else j <= j + 1;
                       end
                   end
                3: begin                                        // den = tot + 1e-20
                       if (!pend) begin a_v <= 1; a_a <= acc; a_b <= EPS20; pend <= 1; end
                       else if (a_vl[LAR]) begin den <= a_y; pend <= 0; st <= 4; j <= 0; end
                   end
                4: begin                                        // w_j = (sc[j] / den) * scale, pipelined
                       if (j < k) begin d_v <= 1; d_a <= sc[j]; j <= j + 1; end
                       if (d_vo) begin q_hold[nqh] <= d_y; nqh <= nqh + 1; end
                       if (m_vl[LMR]) begin w[nw] <= m_y; nw <= nw + 1; end
                       if ((MUT == 4) ? (nqh == k) : (nw == k)) st <= 5;
                   end
                5: begin o_v <= 1; st <= 0; end
                default: ;
            endcase
        end
    end
    always @(posedge clk)
        if (st == 5) begin : wr
            reg [511:0] r;
            reg [15:0]  m;
            r = 512'd0; m = 16'd0;
            for (ww = 0; ww < 16; ww = ww + 1)        // decoded constant-index slices (no runtime part-select)
                for (i = 0; i < KMAX; i = i + 1)
                    if (i < k && {1'b0, off} + i[4:0] == ww[4:0]) begin r[32 * ww +: 32] = (MUT == 4) ? q_hold[i] : w[i]; m[ww] = 1'b1; end
            o_d <= r; o_m <= m;
        end
endmodule
