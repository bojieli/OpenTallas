`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Segmented reducer of the stream unit.  One segment per outer iteration,
// elements arriving one per cycle without gaps inside a segment.
//
// SUM: element i joins partial i mod 8.  The eight partials live in the adder
// pipeline itself -- the sum re-enters exactly 8 cycles later (adder latency 5,
// operand register 1, feedback 2) -- so each partial is a sequential FP32 sum
// started from +0.  A segment's last element launches a pairwise tree
// ((p0+p1)+(p2+p3))+((p4+p5)+(p6+p7)) of three pipelined adder levels.
// MAX: a running maximum, delayed to the same depth so results leave in order.
//
// Results leave DEPTH = 23 cycles after the segment's last element enters.
// ---------------------------------------------------------------------------
module ot_hdc_reduce #(
    parameter integer AW = 24
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [1:0]    mode,       // 1 SUM, 2 MAX
    input  wire [31:0]   x,
    input  wire          ifirst,     // i == 0
    input  wire          first8,     // i < 8: first element of its partial
    input  wire          final_,     // i + 8 >= n: last element of its partial
    input  wire          last,       // i == n - 1
    input  wire [2:0]    p,          // i mod 8
    input  wire [AW-1:0] raddr,
    output reg           o_we,
    output reg  [AW-1:0] o_addr,
    output reg  [31:0]   o_data,
    output wire          busy,
    output wire          fault
);
    localparam integer DEPTH = 23;
    wire vs = v && (mode == 2'd1);
    wire vm = v && (mode == 2'd2);

    // -- SUM: interleaved partials ------------------------------------------
    reg [31:0] op_a, op_b;
    reg        op_v;
    wire [31:0] psum, fb;
    wire f_acc;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) op_v <= 1'b0;
        else op_v <= vs;
    end
    always @(posedge clk) begin
        op_a <= x;
        op_b <= first8 ? 32'd0 : fb;
    end
    ot_hdc_fadd u_acc (clk, rst_n, op_v, op_a, op_b, psum, f_acc);
    ot_hdc_delay #(.W(32), .D(2)) u_fb (.clk(clk), .rst_n(rst_n), .d(psum), .q(fb));

    // tags to the partial's output (6 cycles)
    localparam integer PT = 1 + 1 + 3 + AW;
    wire [PT-1:0] ptag;
    wire [6:0] pv;
    ot_hdc_vline #(.D(6)) u_pv (.clk(clk), .rst_n(rst_n), .v(vs), .vd(pv));
    ot_hdc_delay #(.W(PT), .D(6)) u_pt (.clk(clk), .rst_n(rst_n), .d({final_, last, p, raddr}), .q(ptag));
    wire          q_final, q_last;
    wire [2:0]    q_p;
    wire [AW-1:0] q_addr;
    assign {q_final, q_last, q_p, q_addr} = ptag;

    reg        l0_v;
    reg [AW-1:0] l0_addr;
    reg [31:0] l0 [0:7];
    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_part
            reg [31:0] part;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) part <= 32'd0;
                else if (pv[6] && q_last) part <= 32'd0;
                else if (pv[6] && q_final && q_p == g) part <= psum;
            end
            always @(posedge clk) l0[g] <= (pv[6] && q_final && q_p == g) ? psum : part;
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) l0_v <= 1'b0;
        else l0_v <= pv[6] && q_last;
    end
    always @(posedge clk) l0_addr <= q_addr;
    // three adder levels
    wire [31:0] l1 [0:3];
    wire [31:0] l2 [0:1];
    wire [31:0] l3;
    wire [6:0] tf;
    generate
        for (g = 0; g < 4; g = g + 1) begin : g_l1
            ot_hdc_fadd u_add (clk, rst_n, l0_v, l0[2*g], l0[2*g+1], l1[g], tf[g]);
        end
    endgenerate
    wire [15:0] tv;
    ot_hdc_vline #(.D(15)) u_tv (.clk(clk), .rst_n(rst_n), .v(l0_v), .vd(tv));
    ot_hdc_fadd u_a20 (clk, rst_n, tv[5], l1[0], l1[1], l2[0], tf[4]);
    ot_hdc_fadd u_a21 (clk, rst_n, tv[5], l1[2], l1[3], l2[1], tf[5]);
    ot_hdc_fadd u_a3  (clk, rst_n, tv[10], l2[0], l2[1], l3, tf[6]);
    wire [AW-1:0] t_addr;
    ot_hdc_delay #(.W(AW), .D(15)) u_ta (.clk(clk), .rst_n(rst_n), .d(l0_addr), .q(t_addr));

    // -- MAX: running maximum -------------------------------------------------
    function automatic [31:0] okey(input [31:0] a);
        okey = a[31] ? ~a : {1'b1, a[30:0]};
    endfunction
    reg [31:0] m;
    wire [31:0] m_next = (ifirst || okey(x) > okey(m)) ? x : m;
    reg        mx_v;
    reg [31:0] mx_d;
    reg [AW-1:0] mx_a;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) mx_v <= 1'b0;
        else mx_v <= vm && last;
    end
    always @(posedge clk) begin
        if (vm) m <= m_next;
        mx_d <= m_next;
        mx_a <= raddr;
    end
    wire [DEPTH-1:0] mv;
    wire [31:0] mx_q;
    wire [AW-1:0] mx_aq;
    ot_hdc_vline #(.D(DEPTH - 2)) u_mv (.clk(clk), .rst_n(rst_n), .v(mx_v), .vd(mv[DEPTH-2:0]));
    assign mv[DEPTH-1] = 1'b0;
    ot_hdc_delay #(.W(32 + AW), .D(DEPTH - 2)) u_md (.clk(clk), .rst_n(rst_n), .d({mx_d, mx_a}), .q({mx_q, mx_aq}));

    // -- output (SUM: l0 at +7, tree +15 -> +22, register +23) ----------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we <= 1'b0;
        else o_we <= tv[15] || mv[DEPTH-2];
    end
    always @(posedge clk) begin
        o_data <= tv[15] ? l3 : mx_q;
        o_addr <= tv[15] ? t_addr : mx_aq;
    end
    assign busy = op_v || (|pv) || l0_v || (|tv) || mx_v || (|mv) || o_we;
    assign fault = f_acc || (|tf);
endmodule
