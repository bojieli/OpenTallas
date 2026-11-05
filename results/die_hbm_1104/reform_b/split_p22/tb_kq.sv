`timescale 1ns/1ps
`default_nettype none
// HBM-REFORM-B3 part 22: kport_q ACK_PIPE=1 against the same block with ACK_PIPE=0, one random stimulus. K requests must match edge for edge;
// done / wa exactly DONE_LAG hbm-driven edges later; each sector written once with its data; no fault. MUT 1 = a dropped ack bit: must hang.
module tb_kq;
 parameter integer MUT=0;
 reg s=0,h=0;reg rst=0;always #5 s=~s;always #4 h=~h;
 reg rv=0,rb=0,fb=0,fs=0;reg[15:0]re=0,fe=0;reg[11:0]rt=0;reg[31:0]rbase=0;reg[2311:0]wd=0;
 wire [1:0] sm=0;
 wire[15:0]v0,v1;wire[479:0]a0,a1;wire[4095:0]d0,d1;reg[15:0]rdy=0;reg[15:0]dn0=0,dn1=0;
 wire rd0,rd1,bv0,bv1,f0,f1;wire[11:0]wa0,wa1,bt0,bt1;wire[29:0]bb0,bb1;
 ot_hbm_svc_wb_kport_q_ref u_ref(.stream_clk(s),.stream_rst_n(rst),.hbm_clk(h),.hbm_rst_n(rst),.stream_fifo_clk({4{s}}),.stk(2'd0),.quad(1'b0),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),.wb_reserve_base(rbase),
  .wb_fill_start(fs),.wd(wd),.wb_ready(rd0),.wa(wa0),.wbw_v(bv0),.wbw_base(bb0),.wbw_total(bt0),.w_k_v(v0),.w_k_rdy(rdy),.w_k_addr(a0),.w_k_wdata(d0),.w_k_wr_done(dn0),.fault(f0));
 integer cnt1=0;wire [15:0] dn1m=(MUT==1&&cnt1>=7&&cnt1<40)?(dn1&~16'h1):dn1;
 ot_hbm_svc_wb_kport_q u_new(.stream_clk(s),.stream_rst_n(rst),.hbm_clk(h),.hbm_rst_n(rst),.stream_fifo_clk({4{s}}),.stk(2'd0),.quad(1'b0),
  .wb_reserve_v(rv),.wb_reserve_bank(rb),.wb_fill_bank(fb),.wb_reserve_epoch(re),.wb_fill_epoch(fe),.wb_reserve_sectors(rt),.wb_reserve_base(rbase),
  .wb_fill_start(fs),.wd(wd),.wb_ready(rd1),.wa(wa1),.wbw_v(bv1),.wbw_base(bb1),.wbw_total(bt1),.w_k_v(v1),.w_k_rdy(rdy),.w_k_addr(a1),.w_k_wdata(d1),.w_k_wr_done(dn1m),.fault(f1));
 // write-done model: a random delay of each accepted write, separately per dut but same seed-free delay
 integer q0[0:15],q1[0:15];integer p;integer kbad=0,w0=0,w1=0,doneref=0,donenew=0,ackedn=0;integer seen[0:8191];integer i;
 always @(posedge h)begin
  rdy<=$urandom;
  dn0=0;dn1=0;
  for(p=0;p<16;p=p+1)begin
   if(v0[p]!==v1[p]||(v0[p]&&(a0[30*p+:30]!==a1[30*p+:30]||d0[256*p+:256]!==d1[256*p+:256])))kbad=kbad+1;
   if(v1[p]&&rdy[p])begin w1=w1+1;q1[p]=q1[p]+1;end
   if(v0[p]&&rdy[p])begin w0=w0+1;q0[p]=q0[p]+1;end
  end
  for(p=0;p<16;p=p+1)if($urandom%4==0)begin
   if(q0[p]>0)begin dn0[p]=1;q0[p]=q0[p]-1;end
   if(q1[p]>0)begin dn1[p]=1;q1[p]=q1[p]-1;cnt1=cnt1+1;end
  end
 end
 always @(posedge s)begin if(wa0!=0)doneref=doneref+1;if(wa1!=0)donenew=donenew+1;end
 // stream side
 task automatic fill(input bit b,input [15:0]e,input [28:0]base,input [11:0]tot);
  integer o,k;reg[256:0] x;
  begin
   wait(rd0===1'b0||1);
   @(negedge s);rv=1;rb=b;re=e;rt=tot;rbase={3'b0,base};@(negedge s);rv=0;
   repeat(6)@(negedge s);
   fb=b;fe=e;@(negedge s);fs=1;@(negedge s);fs=0;
   for(o=0;o<tot;o=o+8)begin
    wd=0;
    for(k=0;k<8;k=k+1)if(o+k<tot)begin
     wd[289*k+:256]={8{$urandom}};
     wd[289*k+256+:32]={3'b0,base}+o+k;
     wd[289*k+288]=1;
    end
    @(negedge s);
   end
   wd=0;
  end
 endtask
 initial begin
  for(i=0;i<16;i=i+1)begin q0[i]=0;q1[i]=0;end
  repeat(10)@(negedge s);rst=1;repeat(40)@(negedge s);
  fill(0,16'h11,29'h1000,12'd256);repeat(3000)@(negedge s);
  fill(1,16'h22,29'h2020,12'd77);repeat(3000)@(negedge s);
  fill(0,16'h33,29'h9000,12'd640);repeat(6000)@(negedge s);
  $display("KQ writes ref %0d new %0d kbad %0d done ref %0d new %0d fault %b %b",w0,w1,kbad,doneref,donenew,f0,f1);
  if(kbad==0&&w0==973&&w1==973&&doneref==3&&donenew==3&&f0===1'b0&&f1===1'b0)$display("KQ PASS");else $display("KQ FAIL");
  $finish;
 end
endmodule
`default_nettype wire
