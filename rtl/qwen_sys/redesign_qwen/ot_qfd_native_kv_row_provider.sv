`timescale 1ns/1ps
// Candidate wrapper reuses the REAL sequencer store/FIFO/half-row assembly.
// One finite epoch; formatter words must be the actual SU-derived encoded
// bytes. row_ready reserves ALL four landing seats. Store ACKs are separate
// tagged actual memory-write completion pulses, never a queue credit alias.
module ot_qfd_native_kv_row_provider #(parameter integer ENABLE=0,MUT_ROW=0,MUT_COMMIT=0)(
 input wire clk,rst_n,
 input wire begin_v,input wire [15:0] begin_epoch,input wire [5:0] begin_layer,input wire [17:0] begin_pos,
 output wire begin_ready,
 input wire word_v,input wire [10:0] word_tag,input wire [511:0] word_data,output wire word_ready,
 input wire formatter_emitted,
 output reg row_v,input wire row_ready,output reg row_kind,
 output reg [15:0] row_epoch,output reg [5:0] row_layer,output reg [17:0] row_pos,output reg [1023:0] row_data,
 input wire [3:0] ack_v,ack_kind,input wire [63:0] ack_epoch,input wire [23:0] ack_layer,input wire [71:0] ack_pos,
 output wire [3:0] ack_credit,output wire committed,output wire fault
);
 reg active,local_fault;reg [15:0] epoch;reg [5:0] layer;reg [17:0] pos;
 reg [7:0] received;reg [2:0] tag;reg [3:0] state;reg kind;
 wire wt=word_v&&word_ready,rt=row_v&&row_ready;
 wire fence_ready,fence_fault;
 wire [2047:0] store_kw;wire [1023:0] store_q;
 wire kpop=state==3;
 wire kwgo=state==8;
 assign begin_ready=ENABLE!=0&&(!active||committed)&&fence_ready&&!local_fault&&!row_v;
 assign word_ready=ENABLE!=0&&active&&state==0&&received!=8'h33&&!fault;
 assign fault=local_fault||fence_fault;
 // Store implementation itself captures the data pin and kpop/kwgo controls.
 ot_qkvd_seq_m_store #(.DW(512),.XS(40),.KD(8)) u_store(
 .clk(clk),.rst_n(rst_n),.x_v(wt),.x_cls(3'b010),.x_d(word_data),.qpop(1'b0),
 .kpop(kpop),.kidx(tag),.kwgo(kwgo),.kwn(kind?2'd2:2'd0),.q(store_q),.kw(store_kw));
 ot_qfd_native_kv_commit_fence #(.ENABLE(ENABLE),.MUT_OR(MUT_COMMIT)) u_commit(
 .clk(clk),.rst_n(rst_n),.begin_v(begin_v),.begin_epoch(begin_epoch),.begin_layer(begin_layer),.begin_pos(begin_pos),.begin_ready(fence_ready),
 .formatter_emitted(formatter_emitted&&active&&received==8'h33),.posted_v({4{rt}}),.posted_kind({4{row_kind}}),
 .posted_epoch({4{row_epoch}}),.posted_layer({4{row_layer}}),.posted_pos({4{row_pos}}),
 .ack_v(ack_v),.ack_kind(ack_kind),.ack_epoch(ack_epoch),.ack_layer(ack_layer),.ack_pos(ack_pos),.ack_credit(ack_credit),.committed(committed),.fault(fence_fault));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;local_fault<=0;epoch<=0;layer<=0;pos<=0;received<=0;tag<=0;state<=0;kind<=0;row_v<=0;row_kind<=0;row_epoch<=0;row_layer<=0;row_pos<=0;row_data<=0;end
  else if(ENABLE!=0)begin
   if(begin_v)begin
    if(!begin_ready)local_fault<=1;
    else begin active<=1;epoch<=begin_epoch;layer<=begin_layer;pos<=begin_pos;received<=0;state<=0;kind<=0;end
   end
   if(wt)begin
    if(word_tag[10:3]!=8'b01000000||word_tag[1]||received[word_tag[2:0]])local_fault<=1;
    else begin tag<=word_tag[2:0];received[word_tag[2:0]]<=1;state<=1;end
   end else if(state>=1&&state<6)state<=state+1'b1;
   else if(state==6)begin if(received==8'h33)begin state<=8;kind<=0;end else state<=0;end
   else if(state==8)state<=9;
   else if(state==9)state<=10;
   else if(state==10)state<=11;
   else if(state==11)begin
    row_v<=1;row_kind<=kind;row_epoch<=epoch;row_layer<=layer;row_pos<=pos;
    row_data<=MUT_ROW!=0?{store_kw[511:0],store_kw[1023:512]}:store_kw[1023:0];state<=12;
   end
   if(rt)begin row_v<=0;if(kind==0)begin kind<=1;state<=8;end else state<=13;end
   if(fault)row_v<=0;
  end
 end
endmodule
