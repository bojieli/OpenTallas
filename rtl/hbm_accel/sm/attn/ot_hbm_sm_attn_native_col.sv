`timescale 1ns/1ps
`default_nettype none
// Source-compatible arithmetic integration boundary for the revisioned static
// parent. The two CLOSED tcl halves and CLOSED tct retain their original ports
// and arithmetic. QK/PV last pulses are distinct compiler-assigned signals.
// This parent is wires only. New sum-capture and merge leaves have separate
// names; no physical view is inherited from a closed master.
module ot_hbm_sm_attn_native_col #(
    parameter integer TAGW=16, LV=4, MUT=0, PUBLISH=0
)(
    input wire clk, rst_n,
    input wire i_v, i_first, i_qk_last, i_pv_last,
    input wire i_run_first, i_run_last,
    input wire [TAGW-1:0] i_tag,
    input wire [255:0] i_w, i_x,
    output wire ov,
    output wire [31:0] y,
    output wire [TAGW-1:0] otag,
    output wire pv_v,
    output wire [511:0] pv_y,
    output wire [TAGW-1:0] pv_tag,
    output wire fault,
    input wire pub_start,
    input wire [2:0] pub_slot,
    output wire pub_v,
    output wire [31:0] pub_data,
    output wire [3:0] pub_word,
    output wire [2:0] pub_out_slot,
    output wire [TAGW-1:0] pub_tag,
    input wire fold_start,
    input wire [2:0] fold_a,
    input wire [2:0] fold_b
);
    wire [255:0] s0,s1;
    wire lf0,lf1,qf,mf;
    ot_hbm_accel_smh_tcl u_h0(.clk(clk),.rst_a(rst_n),.i_v(i_v),.i_first(i_first),
        .i_w(i_w[127:0]),.i_x(i_x[127:0]),.sum_o(s0),.lfault(lf0));
    ot_hbm_accel_smh_tcl u_h1(.clk(clk),.rst_a(rst_n),.i_v(i_v),.i_first(i_first),
        .i_w(i_w[255:128]),.i_x(i_x[255:128]),.sum_o(s1),.lfault(lf1));
    ot_hbm_accel_smh_tct #(.TAGW(TAGW)) u_qk(.clk(clk),.rst_a(rst_n),.i_v(i_v),
        .i_last(i_qk_last),.i_tag(i_tag),.sum_i({s1,s0}),.lf_a(lf0),.lf_b(lf1),
        .ov(ov),.y(y),.otag(otag),.fault(qf));
    wire event_v;
    wire [511:0] event_sum;
    wire [TAGW-1:0] event_tag;
    ot_hbm_sm_attn_sum_capture #(.TAGW(TAGW)) u_cap(.clk(clk),.rst_n(rst_n),
        .i_v(i_v),.i_last(i_pv_last),.i_run_first(i_run_first),.i_run_last(i_run_last),
        .i_tag(i_tag),.sum_i({s1,s0}),.event_v(event_v),.event_sum(event_sum),.event_tag(event_tag));
    ot_hbm_sm_pv_merge #(.TAGW(TAGW),.LV(LV),.MUT(MUT),.PUBLISH(PUBLISH)) u_merge(.clk(clk),.rst_n(rst_n),
        .ev(event_v),.sum(event_sum),.tag_d(event_tag),.pv_v(pv_v),.pv_y(pv_y),.pv_tag(pv_tag),.fault(mf),.pub_start(pub_start),.pub_slot(pub_slot),
        .pub_v(pub_v),.pub_data(pub_data),.pub_word(pub_word),.pub_out_slot(pub_out_slot),.pub_tag(pub_tag),
        .fold_start(fold_start),.fold_a(fold_a),.fold_b(fold_b));
    assign fault=qf|mf;
endmodule

// Registered sum/control boundary copied from CLOSED ot_hbm_accel_smh_tct.
// LL=ML7+ALAT7+2=16, after j and the two control rungs. Capture has no ready
// input: it never delays a compiled last pulse to wait for data.
module ot_hbm_sm_attn_sum_capture #(
    parameter integer TAGW=16
)(
    input wire clk,rst_n,i_v,i_last,i_run_first,i_run_last,
    input wire [TAGW-1:0] i_tag,
    input wire [511:0] sum_i,
    output wire event_v,
    output wire [511:0] event_sum,
    output wire [TAGW-1:0] event_tag
);
    localparam integer LL=16;
    reg jv,jlast,v_q,last_q,last_q2;
    reg [TAGW-1:0] jtag,tag_q,tag_q2;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin jv<=0;v_q<=0;last_q<=0;last_q2<=0;end
        else begin jv<=i_v;v_q<=jv;last_q<=jv&&jlast;last_q2<=last_q;end
    always @(posedge clk)begin
        jlast<=i_last;
        jtag<={1'b1,i_run_first,i_run_last,i_tag[TAGW-4:0]};
        tag_q<=jtag;tag_q2<=tag_q;
    end
    wire [LL:0] ll;
    ot_hdc_vline #(.D(LL)) u_l(.clk(clk),.rst_n(rst_n),.v(last_q2),.vd(ll));
    ot_hdc_delay #(.W(TAGW),.D(LL)) u_t(.clk(clk),.rst_n(rst_n),.d(tag_q2),.q(event_tag));
    reg [511:0] sum_q2;
    always @(posedge clk)sum_q2<=sum_i;
    assign event_sum=sum_q2;
    assign event_v=ll[LL];
endmodule
`default_nettype wire
