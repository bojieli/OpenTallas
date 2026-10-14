`timescale 1ps/1fs
`default_nettype none
// Per-bank ordered completion station. Native ring mirror_busy counts actual
// WBC acknowledgements only after each destination's xq_done macro commit.
// Preserve source order: ordinary writes never bypass an earlier mirrored write.
module ot_hbm_b2_mirror_commit #(parameter integer MUT=0)(
 input wire clk,rst_n,posted,mirror,local_done,global_busy,
 output reg done,output wire fault
);
 reg [15:0] local_m,local_m_n;reg [3:0] lh,lt,lh_n,lt_n;reg [4:0] ln,ln_n;
 reg [63:0] complete_m,complete_m_n;reg [5:0] ch,ct,ch_n,ct_n;reg [6:0] cn,cn_n;
 reg seen,seen_n,ff;
 wire pop=cn!=0&&(!complete_m[ch]||(MUT==1)||(!global_busy&&seen));
 wire push=local_done&&ln!=0;
 wire [5:0] nln={1'b0,ln}+posted-push;
 wire [7:0] ncn={1'b0,cn}+push-pop;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  local_m<=0;local_m_n<='1;complete_m<=0;complete_m_n<='1;
  lh<=0;lt<=0;lh_n<='1;lt_n<='1;ln<=0;ln_n<='1;
  ch<=0;ct<=0;ch_n<='1;ct_n<='1;cn<=0;cn_n<='1;seen<=0;seen_n<=1;ff<=0;done<=0;
 end else begin
  done<=pop;
  if(local_m!=~local_m_n||complete_m!=~complete_m_n||lh!=~lh_n||lt!=~lt_n||ln!=~ln_n||
    ch!=~ch_n||ct!=~ct_n||cn!=~cn_n||seen!=~seen_n||nln>16||ncn>64||local_done&&ln==0)ff<=1;
  if(posted)begin local_m[lt]<=mirror;local_m_n[lt]<=~mirror;lt<=lt+1'b1;lt_n<=~(lt+1'b1);end
  if(push)begin complete_m[ct]<=local_m[lh];complete_m_n[ct]<=~local_m[lh];ct<=ct+1'b1;ct_n<=~(ct+1'b1);lh<=lh+1'b1;lh_n<=~(lh+1'b1);end
  if(pop)begin ch<=ch+1'b1;ch_n<=~(ch+1'b1);end
  ln<=nln[4:0];ln_n<=~nln[4:0];cn<=ncn[6:0];cn_n<=~ncn[6:0];
  if(global_busy)begin seen<=1;seen_n<=0;end
  else if(ln==0&&cn==0&&!posted&&!local_done)begin seen<=0;seen_n<=1;end
 end
 assign fault=ff;
endmodule
`default_nettype wire
