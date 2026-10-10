`timescale 1ns/1ps
module tb_s81_engine_adapter #(parameter integer MUT=0, NEG=0, SAME=0);
 reg cc=0,ec=0,crst=0,erst=0;
 always #0.4166 cc=~cc;
 generate if(SAME) begin always #0.4166 ec=~ec;end
 else begin always #0.5555 ec=~ec;end endgenerate
 reg cv=0;reg[83:0] cd=0;wire dv;wire[7:0] dt;wire fault,online;
 wire ev;wire[83:0] ed;reg er=0,go=0,edv=0;reg[7:0] edt=0;
 ot_s81_engine_adapter #(.QD(8),.MUT(MUT)) dut(.c_clk(cc),.c_rst_n(crst),.c_cmd_v(cv),.c_cmd_d(cd),
 .c_done_v(dv),.c_done_tag(dt),.fault(fault),.online(online),.e_clk(ec),.e_rst_n(erst),.e_cmd_v(ev),.e_cmd_d(ed),
 .e_cmd_ready(er),.e_inputs_present(go),.e_done_v(edv),.e_done_tag(edt));
 function automatic[83:0] desc(input integer i);
 desc={1'(i%2),10'(613+i),21'(1048575-i),21'(62000+i),24'(24'habc001^i),7'(i)};
 endfunction
 integer cs=0,es=0,sent=0,starts=0,done=0,outstanding=0,errors=0,maxout=0,maxactive=0;
 integer due[0:255];reg[255:0] cseen=0,eseen=0,retired=0;
 integer sendat[0:255];integer first_cmd_latency=-1,first_visibility=-1,max_done_latency=0;integer doneat[0:255];
 wire[7:0] tag={ed[83],ed[6:0]};
 always @(posedge cc) if(crst&&erst) begin
 cs=cs+1;
 if(cv) begin cseen[{cd[83],cd[6:0]}]=1;sendat[{cd[83],cd[6:0]}]=cs;sent=sent+1;outstanding=outstanding+1;end
 if(dv) begin
  if(cs-doneat[dt]>max_done_latency)max_done_latency=cs-doneat[dt];
  if(!cseen[dt]||retired[dt]) errors=errors+1;
  else begin retired[dt]=1;outstanding=outstanding-1;done=done+1;end
 end
 if(outstanding>maxout)maxout=outstanding;
 end
 always @(negedge cc) if(crst&&erst&&NEG==0) begin
 cv=0;
 if(online&&sent<64&&outstanding<8)begin cv=1;cd=desc(sent);end
 end
 always @(posedge ec) if(crst&&erst) begin
 es=es+1;
 if(dut.cv&&first_visibility<0)first_visibility=cs-sendat[{dut.cd[83],dut.cd[6:0]}];
 if(ev&&er) begin
  if(ed!==desc(starts)||eseen[tag]||!go)errors=errors+1;
  if(starts==0)first_cmd_latency=cs-sendat[tag];
  eseen[tag]=1;due[tag]=es+1+(tag%7);starts=starts+1;
 end
 if(edv) begin eseen[edt]=0;doneat[edt]=cs;end
 if($countones(eseen)>maxactive)maxactive=$countones(eseen);
 end
 always @(negedge ec) if(crst&&erst&&NEG==0) begin
 edv=0;go=(cs>=40);er=(es%5!=1);
 if(go)for(integer t=255;t>=0;t=t-1)if(eseen[t]&&due[t]<=es)begin edv=1;edt=t;end
 end
 initial begin
 for(integer t=0;t<256;t=t+1)begin due[t]=0;sendat[t]=0;doneat[t]=0;end
 repeat(5)@(negedge cc);crst=1;repeat(3)@(negedge ec);erst=1;
 if(NEG==1) begin
  wait(online);@(negedge ec);edv=1;edt=8'h99;@(negedge ec);edv=0;
  repeat(16)@(negedge cc);
  $display("TB_S81_ENGINE_ADAPTER neg=orphan_done fault=%b done=%0d %s",fault,done,(fault&&done==0)?"PASS":"FAIL");
  if(!fault||done!=0)$fatal(1,"orphan accepted");$finish;
 end
 if(NEG==2)begin
  wait(online);for(integer i=0;i<9;i=i+1)begin @(negedge cc);cv=1;cd=desc(i);end
  @(negedge cc);cv=0;repeat(16)@(negedge cc);
  $display("TB_S81_ENGINE_ADAPTER neg=ninth_credit fault=%b %s",fault,fault?"PASS":"FAIL");
  if(!fault)$fatal(1,"ninth credit accepted");$finish;
 end
 if(NEG==3)begin
  wait(online);for(integer i=0;i<4;i=i+1)begin @(negedge cc);cv=1;cd=desc(i);end
  @(negedge cc);cv=0;repeat(12)@(negedge cc);
  @(negedge ec);erst=0;repeat(6)@(negedge cc);
  cseen=0;retired=0;eseen=0;sent=0;starts=0;done=0;outstanding=0;
  @(negedge ec);erst=1;wait(online);repeat(16)@(negedge cc);
  if(starts!=0||done!=0||fault)errors=errors+1;
  er=1;go=1;@(negedge cc);cv=1;cd=desc(0);@(negedge cc);cv=0;
  wait(starts==1);@(negedge ec);edv=1;edt=0;@(negedge ec);edv=0;
  repeat(24)@(negedge cc);
  if(done!=1||fault)errors=errors+1;
  $display("TB_S81_ENGINE_ADAPTER neg=reset_epoch start=%0d done=%0d errors=%0d fault=%b %s",starts,done,errors,fault,errors==0?"PASS":"FAIL");
  if(errors)$fatal(1,"reset epoch gate");$finish;
 end
 // This bounded cycle count detects protocol nonprogress on the small mechanism;
 // it is not a build/resource deadline. Faulted mutants cannot return credits.
 repeat(900)@(negedge cc);
 if(done!=64||starts!=64||sent!=64||fault||maxout!=8||maxactive<2)errors=errors+1;
 $display("TB_S81_ENGINE_ADAPTER mut=%0d same=%0d cmd=%0d start=%0d done=%0d errors=%0d fault=%b maxout=%0d maxactive=%0d first_dispatch_after_input_stall=%0d first_visibility=%0d max_done_visibility=%0d %s",MUT,SAME,sent,starts,done,errors,fault,maxout,maxactive,first_cmd_latency,first_visibility,max_done_latency,errors==0?"PASS":"FAIL");
 $finish;
 end
endmodule
