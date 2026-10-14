`timescale 1ns/1ps
`default_nettype none
// c5 native HC window leaf. Every cross-leaf input first enters a pin flop.
// HBM requests use one retained receiver seat, returned only when consumed.
// Payload/read datapath is not reset; the local reset controls validity only.
module ot_hgi_hc_win #(
    parameter integer W=32, WORDS=32, AW=16, HAW=35,
    parameter integer RTW=7, TG=RTW+4, CW=$clog2(WORDS+1),
    parameter integer MACRO=1, MUT=0
)(
    input wire clk,rst_n,
    input wire c_start,c_rel,
    input wire [HAW-1:0] c_base,c_soff,
    input wire [CW-1:0] c_nwords,
    input wire [AW-1:0] c_bound,c_limit,
    input wire hr_v,input wire [TG-1:0] hr_tag,
    input wire [1:0] hr_beat,input wire [127:0] hr_data_lo,hr_data_hi,
    input wire rom_re,input wire [AW-1:0] rom_addr,
    output reg rom_v,
    output wire [127:0] rom_0,rom_1,rom_2,rom_3,rom_4,rom_5,rom_6,rom_7,
    output reg hq_v,output reg [HAW-1:0] hq_addr,
    output reg [2:0] hq_len,output reg [TG-1:0] hq_tag,
    input wire hq_cr,
    output reg ready,output reg fault
);
    wire [0:0] rn;
    ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
    initial if(W!=32)$fatal(1,"HC window leaf requires32 lanes");
    reg [1023:0] rom_data;
    assign {rom_7,rom_6,rom_5,rom_4,rom_3,rom_2,rom_1,rom_0}=rom_data;
    reg start_q,rel_q,start_qq,rel_qq,rv_q,re_q,credit_q;
    reg [HAW-1:0] base_q,soff_q,hbase;
    reg [CW-1:0] n_q,n_qq;
    reg [AW-1:0] bound_q,limit_q,addr_q;
    reg [TG-1:0] tag_q;reg[1:0]beat_q;reg[255:0]data_q;
    always @(posedge clk)begin
        base_q<=c_base;soff_q<=c_soff;hbase<=base_q+soff_q;
        n_q<=c_nwords;n_qq<=n_q;bound_q<=c_bound;limit_q<=c_limit;
        addr_q<=rom_addr;tag_q<=hr_tag;beat_q<=hr_beat;data_q<={hr_data_hi,hr_data_lo};
    end
    always @(posedge clk or negedge rn[0])begin
        if(!rn[0])begin start_q<=0;rel_q<=0;start_qq<=0;rel_qq<=0;rv_q<=0;re_q<=0;credit_q<=0;end
        else begin start_q<=c_start;rel_q<=c_rel;start_qq<=start_q;rel_qq<=rel_q;
            rv_q<=hr_v;re_q<=rom_re;credit_q<=hq_cr;end
    end
    wire select_q=addr_q>=bound_q&&addr_q<limit_q;
    wire wrdy,wflt,wv;wire[HAW-1:0]wa;wire[2:0]wl;wire[RTW-1:0]wt;
    wire[W*32-1:0]raw;wire[3:0]why;wire[CW-1:0]fetched;wire[31:0]received;
    reg credit;
    wire send=wv&&(credit||MUT==3);
    ot_hdc_v41x_weight_window #(.WB(W*32),.SB(256),.WORDS(WORDS),.AW(AW),.HAW(HAW),.NPC(1),.LENW(3),
        .BURST_MAX(4),.RTW(RTW),.MACRO(MACRO)) u_w(
        .clk(clk),.rst_n(rn[0]),.start(start_qq&&n_qq!=0),.release_window(rel_qq),
        .rom_base({AW{1'b0}}),.hbm_base(hbase),.nwords(n_qq),.ready(wrdy),
        .hq_v(wv),.hq_rdy(send),.hq_addr(wa),.hq_len(wl),.hq_tag(wt),
        .hr_v(rv_q&&tag_q[TG-1-:4]!=4'd8),.hr_rdy(),.hr_tag(tag_q[RTW-1:0]),.hr_beat(beat_q),.hr_data(data_q),
        .rom_re(re_q&&select_q),.rom_addr(addr_q-bound_q),.rom_q(raw),.fault(wflt),.fault_why(why),
        .fetched_words(fetched),.received_sectors(received));
    reg v1,v2;reg[W*32-1:0]capture;
    always @(posedge clk)begin
        capture<=raw;
        rom_data<=(capture&{W*32{v2}}) ^ ((MUT==1&&v2)?{{(W*32-1){1'b0}},1'b1}:{W*32{1'b0}});
        if(send)begin hq_addr<=wa;hq_len<=wl;hq_tag<={4'd0,(MUT==2)?wt^RTW'(1):wt};end
    end
    always @(posedge clk or negedge rn[0])begin
        if(!rn[0])begin credit<=1;hq_v<=0;v1<=0;v2<=0;rom_v<=0;ready<=0;fault<=0;end
        else begin
            if(send&&!credit_q)credit<=0;else if(!send&&credit_q)credit<=1;
            hq_v<=send;v1<=re_q&&select_q;v2<=v1;rom_v<=v2;
            ready<=n_qq==0||wrdy;
            if(wflt||(credit_q&&credit&&!send))fault<=1;
        end
    end
endmodule
`default_nettype wire
