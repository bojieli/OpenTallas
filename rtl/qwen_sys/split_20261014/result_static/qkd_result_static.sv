`timescale 1ns/1ps
// One producer-local retention register and one registered transport hop.
// Ages are compiler inputs, NOT measured/guessed physical sign-off calendars.
module qkd_result_node #(
 parameter integer BEAT=0, CAPTURE_AGE=8, INJECT_AGE=25, DATA_MUT=0
)(input wire ck,rst_n,cmd_v,input wire[15:0]cmd_epoch,input wire[5:0]cmd_layer,
 input wire producer_v,input wire[15:0]producer_epoch,input wire[5:0]producer_layer,input wire[511:0]producer_data,
 input wire upstream_v,input wire[547:0]upstream_record,
 output reg out_v,output reg[547:0]out_record,output reg fault);
 reg active,seen,sent;reg[31:0]age;reg[15:0]epoch;reg[5:0]layer;reg[547:0]held;
 wire capture=active&&age==CAPTURE_AGE;
 wire inject=active&&age==INJECT_AGE;
 initial begin
  if(CAPTURE_AGE<0||INJECT_AGE<=CAPTURE_AGE||BEAT<0||BEAT>31)$fatal(1,"invalid compiled result ages");
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin active<=0;seen<=0;sent<=0;age<=0;epoch<=0;layer<=0;held<=0;out_v<=0;out_record<=0;fault<=0;end
  else begin
   out_v<=upstream_v;out_record<=upstream_record;
   if(active)age<=age+1;
   if(cmd_v)begin
    if((active&&!sent)||producer_v||cmd_layer>=36)fault<=1;
    active<=1;age<=0;seen<=0;sent<=0;epoch<=cmd_epoch;layer<=cmd_layer;
   end else begin
    if(producer_v!=capture)fault<=1;
    if(capture)begin
     if(producer_v&&producer_epoch==epoch&&producer_layer==layer)begin
      held<={5'd0,4'd3,layer,epoch,5'(BEAT),producer_data ^ (512'(DATA_MUT))};seen<=1;
     end else fault<=1;
    end
    if(inject)begin
     sent<=1;
     if(!seen||upstream_v)fault<=1;
     out_v<=seen;out_record<=held;
    end
   end
  end
 end
endmodule

// A scheduled two-input merge has one output register. No arrival arbitration.
module qkd_result_merge #(
 parameter integer A_FIRST=32,A_COUNT=8,B_FIRST=40,B_COUNT=8
)(input wire ck,rst_n,cmd_v,input wire av,bv,input wire[547:0]ar,br,
 output reg ov,output reg[547:0]record_out,output reg fault);
 reg active;reg[31:0]age;
 wire aslot=active&&age>=A_FIRST&&age<A_FIRST+A_COUNT;
 wire bslot=active&&age>=B_FIRST&&age<B_FIRST+B_COUNT;
 initial if(A_FIRST+A_COUNT>B_FIRST)$fatal(1,"overlapping compiled result merge slots");
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin active<=0;age<=0;ov<=0;record_out<=0;fault<=0;end
  else begin
   ov<=0;
   if(active)age<=age+1;
   if(cmd_v)begin
    if(active&&age<B_FIRST+B_COUNT)fault<=1;
    active<=1;age<=0;
    if(av||bv)fault<=1;
   end else begin
    if(av!=aslot||bv!=bslot)fault<=1;
    ov<=aslot?av:(bslot?bv:1'b0);
    if(aslot)record_out<=ar;
    if(bslot)record_out<=br;
   end
  end
 end
endmodule

// Physical decomposition: 32 node masters, 3 binary merge masters, no
// 16384-bit central mux. Node b=8*h+n remains adjacent to join producer b.
// This logical composition does not claim routed hop lengths or clock phase.
// CAPTURE_AGES packs 32 compiler ages; STACK_FIRST packs four output ages.
module qkd_result_static #(
 parameter [1023:0] CAPTURE_AGES={32{32'd8}},
 parameter [127:0] STACK_FIRST={32'd56,32'd48,32'd40,32'd32},
 parameter integer DATA_MUT=0
)(input wire[31:0]clk_node,input wire[2:0]clk_merge,input wire rst_n,
 input wire[31:0]cmd_v,input wire[511:0]cmd_epoch,input wire[191:0]cmd_layer,
 input wire merge_cmd_v,
 input wire[31:0]producer_v,input wire[511:0]producer_epoch,input wire[191:0]producer_layer,input wire[16383:0]producer_data,
 output wire result_v,output wire[547:0]result_record,output wire fault);
 initial begin
  if(STACK_FIRST[32+:32]!=STACK_FIRST[0+:32]+8 ||
     STACK_FIRST[64+:32]!=STACK_FIRST[32+:32]+8 ||
     STACK_FIRST[96+:32]!=STACK_FIRST[64+:32]+8)
   $fatal(1,"result stack windows must be consecutive compiled groups of eight");
 end
 wire[31:0]nv,nf;wire[547:0]nr[0:31];
 wire[3:0]sv;wire[547:0]sr[0:3];
 genvar h,n;
 generate for(h=0;h<4;h=h+1)begin:stack
  for(n=0;n<8;n=n+1)begin:node
   localparam integer B=8*h+n;
   wire uv;wire[547:0]ur;
   if(n==0)begin assign uv=0;assign ur=0;end
   else begin assign uv=nv[B-1];assign ur=nr[B-1];end
   qkd_result_node #(.BEAT(B),.CAPTURE_AGE(CAPTURE_AGES[B*32+:32]),
    .INJECT_AGE(STACK_FIRST[h*32+:32]+2*n-7),.DATA_MUT((B==17)?DATA_MUT:0))u(
    .ck(clk_node[B]),.rst_n(rst_n),.cmd_v(cmd_v[B]),.cmd_epoch(cmd_epoch[B*16+:16]),.cmd_layer(cmd_layer[B*6+:6]),
    .producer_v(producer_v[B]),.producer_epoch(producer_epoch[B*16+:16]),.producer_layer(producer_layer[B*6+:6]),.producer_data(producer_data[B*512+:512]),
    .upstream_v(uv),.upstream_record(ur),.out_v(nv[B]),.out_record(nr[B]),.fault(nf[B]));
  end
  assign sv[h]=nv[8*h+7];assign sr[h]=nr[8*h+7];
 end endgenerate
 wire av,bv,af,bf,rf;wire[547:0]ar,br;
 // Nonblocking registered outputs are sampled on the following edge.
 qkd_result_merge #(.A_FIRST(STACK_FIRST[0+:32]+1),.B_FIRST(STACK_FIRST[32+:32]+1))ma(
 .ck(clk_merge[0]),.rst_n(rst_n),.cmd_v(merge_cmd_v),.av(sv[0]),.bv(sv[1]),.ar(sr[0]),.br(sr[1]),.ov(av),.record_out(ar),.fault(af));
 qkd_result_merge #(.A_FIRST(STACK_FIRST[64+:32]+1),.B_FIRST(STACK_FIRST[96+:32]+1))mb(
 .ck(clk_merge[1]),.rst_n(rst_n),.cmd_v(merge_cmd_v),.av(sv[2]),.bv(sv[3]),.ar(sr[2]),.br(sr[3]),.ov(bv),.record_out(br),.fault(bf));
 qkd_result_merge #(.A_FIRST(STACK_FIRST[0+:32]+2),.A_COUNT(16),.B_FIRST(STACK_FIRST[64+:32]+2),.B_COUNT(16))mr(
 .ck(clk_merge[2]),.rst_n(rst_n),.cmd_v(merge_cmd_v),.av(av),.bv(bv),.ar(ar),.br(br),.ov(result_v),.record_out(result_record),.fault(rf));
 assign fault=(|nf)||af||bf||rf;
endmodule
