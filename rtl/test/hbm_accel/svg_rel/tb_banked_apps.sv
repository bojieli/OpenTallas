`timescale 1ns/1ps
module banked_app_case #(parameter SVG=1,PREL=1,W=SVG?135:173,XW=SVG?46:5,TW=62+XW,QW=(W+15)/16)(output reg finished=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cfg_we=0,start_v=0;reg[10:0]cfg_addr=0,start_base=0;reg[255:0]cfg_data=0;
 reg[11:0]start_limit=0;reg[15:0]start_loops=0;reg[XW-1:0]start_ctx=0;
 wire cw0,cw1;wire[9:0]ca;wire[255:0]cd;wire[TW-1:0]rq0,rq1,t0,t1;wire[W-1:0]r0,r1;wire[QW-1:0]ok0,ok1;
 wire[W-1:0]oldapp,newapp;wire ov,nv,oa,na,od,nd,ofault,nfault;
 generate if(SVG)begin:g_svg
 banked_app_reference_svg #(.PREL(PREL)) refapp(.*,.app(oldapp),.app_v(ov),.active(oa),.done(od),.fault(ofault));
 ot_smh_banked_svg_central #(.PREL(PREL)) dut(.*,.cfg0_we(cw0),.cfg1_we(cw1),.bank_cfg_addr(ca),.bank_cfg_data(cd),.request0(rq0),.request1(rq1),.row0(r0),.row1(r1),.ok0(ok0),.ok1(ok1),.token0(t0),.token1(t1),.programme(newapp),.programme_v(nv),.active(na),.done(nd),.fault(nfault),.command_class_observe(),.command_context_valid_observe(),.command_envelope());
 end else begin:g_xc
 banked_app_reference_xc #(.PREL(PREL)) refapp(.*,.app(oldapp),.app_v(ov),.active(oa),.done(od),.fault(ofault));
 ot_smh_banked_xc_central #(.PREL(PREL)) dut(.*,.cfg0_we(cw0),.cfg1_we(cw1),.bank_cfg_addr(ca),.bank_cfg_data(cd),.request0(rq0),.request1(rq1),.row0(r0),.row1(r1),.ok0(ok0),.ok1(ok1),.token0(t0),.token1(t1),.cmd_ext(newapp[108:0]),.kv_desc(newapp[172:109]),.active(na),.done(nd),.fault(nfault),.command_class_observe(),.command_context_valid_observe(),.command_envelope());
 assign nv=0;
 end endgenerate
 ot_smh_calendar_bank_leaf #(.W(W),.XW(XW),.BANK(0)) b0(.clk(clk),.rst_n(rst_n),.cfg_we(cw0),.cfg_addr(ca),.cfg_data(cd),.read_token(rq0),.row(r0),.word_ok(ok0),.row_token(t0));
 ot_smh_calendar_bank_leaf #(.W(W),.XW(XW),.BANK(1)) b1(.clk(clk),.rst_n(rst_n),.cfg_we(cw1),.cfg_addr(ca),.cfg_data(cd),.read_token(rq1),.row(r1),.word_ok(ok1),.row_token(t1));
 reg[W-1:0]aq[0:1];reg vq[0:1],dq[0:1],fq[0:1];integer warm=0,cycle=0,checked=0,completed=0;
 always @(posedge clk)begin #1;cycle=cycle+1;if(cycle>20000)$fatal(1,"APP_FAIL watchdog");
 if(!rst_n)begin warm=0;for(integer j=0;j<2;j=j+1)begin aq[j]=0;vq[j]=0;dq[j]=0;fq[j]=0;end end
 else begin
 if(warm>=12)begin
  if(newapp!==aq[1] || nd!==dq[1] || nfault!==fq[1] || (SVG&&nv!==vq[1]))
   $fatal(1,"APP_FAIL SVG=%0d PREL=%0d cycle=%0d app=%h/%h v=%b/%b done=%b/%b fault=%b/%b",SVG,PREL,cycle,newapp,aq[1],nv,vq[1],nd,dq[1],nfault,fq[1]);
  checked=checked+1;if(nd)completed=completed+1;
 end
 aq[1]=aq[0];vq[1]=vq[0];dq[1]=dq[0];fq[1]=fq[0];aq[0]=oldapp;vq[0]=ov;dq[0]=od;fq[0]=ofault;warm=warm+1;
 end end
 function automatic[255:0]word(input integer a);
 reg[255:0]z;begin z=0;z[255:240]=16'hc7a1;z[234:224]=11'(a);
 if(SVG)begin z[25]=1;z[29]=1;z[22:11]=12'(a);z[9:7]=3'(a);z[6:0]=7'(a);z[39:30]=10'(a);z[83]=1;z[106:101]=6'(a);z[116:107]=10'(a);z[117]=1;z[134:119]=16'hda71;z[118]=1;end
 else begin z[108:101]=8'ha2;z[100:98]=3'(a);z[97:0]=98'(a*1347+573);z[172:109]=64'(a*9173+721);end
 word=z;end endfunction
 task automatic idle(input integer n);repeat(n)@(negedge clk);endtask
 task automatic reset;begin @(negedge clk);rst_n=0;cfg_we=0;start_v=0;idle(4);rst_n=1;idle(14);if(nfault||nd||(SVG&&nv))$fatal(1,"APP_FAIL reset");end endtask
 task automatic run(input integer base,lim,loops,input[XW-1:0]ctx);
 integer target;begin target=completed+1;@(negedge clk);start_base=11'(base);start_limit=12'(lim);start_loops=16'(loops);start_ctx=ctx;start_v=1;@(negedge clk);start_v=0;wait(completed==target);idle(8);end endtask
 initial begin reset();
 for(integer a=0;a<2048;a=a+1)begin @(negedge clk);cfg_we=1;cfg_addr=11'(a);cfg_data=word(a);end
 @(negedge clk);cfg_we=0;idle(8);
 run(1024,1031,1,XW'(43));run(2044,2048,3,{XW{1'b1}});run(1022,1027,5,XW'(64'h2d35ac78e19b));run(0,2048,1,XW'(64'h136b9d725ae3));
 reset();run(1023,1025,4,XW'(43));reset();
 // Actual protected-word fault transition, sticky state and reset clearing.
 @(negedge clk);cfg_we=1;cfg_addr=1024;cfg_data=word(1024);cfg_data[255]=~cfg_data[255];
 @(negedge clk);cfg_we=0;idle(8);run(1024,1025,1,XW'(43));
 if(!ofault||!nfault)$fatal(1,"APP_FAIL fault witness missing");reset();
 $display("BANKED_APP_PROFILE_PASS SVG=%0d PREL=%0d checked=%0d completed=%0d",SVG,PREL,checked,completed);finished=1;end
endmodule
module tb_banked_apps;
 wire[3:0]finished;
 banked_app_case #(.SVG(1),.PREL(1)) svgrel(.finished(finished[0]));
 banked_app_case #(.SVG(1),.PREL(0)) svgabs(.finished(finished[1]));
 banked_app_case #(.SVG(0),.PREL(1)) xcrel(.finished(finished[2]));
 banked_app_case #(.SVG(0),.PREL(0)) xcabs(.finished(finished[3]));
 initial begin wait(&finished);$display("BANKED_APPLICATION PASS profiles=4 calendar_shift=2 R_C_extra=0");$finish;end
endmodule
