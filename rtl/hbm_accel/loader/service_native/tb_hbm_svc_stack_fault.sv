`timescale 1ns/1ps
`default_nettype none
// Bench of ot_hbm_svc_stack_fault: (1) legal traffic (each channel pair never issues row commands on the same edge, all
// faults low) -> fault stays 0; (2) each fault source alone (CA pair collision on a random channel, one pc_fault, one
// owner_fault, one svg / share / del / cal fault) -> fault and exactly its status bit rise and stay (sticky).
// MUT=1 (pair rule 2c / 2c+2) must miss the pair collision or flag legal traffic.
module tb_hbm_svc_stack_fault;
 parameter integer MUT=0;
 reg hc=0,sc=0,hr=0,sr=0;always #0.6 hc=~hc;always #0.5 sc=~sc;
 reg[31:0]row_v,pf,of;reg[7:0]sg,sh,dl;reg cl;wire fault;wire[6:0]status;
 ot_hbm_svc_stack_fault #(.MUT(MUT)) dut(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),.row_v(row_v),.pc_fault(pf),
  .owner_fault(of),.svg_fault(sg),.share_fault(sh),.del_fault(dl),.cal_fault(cl),.fault(fault),.status(status));
 integer errors=0,t,c,src;
 task automatic legal(input integer n);integer k,ch;begin
  repeat(n)begin @(negedge hc);row_v=0;for(ch=0;ch<16;ch=ch+1)case($urandom%3)1:row_v[2*ch]=1;2:row_v[2*ch+1]=1;default:;endcase end
  @(negedge hc);row_v=0;end endtask
 initial begin
  for(src=-1;src<7;src=src+1)begin
   hr=0;sr=0;row_v=0;pf=0;of=0;sg=0;sh=0;dl=0;cl=0;#5;hr=1;sr=1;
   legal(200);
   case(src)
    0:begin @(negedge hc);c=$urandom%16;row_v=0;row_v[2*c]=1;row_v[2*c+1]=1;@(negedge hc);row_v=0;end
    1:begin @(negedge hc);pf[$urandom%32]=1;end
    2:begin @(negedge hc);of[$urandom%32]=1;end
    3:begin @(negedge sc);sg[$urandom%8]=1;end
    4:begin @(negedge sc);sh[$urandom%8]=1;end
    5:begin @(negedge sc);dl[$urandom%8]=1;end
    6:begin @(negedge sc);cl=1;end
    default:;
   endcase
   legal(20);pf=0;of=0;sg=0;sh=0;dl=0;cl=0;legal(20);
   if(src<0)begin if(fault||status!=0)begin errors=errors+1;$display("legal traffic flagged status %b",status);end end
   else if(!fault||status!==(7'b1<<src))begin errors=errors+1;$display("source %0d: fault %b status %b",src,fault,status);end
  end
  $display("%s tb_hbm_svc_stack_fault MUT=%0d errors=%0d",errors==0?"PASS":"FAIL",MUT,errors);$finish;
 end
endmodule
`default_nettype wire
