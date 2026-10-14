`timescale 1ns/1ps
// Default-off exact selected tree copy: original tree remains byte-identical.
// Only its pair-adder implementation is selectable. Same golden pairing,
// ring hold, tags/fault path and stage schedule; no ready/stall/extra cut.
module ot_qwen_me_sptree_bypass_w12 #(
    parameter integer GT = 80,
    parameter integer SMIN = 3,
    parameter integer TCUT = 3,
    parameter integer TREE_LAT = 3,
    parameter integer TINREG = 1,
    parameter bit BYPASS_AFTER_CAPTURE = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [(GT >> TCUT)*32-1:0] t_in,       // this lane of tree level TCUT
    input  wire [$clog2(GT):0] sel_e,             // per level: (split >= level) when its sums emerge, one cycle early
    input  wire [$clog2(GT):0] tv_e,              // per level: the adders' valid, one cycle early
    output wire [(GT >> SMIN)*32-1:0] y,          // this lane of tree level LG-1, the result-port positions
    output reg         fault
);
    localparam integer LG = $clog2(GT);
    localparam integer LV0 = TCUT;
    localparam integer GI = GT >> TCUT;
    localparam integer NPG = GT >> SMIN;
    localparam integer TA = TREE_LAT;
    localparam integer PRUNE = (SMIN > 0);
    reg  [LG:0] sel_r, tv_r;
    always @(posedge clk) sel_r <= sel_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) tv_r <= 0; else tv_r <= tv_e;
    //: level lv's words at lvf[lv*GI*32 +: GI*32] (a flat vector: Yosys 0.68 asserts on a wire array here)
    wire [LG*GI*32-1:0] lvf;
    wire [LG:0] tfault;
    generate if (TINREG != 0) begin : g_tin
        reg [GI*32-1:0] tin_q;
        always @(posedge clk) tin_q <= t_in;
        assign lvf[LV0*GI*32 +: GI*32] = tin_q;
    end else begin : g_tin_w
        assign lvf[LV0*GI*32 +: GI*32] = t_in;
    end endgenerate
    assign tfault[LV0:0] = 0;
    assign tfault[LG] = 1'b0;
    genvar lv, p;
    generate
        for (lv = LV0 + 1; lv <= LG - 1; lv = lv + 1) begin : g_lvl
            localparam integer ALWAYS = PRUNE && (SMIN >= lv);
            localparam integer HOLD_TO = NPG;
            localparam integer R0 = (GT >> lv);
            localparam integer R1 = ALWAYS ? R0 : ((HOLD_TO > R0) ? HOLD_TO : R0);
            localparam integer RW = (R1 > 0) ? R1 : 1;
            localparam integer PAIRS = R0;
            reg  [RW*32-1:0] lq;
            wire [GI*32-1:0] held;
            wire [(PAIRS > 0 ? PAIRS : 1)-1:0] pf;
            if (PAIRS == 0) begin : g_nopf
                assign pf = 1'b0;
            end
            if (!ALWAYS && HOLD_TO > 0) begin : g_hold
                ot_qwen_me_rdelay_w12 #(.W(HOLD_TO*32), .D(TA)) u_hold (.clk(clk), .rst_n(rst_n),
                    .d(lvf[(lv-1)*GI*32 +: HOLD_TO*32]), .q(held[HOLD_TO*32-1:0]));
                if (HOLD_TO < GI) begin : g_hz
                    assign held[GI*32-1:HOLD_TO*32] = 0;
                end
            end else begin : g_nohold
                assign held = {GI*32{1'b0}};
            end
            for (p = 0; p < PAIRS; p = p + 1) begin : g_add
                wire [31:0] s_out;
                ot_qwen_me_tadd_bypass_w12 #(.LAT(TREE_LAT),.BYPASS_AFTER_CAPTURE(BYPASS_AFTER_CAPTURE)) u_add (clk, rst_n, tv_r[lv],
                                   lvf[(lv-1)*GI*32 + 32*(2*p) +: 32], lvf[(lv-1)*GI*32 + 32*(2*p+1) +: 32], s_out, pf[p]);
                if (ALWAYS) begin : g_a
                    always @(posedge clk) lq[32*p +: 32] <= s_out;
                end else begin : g_s
                    always @(posedge clk) lq[32*p +: 32] <= sel_r[lv] ? s_out : held[32*p +: 32];
                end
            end
            if (R1 > R0) begin : g_rest
                always @(posedge clk) lq[R1*32-1 : R0*32] <= held[R1*32-1 : R0*32];
            end
            if (R1 == 0) begin : g_lz
                assign lvf[lv*GI*32 +: GI*32] = {GI*32{1'b0}};
            end else if (R1 < GI) begin : g_lp
                assign lvf[lv*GI*32 +: GI*32] = {{((GI - R1) * 32){1'b0}}, lq};
            end else begin : g_lf
                assign lvf[lv*GI*32 +: GI*32] = lq;
            end
            assign tfault[lv] = |pf;
        end
    endgenerate
    assign y = lvf[(LG-1)*GI*32 +: NPG*32];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else fault <= |tfault;
    end
endmodule
module ot_qwen_me_tadd_bypass_w12 #(
    parameter integer LAT=7, parameter bit BYPASS_AFTER_CAPTURE=0
)(input wire clk,rst_n,v,input wire [31:0] a,b,
  output wire [31:0] y,output wire fault);
    generate if (BYPASS_AFTER_CAPTURE) begin : g_on
        wire [1:0] err; wire vo;
        ot_qwen_me_add_bypass_w12 #(.LAT(LAT),.BYPASS_AFTER_CAPTURE(1)) u (
            .clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y),.err(err),.valid_out(vo));
        assign fault=vo&&(err!=0);
    end else begin : g_off
        ot_qwen_w12_tadd #(.LAT(LAT)) u(clk,rst_n,v,a,b,y,fault);
    end endgenerate
endmodule
