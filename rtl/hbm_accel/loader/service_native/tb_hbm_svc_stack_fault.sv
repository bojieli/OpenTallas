`timescale 1ns/1ps
`default_nettype none
// Bench of ot_hbm_svc_stack_fault: (1) legal traffic (each channel pair never issues row commands on the same edge, all
// faults low) -> fault stays 0; (2) each fault source alone (CA pair collision on a random channel, one pc_fault, one
// owner_fault, one svg / share / del / cal fault) -> fault and exactly its status bit rise and stay (sticky).
// MUT=1 (pair rule 2c / 2c+2) must miss the pair collision or flag legal traffic; MUT=2 (owner crossing dropped) must miss
// the owner fault.
// HBM-KITS-B/SFAULT 10-18: NPC / NG / ND parameters (default 32 / 8 / 8 = the original bench); the d4g kit runs NPC 16,
// NG 4, ND 8, OWN_W 6 (port_bind sfault_<q>).
module tb_hbm_svc_stack_fault;
 parameter integer MUT=0;
 parameter integer OWN_W=6;   // HBMA-SVC 10-17: the d4f die binding (H8 owner_fault_split[5:0] per controller)
 parameter integer NPC=32,NG=8,ND=8;
 reg hc=0,sc=0,hr=0,sr=0;always #0.6 hc=~hc;always #0.5 sc=~sc;
 reg[NPC-1:0]row_v,pf;reg[NPC*OWN_W-1:0]of;reg[NG-1:0]sg,sh;reg[ND-1:0]dl;reg cl;wire fault;wire[6:0]status;
 ot_hbm_svc_stack_fault #(.MUT(MUT),.OWN_W(OWN_W),.NPC(NPC),.NG(NG),.ND(ND)) dut(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),.row_v(row_v),.pc_fault(pf),
  .owner_fault(of),.svg_fault(sg),.share_fault(sh),.del_fault(dl),.cal_fault(cl),.fault(fault),.status(status));
 integer errors=0,t,c,src;
 task automatic legal(input integer n);integer k,ch;begin
  repeat(n)begin @(negedge hc);row_v=0;for(ch=0;ch<NPC/2;ch=ch+1)case($urandom%3)1:row_v[2*ch]=1;2:row_v[2*ch+1]=1;default:;endcase end
  @(negedge hc);row_v=0;end endtask
 initial begin
  for(src=-1;src<7;src=src+1)begin
   hr=0;sr=0;row_v=0;pf=0;of=0;sg=0;sh=0;dl=0;cl=0;#5;hr=1;sr=1;
   legal(200);
   case(src)
    0:begin @(negedge hc);c=$urandom%(NPC/2);row_v=0;row_v[2*c]=1;row_v[2*c+1]=1;@(negedge hc);row_v=0;end
    1:begin @(negedge hc);pf[$urandom%NPC]=1;end
    2:begin @(negedge hc);of[$urandom%(NPC*OWN_W)]=1;end
    3:begin @(negedge sc);sg[$urandom%NG]=1;end
    4:begin @(negedge sc);sh[$urandom%NG]=1;end
    5:begin @(negedge sc);dl[$urandom%ND]=1;end
    6:begin @(negedge sc);cl=1;end
    default:;
   endcase
   legal(20);pf=0;of=0;sg=0;sh=0;dl=0;cl=0;legal(20);
   if(src<0)begin if(fault||status!=0)begin errors=errors+1;$display("legal traffic flagged status %b",status);end end
   else if(!fault||status!==(7'b1<<src))begin errors=errors+1;$display("source %0d: fault %b status %b",src,fault,status);end
  end
  $display("%s tb_hbm_svc_stack_fault MUT=%0d OWN_W=%0d NPC=%0d NG=%0d ND=%0d errors=%0d checks=8",errors==0?"PASS":"FAIL",MUT,OWN_W,NPC,NG,ND,errors);$finish;
 end
endmodule
`default_nettype wire
