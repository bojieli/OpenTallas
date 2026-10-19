`timescale 1ns/1ps
`default_nettype none
// RTL-BUILD-HBM/stk 2026-10-18: LOCKSTEP of the d4g per-quadrant stack fault (ot_hbm_svc_stack_fault NPC 16 / NG 4 /
// ND 8, OWN_W 6 as the die) against today's per-stack master (NPC 32 / NG 8 / ND 8) on the quadrant's own inputs.
// Two quadrant instances W (PCs 0..15, svg/vmks 0..3) and E (PCs 16..31, svg/vmks 4..7), each with its own 8 delivery
// lanes and fill calendar.  Reference per quadrant = the GEN0 master fed the quadrant's inputs at their stack positions
// (W: PCs 0..15 / groups 0..3, E: PCs 16..31 / groups 4..7; its 8 del lanes and cal) and zeros elsewhere.
// Stimulus: per epoch a reset, legal row traffic (no channel pair (2c, 2c+1) on the same edge) on all 32 PCs, then a
// random set of fault events (CA pair collision on a random channel, pc / owner class, svg / share / del / cal) on random
// positions of both halves at random edges; outputs fault and status[6:0] compared on EVERY stream edge.
// MUT (quadrant instances only): 1 = pair rule (2c, 2c+2).  A sed mutant (run script) drops the share sticky.
module tb_hbm_svc_stack_fault_q;
 parameter integer MUT=0;
 parameter integer EPOCHS=120;
 reg hc=0,sc=0,hr=0,sr=0;always #0.6 hc=~hc;always #0.5 sc=~sc;
 reg[31:0]row_v,pf;reg[191:0]of;reg[7:0]sg,sh,dlw,dle;reg clw,cle;
 wire fw,fe,frw,fre;wire[6:0]stw,ste,strw,stre;
 ot_hbm_svc_stack_fault #(.MUT(MUT),.OWN_W(6),.NPC(16),.NG(4),.ND(8)) q_w(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),
  .row_v(row_v[15:0]),.pc_fault(pf[15:0]),.owner_fault(of[95:0]),.svg_fault(sg[3:0]),.share_fault(sh[3:0]),.del_fault(dlw),.cal_fault(clw),
  .fault(fw),.status(stw));
 ot_hbm_svc_stack_fault #(.MUT(MUT),.OWN_W(6),.NPC(16),.NG(4),.ND(8)) q_e(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),
  .row_v(row_v[31:16]),.pc_fault(pf[31:16]),.owner_fault(of[191:96]),.svg_fault(sg[7:4]),.share_fault(sh[7:4]),.del_fault(dle),.cal_fault(cle),
  .fault(fe),.status(ste));
 ot_hbm_svc_stack_fault #(.MUT(0),.OWN_W(6)) m_w(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),
  .row_v({16'd0,row_v[15:0]}),.pc_fault({16'd0,pf[15:0]}),.owner_fault({96'd0,of[95:0]}),.svg_fault({4'd0,sg[3:0]}),.share_fault({4'd0,sh[3:0]}),
  .del_fault(dlw),.cal_fault(clw),.fault(frw),.status(strw));
 ot_hbm_svc_stack_fault #(.MUT(0),.OWN_W(6)) m_e(.hbm_clk(hc),.hbm_rst_n(hr),.stream_clk(sc),.stream_rst_n(sr),
  .row_v({row_v[31:16],16'd0}),.pc_fault({pf[31:16],16'd0}),.owner_fault({of[191:96],96'd0}),.svg_fault({sg[7:4],4'd0}),.share_fault({sh[7:4],4'd0}),
  .del_fault(dle),.cal_fault(cle),.fault(fre),.status(stre));
 integer errors=0,checks=0,raised=0,ep,n,ev,c;reg[6:0]seen;
 always @(negedge sc) if(sr) begin
  checks=checks+1;
  if({fw,stw}!=={frw,strw}||{fe,ste}!=={fre,stre})begin
   errors=errors+1;if(errors<10)$display("STACK_FAULT_Q_MISMATCH epoch %0d W %b/%b ref %b/%b  E %b/%b ref %b/%b",ep,fw,stw,frw,strw,fe,ste,fre,stre);
  end
 end
 task automatic legal(input integer k);integer ch;begin
  repeat(k)begin @(negedge hc);row_v=0;for(ch=0;ch<16;ch=ch+1)case($urandom%3)1:row_v[2*ch]=1;2:row_v[2*ch+1]=1;default:;endcase end
  @(negedge hc);row_v=0;end endtask
 initial begin
  seen=0;
  for(ep=0;ep<EPOCHS;ep=ep+1)begin
   hr=0;sr=0;row_v=0;pf=0;of=0;sg=0;sh=0;dlw=0;dle=0;clw=0;cle=0;#5;hr=1;sr=1;
   legal(50+$urandom%50);
   n=(ep<8)?1:$urandom%4;          // first epochs: one class each (both halves)
   for(ev=0;ev<n;ev=ev+1)begin
    c=(ep<8)?(ep%7):$urandom%7;
    case(c)
     0:begin @(negedge hc);c=$urandom%16;row_v=0;row_v[2*c]=1;row_v[2*c+1]=1;@(negedge hc);row_v=0;seen[0]=1;end
     1:begin @(negedge hc);pf[$urandom%32]=1;seen[1]=1;end
     2:begin @(negedge hc);of[$urandom%192]=1;seen[2]=1;end
     3:begin @(negedge sc);sg[$urandom%8]=1;seen[3]=1;end
     4:begin @(negedge sc);sh[$urandom%8]=1;seen[4]=1;end
     5:begin @(negedge sc);if($urandom%2)dlw[$urandom%8]=1;else dle[$urandom%8]=1;seen[5]=1;end
     default:begin @(negedge sc);if($urandom%2)clw=1;else cle=1;seen[6]=1;end
    endcase
    legal(5+$urandom%20);
    // also legal traffic that collides only under the 2c/2c+2 rule (catches MUT 1)
    @(negedge hc);row_v=0;c=$urandom%8;row_v[2*c]=1;row_v[(2*c+2)%16]=1;@(negedge hc);row_v=0;
    @(negedge hc);row_v=0;c=8+$urandom%8;row_v[2*c]=1;row_v[16+((2*c+2)%16)]=1;@(negedge hc);row_v=0;
   end
   legal(10);pf=0;of=0;sg=0;sh=0;dlw=0;dle=0;clw=0;cle=0;legal(20);
   if(fw||fe)raised=raised+1;
  end
  if(seen!=7'h7f||raised<EPOCHS/3||checks<EPOCHS*50)begin errors=errors+1;$display("STACK_FAULT_Q_VACUOUS classes %b raised %0d checks %0d",seen,raised,checks);end
  if(errors==0)$display("STACK_FAULT_Q PASS epochs=%0d checks=%0d raised_epochs=%0d classes=%b MUT=%0d",EPOCHS,checks,raised,seen,MUT);
  else $fatal(1,"STACK_FAULT_Q FAIL errors=%0d MUT=%0d",errors,MUT);
  $finish;
 end
endmodule
`default_nettype wire
