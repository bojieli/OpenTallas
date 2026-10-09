`timescale 1ns/1ps
module tb_hgi_coll_row_formatter;
 parameter integer MUT_OWNER=0,MUT_ORDER=0,MUT_WRITTEN=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,sv=0,iv=0,rr=0,rv=0,ow=0,dr=0,written=1;
 reg [7:0] g=96,b=8,dest=8;reg [19:0] k=0,id=0;
 reg [15:0] words=0;reg [511:0] data=0;
 wire sr,ir,req,rspready,ov,done,fault;
 wire [7:0] owner,odest;wire [19:0] localrow,oi;
 wire [15:0] word_,oword;wire [511:0] odata;
 ot_hgi_coll_row_formatter #(.ENABLE(1),.MUT_OWNER(MUT_OWNER),.MUT_ORDER(MUT_ORDER),.MUT_WRITTEN(MUT_WRITTEN)) dut
 (.clk(clk),.rst_n(rst_n),.start_v(sv),.start_r(sr),.group_size(g),.owner_block(b),.destinations(dest),
 .row_count(k),.row_words(words),.id_v(iv),.id_r(ir),.id(id),.read_v(req),.read_r(rr),
 .read_owner(owner),.read_local_row(localrow),.read_word(word_),.response_v(rv),.response_r(rspready),
 .response_data(data),.response_written(written),.out_v(ov),.out_r(ow),.out_data(odata),
 .out_index(oi),.out_word(oword),.out_destinations(odest),.done_v(done),.done_r(dr),.fault(fault));
 integer totalrows=0,totalwords=0,calls=0,cycles=0;
 always @(posedge clk)cycles=cycles+1;
 function [511:0] payload(input integer r,l,w);
  integer j;begin for(j=0;j<16;j=j+1)payload[j*32+:32]=(r*73471)^(l*104729)^(w*155921)^j;end
 endfunction
 task wait_req;integer n;begin n=0;while(!req)begin @(negedge clk);n=n+1;if(n>100)$fatal(1,"mapping stalled");end end endtask
 task call;
 input integer G,B,K,W,D,badrow;
 integer i,j,sel,expect_owner,expect_local,startcycle;reg [511:0] expected;
 begin
  @(negedge clk);g=G;b=B;k=K;words=W;dest=D;sv=1;startcycle=cycles;
  if(!sr)$fatal(1,"start notready");@(negedge clk);sv=0;
  for(i=0;i<K;i=i+1)begin
   if(!ir)$fatal(1,"ID notready");sel=(i*977+13)%1048576;id=sel;iv=1;
   @(negedge clk);iv=0;
   expect_owner=(sel/B)%G;expect_local=(sel/(B*G))*B+sel%B;
   for(j=0;j<W;j=j+1)begin
    wait_req();
    if(owner!=expect_owner||localrow!=expect_local||word_!=j)$fatal(1,"owner/local/word mismatch g%0d b%0d idx%0d got%0d/%0d/%0d expected%0d/%0d/%0d",G,B,i,owner,localrow,word_,expect_owner,expect_local,j);
    // Current reader fixture uses its real owner/local-row/word request and
    // provides a written flag; unwritten response must not leak a payload.
    expected=payload(expect_owner,expect_local,j);rr=1;
    @(negedge clk);rr=0;data=payload(owner,localrow,word_);written=(i!=badrow);rv=1;
    if(!rspready)$fatal(1,"response notready");@(negedge clk);rv=0;
    if(i==badrow)begin
     if(!done || !fault || ov)$fatal(1,"unwritten row leaked instead of fault");
     j=W;i=K;
    end else begin
     if(!ov || fault || odata!==expected || oi!=i || oword!=j || odest!=D)$fatal(1,"payload/list-order/count mismatch");
     repeat(2)begin
      @(negedge clk);data=~data;
      if(!ov||req||odata!==expected||oi!=i||oword!=j)$fatal(1,"output backpressure changed held payload");
     end
     ow=1;@(negedge clk);ow=0;totalwords=totalwords+1;
    end
   end
   totalrows=totalrows+1;
  end
  if(!done || (fault!=(badrow>=0)))$fatal(1,"completion/fault mismatch");
  $display("CALL G=%0d B=%0d K=%0d W=%0d destinations=%0d badrow=%0d cycles=%0d",G,B,K,W,D,badrow,cycles-startcycle);
  dr=1;@(negedge clk);dr=0;calls=calls+1;
 end
 endtask
 integer gg;reg [7:0] groups[0:4];
 initial begin
  groups[0]=1;groups[1]=2;groups[2]=4;groups[3]=8;groups[4]=96;
  repeat(2)@(negedge clk);rst_n=1;
  for(gg=0;gg<5;gg=gg+1)begin
   call(groups[gg],8,7,32,groups[gg],-1);
   call(groups[gg],8,512,32,groups[gg],-1);
   call(groups[gg],8,2048,32,groups[gg],-1);
   call(groups[gg],3,7,2,groups[gg],-1);
   call(groups[gg],255,7,2,groups[gg],-1);
   call(groups[gg],8,7,32,groups[gg],3);
  end
  $display("PASS HGI ROW_GATHER calls=%0d rows=%0d words=%0d cycles=%0d k7/512/2048 G1/2/4/8/96 B8/3/255 payloadorder/written/backpressure",calls,totalrows,totalwords,cycles);$finish;
 end
endmodule
