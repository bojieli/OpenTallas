// Counter observes ONLY handshakes gated by allow. It includes reserved unsent
// flits and forward flight; only a fresh returned grant (seq>0) discharges debt.
module ot_hbm_credit_source_debt #(parameter integer ENABLE=0)(
 input wire clk,rst_n,cold_link_start,input wire[23:0]link_epoch,
 input wire reserve_fire,grant_fire,input wire[71:0]grant_word,
 output wire allow,output wire debt_zero,output wire fault
);
 import ot_hbm_credit_secded_pkg::*;
 reg[71:0]state_q;reg[1:0]healthy_q;
 wire[65:0]s=decode64(state_q),g=decode64(grant_word);
 wire[23:0]epoch=s[63:40],seq=s[39:16];
 wire[6:0]debt=s[15:9],lastcount=s[7:1];wire seen=s[8],active=s[0];
 wire clean=s[65:64]==0;
 assign fault=healthy_q!=2'b01;
 assign allow=ENABLE!=0&&!fault&&clean&&active&&!cold_link_start;
 assign debt_zero=ENABLE!=0&&!fault&&clean&&debt==0;
 reg[63:0]n;reg bad;reg[7:0]nextdebt;
 always @*begin
  n=s[63:0];bad=0;nextdebt={1'b0,debt};
  if(cold_link_start)begin
   if(active)bad=1;
   else n={link_epoch,24'b0,7'b0,1'b0,7'b0,1'b1};
  end else begin
   if(reserve_fire)begin
    if(!allow)bad=1;else nextdebt=nextdebt+1'b1;
   end
   if(grant_fire)begin
    if(!allow||g[65]||g[63:56]!=8'h47)bad=1;
    else if(g[55:32]!=epoch)begin end
    else if(seen&&g[31:8]==seq)begin if(g[7:0]!={1'b0,lastcount})bad=1;end
    else if(seen&&g[31:8]<seq)begin end
    else if(!seen)begin
     if(g[31:8]!=0||g[7:0]!=64)bad=1;
     else begin n[8]=1;n[7:1]=64;end
    end else if(seq==24'hffffff||g[31:8]!=seq+24'd1||g[7:0]==0||g[7:0]>64||g[7:0]>nextdebt)bad=1;
    else begin nextdebt=nextdebt-g[7:0];n[39:16]=g[31:8];n[7:1]=g[6:0];end
   end
   if(nextdebt>64)bad=1;
   n[15:9]=nextdebt[6:0];
  end
  if(debt>64||lastcount>64)bad=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state_q<=encode64(0);healthy_q<=1;end
  else if(ENABLE!=0&&!fault)begin
   if(s[65])healthy_q<=2;
   else if(s[64])state_q<=encode64(s[63:0]);
   else if(bad)healthy_q<=2;
   else state_q<=encode64(n);
  end
 end
endmodule
