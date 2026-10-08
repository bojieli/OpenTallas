`timescale 1ns/1ps
// Opt-in SRAM payload SECDED wrapper. Original controller/macro geometry unchanged.
// Two encode edges before publishing receipt; two elastic decode stages after
// the original three-entry output queue. Mutable-control sealing is separate.
module ot_hbrom_bulk_copy_protected #(
 parameter integer PROTECT=0,ENABLE=1,LINE_BITS=1088,DEPTH=1024,MAX_OUT=512,
 parameter integer AW=32,DQ=4,SRAM_RING=1,RING_MACRO=1
)(input wire clk,rst_n,input wire d_valid,output wire d_ready,
 input wire[AW-1:0]d_base,input wire[23:0]d_lines,
 output wire req_v,input wire req_ready,output wire[AW-1:0]req_addr,
 output wire[$clog2(DEPTH)-1:0]req_tag,
 input wire rsp_v,input wire[$clog2(DEPTH)-1:0]rsp_tag,input wire[LINE_BITS-1:0]rsp_data,
 output wire s_valid,input wire s_ready,output wire[LINE_BITS-1:0]s_data,
 output wire[$clog2(MAX_OUT+1)-1:0]outstanding,output wire idle,output wire fault);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbrom_secded_pipeline_pkg::*;
 generate if(PROTECT==0)begin:g_legacy
  assign fault=1'b0;
  ot_hbm_accel_bulk_copy #(.ENABLE(ENABLE),.LINE_BITS(LINE_BITS),.DEPTH(DEPTH),.MAX_OUT(MAX_OUT),
   .AW(AW),.DQ(DQ),.SRAM_RING(SRAM_RING),.RING_MACRO(RING_MACRO)) legacy(
   .clk(clk),.rst_n(rst_n),.d_valid(d_valid),.d_ready(d_ready),.d_base(d_base),.d_lines(d_lines),
   .req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),
   .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),.s_valid(s_valid),.s_ready(s_ready),.s_data(s_data),
   .outstanding(outstanding),.idle(idle));
 end else begin:g_protected
  if(LINE_BITS!=1088||DEPTH!=1024||MAX_OUT!=512||SRAM_RING!=1||RING_MACRO!=1||ENABLE!=1)
   initial $fatal(1,"protected ring requires priced1024/512,1088bit,even/oddSRAM shape");
  localparam integer WORDS=17,CODE_BITS=1224,TW=$clog2(DEPTH);
  reg[1:0]ev;reg[TW-1:0]tag1,tag2;
  wire[CODE_BITS-1:0]encoded,raw;
  wire raw_v,raw_r,raw_idle,core_req_v,core_d_ready;
  reg v1,v2,bad;
  (* keep = "true", dont_touch = "yes" *) reg[1:0] ev_shadow;
  (* keep = "true", dont_touch = "yes" *) reg[TW-1:0]tag1_shadow,tag2_shadow;
  (* keep = "true", dont_touch = "yes" *) reg v1_shadow,v2_shadow,bad_shadow;
  wire codec_control_bad=(ev_shadow!==~ev)||(tag1_shadow!==~tag1)||(tag2_shadow!==~tag2)||
    (v1_shadow!==~v1)||(v2_shadow!==~v2)||(bad_shadow!==~bad);
  wire core_control_fault;
  wire stop=bad||codec_control_bad||core_control_fault;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin ev_shadow<=2'b11;tag1_shadow<={TW{1'b1}};tag2_shadow<={TW{1'b1}};v1_shadow<=1;v2_shadow<=1;bad_shadow<=1;end
   else begin
    ev_shadow<={ev_shadow[0],~(rsp_v&&!stop)};
    tag1_shadow<=~rsp_tag;tag2_shadow<=tag1_shadow;
    if(step1)v1_shadow<=~(raw_v&&!stop);
    if(step2)v2_shadow<=~(v1&&!stop&&!(|ue));
    if(codec_control_bad||(v1&&(|ue)))bad_shadow<=0;
   end
  wire step2=!v2||s_ready;
  wire step1=!v1||step2;
  wire[WORDS-1:0]ue;
  wire[LINE_BITS-1:0]decoded2;
  assign fault=stop;
  assign raw_r=step1&&!stop;
  assign req_v=core_req_v&&!stop;
  assign d_ready=core_d_ready&&!stop;
  assign s_valid=v2&&!stop;
  assign s_data=decoded2;
  assign idle=raw_idle&&!(|ev)&&!v1&&!v2;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin ev<=0;v1<=0;v2<=0;bad<=0;end
   else begin
    ev<={ev[0],rsp_v&&!stop};
    if(step1)v1<=raw_v&&!stop;
    if(step2)v2<=v1&&!stop&&!(|ue);
    if(codec_control_bad||(v1&&(|ue)))bad<=1;
   end
  always @(posedge clk or negedge rst_n)if(!rst_n)begin tag1<=0;tag2<=0;end else begin tag1<=rsp_tag;tag2<=tag1;end
  genvar w;
  for(w=0;w<WORDS;w=w+1)begin:g_word
   reg[71:0]e1,e2;reg[79:0]d1;reg[63:0]d2;
   wire[65:0]fixed_word=correct72(d1[71:0],d1[79:72]);
   always @(posedge clk)begin
    e1<=encode64(rsp_data[w*64+:64])&{1'b0,{71{1'b1}}};e2<={^e1[70:0],e1[70:0]};
    if(step1)d1<={check72(raw[w*72+:72]),raw[w*72+:72]};
    if(step2)d2<=fixed_word[63:0];
   end
   assign encoded[w*72+:72]=e2;
   assign ue[w]=fixed_word[65];assign decoded2[w*64+:64]=d2;
  end
  ot_hbrom_bulk_copy_control_protected #(.PROTECT(1),.ENABLE(1),.LINE_BITS(CODE_BITS),.DEPTH(DEPTH),.MAX_OUT(MAX_OUT),
   .AW(AW),.DQ(DQ),.SRAM_RING(1),.RING_MACRO(1)) core(
   .clk(clk),.rst_n(rst_n),.d_valid(d_valid&&!stop),.d_ready(core_d_ready),.d_base(d_base),.d_lines(d_lines),
   .req_v(core_req_v),.req_ready(req_ready&&!stop),.req_addr(req_addr),.req_tag(req_tag),
   .rsp_v(ev[1]&&!stop),.rsp_tag(tag2),.rsp_data(encoded),.s_valid(raw_v),.s_ready(raw_r),.s_data(raw),
   .outstanding(outstanding),.idle(raw_idle),.control_fault(core_control_fault));
 end endgenerate
endmodule
