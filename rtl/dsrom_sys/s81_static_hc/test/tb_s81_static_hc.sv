`timescale 1ns/1ps
module tb_s81_static_hc;
 import ot_fp32_rne_pkg::*;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,slot=0;reg[3:0]rank_valid=0;reg[2047:0]rank_data=0;
 reg[31:0]tag=0;reg[15:0]seq=0;reg last=0;
 wire word_valid,word_error,fault,word_last;
 wire[511:0]word_data;wire[31:0]word_tag;wire[15:0]word_seq;
 s81_static_hc_reduce #(.MUT(MUT==1)) dut(.*);
 reg pack_en=1,emit_slot=0;reg[31:0]emit_tag=0;
 wire row_valid,row_fault;wire[8191:0]row_data;wire[31:0]row_tag;
 s81_static_hc_assemble #(.MUT(MUT==2)) pack(.clk(clk),.rst_n(rst_n),
  .write_slot(pack_en&&word_valid),.word_valid(pack_en&&word_valid),.word_index(word_seq[3:0]),
  .word_data(word_data),.word_tag(word_tag),.word_error(word_error),.emit_slot(emit_slot),.emit_tag(emit_tag),
  .row_valid(row_valid),.row_data(row_data),.row_tag(row_tag),.fault(row_fault));
 always @(posedge clk)begin
  emit_slot<=pack_en&&word_valid&&(word_seq[3:0]==15);
  emit_tag<=word_tag;
 end
 reg[511:0]expected[0:2047];reg[48:0]ids[0:2047];reg errs[0:2047];integer edges[0:2047];
 reg[8191:0]rows[0:19];integer rowedges[0:19];
 integer cyc=0,put=0,get=0,gotrows=0,lan,i,j,r,n,edge_due;
 reg[33:0]x,y,z;reg[511:0]want;reg want_err;
 integer seed=32'h71c4;
 reg[31:0]a;
 always @(posedge clk)begin
  cyc=cyc+1;
  if(rst_n&&slot&&rank_valid==15)begin
   want=0;want_err=0;
   for(lan=0;lan<16;lan=lan+1)begin
    x=fp32_add_rne(rank_data[lan*32+:32],rank_data[512+lan*32+:32]);
    y=fp32_add_rne(rank_data[1024+lan*32+:32],rank_data[1536+lan*32+:32]);
    z=fp32_add_rne(x[31:0],y[31:0]);
    want[lan*32+:32]=z[31:0];want_err=want_err||(|x[33:32])||(|y[33:32])||(|z[33:32]);
   end
   expected[put]=want;errs[put]=want_err;ids[put]={tag,seq,last};edges[put]=cyc+17;
   if(put<320)begin rows[put/16][(put%16)*512+:512]=want; if(put%16==15)rowedges[put/16]=cyc+19;end
   put=put+1;
  end
  #1;
  if(rst_n)begin
   if(word_valid)begin
    if(get>=put)$fatal(1,"unexpected result");
    if(cyc!=edges[get])$fatal(1,"latency got %0d want %0d",cyc,edges[get]);
    if(word_data!==expected[get]||word_error!==errs[get]||{word_tag,word_seq,word_last}!==ids[get])
     $fatal(1,"word mismatch item %0d got=%h want=%h error=%b/%b",get,word_data,expected[get],word_error,errs[get]);
    get=get+1;
   end else if(get<put&&cyc==edges[get])$fatal(1,"missing fixed output item %0d",get);
   if(row_valid)begin
    if(cyc!=rowedges[gotrows])$fatal(1,"row latency got %0d want %0d",cyc,rowedges[gotrows]);
    if(gotrows>=20||row_data!==rows[gotrows]||row_tag!==(32'h12340000+gotrows))$fatal(1,"row mismatch %0d",gotrows);
    gotrows=gotrows+1;
   end
  end
 end
 task drive(input integer number,input integer phase);
 begin
  @(negedge clk);slot=1;rank_valid=15;seq=number;last=(number%16==15);tag=32'h12340000+number/16;
  for(integer rr=0;rr<4;rr=rr+1)for(integer ll=0;ll<16;ll=ll+1)begin
   a=$random(seed);
   // Production finite exponent spread, cancellation, tiny/subnormal and signed zero.
   a={a[31],8'(80+(a[7:0]%80)),a[22:0]};
   if(number%17==0)a=(rr==0)?32'h4b800000:(rr==1)?32'h3f800000:(rr==2)?32'hcb800000:32'h3f800000;
   if(number%19==0)a=(rr<2)?32'h00000001:32'h80000001;
   if(number%23==0)a=32'h80000000;
   if(phase==1)begin
    case(number%8)
     0:a=(rr<2)?32'h7f7fffff:0; // inner overflow must reach output error
     1:a=(rr==0)?32'h7fc00001:32'h3f800000;
     2:a=(rr==2)?32'h7f800000:0;
     3:a=(rr==0)?32'h00800000:32'h807fffff;
     default:a=$random(seed);
    endcase
   end
   rank_data[rr*512+ll*32+:32]=a;
  end
 end
 endtask
 task idle;begin @(negedge clk);slot=0;rank_valid=0;end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  // Full D5120=320-record source mechanism, repeated20rows, actual link cadence4/4/8.
  for(n=0;n<320;n=n+1)begin
   drive(n,0);
   for(j=0;j<((n%3==2)?7:3);j=j+1)idle();
  end
  repeat(24)idle();
  if(gotrows!=20||row_fault||fault)$fatal(1,"production rows %0d faults %b/%b",gotrows,row_fault,fault);
  pack_en=0;
  // Pipeline sustained II1 stress + finite/error corpus, while production cadence was checked above.
  for(n=320;n<832;n=n+1)drive(n,1);
  repeat(24)idle();
  if(put!=832||get!=put||!fault)$fatal(1,"word accounting or missing arithmetic sticky fault");
  // Compiler source violation: scheduled rank absent -> fault and no word.
  @(negedge clk);rst_n=0;repeat(2)idle();rst_n=1;
  @(negedge clk);slot=1;rank_valid=7;
  idle();repeat(24)idle();
  if(!fault||word_valid)$fatal(1,"missing rank must fault without variable wait");
  $display("PASS static HC: 832 exact words,20 full8192bit rows, pipeline18regs/sampleedge+17, FMT1cadence4/4/8 and II1, arithmetic+missingrank fault");
  $finish;
 end
endmodule
