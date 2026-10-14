`timescale 1ns/1ps
`default_nettype none
// Controller and four independent SRAM/capture leaves. Parent is wires only.
module ot_hgi_hc_win_ctl #(
    parameter integer W=32, WORDS=32, AW=16, HAW=35,
    parameter integer RTW=7, TG=RTW+4, CW=$clog2(WORDS+1),
    parameter integer MACRO=0, MUT=0
)(
    input wire clk,rst_n,
    input wire c_start,c_rel,
    input wire [HAW-1:0] c_base,c_soff,
    input wire [CW-1:0] c_nwords,
    input wire [AW-1:0] c_bound,c_limit,
    input wire hr_v,input wire [TG-1:0] hr_tag,
    input wire [1:0] hr_beat,
    input wire rom_re,input wire [AW-1:0] rom_addr,
    output reg sector_read,sector_live,output reg [6:0] sector_addr,
    input wire [3:0] sector_fault,
    output reg hq_v,output reg [HAW-1:0] hq_addr,
    output reg [2:0] hq_len,output reg [TG-1:0] hq_tag,
    input wire hq_cr,
    output reg ready,output reg fault
);
    wire [0:0] rn;
    ot_rst_relay #(.REGIONS(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
    initial if(W!=32)$fatal(1,"HC window leaf requires32 lanes");

    reg start_q,rel_q,start_qq,rel_qq,rv_q,re_q,credit_q;
    reg [HAW-1:0] base_q,soff_q,hbase;
    reg [CW-1:0] n_q,n_qq;
    reg [AW-1:0] bound_q,limit_q,addr_q;
    reg [TG-1:0] tag_q;reg[1:0]beat_q;
    always @(posedge clk)begin
        base_q<=c_base;soff_q<=c_soff;hbase<=base_q+soff_q;
        n_q<=c_nwords;n_qq<=n_q;bound_q<=c_bound;limit_q<=c_limit;
        addr_q<=rom_addr;tag_q<=hr_tag;beat_q<=hr_beat;
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
        .hr_v(rv_q&&tag_q[TG-1-:4]!=4'd8),.hr_rdy(),.hr_tag(tag_q[RTW-1:0]),.hr_beat(beat_q),.hr_data(256'd0),
        .rom_re(re_q&&select_q),.rom_addr(addr_q-bound_q),.rom_q(raw),.fault(wflt),.fault_why(why),
        .fetched_words(fetched),.received_sectors(received));
    reg [3:0] sf_q;
    always @(posedge clk)begin
        sf_q<=sector_fault;
        sector_addr<=7'(addr_q-bound_q);
        if(send)begin hq_addr<=wa;hq_len<=wl;hq_tag<={4'd0,(MUT==2)?wt^RTW'(1):wt};end
    end
    always @(posedge clk or negedge rn[0])begin
        if(!rn[0])begin credit<=1;hq_v<=0;sector_read<=0;sector_live<=0;ready<=0;fault<=0;end
        else begin
            if(send&&!credit_q)credit<=0;else if(!send&&credit_q)credit<=1;
            hq_v<=send;sector_read<=re_q&&select_q&&wrdy;
            if(start_qq)sector_live<=n_qq!=0;else if(rel_qq)sector_live<=0;
            ready<=n_qq==0||wrdy;
            if(wflt||(|sf_q)||(credit_q&&credit&&!send))fault<=1;
        end
    end
endmodule

module ot_hgi_hc_win_sector #(parameter integer MUT=0)(
 input wire clk,rst_n,live,input wire[1:0]sid,
 input wire hr_v,input wire [10:0]hr_tag,input wire [1:0]hr_beat,
 input wire[127:0]hr_data_lo,hr_data_hi,
 input wire read_v,input wire[6:0]read_addr,
 output reg rom_v,output wire[127:0]rom_lo,rom_hi,output reg fault
);
 reg[255:0]rom_data;assign {rom_hi,rom_lo}=rom_data;
 wire[0:0]rn;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
 reg live_q,hr_q,re_q;reg[1:0]sid_q;reg[10:0]tag_q;reg[1:0]beat_q;reg[255:0]data_q;reg[6:0]addr_q;
 always @(posedge clk)begin sid_q<=sid;tag_q<=hr_tag;beat_q<=hr_beat;data_q<={hr_data_hi,hr_data_lo};addr_q<=read_addr;end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin live_q<=0;hr_q<=0;re_q<=0;end
  else begin live_q<=live;hr_q<=hr_v;re_q<=read_v;end
 end
 wire write=hr_q&&live_q&&tag_q[10:7]!=4'd8&&beat_q==sid_q;
 wire[255:0]raw;
 ot_sram_1r1w_128x256_m1_r2c2 u_mem(.clk(clk),.r_ce_in(re_q),.r_addr_in(addr_q),.rd_out(raw),
  .w_ce_in(write),.w_addr_in({2'd0,tag_q[4:0]}),.wd_in(data_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 reg[255:0]capture;reg v1,v2;
 always @(posedge clk)begin capture<=raw;rom_data<=(capture&{256{v2}})^((MUT==1&&v2)?256'd1:256'd0);end
 always @(posedge clk or negedge rn[0])begin
  if(!rn[0])begin v1<=0;v2<=0;rom_v<=0;fault<=0;end
  else begin v1<=re_q;v2<=v1;rom_v<=v2;if(hr_q&&!live_q&&tag_q[10:7]!=4'd8)fault<=1;end
 end
endmodule

module ot_hgi_hc_win_partitioned #(parameter integer MUT=0)(
 input wire clk_ctl,clk_mem0,clk_mem1,clk_mem2,clk_mem3,rst_n,
 input wire c_start,c_rel,input wire[34:0]c_base,c_soff,input wire[5:0]c_nwords,
 input wire[15:0]c_bound,c_limit,input wire hr_v,input wire[10:0]hr_tag,input wire[1:0]hr_beat,
 input wire[127:0]hr_data_lo,hr_data_hi,input wire rom_re,input wire[15:0]rom_addr,
 output wire rom_v,output wire[127:0]rom_0,rom_1,rom_2,rom_3,rom_4,rom_5,rom_6,rom_7,
 output wire hq_v,output wire[34:0]hq_addr,output wire[2:0]hq_len,output wire[10:0]hq_tag,
 input wire hq_cr,output wire ready,fault
);
 wire rv,live;wire[6:0]ra;wire[3:0]sf,sv;wire[1023:0]data;
 ot_hgi_hc_win_ctl #(.MUT(MUT))u_ctl(.clk(clk_ctl),.rst_n(rst_n),.c_start(c_start),.c_rel(c_rel),
  .c_base(c_base),.c_soff(c_soff),.c_nwords(c_nwords),.c_bound(c_bound),.c_limit(c_limit),
  .hr_v(hr_v),.hr_tag(hr_tag),.hr_beat(hr_beat),.rom_re(rom_re),.rom_addr(rom_addr),
  .sector_read(rv),.sector_live(live),.sector_addr(ra),.sector_fault(sf),
  .hq_v(hq_v),.hq_addr(hq_addr),.hq_len(hq_len),.hq_tag(hq_tag),.hq_cr(hq_cr),.ready(ready),.fault(fault));
 wire[3:0]ck={clk_mem3,clk_mem2,clk_mem1,clk_mem0};
 for(genvar s=0;s<4;s=s+1)begin:g_sector
  ot_hgi_hc_win_sector #(.MUT((s==0)?MUT:0))u_data(.clk(ck[s]),.rst_n(rst_n),.live(live),.sid(2'(s)),
   .hr_v(hr_v),.hr_tag(hr_tag),.hr_beat(hr_beat),.hr_data_lo(hr_data_lo),.hr_data_hi(hr_data_hi),
   .read_v(rv),.read_addr(ra),.rom_v(sv[s]),.rom_lo(data[s*256+:128]),.rom_hi(data[s*256+128+:128]),.fault(sf[s]));
 end
 assign rom_v=sv[0];assign {rom_7,rom_6,rom_5,rom_4,rom_3,rom_2,rom_1,rom_0}=data;
endmodule
`default_nettype wire
