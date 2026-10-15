`timescale 1ns/1ps
// Actual external capture successor. Five protocol/reset FF are inside the hard core.
module qfd_xs_leaf_extcap (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          w_v,
    input  wire          w_ep,
    input  wire [5:0]    w_off,
    input  wire [63:0]   w_m,
    input  wire [1023:0] w_d,
    input  wire [72-1:0] w_ctl,         // 2 tiles x CTW = 18 b a leaf
    input  wire          c_v,
    input  wire          c_ep,
    output wire          wo_v,
    output wire          wo_ep,
    output wire [5:0]    wo_off,
    output wire [63:0]   wo_m,
    output wire [1023:0] wo_d,
    output wire [72-1:0] wo_ctl,
    output wire          co_v,
    output wire          co_ep,
    input  wire          r_v,
    input  wire          r_t,
    input  wire          r_ep,
    input  wire [27:0]   r_p,
    output wire           q_v,
    output wire  [63:0]   q,
    output wire           q_bad,
    input wire [1:0] wd0_flags,wd1_flags,
    output reg fault
);
    reg [1:0] boot;
    reg valid_q,epoch_q;
    wire capture_window=(boot==3);
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin boot<=0;valid_q<=0;fault<=0;end
        else begin
            if(boot!=3)boot<=boot+1'b1;
            valid_q<=w_v&&capture_window;
            if(w_v&&!capture_window)fault<=1;
            if(valid_q&&(!wd0_flags[1]||!wd1_flags[1]||wd0_flags[0]!=epoch_q||wd1_flags[0]!=epoch_q))fault<=1;
        end
    always @(posedge clk)epoch_q<=w_ep;
    ot_qfd_xs_leaf #(.NCH(4),.BANK_PIPE(1),.FILL_PIPE(1),.EXTERNAL_WD_CAPTURE(1)) u_leaf (
        .clk(clk),
        .rst_n(rst_n),
        .w_v(w_v&&capture_window),
        .w_ep(w_ep),
        .w_off(w_off),
        .w_m(w_m),
        .w_d(w_d),
        .w_ctl(w_ctl),
        .c_v(c_v),
        .c_ep(c_ep),
        .wo_v(wo_v),
        .wo_ep(wo_ep),
        .wo_off(wo_off),
        .wo_m(wo_m),
        .wo_d(wo_d),
        .wo_ctl(wo_ctl),
        .co_v(co_v),
        .co_ep(co_ep),
        .r_v(r_v),
        .r_t(r_t),
        .r_ep(r_ep),
        .r_p(r_p),
        .q_v(q_v),
        .q(q),
        .q_bad(q_bad));
endmodule
module qfd_xs_leaf_capture_parent #(parameter integer MUT=0)(

    input  wire          clk,
    input wire clk_wd0,clk_wd1,
    input  wire          rst_n,
    input  wire          w_v,
    input  wire          w_ep,
    input  wire [5:0]    w_off,
    input  wire [63:0]   w_m,
    input  wire [1023:0] w_d,
    input  wire [72-1:0] w_ctl,         // 2 tiles x CTW = 18 b a leaf
    input  wire          c_v,
    input  wire          c_ep,
    output wire          wo_v,
    output wire          wo_ep,
    output wire [5:0]    wo_off,
    output wire [63:0]   wo_m,
    output wire [1023:0] wo_d,
    output wire [72-1:0] wo_ctl,
    output wire          co_v,
    output wire          co_ep,
    input  wire          r_v,
    input  wire          r_t,
    input  wire          r_ep,
    input  wire [27:0]   r_p,
    output wire           q_v,
    output wire  [63:0]   q,
    output wire           q_bad,
    output wire fault
);

    wire [513:0] wd0_q,wd1_q;
    qwen_glue_v514 u_capture0(.clk(clk_wd0),.rst_n(rst_n),.d({w_v,w_ep,w_d[511:0]}),.q(wd0_q));
    qwen_glue_v514 u_capture1(.clk(clk_wd1),.rst_n(rst_n),.d({w_v,w_ep,w_d[1023:512]}),.q(wd1_q));
    qfd_xs_leaf_extcap u_core (
        .clk(clk),
        .rst_n(rst_n),
        .w_v(w_v),
        .w_ep(w_ep),
        .w_off(w_off),
        .w_m(w_m),
        .w_d((MUT==1)?w_d:{wd1_q[511:0],wd0_q[511:0]}),
        .w_ctl(w_ctl),
        .c_v(c_v),
        .c_ep(c_ep),
        .wo_v(wo_v),
        .wo_ep(wo_ep),
        .wo_off(wo_off),
        .wo_m(wo_m),
        .wo_d(wo_d),
        .wo_ctl(wo_ctl),
        .co_v(co_v),
        .co_ep(co_ep),
        .r_v(r_v),
        .r_t(r_t),
        .r_ep(r_ep),
        .r_p(r_p),
        .q_v(q_v),
        .q(q),
        .q_bad(q_bad),.wd0_flags(wd0_q[513:512]),.wd1_flags(wd1_q[513:512]),.fault(fault));
endmodule
