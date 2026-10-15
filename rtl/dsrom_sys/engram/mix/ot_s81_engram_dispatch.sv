`timescale 1ns/1ps
// Engine10 lookup/MIX command transport. Descriptor arg[23] (c_cmd[30])
// selects MIX; the selector is cleared before either real endpoint. Lookup
// keeps arg[15:0]=window sequence; MIX keeps arg[13:0]=descriptor row.
// Completion service is a fixed alternating calendar, NOT ready arbitration:
// phase0 lookup, phase1 MIX, even if the selected queue is empty. Compiler
// prices these slots and all transport stages. Eight pending completions per
// lane bound the engine's eight globally admitted descriptors; overflow faults.
module ot_s81_engram_dispatch #(parameter integer MUT=0)(
 input wire [0:0] ck,rst,input wire [84:0] c_cmd,
 output reg [8:0] c_done,output reg [1:0] c_st,
 output reg [84:0] t_lk_cmd,t_mix_cmd,
 input wire [8:0] f_lk_done,f_mix_done,input wire [1:0] f_lk_st,f_mix_st);
 wire rn;ot_s81_engram_reset reset_leaf(ck[0],rst[0],rn);
 reg [84:0] cmdq;reg [8:0] ldq,mdq;reg [1:0] lsq,msq;
 always @(posedge ck[0] or negedge rn)if(!rn)begin cmdq<=0;ldq<=0;mdq<=0;lsq<=0;msq<=0;end
 else begin cmdq<=c_cmd;ldq<=f_lk_done;mdq<=f_mix_done;lsq<=f_lk_st;msq<=f_mix_st;end
 reg phase,fault;reg [7:0] lq[0:7],mq[0:7];reg [2:0] lrp,lwp,mrp,mwp;reg [3:0] ln,mn;
 wire lp=!phase&&ln!=0,mp=phase&&mn!=0;
 wire lw=ldq[8]&&(ln<8||lp),mw=mdq[8]&&(mn<8||mp);
 always @(posedge ck[0] or negedge rn)if(!rn)begin
  phase<=0;fault<=0;lrp<=0;lwp<=0;mrp<=0;mwp<=0;ln<=0;mn<=0;
  c_done<=0;c_st<=0;t_lk_cmd<=0;t_mix_cmd<=0;
 end else begin
  phase<=!phase;
  t_lk_cmd<=0;t_mix_cmd<=0;
  if(cmdq[84])begin
   if(cmdq[30])begin t_mix_cmd<=cmdq;t_mix_cmd[30]<=0;end
   else begin t_lk_cmd<=cmdq;t_lk_cmd[30]<=0;end
  end
  c_done<=0;
  if(lp)begin c_done<={1'b1,lq[lrp]};lrp<=lrp+1;end
  if(mp)begin c_done<={1'b1,mq[mrp]};mrp<=mrp+1;end
  if(lw)begin lq[lwp]<=ldq[7:0];lwp<=lwp+1;end
  if(mw)begin mq[mwp]<=mdq[7:0]^((MUT==1)?8'd1:8'd0);mwp<=mwp+1;end
  case({lw,lp})2'b10:ln<=ln+1;2'b01:ln<=ln-1;default:;endcase
  case({mw,mp})2'b10:mn<=mn+1;2'b01:mn<=mn-1;default:;endcase
  if((ldq[8]&&!lw)||(mdq[8]&&!mw))fault<=1;
  c_st<={lsq[1]&&msq[1],lsq[0]||msq[0]||fault};
 end
endmodule
