`timescale 1ns/1ps
// Native pin boundary for the fixed SU controller: +1 startup/observation stage, II1.
module ot_s81_su_calendar_ctl_p (
    input wire clk, rst_n, arm,
    input wire calendar_valid,
    input wire [31:0] calendar_cycle,
    input wire [1023:0] calendar_word,
    output wire [31:0] cycle,
    output wire [15:0] rq_v,
    output wire [223:0] rq_row,
    input wire [15:0] rs_v, wq_v,
    input wire [223:0] wq_row,
    input wire [255:0] wq_mask,
    output wire dn_st,
    output wire [3:0] dn_kind,
    output wire [1:0] dn_gsel,
    output wire dn_fp4,
    output wire [7:0] dn_jid,
    output wire moe_v,
    output wire [13:0] moe_row,
    output wire done,
    output wire [7:0] done_tag,
    input wire up_fu, up_fo, up_alive, up_den, up_rdy,
    input wire [7:0] up_rjid,
    output wire fault,
    output wire [3:0] fault_code,
    output wire running,
    output reg prefetch_arm, prefetch_halt
);
    reg [1:0] reset_sync;
    always @(posedge clk or negedge rst_n)if(!rst_n)reset_sync<=0;else reset_sync<={reset_sync[0],1'b1};
    wire rn=reset_sync[1];
    reg q_valid;
    reg [31:0] q_calendar_cycle;
    reg [1023:0] q_calendar_word;
    reg [15:0] q_rs_v;
    reg [15:0] q_wq_v;
    reg [223:0] q_wq_row;
    reg [255:0] q_wq_mask;
    reg q_up_fu;
    reg q_up_fo;
    reg q_up_alive;
    reg q_up_den;
    reg q_up_rdy;
    reg [7:0] q_up_rjid;
    always @(posedge clk or negedge rn)if(!rn)begin
        prefetch_arm<=0;prefetch_halt<=0;q_valid<=0;
    end else begin prefetch_arm<=arm;prefetch_halt<=arm?1'b0:calendar_word[788];q_valid<=calendar_valid;end
    always @(posedge clk)begin
        q_calendar_cycle<=calendar_cycle;
        q_calendar_word<=calendar_word;
        q_rs_v<=rs_v;
        q_wq_v<=wq_v;
        q_wq_row<=wq_row;
        q_wq_mask<=wq_mask;
        q_up_fu<=up_fu;
        q_up_fo<=up_fo;
        q_up_alive<=up_alive;
        q_up_den<=up_den;
        q_up_rdy<=up_rdy;
        q_up_rjid<=up_rjid;
    end
    ot_s81_su_calendar_ctl core(
        .clk(clk),.rst_n(rn),.arm(prefetch_arm),.calendar_valid(q_valid),
        .calendar_cycle(q_calendar_cycle),.calendar_word(q_calendar_word),.cycle(cycle),.rq_v(rq_v),
        .rq_row(rq_row),.rs_v(q_rs_v),.wq_v(q_wq_v),.wq_row(q_wq_row),
        .wq_mask(q_wq_mask),.dn_st(dn_st),.dn_kind(dn_kind),.dn_gsel(dn_gsel),
        .dn_fp4(dn_fp4),.dn_jid(dn_jid),.moe_v(moe_v),.moe_row(moe_row),
        .done(done),.done_tag(done_tag),.up_fu(q_up_fu),.up_fo(q_up_fo),
        .up_alive(q_up_alive),.up_den(q_up_den),.up_rdy(q_up_rdy),.up_rjid(q_up_rjid),
        .fault(fault),.fault_code(fault_code),.running(running));
endmodule

// Actual fixed lookahead logic for the mapped programme/control component.
// It adds one startup edge, retains one instruction per edge, and samples observed
// response/status pins one edge before their core comparison. No demand gating.
module ot_s81_su_calendar_prefetch_p(
 input wire running,arm_d,halt_d,input wire [31:0] cycle,
 output wire store_running,output wire [31:0] store_cycle,word_cycle);
 assign store_running=(running||arm_d)&&!halt_d;
 assign store_cycle=running?cycle+32'd1:32'd0;
 assign word_cycle=running?cycle+32'd1:cycle;
endmodule
