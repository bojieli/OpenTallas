`timescale 1ns/1ps
module tb_s81_primary_shared_last;
 reg clk=0;always #0.555555 clk=~clk;
 reg stream_clk=0;always #0.416667 stream_clk=~stream_clk;
`ifdef PRIMARY_ASYNC
 wire source_clk=stream_clk;
`else
 wire source_clk=clk;
`endifreg rst_n=0;
 reg p_valid=0,s_valid=0,out_ready=0;wire p_ready,s_ready;
 reg[511:0] p_data=0,s_data=0;reg[73:0] p_tag=0,s_tag=0;
 reg[6:0] p_word=0,s_word=0;reg p_last=0,s_last=0;
 wire out_valid,out_last,busy,fault,context_done;wire[511:0] out_data;
 wire[73:0] out_tag;wire[6:0] out_word;
 `ifdef PRIMARY_ASYNC
 ot_s81_primary_shared_receive #(.ENABLE(1)) dut(.serial_clk(clk),.*);
`else
 ot_s81_primary_shared_last #(.ENABLE(1)) dut(.*);
`endif
 reg[511:0] prefix[0:1919],shared[0:1919],expected[0:1919];
 string vectors;integer bad=0,cycles=0,c,pn=0,sn=0,on=0,done=0,start=0,total=0;
 reg[511:0] held;reg[81:0] heldmeta;reg stalled=0;
 function automatic[73:0] tag(input integer ctx);
  tag={3'(ctx%5),2'(ctx%4),2'(ctx%3),4'd13,21'd1048575,10'd513,32'(32'hdead0000+ctx)};
 endfunction
 always @(posedge clk)if(rst_n)begin
  cycles=cycles+1;

  if(out_valid&&out_ready)begin
   if(out_data!==expected[c*80+on]||out_tag!==tag(c)||out_word!==on||out_last!=(on==79))
    $fatal(1,"numeric/context mismatch ctx%0d word%0d got%h exp%h",c,on,out_data[31:0],expected[c*80+on][31:0]);
   on=on+1;
  end
  if(out_valid&&!out_ready)begin
   if(stalled&&(held!==out_data||heldmeta!=={out_last,out_word,out_tag}))$fatal(1,"stalledoutput altered");
   held=out_data;heldmeta={out_last,out_word,out_tag};stalled=1;
  end else stalled=0;
  if(context_done)done=done+1;
 end
 always @(posedge source_clk)if(rst_n)begin
  if(p_valid&&p_ready)pn=pn+1;
  if(s_valid&&s_ready)sn=sn+1;
 end
 initial begin
  if(!$value$plusargs("vectors=%s",vectors))$fatal(1,"missing vectors");
  if($value$plusargs("bad=%d",bad))begin end
  $readmemh({vectors,"/prefix.hex"},prefix);$readmemh({vectors,"/shared.hex"},shared);$readmemh({vectors,"/expected.hex"},expected);
  repeat(4)@(negedge source_clk);rst_n=1;@(negedge source_clk);
  if(bad==5)begin
   c=0;pn=0;sn=0;out_ready=0;
   while(pn<5||sn<5)begin
    p_valid=pn<5;s_valid=sn<5;p_tag=tag(0);s_tag=tag(0);
    p_word=pn;s_word=sn;p_last=0;s_last=0;
    p_data=prefix[pn];s_data=shared[sn];@(negedge source_clk);
   end
   p_valid=0;s_valid=0;rst_n=0;repeat(6)@(negedge source_clk);
   rst_n=1;repeat(30)@(negedge source_clk);
   if(fault||busy||out_valid)$fatal(1,"commonreset retainedpartialcontext");
   $display("PRIMARY_SHARED_LAST partialcommonreset flushed PASS");$finish;
  end
  if(bad!=0)begin
   c=0;p_valid=1;s_valid=1;p_data=prefix[0];s_data=shared[0];p_tag=tag(0);s_tag=tag(0);
   if(bad==1)s_tag[32]=!s_tag[32];
   if(bad==2)s_data[0]=1;
   if(bad==3)s_last=1;
   if(bad==4)p_word=1;
   repeat(40)@(negedge source_clk);
   if(!fault||out_valid)$fatal(1,"invalidnative input not rejected");
   $display("PRIMARY_SHARED_LAST negative%0d rejected PASS",bad);$finish;
  end
  for(c=0;c<24;c=c+1)begin
   pn=0;sn=0;on=0;start=cycles;
   while(on<80)begin
    p_valid=pn<80&&cycles%5!=0;s_valid=sn<80&&cycles%7!=0;out_ready=cycles%11>2;
    p_tag=tag(c);s_tag=tag(c);p_word=pn;s_word=sn;p_last=pn==79;s_last=sn==79;
    if(pn<80)p_data=prefix[c*80+pn];if(sn<80)s_data=shared[c*80+sn];
    @(negedge source_clk);if(fault)$fatal(1,"positiveconsumer fault ctx%0d",c);
   end
   p_valid=0;s_valid=0;repeat(4)@(negedge clk);total=total+cycles-start;
   if(busy||done!=c+1)$fatal(1,"actualfinalhandshake failedcontextretire");
  end
  $display("PRIMARY_SHARED_LAST fullshape PASS contexts24 TP4rank1280 values30720 frames1920 sharedLAST roundingonce cycles%0d",total);$finish;
 end
 initial begin #1000000;$fatal(1,"minimummechanism deadlock");end
endmodule
