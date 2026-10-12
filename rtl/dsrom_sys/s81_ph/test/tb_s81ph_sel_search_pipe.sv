`timescale 1ns/1ps
// Smallest full-shape threshold mechanism: static histograms, a different quota
// every edge, independent group-return paths, and exact +7-edge comparison.
module tb_s81ph_sel_search_pipe #(parameter integer QW=21);
 localparam Q=4,CB=11,GW=15,XR=4;
 reg clk=0; always #1 clk=~clk;
 reg [Q*16*GW-1:0] gs;
 reg [Q*16*CB-1:0] bs0,bs1;
 reg [QW-1:0] q;
 reg [CB-1:0] bins [0:Q-1][0:255];
 wire [3:0] g0,g1;
 wire [7:0] b0,b1; wire [20:0] a0,a1;wire ok0,ok1;wire [43:0] eq0,eq1;
 ot_s81ph_native_sel_su #(.QW(QW),.XR(XR)) ref_s(.clk(clk),.gs(gs),.bs(bs0),.q(q),.g_out(g0),.res_b(b0),.res_above(a0),.res_ok(ok0),.res_eq(eq0));
 ot_s81ph_sel_su_pipe #(.QW(QW),.XR(XR)) dut_s(.clk(clk),.gs(gs),.bs(bs1),.q(q),.g_out(g1),.res_b(b1),.res_above(a1),.res_ok(ok1),.res_eq(eq1));
 reg [3:0] gd0[0:XR],gd1[0:XR];
 reg [29:0] expect_d[0:6];
 integer cyc=0,errors=0,checks=0,phase=0;
 always @(posedge clk) begin
  gd0[0]<=g0;gd1[0]<=g1;
  for(integer i=1;i<=XR;i=i+1) begin gd0[i]<=gd0[i-1];gd1[i]<=gd1[i-1];end
  for(integer s=0;s<Q;s=s+1) for(integer i=0;i<16;i=i+1) begin
   bs0[CB*(16*s+i)+:CB]<=bins[s][16*gd0[XR]+i];
   bs1[CB*(16*s+i)+:CB]<=bins[s][16*gd1[XR]+i];
  end
  expect_d[0]<={ok0,a0,b0};for(integer i=1;i<7;i=i+1) expect_d[i]<=expect_d[i-1];
  if (phase>90) begin
   checks<=checks+1;
   if ({ok1,a1,b1} !== expect_d[6]) begin
    if(errors<10) $display("SEARCH MISMATCH cyc=%0d got=%h expected=%h",cyc,{ok1,a1,b1},expect_d[6]);
    errors<=errors+1;
   end
  end
  cyc<=cyc+1;
 end
 initial begin
  q=0;gs=0;bs0=0;bs1=0;
  for(integer test=0;test<12;test=test+1) begin
   @(negedge clk); phase=0;
   for(integer s=0;s<Q;s=s+1) for(integer i=0;i<256;i=i+1) bins[s][i]=(test==0)?0:(test==1)?2047:$urandom%32;
   for(integer s=0;s<Q;s=s+1) for(integer g=0;g<16;g=g+1) begin
    integer sum;sum=0;for(integer i=0;i<16;i=i+1) sum=sum+bins[s][16*g+i];gs[GW*(16*s+g)+:GW]=sum;
   end
   for(integer t=0;t<260;t=t+1) begin
    @(negedge clk);phase=t;
    case(t%8) 0:q=0;1:q=1;2:q=512;3:q={QW{1'b1}};default:q=$urandom%15000;endcase
   end
  end
  @(negedge clk);
  $display("SEARCH_PIPE %s checks=%0d errors=%0d QW=%0d",errors==0?"PASS":"FAIL",checks,errors,QW);
  if(errors) $fatal(1,"search alignment");$finish;
 end
endmodule
