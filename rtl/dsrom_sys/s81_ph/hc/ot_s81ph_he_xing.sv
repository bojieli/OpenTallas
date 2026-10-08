`timescale 1ns/1ps
// CLAUDE S81-PH hc (2026-10-06): the HC slab's die crossing around ot_s81ph_he_adapt (REMOTE-READ split, as the SU's
// ot_s81ph_su_xing).  VM -> HC, DF cycles: go + op fields, x_q.  HC -> VM, DR cycles: x_re/x_addr, ready/idle/fault and
// the masked writes o_*.  The weight banks are resident in the HC slab (w_* do not cross).  ready/idle are false for
// DF + DR cycles after every go.  DF = DR = 0 is ot_hdc_v41x_he_adapt exactly.  NEG (bench only): 1 x-read delay one
// short, 2 ready/idle not held while a go is in flight.
module ot_s81ph_he_xing #(
    parameter integer DF = 0,
    parameter integer DR = 0,
    parameter integer NEG = 0,

    parameter integer HW   = 8,            // engine lanes per group (8 * HW FP32 MAC lanes)
    parameter integer TL   = 9,            // engine tail levels
    parameter integer KCMAX = 128,         // largest he_k (chunks per row)
    parameter integer PMAX = 8,            // positions per op (power of two >= MP)
    parameter integer BAW  = 16,           // weight bank word address width
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer S    = 8,            // x read ports (the as-built HC_SPLIT)
    parameter integer MP   = 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_obase,
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps,
    input  wire [AW-1:0]     i_ops,
    // weight banks (binary32), bank k at [k*...]
    output wire [7:0]        w_re,
    output wire [8*BAW-1:0]  w_addr,
    input  wire [8*HW*32-1:0] w_data,
    // vector memory: x reads (the as-built HE's per-chunk ports) and the masked write
    output wire [MP*S-1:0]   x_re,
    output wire [MP*S*AW-1:0] x_addr,
    input  wire [MP*S*32-1:0] x_q,
    output wire [MP-1:0]     o_we,
    output wire [MP*AW-1:0]  o_addr,
    output wire [MP*32-1:0]  o_mask,
    output wire [MP*1024-1:0] o_data,
    output wire              fault
);
    localparam integer FW = $bits(i_nout) + $bits(i_k) + $bits(i_wbase) + $bits(i_xbase) + $bits(i_obase) + $bits(i_m) + $bits(i_xps) + $bits(i_ops);
    localparam integer WIN = DF + DR;
    wire [NW-1:0] d_nout;
    wire [NW-1:0] d_k;
    wire [AW-1:0] d_wbase;
    wire [AW-1:0] d_xbase;
    wire [AW-1:0] d_obase;
    wire [2:0] d_m;
    wire [AW-1:0] d_xps;
    wire [AW-1:0] d_ops;
    wire d_go;
    ot_hdc_delay #(.W(1), .D(DF), .RESET(1)) u_dgo (.clk(clk), .rst_n(rst_n), .d(go), .q(d_go));
    ot_hdc_delay #(.W(FW), .D(DF)) u_dfld (.clk(clk), .rst_n(rst_n), .d({i_nout, i_k, i_wbase, i_xbase, i_obase, i_m, i_xps, i_ops}), .q({d_nout, d_k, d_wbase, d_xbase, d_obase, d_m, d_xps, d_ops}));
    wire inflight;
    generate if (WIN == 0) begin : g_w0
        assign inflight = 1'b0;
    end else begin : g_w
        reg [WIN-1:0] gw;
        always @(posedge clk or negedge rst_n) if (!rst_n) gw <= {WIN{1'b0}}; else gw <= {gw, go};
        assign inflight = |gw;
    end endgenerate
    wire u_ready, u_idle, u_fault, r_ready, r_idle;
    ot_hdc_delay #(.W(3), .D(DR), .RESET(1)) u_rst (.clk(clk), .rst_n(rst_n), .d({u_ready, u_idle, u_fault}), .q({r_ready, r_idle, fault}));
    assign ready = r_ready && (!inflight || NEG == 2);
    assign idle = r_idle && (!inflight || NEG == 2);
    wire [MP*S-1:0] u_x_re; wire [MP*S*AW-1:0] u_x_addr; wire [MP*S*32-1:0] u_x_q;
    ot_hdc_delay #(.W(MP*S), .D(DR), .RESET(1)) u_dxr (.clk(clk), .rst_n(rst_n), .d(u_x_re), .q(x_re));
    ot_hdc_delay #(.W(MP*S*AW), .D(DR)) u_dxa (.clk(clk), .rst_n(rst_n), .d(u_x_addr), .q(x_addr));
    ot_hdc_delay #(.W(MP*S*32), .D(DF)) u_dxq (.clk(clk), .rst_n(rst_n), .d(x_q), .q(u_x_q));
    wire [MP-1:0] u_o_we; wire [MP*AW-1:0] u_o_addr; wire [MP*32-1:0] u_o_mask; wire [MP*1024-1:0] u_o_data;
    ot_hdc_delay #(.W(MP), .D(DR), .RESET(1)) u_dowe (.clk(clk), .rst_n(rst_n), .d(u_o_we), .q(o_we));
    ot_hdc_delay #(.W(MP*(AW+32+1024)), .D(DR)) u_dod (.clk(clk), .rst_n(rst_n), .d({u_o_addr, u_o_mask, u_o_data}), .q({o_addr, o_mask, o_data}));
    ot_s81ph_he_adapt #(.RX(DF + DR - (NEG == 1 ? 1 : 0)), .HW(HW), .TL(TL), .KCMAX(KCMAX), .PMAX(PMAX), .BAW(BAW), .AW(AW), .NW(NW), .S(S), .MP(MP)) u_he (
        .clk(clk), .rst_n(rst_n), .go(d_go), .ready(u_ready), .idle(u_idle),
        .i_nout(d_nout),
        .i_k(d_k),
        .i_wbase(d_wbase),
        .i_xbase(d_xbase),
        .i_obase(d_obase),
        .i_m(d_m),
        .i_xps(d_xps),
        .i_ops(d_ops),
        .w_re(w_re), .w_addr(w_addr), .w_data(w_data),
        .x_re(u_x_re), .x_addr(u_x_addr), .x_q(u_x_q),
        .o_we(u_o_we), .o_addr(u_o_addr), .o_mask(u_o_mask), .o_data(u_o_data), .fault(u_fault));
endmodule
