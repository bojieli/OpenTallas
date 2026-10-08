`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_tc16: ot_gpu_tc16 (rtl/gpu/ot_gpu_tc_col.sv, L = 16) with its bubble gate moved off the multiplier's
// first stage, for 1.2 GHz SS: the original forces a bubble lane's registered weight to +0 in front of
// ot_hdc_bmul's decode/exponent-add stage; here the weight enters unchanged and the bubble raises the multiplier's
// zero flag instead (ot_hbm_accel_bmul `kill`).  Same result bits: a zero operand already gives y = +0 whatever
// the other operand is, and the fault output is gated by the bubble's own valid (v = 0), as in the original.
// Zero added cycles.
// ---------------------------------------------------------------------------
module ot_hbrom_tc_col_protected #(
    parameter integer PROTECT = 0,
    parameter integer L    = 32,        // defaults = the hardened macro (Qwen SM: 32 lanes, 16-bit tag)
    parameter integer IL   = 8,
    parameter integer TAGW = 16,
    parameter integer ALAT = 7          // adder latency: the IL-slot ring needs ALAT <= IL - 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire            first,
    input  wire            last,
    input  wire [TAGW-1:0] tag,
    input  wire [L*16-1:0] w,
    input  wire [L*16-1:0] x,
    output wire            ov,
    output wire [31:0]     y,
    output wire [TAGW-1:0] otag,
    output wire            fault
);
    generate if(!PROTECT) begin:g_original
    ot_hbm_accel_tc_col #(.L(L),.IL(IL),.TAGW(TAGW),.ALAT(ALAT)) u_original(.*);
    end else begin:g_protected
    localparam integer FB = IL - ALAT;          // ring = acc register + adder + (FB - 1) delay = IL
    reg            v_q, first_q, last_q;
    reg [L-1:0]    v_ql;                // per-lane copy of v for the bubble gate
    reg [TAGW-1:0] tag_q;
    reg [L*16-1:0] w_q, x_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v_q <= 1'b0; first_q <= 1'b0; last_q <= 1'b0; v_ql <= {L{1'b0}}; end
        else begin v_q <= v; first_q <= v && first; last_q <= v && last; v_ql <= {L{v}}; end
    end
    always @(posedge clk) begin
        w_q <= w;
        x_q <= x;
        if(!rst_n) tag_q<=0;else tag_q <= tag;
    end
    wire [5:0] fl;
    wire pf0; ot_hbrom_metadata_pipe #(.W(1),.D(5)) u_f (.clk(clk),.rst_n(rst_n),.d(first_q),.q(),.taps(fl),.fault(pf0));
    // chunk end: the lane's final sum leaves the adder 5 (mul) + 5 (add) cycles after the input register
    localparam integer LL = 5 + ALAT;
    wire [LL:0] ll;
    wire pf1; ot_hbrom_metadata_pipe #(.W(1),.D(LL)) u_l (.clk(clk),.rst_n(rst_n),.d(last_q),.q(),.taps(ll),.fault(pf1));
    wire [TAGW-1:0] tag_d;
    wire pf3; ot_hbrom_metadata_pipe #(.W(TAGW),.D(LL)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_q), .q(tag_d),.taps(),.fault(pf3));
    wire [5:0] vl;
    wire pf2; ot_hbrom_metadata_pipe #(.W(1),.D(5)) u_v (.clk(clk),.rst_n(rst_n),.d(v_q),.q(),.taps(vl),.fault(pf2));
    wire [L*32-1:0] sum;
    wire [L-1:0] lf;
    genvar l;
    for (l = 0; l < L; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        wire f0, f1;
        // a bubble multiplies by +0: the slot's sum holds
        ot_hbm_accel_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(v_q), .kill(!v_ql[l]), .a({w_q[16*l +: 16], 16'd0}),
                           .b({x_q[16*l +: 16], 16'd0}), .y(prod), .fault(f0));
        always @(posedge clk) acc_q <= fl[4] ? 32'd0 : fb_pre;
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(vl[5]), .a(acc_q), .b(prod), .y(sum[32*l +: 32]), .fault(f1));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        assign lf[l] = f0 | f1;
    end
    wire tf, t_ov;
    wire [31:0] t_y;
    wire [TAGW-1:0] t_tag;
    ot_hbrom_tree_protected #(.PROTECT(1),.N(L), .TAGW(TAGW), .ALAT(ALAT)) u_tree (.clk(clk), .rst_n(rst_n), .v(ll[LL]), .d(sum), .tag(tag_d),
                                             .ov(t_ov), .y(t_y), .otag(t_tag), .fault(tf));
    reg lane_fault, ov_q, fault_q;
    reg [31:0] y_q;
    reg [TAGW-1:0] otag_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lane_fault <= 1'b0; ov_q <= 1'b0; fault_q <= 1'b0; end
        else begin
            lane_fault <= lane_fault | (|lf);
            ov_q <= t_ov;
            fault_q <= lane_fault | tf;
        end
    always @(posedge clk) begin y_q <= t_y; if(!rst_n) otag_q<=0;else otag_q <= t_tag; end
    assign ov = ov_q && !fault;
    assign y = y_q;
    assign otag = otag_q;
    assign fault = fault_q | fault_b | ctrl_bad | poison_a | poison_b;

    (* keep *) reg v_b,first_b,last_b;
    (* keep *) reg [L-1:0] vl_b;
    (* keep *) reg [TAGW-1:0] tag_b;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin v_b<=0;first_b<=0;last_b<=0;vl_b<=0;tag_b<=0;end
      else begin v_b<=v;first_b<=v&&first;last_b<=v&&last;vl_b<={L{v}};tag_b<=tag;end
    end
    wire ingress_bad=({v_q,first_q,last_q,v_ql,tag_q}!={v_b,first_b,last_b,vl_b,tag_b});
    (* keep *) reg lane_fault_b;
    always @(posedge clk or negedge rst_n) if(!rst_n) lane_fault_b<=0;else lane_fault_b<=lane_fault_b|(|lf);

    (* keep *) reg ov_b,fault_b,poison_a,poison_b;
    (* keep *) reg [TAGW-1:0] otag_b;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin ov_b<=0;fault_b<=0;otag_b<=0;end
      else begin ov_b<=t_ov;fault_b<=lane_fault_b|tf;otag_b<=t_tag;end
    end
    wire ctrl_bad=ingress_bad|(lane_fault!=lane_fault_b)|(ov_q!=ov_b)|(fault_q!=fault_b)|(otag_q!=otag_b)|pf0|pf1|pf2|pf3;
    always @(posedge clk or negedge rst_n) if(!rst_n) poison_a<=0;else poison_a<=poison_a|poison_b|ctrl_bad;
    always @(posedge clk or negedge rst_n) if(!rst_n) poison_b<=0;else poison_b<=poison_b|poison_a|ctrl_bad;
    end endgenerate
endmodule