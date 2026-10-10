`timescale 1ns/1ps
module tb_hgi_coll_slot_map;
 parameter integer MUT_ORDER=0;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,start=0,edone=0;
 reg [7:0] G=96,GB=0,R=77,D=96;
 reg [15:0] PF=162,W=9;
 reg [3:0] iv=0;reg [4*545-1:0] flit=0;
 wire [3:0] ov;wire [2047:0] od;wire [79:0] row_;wire [63:0] word_;
 wire done,fault;
 integer sent=0,got=0,cycle=0;reg [31:0] mem[0:55295];
 ot_hgi_coll_slot_map #(.ENABLE(1),.MUT_ORDER(MUT_ORDER)) dut(
  .clk(clk),.rst_n(rst_n),.start(start),.group_size(G),.group_base(GB),.rank(R),.destinations(D),
  .flits_per_rank(PF),.row_words(W),.in_v(iv),.in_flit(flit),.endpoint_done(edone),
  .out_v(ov),.out_data(od),.out_row(row_),.out_word(word_),.done(done),.fault(fault));
 function automatic[511:0] payload(input integer src,slot,w);
  for(integer a=0;a<16;a=a+1)payload[a*32+:32]=(a==0)?32'h80000000:(a==1)?32'h7fc12345:32'(src*100000+slot*100+w*16+a);
 endfunction
 always @(negedge clk) if(rst_n)begin
  cycle=cycle+1;
  for(integer l=0;l<4;l=l+1)if(ov[l])begin
   integer rr,ww,src,j;
   rr=row_[l*20+:20];ww=word_[l*16+:16];src=rr%G;j=rr/G;
   if(od[l*512+:512]!==payload(src,j,ww))$fatal(1,"slot-major data changed row=%0d word=%0d",rr,ww);
   if(mem[rr*W+ww]!=0)$fatal(1,"duplicate destination");mem[rr*W+ww]=1;
   got=got+1;
  end
 end
 task run(input integer grp,rank_,slots_,words_);
  integer src,j,w;
  begin
   G=grp;R=rank_;D=grp;W=words_;PF=slots_*words_;got=0;sent=0;
   for(integer t=0;t<55296;t=t+1)mem[t]=0;
   @(negedge clk);start=1;@(negedge clk);start=0;
   while(sent<G*PF)begin
    iv=0;
    for(integer l=0;l<4;l=l+1)if(sent<G*PF)begin
     src=sent/PF;j=(sent%PF)/W;w=sent%W;
     // Reverse source order exercises out-of-order wire arrival.
     src=G-1-src;
     flit[l*545+:545]={1'b1,8'hff,8'(src),16'(src*PF+j*W+w),payload(src,j,w)};
     iv[l]=1;sent=sent+1;
    end
    @(negedge clk);
   end
   iv=0;edone=1;@(negedge clk);edone=0;
   repeat(6)@(negedge clk);
   if(fault||got!=G*PF)$fatal(1,"map count fault=%0d got=%0d expected=%0d",fault,got,G*PF);
   $display("MAP EXACT G=%0d rank=%0d M=%0d words=%0d delivered=%0d",G,R,slots_,W,got);
  end
 endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  run(96,77,18,9);run(96,0,32,16);run(8,3,16,32);run(1,0,1,9);
  // Non-recipient rank drains the wire stream but publishes no rows.
  @(negedge clk);G=96;R=77;D=64;PF=9;W=9;start=1;
  @(negedge clk);start=0;iv=1;flit[0+:545]={1'b1,8'hff,8'd0,16'd0,payload(0,0,0)};
  @(negedge clk);iv=0;repeat(6)@(negedge clk);
  if(ov||fault)$fatal(1,"nonrecipient published");
  @(negedge clk);R=0;D=96;PF=9;W=9;start=1;
  @(negedge clk);start=0;iv=1;flit[0+:545]={1'b1,8'hff,8'd95,16'd0,payload(95,0,0)};
  @(negedge clk);iv=0;repeat(6)@(negedge clk);
  if(!fault)$fatal(1,"bad transaction identity accepted");
  $display("PASS HGI_SLOT_MAP fullshape transpose/nonrecipient/identity");$finish;
 end
endmodule
